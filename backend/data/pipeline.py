"""
EstimIA — Pipeline de données
Département : Paris (75)

Étapes :
  1. Téléchargement DVF (transactions foncières)
  2. Téléchargement DPE (diagnostics énergétiques)
  3. Enrichissement Géorisques (par commune INSEE)
  4. Enrichissement Délinquance (par commune INSEE)
  5. Nettoyage & fusion → dataset_propre.csv

Usage :
  python pipeline.py
  python pipeline.py --dept 92        # autre département
  python pipeline.py --skip-download  # si fichiers déjà téléchargés
"""

import argparse
import io
import openpyxl 
import json
import logging
import os
import time
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "raw"
OUTPUT_DIR = Path(__file__).parent / "processed"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

DEPT = "75"


def get_raw_file_path(filename: str) -> Path:
    """
    Recherche un fichier de données brutes.
    1. Dans backend/data/raw/
    2. En fallback, dans le dossier racine data/raw/
    """
    local_path = (Path(__file__).parent / "raw" / filename).resolve()
    if local_path.exists():
        return local_path
    
    root_path = (Path(__file__).parents[2] / "data" / "raw" / filename).resolve()
    if root_path.exists():
        return root_path
        
    return local_path

# DVF — fichiers annuels sur data.gouv.fr (format CSV)
DVF_URL = (
    "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dept}.csv.gz"
)

# DPE Logements existants — data.ademe.fr (export CSV complet)
DPE_URL = (
    "https://data.ademe.fr/data-fair/api/v1/datasets/"
    "dpe-v2-logements-existants-bdnb/lines"
    "?size=10000&q_fields=code_insee_commune_actualise&q={dept_star}"
    "&select=numero_dpe,code_insee_commune_actualise,"
    "etiquette_dpe,date_etablissement_dpe"
    "&format=csv"
)

# Géorisques — API par commune (appel unitaire par code INSEE)
GEORISQUES_URL = "https://georisques.gouv.fr/api/v1/gaspar/risques?code_insee={insee}"

# Délinquance — Interstats data.gouv.fr (taux pour 1000 habitants par département)
DELINQUANCE_URL = (
    "https://www.data.gouv.fr/fr/datasets/r/"
    "5d9b8b1f-9ac5-4d54-8419-b0e6b9fc68d7"
)

# ---------------------------------------------------------------------------
# 1. Téléchargement DVF
# ---------------------------------------------------------------------------

