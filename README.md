# EstimIA — L'estimation immobilière augmentée
 
> Application web terrain permettant aux agents immobiliers de produire un rapport d'estimation complet, précis et professionnel en moins de 5 minutes — directement sur le terrain.
 
---
 
## Présentation
 
EstimIA combine la précision du calcul statistique et l'intelligence d'un modèle de langage local (SLM) pour produire des estimations immobilières en temps réel. L'application interroge les données ouvertes françaises (DVF, DPE, Géorisques) et génère un rapport structuré sans jamais envoyer de données sensibles vers un cloud externe.
 
**Projet annuel — groupe de 2-3 personnes**
 
---
 
## Architecture
 
```
Frontend Next.js (AWS / Vercel)
        │
        │  HTTP JSON (adresse + critères)
        ▼
Backend Python FastAPI
        │
        ├──► Moteur ML (Scikit-learn)
        │       ├── Régression prix (RandomForest / XGBoost)
        │       └── Clustering biens (K-Means)
        │
        ├──► Agent IA (Strands framework)
        │       └── LM Studio — modèle GGUF quantisé local
        │
        └──► MCP datagouv
                ├── DVF (transactions foncières)
                ├── DPE (diagnostics énergétiques)
                └── Géorisques
```
 
### Choix techniques justifiés
 
| Composant | Choix | Justification |
|-----------|-------|---------------|
| Frontend | Next.js + React | SSR natif, déploiement Vercel gratuit |
| Backend | Python FastAPI | Async, compatible ML, léger |
| ML | Scikit-learn + XGBoost | Régression tabulaire, pas de GPU requis |
| LLM | LM Studio (GGUF local) | Zéro coût API, RGPD natif, données non exposées |
| Modèle | Mistral 7B / Llama 3.1 8B Q4_K_M | 8B params : bon PC ; 12–24B : RTX 3090/4090 |
| Orchestration agent | Strands (AWS) | Framework agent Python open source |
| Données | data.gouv.fr + MCP datagouv | Open data officiel, gratuit |
| Hébergement | Vercel (front) + EC2 t3.micro (back) | Free Tier AWS 12 mois |
 
---
 
## Stack technique
 
- **Frontend** : Next.js 14, React, Tailwind CSS
- **Backend** : Python 3.11+, FastAPI, Uvicorn
- **Machine Learning** : Scikit-learn, XGBoost, Pandas, NumPy
- **Agent IA** : Strands framework, LM Studio (API format OpenAI)
- **Données** : MCP datagouv, API Géorisques, data.gouv.fr
- **Infra** : Docker, GitHub Actions, AWS EC2 / Vercel
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