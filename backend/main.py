"""
EstimIA — Driver Principal d'Extraction et Fusion (Île-de-France)
"""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd

# S'assurer que le dossier 'backend' est dans le PATH de recherche Python
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from data.pipeline import run as run_pipeline
from api import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEPT_IDF = ["75", "77", "78", "91", "92", "93", "94", "95"]

def main():
    parser = argparse.ArgumentParser(description="EstimIA — Extraction et Fusion Île-de-France")
    parser.add_argument(
        "--depts",
        nargs="+",
        default=DEPT_IDF,
        help="Liste des départements à extraire (par défaut tous ceux de l'Île-de-France)"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Passer le téléchargement des fichiers s'ils sont déjà présents"
    )
    args = parser.parse_args()

    processed_dir = backend_dir / "data" / "processed"
    processed_dir.mkdir(exist_ok=True)

    log.info(f"=== Début de l'extraction pour les départements : {args.depts} ===")

    generated_files = []
    for dept in args.depts:
        log.info(f"\n>>> Traitement du département {dept}...")
        try:
            output_file = run_pipeline(dept=dept, skip_download=args.skip_download)
            generated_files.append((dept, output_file))
        except Exception as e:
            log.error(f"Erreur lors du traitement du département {dept} : {e}", exc_info=True)

    if not generated_files:
        log.error("Aucun fichier n'a été généré. Arrêt de la fusion.")
        return

    log.info("\n=== Début de la fusion des datasets ===")
    dfs = []
    for dept, filepath in generated_files:
        if filepath.exists():
            log.info(f"Lecture du fichier : {filepath.name}")
            try:
                df_dept = pd.read_csv(
                    filepath,
                    dtype={'code_postal': str, 'code_insee': str, 'departement': str},
                    low_memory=False
                )
                # S'assurer que le département est stocké proprement
                df_dept["departement"] = str(dept).zfill(2)
                dfs.append(df_dept)
            except Exception as e:
                log.error(f"Erreur lors de la lecture de {filepath.name} : {e}")

    if dfs:
        df_merged = pd.concat(dfs, ignore_index=True)
        merged_filepath = processed_dir / "dataset_propre.csv"
        df_merged.to_csv(merged_filepath, index=False, encoding="utf-8")
        
        size_mb = merged_filepath.stat().st_size / 1e6
        log.info(f"\n✅ Fusion réussie ! Fichier global enregistré sous : {merged_filepath}")
        log.info(f"  Taille totale : {size_mb:.2f} MB")
        log.info(f"  Nombre de lignes cumulées : {len(df_merged):,}")

        # Affichage d'un rapport de qualité global
        print("\n" + "=" * 65)
        print("  RAPPORT GLOBAL DE QUALITÉ — Île-de-France")
        print("=" * 65)
        print(f"  Lignes totales          : {len(df_merged):>10,}")
        for dept in args.depts:
            count = (df_merged["departement"] == dept).sum()
            print(f"  - Département {dept:<3}       : {count:>10,} lignes")
        print(f"  Appartements            : {(df_merged['type_bien']=='Appartement').sum():>10,}")
        print(f"  Maisons                 : {(df_merged['type_bien']=='Maison').sum():>10,}")
        print(f"  Prix moyen global       : {df_merged['prix'].mean():>10,.0f} €")
        print(f"  Prix/m² moyen global    : {df_merged['prix_m2'].mean():>10,.0f} €/m²")
        print(f"  Valeurs manquantes      : {df_merged.isna().sum().sum():>10,}")
        print("=" * 65 + "\n")
    else:
        log.error("Aucune donnée valide à fusionner.")

if __name__ == "__main__":
    main()
