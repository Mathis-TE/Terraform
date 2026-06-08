import joblib
import pandas as pd
from pathlib import Path

# Résolution des chemins robustes pour les modèles
script_dir = Path(__file__).resolve().parent
model_dir = script_dir / "model"

MODELE = None
COLONNES_MODELE = None
LOOKUP_POSTAUX = None

# Chargement unique des artefacts au démarrage de l'API
try:
    modele_path = model_dir / "modele_estimation.pkl"
    colonnes_path = model_dir / "colonnes_modele.pkl"
    lookup_path = model_dir / "lookup_postaux.pkl"
    
    # Fallback paths
    if not modele_path.exists():
        modele_path = Path("backend/model/modele_estimation.pkl")
    if not colonnes_path.exists():
        colonnes_path = Path("backend/model/colonnes_modele.pkl")
    if not lookup_path.exists():
        lookup_path = Path("backend/model/lookup_postaux.pkl")

    if modele_path.exists() and colonnes_path.exists():
        MODELE = joblib.load(modele_path)
        COLONNES_MODELE = joblib.load(colonnes_path)
        print(f"[SUCCESS] Modele ML charge depuis : {modele_path.name}")
    else:
        print("[WARNING] Fichiers de modele ML non trouves.")
        
    if lookup_path.exists():
        LOOKUP_POSTAUX = joblib.load(lookup_path)
        print(f"[SUCCESS] Table de correspondance geographique chargee : {lookup_path.name}")
    else:
        print("[WARNING] Table de correspondance geographique non trouvee.")

except Exception as e:
    print(f"[ERROR] Erreur lors du chargement des modeles : {e}")

