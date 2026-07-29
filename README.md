# EstimIA — L'estimation immobilière augmentée

> Application web permettant aux agents immobiliers de produire un rapport d'estimation immobilière complet en temps réel, couvrant toute l'Île-de-France.

---

## Présentation

EstimIA combine un modèle RandomForest entraîné sur **787 260 transactions** DVF Île-de-France (2021–2025) et un agent conversationnel IA local (Ollama + LangChain) pour produire des estimations enrichies avec des indicateurs micro-locaux : DPE, Géorisques, Délinquance.

Le projet fonctionne **sans aucun coût d'API** — le LLM tourne en local via Ollama. Un FallbackAgent déterministe prend le relais automatiquement si Ollama est hors-ligne.

**Projet annuel — groupe de 2-3 personnes**

---

## Architecture

```
Frontend — Next.js 16 + React 19   (port 3000)
        │
        │  POST /estimate   →  { surface, pieces, code_postal, type_bien, annee_visite }
        │  POST /agent/chat →  { message }
        ▼
Backend — Python FastAPI            (port 8000)
        │
        ├──► tools.py
        │       ├── modele_estimation.pkl    (RandomForest entraîné)
        │       ├── colonnes_modele.pkl      (ordre des features)
        │       └── lookup_postaux.pkl       (code postal → GPS + scores)
        │
        └──► agent.py
                ├── LangChain ReAct Agent   (si Ollama est lancé)
                └── FallbackAgent           (si Ollama est hors-ligne)
```

---

## Stack technique

**Backend**
- Python 3.11+, FastAPI, Uvicorn
- Scikit-learn, Pandas, NumPy, GeoPandas, Joblib
- LangChain, LangChain-Community, Ollama (Llama 3 GGUF)
- Ruff (linter + formatter)

**Frontend**
- Next.js 16, React 19, Tailwind CSS 4
- Leaflet 1.9.4, react-leaflet 5
- Fetch API

**Infra**
- Docker, Terraform — déployable sur **Azure** (Container Apps, ACR, Blob Storage)
- CI/CD : GitHub Actions

---

## Features du modèle ML

| Feature | Source | Type |
|---------|--------|------|
| Surface (m²) | DVF | Numérique |
| Nombre de pièces | DVF | Numérique |
| Année de référence | DVF | Numérique |
| Latitude / Longitude | Lookup postal | Numérique |
| Score DPE médian (1=A … 7=G) | DPE ADEME | Ordinal |
| Score Géorisques (0–10) | API Géorisques | Numérique |
| Score délinquance (0–10) | Interstats | Numérique |
| Type de bien | DVF | One-Hot (Maison / Appartement) |
| Département | DVF | One-Hot (75, 77, 78, 91–95) |

---

## Structure du projet

