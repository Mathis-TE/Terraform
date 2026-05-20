# EstimIA — L'estimation immobilière augmentée
 
> Application web terrain permettant aux agents immobiliers de produire un rapport d'estimation complet, précis et professionnel en moins de 5 minutes — directement sur le terrain.
 
---
 
## Présentation
 
EstimIA combine la précision du calcul statistique et l'intelligence d'un modèle de langage local (SLM) pour produire des estimations immobilières en temps réel. L'application interroge les données ouvertes françaises (DVF, DPE, Géorisques) et génère un rapport structuré sans jamais envoyer de données sensibles vers un cloud externe.
 
**Projet annuel — groupe de 2-3 personnes**
 
---
 
## Architecture
 
```
Agent immobilier (saisit adresse + critères)
        │
        ▼
Frontend — Streamlit + Folium (carte interactive)
        │
        │  Appels Python directs
        ▼
Backend — Python FastAPI
        │
        ├──► Moteur ML (Scikit-learn)
        │       ├── Régression prix (RandomForest / KNN)
        │       └── Clustering biens (K-Means)
        │
        ├──► tools.py (outils de l'agent)
        │       ├── estimer_prix()
        │       └── obtenir_risques_climatiques()
        │
        └──► Agent IA (Ollama + LangChain)
                └── Modèle local Llama 3 — synthèse rapport
 
Sources de données (data.gouv.fr — open data officiel)
        ├── DVF (transactions foncières)
        ├── DPE (diagnostics énergétiques — ADEME)
        ├── Géorisques (API officielle)
        └── Délinquance (Interstats)
 
Déploiement
        └── Docker → AWS EC2 
```
 
### Choix techniques justifiés
 
| Composant | Choix | Justification |
|-----------|-------|---------------|
| Frontend | Streamlit + streamlit-folium | Tout en Python, carte interactive, démo jury immédiate |
| Carte | Folium | Clic → latitude/longitude automatique |
| Backend | Python FastAPI | Async, compatible ML, léger |
| ML | Scikit-learn (RandomForest / KNN) | Adapté aux données spatiales, pas de GPU requis |
| LLM | Ollama (Llama 3 local) | Zéro coût API, RGPD natif, données non exposées |
| Orchestration | LangChain ou LlamaIndex | Liaison LLM ↔ tools.py |
| Données | data.gouv.fr + API Géorisques | Open data officiel, gratuit |
| Déploiement | Docker + AWS EC2 | Scalable, Free Tier 12 mois |
 
---
 
## Stack technique
 
- **Frontend** : Streamlit, streamlit-folium, Folium
- **Backend** : Python 3.11+, FastAPI, Uvicorn
- **Machine Learning** : Scikit-learn, Pandas, NumPy, GeoPandas
- **Agent IA** : Ollama (Llama 3), LangChain ou LlamaIndex
- **Données** : DVF data.gouv.fr, DPE ADEME, API Géorisques, Délinquance Interstats
- **Infra** : Docker, AWS EC2, Ngrok (hybride si besoin)
- **Qualité code** : Ruff (linter + formatter)
---
 
## Features du modèle ML
 
Features utilisées pour la régression de prix :
 
| Feature | Source | Type |
|---------|--------|------|
| Surface (m²) | DVF | Numérique |
| Nombre de pièces | DVF | Numérique |
| Type de bien (appt/maison) | DVF | Catégoriel |
| Classe DPE (A→G encodée 1–7) | DPE data.gouv | Ordinal |
| Score Géorisques (0–10) | Géorisques | Numérique |
| Score insécurité | data.gouv | Numérique |
| Code INSEE commune | DVF | Encodé |
| Médiane transactions DVF 500m | DVF | Numérique |
 
**Clustering K-Means** : les biens sont regroupés en 4–6 classes (ex : studio centre-ville, appartement familial périurbain, maison avec terrain) pour contextualiser l'estimation dans le rapport.
 
---
 
## Utilisation du LLM
 
Le LLM est utilisé **uniquement pour la synthèse narrative** du rapport. Il ne prédit pas de prix.
 
- Reçoit en entrée : prix estimé, intervalle de confiance, classe DPE, score risques, cluster du bien, transactions comparables
- Génère : un rapport en langage naturel structuré (résumé, analyse, points forts/faibles, recommandations)
- Pas de fine-tuning, pas d'entraînement : modèle pré-entraîné GGUF quantisé
- API locale format OpenAI-compatible (`http://localhost:1234/v1/chat/completions`)
---

## Installation et lancement
 
### Prérequis
 
- Python 3.11+
- Node.js 18+
- [LM Studio](https://lmstudio.ai/) installé avec un modèle GGUF chargé
- Git
### 1. Cloner le repo
 
```bash
git clone https://github.com/<votre-org>/estimia.git
cd estimia
```
 
### 2. Backend Python
 
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --reload --port 8000
```
 
### 3. Frontend Next.js
 
```bash
cd frontend
npm install
npm run dev
```
 
### 4. LM Studio
 
1. Télécharger [LM Studio](https://lmstudio.ai/)
2. Charger un modèle GGUF (ex : `mistral-7b-instruct-v0.3.Q4_K_M.gguf`)
3. Démarrer le serveur local sur `http://localhost:1234`
### 5. Docker 
 
```bash
docker-compose up --build
```
 
---

## Données utilisées
 
Toutes les données sont open source et disponibles sur [data.gouv.fr](https://data.gouv.fr) :
 
- **DVF** (Demandes de Valeurs Foncières) — transactions immobilières
- **DPE** — diagnostics de performance énergétique
- **Géorisques** — risques naturels et technologiques par commune
- **MCP datagouv** — [github.com/datagouv/datagouv-mcp](https://github.com/datagouv/datagouv-mcp)
---