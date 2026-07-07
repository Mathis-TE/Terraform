# EstimIA — L'estimation immobilière augmentée

> Application web permettant d'estimer la valeur d'un bien immobilier en Île-de-France en quelques secondes, à partir de données ouvertes (DVF, DPE, Géorisques, délinquance) et d'un agent conversationnel.

---

## Présentation

EstimIA combine un modèle de Machine Learning (RandomForest) entraîné sur les transactions DVF d'Île-de-France avec un agent conversationnel (LangChain + Ollama, avec repli déterministe si aucun LLM n'est disponible) pour produire une estimation de prix contextualisée : diagnostic DPE médian, score de risques naturels (Géorisques) et score de délinquance du secteur.

**Projet annuel — groupe de 2-3 personnes**

---

## Architecture réelle

```
Utilisateur (formulaire + carte + chat)
        │
        ▼
Frontend — Next.js 16 (App Router) + React 19
        ├── EstimationForm.js   → saisit surface / pièces / code postal / type de bien
        ├── InteractiveMap.js / MapInner.js  → carte Leaflet
        ├── EstimationResult.js → affiche le rapport d'estimation
        └── Chatbot.js          → interface de chat avec l'agent
        │
        │  fetch() HTTP → http://localhost:8000
        ▼
Backend — FastAPI (backend/api.py)
        ├── GET  /             → statut de l'API et des modèles chargés
        ├── POST /estimate     → estimation directe (tools.py)
        └── POST /agent/chat   → agent conversationnel (agent.py)
                │
                ├──► tools.py — outil_estimation_ml()
                │       charge modele_estimation.pkl (RandomForest) + lookup_postaux.pkl
                │       et résout code postal → GPS / DPE / Géorisques / délinquance
                │
                └──► agent.py
                        ├── LangChain ReAct Agent + Ollama (llama3), si disponible
                        └── FallbackAgent — extraction regex + réponse déterministe sinon

Pipeline de données (backend/data/pipeline.py, piloté par backend/main.py)
        ├── DVF (data.gouv.fr — transactions foncières)
        ├── DPE (ADEME — diagnostics énergétiques)
        ├── Géorisques (API officielle)
        └── Délinquance (Interstats)
        → fusionne les 8 départements d'Île-de-France dans dataset_propre.csv

Entraînement (backend/train_model.py)
        → RandomForestRegressor entraîné sur dataset_propre.csv
        → sauvegarde backend/model/modele_estimation.pkl, colonnes_modele.pkl, lookup_postaux.pkl
```

### Choix techniques

| Composant | Choix | Justification |
|-----------|-------|---------------|
| Frontend | Next.js 16 + React 19 | App Router, rendu rapide, écosystème JS mature |
| Carte | Leaflet / react-leaflet | Carte interactive légère, pas de clé API requise |
| Style | Tailwind CSS 4 | Utilitaire, rapide à itérer |
| Backend | FastAPI | Async, typé (Pydantic), léger |
| ML | Scikit-learn (RandomForestRegressor) | Adapté aux données tabulaires/spatiales, pas de GPU requis |
| Agent IA | LangChain (ReAct) + Ollama (llama3) | Zéro coût API, RGPD natif, données non exposées ; repli déterministe si LLM indisponible |
| Données | data.gouv.fr (DVF, DPE), API Géorisques, Interstats | Open data officiel, gratuit |
| Qualité code | Ruff (linter + formatter) | Remplace flake8 + black + isort |

---

## Stack technique

- **Frontend** : Next.js 16, React 19, Tailwind CSS 4, Leaflet / react-leaflet
- **Backend** : Python 3.11+, FastAPI, Uvicorn
- **Machine Learning** : Scikit-learn, XGBoost, Pandas, NumPy, GeoPandas, joblib
- **Agent IA** : Ollama (llama3), LangChain (ReAct Agent) — optionnels, avec repli déterministe (`FallbackAgent`)
- **Données** : DVF (data.gouv.fr), DPE (ADEME), API Géorisques, délinquance (Interstats)
- **Qualité code** : Ruff (linter + formatter)

---

## Features du modèle ML

Features utilisées pour la régression de prix (`backend/train_model.py`) :

