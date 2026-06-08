import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def run_training(sample_size=None):
    print("===========================================================")
    print("DEMARRAGE DE L'ENTRAINEMENT DU MODELE IA - ESTIMIA")
    print("===========================================================")

    # 1. Resolution robuste des chemins
    script_dir = Path(__file__).resolve().parent
    csv_path = script_dir / "data" / "processed" / "dataset_propre.csv"
    
    # Recherche fallback
    if not csv_path.exists():
        csv_path = Path("backend/data/processed/dataset_propre.csv")
    if not csv_path.exists():
        csv_path = Path("data/processed/dataset_propre.csv")
        
    if not csv_path.exists():
        print(f"[ERROR] Impossible de trouver le dataset propre a l'emplacement : {csv_path}")
        sys.exit(1)

    print(f"1. Chargement des donnees depuis : {csv_path.resolve()}")
    df = pd.read_csv(
        csv_path, 
        dtype={'code_postal': str, 'code_insee': str, 'departement': str}, 
        low_memory=False
    )
    print(f"   -> Dataset charge : {len(df):,} lignes et {len(df.columns)} colonnes.")

    # 2. Nettoyage des valeurs aberrantes extremes (methodologie immobiliere)
    print("2. Nettoyage des valeurs extremes aberrantes...")
    initial_len = len(df)
    
    # Filtres sur le prix
    df = df[(df['prix'] >= 50000) & (df['prix'] <= 2000000)]
    # Filtres sur la surface
    df = df[(df['surface_m2'] >= 10) & (df['surface_m2'] <= 300)]
    # Filtres sur le nombre de pieces
    df = df[(df['nb_pieces'] >= 1) & (df['nb_pieces'] <= 10)]
    # S'assurer de n'avoir aucun NaN sur les coordonnees GPS cles
    df = df.dropna(subset=['latitude', 'longitude', 'prix', 'surface_m2'])
    
    filtered_len = len(df)
    print(f"   -> {initial_len - filtered_len:,} lignes filtrees ({filtered_len / initial_len * 100:.1f}% conservees).")
    print(f"   -> Taille du dataset apres filtres : {filtered_len:,} lignes.")

    # Optionnel : echantillonnage pour accelerer si demande
    if sample_size and sample_size < filtered_len:
        print(f"   [WARNING] Echantillonnage de {sample_size:,} lignes demande pour accelerer l'entrainement...")
        df = df.sample(n=sample_size, random_state=42)

    # 3. Preparation des variables et Encodage categoriel
    print("3. Preparation des variables et Encodage categoriel...")
    
    # Definition explicite des colonnes a exclure pour eviter toute fuite (leakage) ou bruit inutile
    # 'prix_m2' est exclu imperativement car c'est un target leak absolu (prix_m2 = prix / surface_m2)
    cols_to_drop = [
        'id_mutation', 'date_mutation', 'nom_commune', 
        'code_insee', 'code_postal', 'prix_m2'
    ]
    cols_present_to_drop = [c for c in cols_to_drop if c in df.columns]
    
    df_model = df.drop(columns=cols_present_to_drop)
    
    # Encodage par One-Hot Encoding de 'type_bien' et de 'departement'
    # 'departement' est traite comme une variable categorielle (ex: '75', '92'...)
    categorical_cols = ['type_bien', 'departement']
    categorical_cols = [c for c in categorical_cols if c in df_model.columns]
    
    print(f"   -> Encodage One-Hot des colonnes categorielles : {categorical_cols}")
    df_model = pd.get_dummies(df_model, columns=categorical_cols, drop_first=True)
    
    # Separation en X et y
    y = df_model['prix']
    X = df_model.drop(columns=['prix'])
    
    # Remplir les eventuelles valeurs manquantes restantes par la mediane de la colonne
    X = X.fillna(X.median())
    
    print(f"   -> Features finales ({len(X.columns)}) : {list(X.columns)}")

    # 4. Separation Train (80%) / Test (20%)
    print("4. Separation Train (80%) / Test (20%)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"   -> Set d'entrainement : {len(X_train):,} lignes.")
    print(f"   -> Set de test : {len(X_test):,} lignes.")

    # 5. Entrainement de l'algorithme Random Forest
    print("5. Entrainement du modele RandomForestRegressor (n_jobs=-1)...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42
    )
    
    import time
    start_time = time.time()
    model.fit(X_train, y_train)
    duration = time.time() - start_time
    print(f"   -> Entrainement complete en {duration:.1f} secondes ({duration/60:.1f} minutes).")

    # 6. Evaluation du modele sur le set de test
    print("6. Evaluation des performances du modele...")
    predictions = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    
    # Statistiques d'erreur relative
    errors_pct = np.abs(predictions - y_test) / y_test * 100
    median_error_pct = np.median(errors_pct)
    
    print("\n" + "=" * 55)
    print("  RESULTATS DE L'EVALUATION DU MODELE IA")
    print("=" * 55)
    print(f"  Erreur Absolue Moyenne (MAE) : {mae:>12,.2f} eur")
    print(f"  Erreur Quadratique (RMSE)    : {rmse:>12,.2f} eur")
    print(f"  Coefficient R2               : {r2:>12.4f}")
    print(f"  Marge d'erreur mediane (%)   : {median_error_pct:>12.2f} %")
    print("=" * 55 + "\n")

    # 7. Sauvegarde des artefacts du modèle
    model_dir = script_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / "modele_estimation.pkl"
    columns_path = model_dir / "colonnes_modele.pkl"
    
    print("7. Sauvegarde des fichiers d'artefacts...")
    joblib.dump(model, model_path)
    joblib.dump(list(X.columns), columns_path)
    print(f"   -> Modele sauvegarde sous   : {model_path.resolve()}")
    print(f"   -> Liste des colonnes sous  : {columns_path.resolve()}")
    print("[SUCCESS] Entrainement IA EstimIA termine avec succes !")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EstimIA -- Entrainement modele ML")
    parser.add_argument(
        "--sample", 
        type=int, 
        default=None, 
        help="Nombre de lignes a echantillonner pour accelerer (ex: 200000)"
    )
    args = parser.parse_args()
    run_training(sample_size=args.sample)