```
estimia/
│
├── backend/
│   ├── api.py                      # Routes FastAPI : / · /estimate · /agent/chat
│   ├── main.py                     # Driver : pipeline IDF multi-départements
│   ├── tools.py                    # outil_estimation_ml() — moteur ML
│   ├── agent.py                    # LangChain ReAct Agent + FallbackAgent
│   ├── train_model.py              # Entraînement RandomForest
│   ├── requirements.txt
│   │
│   ├── data/
│   │   ├── pipeline.py             # Pipeline DVF + DPE + Géorisques + Délinquance
│   │   ├── raw/                    # Fichiers bruts (gitignore)
│   │   └── processed/
│   │       └── dataset_propre.csv  # Dataset IDF fusionné
│   │
│   ├── model/
│   │   ├── modele_estimation.pkl
│   │   ├── colonnes_modele.pkl
│   │   └── lookup_postaux.pkl
│   │
│   └── scripts/
│       └── create_lookup_table.py
│
├── frontend/
│   ├── package.json                # Next.js 16, React 19, Leaflet, Tailwind 4
│   ├── jsconfig.json               # Alias @/* → ./src/*
│   ├── next.config.mjs
│   ├── postcss.config.mjs
│   └── src/
│       ├── app/
│       │   ├── layout.js
│       │   ├── page.js             # Page principale — 2 onglets
│       │   └── globals.css
│       └── components/
│           ├── EstimationForm.js   # Formulaire + validation IDF
│           ├── EstimationResult.js # Résultat + animation prix + indicateurs
│           ├── InteractiveMap.js   # Wrapper Leaflet SSR-safe
│           ├── MapInner.js         # Carte dark mode + marqueur
│           └── Chatbot.js          # Interface Geo-Estate AI
│
├── notebooks/
│   ├── 01_eda_dvf.ipynb
│   └── 02_modelisation_ia.ipynb
│
├── docs/
│   ├── generate_eda_plots.py
│   ├── fig_distribution_prix.png
│   ├── fig_correlations.png
│   ├── fig_importances_features.png
│   ├── fig_predictions_vs_reelles.png
│   ├── fig_prix_code_postal.png
│   ├── fig_risques_delinquance_departement.png
│   ├── carte_prix_idf.html
│   └── fig_evolution_prix.html
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint + build backend/frontend sur chaque PR
│       └── cd-azure.yml            # Build, push ACR, déploiement Container Apps
│
├── terraform/
│   └── azure/                      # provisioning Azure (voir docs/azure-setup.md)
│       ├── providers.tf
│       ├── variables.tf
│       ├── main.tf
│       └── outputs.tf
│
├── backend/Dockerfile
├── frontend/Dockerfile
├── docker-compose.yml               # Lancement local complet (backend + frontend)
├── pyproject.toml                  # Config Ruff
└── .gitignore
```

---

## Lancement du projet

### Prérequis