| Feature | Source | Type |
|---------|--------|------|
| Surface (m²) | DVF | Numérique |
| Nombre de pièces | DVF | Numérique |
| Type de bien (Appartement/Maison) | DVF | Catégoriel (one-hot) |
| Année de référence | — | Numérique |
| Latitude / Longitude | Résolues via code postal | Numérique |
| Score DPE médian du secteur (1–7) | DPE data.gouv | Ordinal |
| Score Géorisques (0–10) | Géorisques | Numérique |
| Score de délinquance départemental (0–10) | Interstats | Numérique |
| Département (one-hot) | DVF | Catégoriel |

Le modèle est entraîné sur les 8 départements d'Île-de-France (75, 77, 78, 91, 92, 93, 94, 95).

---

## Utilisation de l'agent IA

L'agent (`backend/agent.py`) répond aux questions en langage naturel et appelle systématiquement l'outil `calculateur_immobilier` (basé sur le modèle ML) pour produire un chiffre — il n'invente jamais de prix.

- **Si Ollama + LangChain sont disponibles** : agent ReAct qui extrait les critères manquants par le dialogue, appelle l'outil, puis rédige une synthèse structurée.
- **Sinon** : `FallbackAgent` prend le relais — extraction des critères par regex (surface, pièces, code postal, type de bien) et génération d'un rapport structuré déterministe.

---

## Installation et lancement

### Prérequis

- Python 3.11+
- Node.js 18+
- Git
- (Optionnel, pour l'agent conversationnel complet) [Ollama](https://ollama.com/) avec un modèle `llama3` téléchargé (`ollama pull llama3`)

### 1. Cloner le repo

```bash
git clone git@github.com:Diane2909/EstimIA_PA.git
cd EstimIA_PA
```

### 2. Récupérer les fichiers du modèle ML

Les fichiers `backend/model/modele_estimation.pkl` et `backend/model/modele_estimation_immo.pkl` dépassent la limite de taille de GitHub et ne sont donc pas versionnés dans le repo (voir `.gitignore`). Deux options :

- **Régénérer le modèle localement** : suivre la section [Pipeline de données et entraînement](#pipeline-de-données-et-entraînement-optionnel) ci-dessous.
- **Récupérer les fichiers déjà entraînés** : demander le lien de partage à l'équipe et les placer dans `backend/model/`.

### 3. Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

L'API est disponible sur `http://localhost:8000` (documentation interactive sur `http://localhost:8000/docs`).

> Pour activer l'agent ReAct LangChain, décommenter les dépendances `langchain*` dans `backend/requirements.txt`, les installer, puis démarrer Ollama (`ollama serve`). Sans cela, l'API bascule automatiquement sur le `FallbackAgent`.

### 4. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Le frontend est disponible sur `http://localhost:3000` et interroge le backend sur `http://localhost:8000`.

---

## Pipeline de données et entraînement (optionnel)

Pour reconstruire le dataset et ré-entraîner le modèle à partir des données brutes :

```bash
cd backend

# 1. Extraction et fusion des données DVF/DPE/Géorisques/délinquance pour l'Île-de-France
python main.py --depts 75 77 78 91 92 93 94 95
# → génère backend/data/processed/dataset_propre.csv

# 2. Construction de la table de correspondance géographique (code postal → GPS/DPE/risques)
python data/create_lookup_table.py

# 3. Entraînement du modèle RandomForest
python train_model.py
# → génère backend/model/modele_estimation.pkl, colonnes_modele.pkl, lookup_postaux.pkl
```

Les notebooks `notebook/01_eda_dvf.ipynb` (analyse exploratoire) et `notebook/02_modelisation_ia.ipynb` (modélisation) documentent la démarche complète. Le script `notebook/generate_eda_plots.py` régénère les figures du dossier `docs/`.

---

## Données utilisées

Toutes les données sont open source et disponibles sur [data.gouv.fr](https://data.gouv.fr) :

- **DVF** (Demandes de Valeurs Foncières) — transactions immobilières
- **DPE** — diagnostics de performance énergétique
- **Géorisques** — risques naturels et technologiques par commune
- **Interstats** — statistiques de délinquance départementales