def outil_estimation_ml(surface: int, pieces: int, code_postal: str, type_bien: str, annee_visite: int = 2025, return_dict: bool = True):
    """
    Estime la valeur vénale d'un bien immobilier en Île-de-France en utilisant
    le modèle Random Forest et la table de correspondance de codes postaux.
    
    Args:
        surface: Surface habitable en m2.
        pieces: Nombre de pièces principales.
        code_postal: Code postal à 5 chiffres (ex: '92100').
        type_bien: 'Maison' ou 'Appartement'.
        annee_visite: Année d'estimation (ex: 2025).
        return_dict: Si True, renvoie un dictionnaire structuré. Si False, renvoie un texte rédigé en français.
    """
    if MODELE is None or COLONNES_MODELE is None:
        err_msg = "Erreur : Le modele ML n'est pas charge."
        return {"erreur": err_msg} if return_dict else err_msg

    try:
        # 1. Uniformisation et formatage du code postal
        code_postal_str = str(code_postal).strip().replace(".0", "").zfill(5)
        
        # 2. Résolution des coordonnées et scores via le cache géographique
        geo_info = None
        source_resolution = "inconnue"
        
        if LOOKUP_POSTAUX:
            if code_postal_str in LOOKUP_POSTAUX.get('postaux', {}):
                geo_info = LOOKUP_POSTAUX['postaux'][code_postal_str]
                source_resolution = "code_postal"
            else:
                # Fallback à l'échelle départementale (2 premiers chiffres)
                dept_code = code_postal_str[:2]
                if dept_code in LOOKUP_POSTAUX.get('departements', {}):
                    geo_info = LOOKUP_POSTAUX['departements'][dept_code].copy()
                    geo_info['departement'] = dept_code
                    source_resolution = "departement"
        
        # Fallback ultime en cas de cache manquant ou d'incompatibilité géographique hors IDF
        if not geo_info:
            geo_info = {
                'latitude': 48.8566,
                'longitude': 2.3522,
                'score_dpe_median': 4.0,       # Classe D par défaut
                'score_georisques': 4.5,
                'score_delinquance': 5.0,
                'departement': '75'
            }
            source_resolution = "fallback_paris"

        # Nettoyage de securite des valeurs NaN pour eviter les erreurs de conversion
        import math
        defaults = {
            'latitude': 48.8566,
            'longitude': 2.3522,
            'score_dpe_median': 4.0,       # Classe D par defaut
            'score_georisques': 4.5,
            'score_delinquance': 5.0,
            'departement': '75'
        }
        for k in ['latitude', 'longitude', 'score_dpe_median', 'score_georisques', 'score_delinquance']:
            val = geo_info.get(k)
            if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
                geo_info[k] = defaults[k]

        if 'departement' not in geo_info or pd.isna(geo_info['departement']) or not geo_info['departement']:
            geo_info['departement'] = code_postal_str[:2]

        # 3. Préparation du vecteur de caractéristiques d'entrée
        donnees_entree = pd.DataFrame(0.0, index=[0], columns=COLONNES_MODELE)


        
        # Injection des features physiques et macro-temporelles
        donnees_entree.at[0, 'surface_m2'] = float(surface)
        donnees_entree.at[0, 'nb_pieces'] = float(pieces)
        donnees_entree.at[0, 'annee'] = float(annee_visite)
        
        # Injection des features géographiques et environnementales résolues
        donnees_entree.at[0, 'latitude'] = float(geo_info['latitude'])
        donnees_entree.at[0, 'longitude'] = float(geo_info['longitude'])
        donnees_entree.at[0, 'score_dpe_median'] = float(geo_info['score_dpe_median'])
        donnees_entree.at[0, 'score_georisques'] = float(geo_info['score_georisques'])
        donnees_entree.at[0, 'score_delinquance'] = float(geo_info['score_delinquance'])
        
        # Gestion du type de bien
        if type_bien.lower() == 'maison' and 'type_bien_Maison' in donnees_entree.columns:
            donnees_entree.at[0, 'type_bien_Maison'] = 1.0
            
        # Gestion des variables One-Hot du département
        dept_str = geo_info['departement']
        dept_column = f"departement_{dept_str}"
        if dept_column in donnees_entree.columns:
            donnees_entree.at[0, dept_column] = 1.0

        # 4. Prédiction mathématique brute
        prix_estime = MODELE.predict(donnees_entree)[0]
        
        # Formater la note de performance DPE en lettre (1=A, 7=G)
        dpe_lettres = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G'}
        lettre_dpe = dpe_lettres.get(int(round(geo_info['score_dpe_median'])), 'D')

        res_dict = {
            "prix_estime": round(prix_estime, 2),
            "surface_m2": surface,
            "nb_pieces": pieces,
            "type_bien": type_bien,
            "code_postal": code_postal_str,
            "departement": geo_info['departement'],
            "latitude": geo_info['latitude'],
            "longitude": geo_info['longitude'],
            "score_dpe_median": geo_info['score_dpe_median'],
            "classe_dpe": lettre_dpe,
            "score_georisques": geo_info['score_georisques'],
            "score_delinquance": geo_info['score_delinquance'],
            "source_resolution": source_resolution
        }

        if return_dict:
            return res_dict
        
        # Version rédigée pour l'Agent IA
        return (f"Le modele statistique RandomForest estime la valeur de ce bien ({type_bien}, {surface}m2, "
                f"{pieces} pieces a {code_postal_str}) a environ {prix_estime:,.0f} €.\n"
                f"Informations micro-locales injectees pour le calcul :\n"
                f"  - Coordonnees GPS : {geo_info['latitude']:.4f}, {geo_info['longitude']:.4f}\n"
                f"  - Diagnostic DPE median : Classe {lettre_dpe}\n"
                f"  - Niveau de risques naturels (Georisques) : {geo_info['score_georisques']:.1f}/10\n"
                f"  - Score d'insecurite departemental : {geo_info['score_delinquance']:.1f}/10\n"
                f"Remarque pour l'agent : Transmets cette estimation brute avec professionnalisme et mentionne "
                f"ces indices contextuels pour valoriser ton analyse.")

    except Exception as e:
        err_msg = f"Erreur de l'outil d'estimation : Impossible de calculer le prix. Detail: {str(e)}"
        return {"erreur": err_msg} if return_dict else err_msg

# Test unitaire rapide
if __name__ == "__main__":
    # Forcer le rechargement local pour le test
    import os
    print("--- Test unitaire de tools.py ---")
    res = outil_estimation_ml(surface=65, pieces=3, code_postal='92100', type_bien='Appartement', return_dict=False)
    print(res)