- Python 3.11+
- Node.js 18+
- Git
- [Ollama](https://ollama.ai/) — optionnel

---

### Étape 1 — Cloner le repo

```bash
git clone https://github.com/<votre-org>/estimia.git
cd estimia
```

---

### Étape 2 — Installer les dépendances Python

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

---

### Étape 3 — Générer le dataset IDF

```bash
# Tous les départements IDF (75, 77, 78, 91, 92, 93, 94, 95)
python main.py

# Si les fichiers sont déjà téléchargés
python main.py --skip-download

# Un seul département pour tester
python data/pipeline.py --dept 75
```

Produit : `backend/data/processed/dataset_propre.csv`

---

### Étape 4 — Entraîner le modèle ML

```bash
# Entraînement complet (~787k transactions, ~10 min)
python train_model.py

# Sur un échantillon (plus rapide, pour tester)
python train_model.py --sample 200000
```

Produit dans `backend/model/` :
- `modele_estimation.pkl`
- `colonnes_modele.pkl`

---

### Étape 5 — Générer la table de correspondance géographique

```bash
python scripts/create_lookup_table.py
```

Produit : `backend/model/lookup_postaux.pkl`

> Cette étape est **obligatoire** avant de lancer l'API.

---

### Étape 6 — Lancer le backend FastAPI

```bash
uvicorn api:app --reload --port 8000
```

- API : `http://localhost:8000`
- Documentation : `http://localhost:8000/docs`

---

### Étape 7 — (Optionnel) Lancer Ollama

```bash
ollama pull llama3
ollama serve
```

Si Ollama n'est pas lancé, le **FallbackAgent** s'active automatiquement — l'application reste 100% fonctionnelle.

---

### Étape 8 — Lancer le frontend Next.js

```bash
cd ../frontend
npm install
npm run dev
```

Application : `http://localhost:3000`

---

### Docker (déploiement local complet en une commande)

```bash
docker-compose up --build
```

- Frontend : `http://localhost:3000`
- Backend : `http://localhost:8000`

Pour que l'estimation ML fonctionne, placez les 3 fichiers `.pkl` générés à
l'étape 4-5 dans `backend/model/` : `docker-compose.yml` monte ce dossier en
volume dans le conteneur backend (pas besoin d'Azure en local).
`backend/scripts/download_model.py` détecte automatiquement, au démarrage,
si les variables d'environnement Azure sont renseignées.

---

## CI/CD & déploiement cloud (Azure)

Le projet se déploie sur **Azure** via Terraform + GitHub Actions.

- **CI** (`.github/workflows/ci.yml`) : à chaque push/PR, installe les
  dépendances, vérifie que l'API s'importe sans erreur, lint + build le
  frontend, et fait un build Docker à blanc des deux images.
- **CD Azure** (`.github/workflows/cd-azure.yml`, [docs/azure-setup.md](docs/azure-setup.md)) :
  build + push sur Azure Container Registry, puis `az containerapp update`
  sur les 2 Container Apps. Infra (`terraform/azure/`) : ACR, Storage Account
  (modèle ML), environnement Container Apps, 2 Container Apps.

L'agent conversationnel s'appuie uniquement sur le `FallbackAgent`
déterministe en production (Ollama n'est pas déployé — trop lourd pour les
paliers de calcul les plus bas d'Azure Container Apps).

---

## Routes API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Status + état des modèles chargés |
| POST | `/estimate` | Estimation ML d'un bien |
| POST | `/agent/chat` | Chat Geo-Estate AI |

### POST /estimate — exemple

Requête :
```json
{
  "surface": 65,
  "pieces": 3,
  "code_postal": "92100",
  "type_bien": "Appartement",
  "annee_visite": 2025
}
```

Réponse :
```json
{
  "prix_estime": 387500.0,
  "surface_m2": 65,
  "nb_pieces": 3,
  "type_bien": "Appartement",
  "code_postal": "92100",
  "departement": "92",
  "latitude": 48.8392,
  "longitude": 2.2408,
  "score_dpe_median": 4.0,
  "classe_dpe": "D",
  "score_georisques": 3.2,
  "score_delinquance": 1.0,
  "source_resolution": "code_postal"
}
```

Codes postaux acceptés : `75xxx · 77xxx · 78xxx · 91xxx · 92xxx · 93xxx · 94xxx · 95xxx`

---

## Générer les figures EDA

```bash
cd docs
python generate_eda_plots.py
```

---

## Données utilisées

| Source | Contenu | Couverture | Statut |
|--------|---------|------------|--------|
| DVF (data.gouv.fr) | Transactions foncières | IDF 2021–2025 | ✅ |
| DPE (ADEME) | Diagnostics énergétiques | IDF | ✅ |
| Géorisques (API) | Risques naturels par commune | IDF | ✅ |
| Délinquance (Interstats) | Taux par département | IDF | ✅ |

---

## Conventions Git

### Branches

| Branche | Rôle |
|---------|------|
| `main` | Production — protégée, merge via PR uniquement |
| `develop` | Intégration continue |
| `feature/data-pipeline` | Pipeline données IDF ✅ |
| `feature/ml-regression` | Entraînement + évaluation modèle ✅ |
| `feature/agent-tools` | tools.py + lookup table ✅ |
| `feature/agent-llm` | LangChain + FallbackAgent ✅ |
| `feature/frontend` | Next.js ✅ |
| `feature/deployment` | Docker + Azure ✅ |

### Format des commits

```
feat(data): pipeline IDF 8 départements — 787260 transactions
feat(ml): RandomForest entraîné MAE + RMSE + R²
feat(tools): outil_estimation_ml avec lookup géographique
feat(agent): LangChain ReAct + FallbackAgent déterministe
feat(frontend): Next.js formulaire + carte Leaflet + chatbot
fix(api): CORS pour Next.js local
chore: update requirements.txt
```

---

## Roadmap

- [x] Phase 1 — Pipeline données IDF (8 départements, 787 260 transactions)
- [x] Phase 2 — Modèle ML RandomForest + notebooks EDA
- [x] Phase 3 — tools.py + table de correspondance géographique
- [x] Phase 4 — Agent LangChain + FallbackAgent déterministe
- [x] Phase 5 — Frontend Next.js (formulaire, carte Leaflet, chatbot)
- [x] Phase 6 — Dockerisation + CI/CD GitHub Actions + déploiement Azure Container Apps (Terraform)

---

## Licence

Projet académique — données sous licence Etalab (Open Data).