#!/bin/sh
set -e

# Un échec de téléchargement du modèle (bucket/blob absent, réseau, etc.) ne
# doit jamais empêcher l'API de démarrer : tools.py gère déjà un modèle
# manquant en répondant en mode dégradé plutôt qu'en plantant.
python scripts/download_model.py || true

exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-8000}"