def download_dvf(dept: str, year: int, skip: bool = False) -> Path | None:
    dest = DATA_DIR / f"dvf_{dept}_{year}.csv.gz"
    if skip and dest.exists():
        log.info(f"DVF {dept} {year} déjà présent, skip téléchargement")
        return dest

    url = DVF_URL.format(year=year, dept=dept)
    log.info(f"Téléchargement DVF {dept} {year} → {dest.name}")
    log.info(f"  URL : {url}")

    try:
        r = requests.get(url, stream=True, timeout=120)
        if r.status_code == 404:
            log.warning(f"  Année {year} non disponible pour le département {dept} (404 Not Found).")
            return None
        r.raise_for_status()
    except Exception as e:
        log.warning(f"  Erreur lors du téléchargement pour {year} : {e}")
        return None

    total = int(r.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r  {pct:.0f}% ({downloaded/1e6:.1f} MB)", end="", flush=True)
    print()
    log.info(f"  Téléchargé : {downloaded/1e6:.1f} MB")
    return dest


def load_dvf(path: Path, dept: str) -> pd.DataFrame:
    log.info("Chargement DVF en mémoire…")

    # Colonnes utiles uniquement (allège la RAM)
    usecols = [
        "id_mutation",
        "date_mutation",
        "nature_mutation",
        "valeur_fonciere",
        "code_postal",
        "code_commune",
        "nom_commune",
        "code_departement",
        "type_local",
        "surface_reelle_bati",
        "nombre_pieces_principales",
        "longitude",
        "latitude",
    ]

    df = pd.read_csv(
        path,
        compression="gzip",
        usecols=lambda c: c in usecols,
        low_memory=False,
        dtype={"code_commune": str, "code_departement": str, "code_postal": str},
    )

    log.info(f"  {len(df):,} lignes brutes chargées")
    return df


# ---------------------------------------------------------------------------
# 2. Nettoyage DVF
# ---------------------------------------------------------------------------

def clean_dvf(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Nettoyage DVF…")
    initial = len(df)

    # Garder uniquement ventes (pas échanges, expropiations…)
    df = df[df["nature_mutation"] == "Vente"].copy()
    log.info(f"  Après filtre 'Vente' : {len(df):,} lignes")

    # Garder uniquement appartements et maisons
    df = df[df["type_local"].isin(["Appartement", "Maison"])].copy()
    log.info(f"  Après filtre type local : {len(df):,} lignes")

    # Supprimer lignes sans coordonnées GPS
    df = df.dropna(subset=["latitude", "longitude"])
    log.info(f"  Après filtre GPS : {len(df):,} lignes")

    # Supprimer lignes sans prix ou surface
    df = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
    log.info(f"  Après filtre prix+surface : {len(df):,} lignes")

    # Supprimer valeurs aberrantes : prix < 10 000 € ou > 20 M€
    df = df[(df["valeur_fonciere"] >= 10_000) & (df["valeur_fonciere"] <= 20_000_000)]

    # Supprimer surfaces aberrantes : < 5 m² ou > 1 000 m²
    df = df[(df["surface_reelle_bati"] >= 5) & (df["surface_reelle_bati"] <= 1_000)]

    # Calculer le prix au m²
    df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]

    # Supprimer prix/m² aberrants (< 500 ou > 50 000 €/m²)
    df = df[(df["prix_m2"] >= 500) & (df["prix_m2"] <= 50_000)]

    # Formater la date
    df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
    df["annee"] = df["date_mutation"].dt.year

    # Code INSEE = code_commune (5 chiffres)
    df["code_insee"] = df["code_commune"].str.zfill(5)

    # Formater le code postal (chaîne de 5 caractères sans décimale)
    if "code_postal" in df.columns:
        df["code_postal"] = df["code_postal"].astype(str).str.replace(r'\.0$', '', regex=True)
        df["code_postal"] = df["code_postal"].apply(lambda x: x.zfill(5) if x not in ['nan', 'None', ''] else '')

    # Renommer pour clarté
    df = df.rename(columns={
        "valeur_fonciere": "prix",
        "surface_reelle_bati": "surface_m2",
        "nombre_pieces_principales": "nb_pieces",
        "type_local": "type_bien",
    })

    log.info(f"  Lignes conservées : {len(df):,} / {initial:,} ({len(df)/initial*100:.1f}%)")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Téléchargement & intégration DPE
# ---------------------------------------------------------------------------

def load_dpe(dept: str, skip: bool = False) -> pd.DataFrame:
    dest = get_raw_file_path(f"dpe_{dept}.csv")

    if not dest.exists():
        log.warning("  Fichier DPE absent — poursuite sans données DPE")
        log.warning(f"  → Placez le fichier CSV dans {DATA_DIR}/dpe_{dept}.csv")
        return pd.DataFrame(columns=["code_insee", "score_dpe_median"])

    log.info("Chargement DPE depuis fichier local…")
    try:
        df = pd.read_csv(
            dest,
            usecols=["etiquette_dpe", "code_insee_ban"],
            dtype={"code_insee_ban": str},
            low_memory=False,
        )

        df = df.rename(columns={"code_insee_ban": "code_insee"})
        df = df.dropna(subset=["etiquette_dpe", "code_insee"])

        dpe_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
        df["score_dpe"] = df["etiquette_dpe"].str.upper().map(dpe_map)
        df = df.dropna(subset=["score_dpe"])

        agg = (
            df.groupby("code_insee")["score_dpe"]
            .median()
            .reset_index()
            .rename(columns={"score_dpe": "score_dpe_median"})
        )

        log.info(f"  {len(df):,} DPE chargés, agrégés sur {len(agg)} communes")
        return agg

    except Exception as e:
        log.warning(f"  Erreur lecture DPE : {e}")
        return pd.DataFrame(columns=["code_insee", "score_dpe_median"])


# ---------------------------------------------------------------------------
# 4. Enrichissement Géorisques (API par commune)
# ---------------------------------------------------------------------------

def fetch_georisques(codes_insee: list[str]) -> pd.DataFrame:
    """
    Interroge l'API Géorisques pour chaque code INSEE unique de manière parallélisée.
    Retourne un DataFrame code_insee → score_risque (0–10).
    """
    import concurrent.futures
    dest = DATA_DIR / "georisques_cache.json"

    # Charger le cache si existant (et filtrer les anciennes valeurs à 0.0/None erronées dues au bug précédent)
    cache: dict = {}
    if dest.exists():
        try:
            with open(dest) as f:
                raw_cache = json.load(f)
                cache = {k: v for k, v in raw_cache.items() if v is not None and v != 0.0}
        except Exception as e:
            log.warning(f"Erreur chargement cache géorisques : {e}")

    results = []
    codes_uniques = list(set(codes_insee))
    nouveaux = [c for c in codes_uniques if c not in cache]

    log.info(f"Géorisques : {len(codes_uniques)} communes ({len(nouveaux)} à fetcher)")

    def fetch_single(insee: str) -> tuple[str, float | None]:
        try:
            insee_query = "75056" if insee.startswith("751") else insee
            r = requests.get(
                GEORISQUES_URL.format(insee=insee_query),
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()

            results_list = data.get("data", [])
            nb_risques = 0
            if isinstance(results_list, list) and len(results_list) > 0:
                risques_detail = results_list[0].get("risques_detail", [])
                if isinstance(risques_detail, list):
                    nb_risques = len(risques_detail)

            score = min(round(nb_risques / 8 * 10, 1), 10.0)
            return insee, score
        except Exception:
            return insee, None

    if nouveaux:
        # Utiliser ThreadPoolExecutor avec 15 workers pour paralléliser les appels d'API
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_insee = {executor.submit(fetch_single, ins): ins for ins in nouveaux}
            
            count = 0
            for future in concurrent.futures.as_completed(future_to_insee):
                insee, score = future.result()
                cache[insee] = score
                count += 1
                
                # Sauvegarder le cache régulièrement
                if count % 50 == 0 or count == len(nouveaux):
                    try:
                        with open(dest, "w") as f:
                            json.dump(cache, f)
                    except Exception as e:
                        log.warning(f"Erreur lors de l'écriture du cache géorisques : {e}")
                    log.info(f"  Géorisques : {count}/{len(nouveaux)} communes traitées en parallèle")

    # Sauvegarde finale
    try:
        with open(dest, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        log.warning(f"Erreur lors de l'écriture finale du cache géorisques : {e}")

    # Construire le DataFrame depuis le cache complet
    for code in codes_uniques:
        results.append({"code_insee": code, "score_georisques": cache.get(code)})

    df = pd.DataFrame(results)
    log.info(f"  Géorisques : {df['score_georisques'].notna().sum()} communes enrichies")
    return df


# ---------------------------------------------------------------------------
# 5. Délinquance (par département)
# ---------------------------------------------------------------------------

def load_delinquance(dept: str, skip: bool = False) -> pd.DataFrame:
    # 1. Rechercher d'abord le fichier CSV officiel (données propres et récentes)
    csv_dest = get_raw_file_path("donnee-dep-data.gouv-2025-geographie2025-produit-le2026-01-22.csv")
    if csv_dest.exists():
        log.info("Chargement délinquance depuis le fichier CSV officiel…")
        try:
            df = pd.read_csv(csv_dest, sep=";", dtype=str)
            df['taux_pour_mille'] = df['taux_pour_mille'].astype(str).str.replace(',', '.').astype(float)
            
            # Nettoyer et filtrer pour le département demandé
            dept_clean = dept.lstrip("0")
            df['Code_departement_clean'] = df['Code_departement'].astype(str).str.lstrip("0").str.strip()
            
            df_dept = df[df['Code_departement_clean'] == dept_clean]
            if not df_dept.empty:
                # Prendre le taux moyen pour l'année la plus récente disponible
                annee_max = df_dept['annee'].astype(int).max()
                df_rec = df_dept[df_dept['annee'].astype(int) == annee_max]
                mean_taux = df_rec['taux_pour_mille'].mean()
                
                # Normaliser le score sur 10 (taux moyen / 30 * 10)
                score = min(round(mean_taux / 30 * 10, 1), 10.0)
                log.info(f"  Score délinquance département {dept} (taux moyen {mean_taux:.2f} en {annee_max}) : {score}/10")
                return pd.DataFrame([{"departement": dept, "score_delinquance": score}])
        except Exception as e:
            log.warning(f"  Erreur lecture CSV délinquance : {e}")

    # 2. Fallback sur l'Excel local si disponible
    dest = get_raw_file_path("delinquance.xlsx")
    if dest.exists():
        log.info("Chargement délinquance depuis fichier Excel local…")
        try:
            # On tente de charger l'une des feuilles contenant des données réelles
            df = pd.read_excel(dest, sheet_name='Services PN 2021', dtype=str)
            
            dept_col = next((c for c in df.columns if "dep" in c.lower()), None)
            if not dept_col:
                raise ValueError(f"Colonne département introuvable")

            df[dept_col] = df[dept_col].astype(str).str.lstrip("0").str.strip()
            dept_clean = dept.lstrip("0")

            row = df[df[dept_col] == dept_clean]
            if row.empty:
                raise ValueError(f"Département {dept} introuvable")

            num_cols = []
            for c in df.columns:
                if c == dept_col:
                    continue
                val = str(row[c].iloc[0]).replace(",", "").replace(".", "").strip()
                if val.isdigit():
                    num_cols.append(c)

            if num_cols:
                taux = float(str(row[num_cols[-1]].iloc[0]).replace(",", "."))
                score = min(round(taux / 30 * 10, 1), 10.0)
            else:
                score = 5.0
            
            log.info(f"  Score délinquance département {dept} : {score}/10")
            return pd.DataFrame([{"departement": dept, "score_delinquance": score}])

        except Exception as e:
            log.warning(f"  Erreur lecture Excel délinquance : {e} — score=5.0")
            score = 5.0

    log.warning("  Fichiers délinquance absents — score=5.0 par défaut")
    return pd.DataFrame([{"departement": dept, "score_delinquance": 5.0}])


# ---------------------------------------------------------------------------
# 6. Fusion finale
# ---------------------------------------------------------------------------

def merge_all(
    dvf: pd.DataFrame,
    dpe: pd.DataFrame,
    georisques: pd.DataFrame,
    delinquance: pd.DataFrame,
) -> pd.DataFrame:
    log.info("Fusion des datasets…")

    df = dvf.copy()

    # Merge DPE (par code INSEE commune)
    if not dpe.empty and "code_insee" in dpe.columns:
        df = df.merge(dpe, on="code_insee", how="left")
        log.info(f"  DPE mergé : {df['score_dpe_median'].notna().sum():,} lignes enrichies")

    # Merge Géorisques (par code INSEE commune)
    if not georisques.empty:
        df = df.merge(georisques, on="code_insee", how="left")
        log.info(f"  Géorisques mergé : {df['score_georisques'].notna().sum():,} lignes enrichies")

    # Merge Délinquance (scalaire département)
    if not delinquance.empty and "score_delinquance" in delinquance.columns:
        score_del = delinquance["score_delinquance"].iloc[0]
        df["score_delinquance"] = score_del
        log.info(f"  Score délinquance appliqué : {score_del}")

    # Remplir les NaN restants par la médiane (stratégie simple)
    for col in ["score_dpe_median", "score_georisques", "score_delinquance"]:
        if col in df.columns:
            median_val = df[col].median()
            n_nan = df[col].isna().sum()
            df[col] = df[col].fillna(median_val)
            if n_nan > 0:
                log.info(f"  {col} : {n_nan} NaN remplacés par médiane ({median_val:.1f})")

    log.info(f"  Dataset final : {len(df):,} lignes, {len(df.columns)} colonnes")
    return df


# ---------------------------------------------------------------------------
# 7. Export
# ---------------------------------------------------------------------------

def export(df: pd.DataFrame, dept: str) -> Path:
    # Colonnes finales propres
    cols = [
        "id_mutation",
        "date_mutation",
        "annee",
        "type_bien",
        "prix",
        "surface_m2",
        "nb_pieces",
        "prix_m2",
        "latitude",
        "longitude",
        "code_insee",
        "nom_commune",
        "code_postal",
        "score_dpe_median",
        "score_georisques",
        "score_delinquance",
    ]
    # Garder uniquement les colonnes disponibles
    cols_dispo = [c for c in cols if c in df.columns]
    df_out = df[cols_dispo].copy()

    # Arrondir les flottants
    for col in ["prix", "prix_m2", "surface_m2"]:
        if col in df_out.columns:
            df_out[col] = df_out[col].round(2)

    dest = OUTPUT_DIR / f"dataset_propre_{dept}.csv"
    df_out.to_csv(dest, index=False, encoding="utf-8")

    size_mb = dest.stat().st_size / 1e6
    log.info(f"Export → {dest} ({size_mb:.1f} MB, {len(df_out):,} lignes)")
    return dest


# ---------------------------------------------------------------------------
# Rapport de qualité
# ---------------------------------------------------------------------------

def quality_report(df: pd.DataFrame) -> None:
    print("\n" + "=" * 55)
    print("  RAPPORT DE QUALITÉ — dataset_propre")
    print("=" * 55)
    print(f"  Lignes totales          : {len(df):>10,}")
    print(f"  Appartements            : {(df['type_bien']=='Appartement').sum():>10,}")
    print(f"  Maisons                 : {(df['type_bien']=='Maison').sum():>10,}")
    print(f"  Prix médian             : {df['prix'].median():>10,.0f} €")
    print(f"  Prix/m² médian          : {df['prix_m2'].median():>10,.0f} €/m²")
    print(f"  Surface médiane         : {df['surface_m2'].median():>10.1f} m²")
    if "score_dpe_median" in df.columns:
        print(f"  DPE médian (1=A, 7=G)   : {df['score_dpe_median'].median():>10.1f}")
    if "score_georisques" in df.columns:
        print(f"  Score géorisques médian : {df['score_georisques'].median():>10.1f}/10")
    print(f"  Valeurs manquantes      : {df.isna().sum().sum():>10,}")
    print(f"  Période couverte        : {df['annee'].min():.0f} – {df['annee'].max():.0f}")
    print("=" * 55 + "\n")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def run(dept: str = "75", skip_download: bool = False) -> Path:
    log.info(f"=== EstimIA Pipeline — Département {dept} ===")

    # 1. DVF (Multi-années à partir de 2020)
    import datetime
    current_year = datetime.datetime.now().year
    years = list(range(2020, current_year + 1))
    
    dvf_cleans = []
    for year in years:
        dvf_path = download_dvf(dept, year, skip=skip_download)
        if dvf_path is None or not dvf_path.exists():
            continue
        try:
            dvf_raw = load_dvf(dvf_path, dept)
            df_year_clean = clean_dvf(dvf_raw)
            if not df_year_clean.empty:
                dvf_cleans.append(df_year_clean)
        except Exception as e:
            log.error(f"  Erreur lors de la lecture/nettoyage de l'année {year} : {e}")

    if not dvf_cleans:
        raise ValueError(f"Aucune donnée DVF n'a pu être chargée pour le département {dept}")

    dvf_clean = pd.concat(dvf_cleans, ignore_index=True)
    log.info(f"  DVF total après concaténation et nettoyage multi-années : {len(dvf_clean):,} lignes")

    # 2. DPE
    dpe = load_dpe(dept, skip=skip_download)

    # 3. Géorisques (uniquement sur les codes INSEE présents dans le DVF)
    codes_insee = dvf_clean["code_insee"].dropna().unique().tolist()
    georisques = fetch_georisques(codes_insee)

    # 4. Délinquance
    delinquance = load_delinquance(dept, skip=skip_download)

    # 5. Fusion
    df_final = merge_all(dvf_clean, dpe, georisques, delinquance)

    # 6. Rapport qualité
    quality_report(df_final)

    # 7. Export
    output_path = export(df_final, dept)

    log.info("Pipeline terminé avec succès.")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EstimIA — Pipeline données")
    parser.add_argument("--dept", default="75", help="Code département (ex: 75, 92)")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Ne pas retélécharger si fichiers déjà présents",
    )
    args = parser.parse_args()
    run(dept=args.dept, skip_download=args.skip_download)
