# EstimIA — Déploiement Azure (Terraform + GitHub Actions)

Ce guide décrit la mise en place **une seule fois** de l'infrastructure Azure,
puis comment le pipeline CI/CD prend le relais à chaque push sur `main`.

> Le projet peut être déployé sur Azure **ou** AWS (voir [docs/aws-setup.md](aws-setup.md)) —
> les deux infras cohabitent dans des dossiers séparés (`infra/azure/`, `infra/aws/`)
> et ne dépendent pas l'une de l'autre.

## Architecture cible

```
GitHub Actions (cd-azure.yml)
   │
   ├─ build & push ──► Azure Container Registry (ACR)
   │
   └─ az containerapp update ──► Azure Container Apps Environment
                                     ├─ estimia-prod-backend   (FastAPI, port 8000)
                                     │      └─ télécharge les .pkl depuis ─┐
                                     └─ estimia-prod-frontend  (Next.js, port 3000)
                                                                          │
                                                            Azure Storage Account (SAS lecture seule)
```

L'agent conversationnel Ollama/LangChain n'est **pas déployé** dans le cloud
(trop lourd pour Container Apps) : en production, `/agent/chat` bascule
automatiquement sur le `FallbackAgent` déterministe (voir `backend/agent.py`).
C'est déjà le comportement par défaut car `langchain`/`langchain-community`
sont commentés dans `requirements.txt`.

---

## Prérequis

- Un abonnement Azure actif
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az`)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.7
- Droits `Owner` ou `Contributor` + `User Access Administrator` sur l'abonnement (pour créer le service principal)

---

## Étape 1 — Se connecter et créer le service principal pour GitHub Actions

```bash
az login
az account set --subscription "<nom-ou-id-de-votre-abonnement>"

# Crée un Service Principal avec les droits Contributor sur l'abonnement.
# La sortie JSON est à coller telle quelle dans le secret GitHub AZURE_CREDENTIALS.
az ad sp create-for-rbac \
  --name "estimia-github-actions" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id> \
  --sdk-auth
```

Conservez la sortie JSON (`{"clientId": ..., "clientSecret": ..., ...}`) —
elle ne sera plus jamais réaffichée.

---

## Étape 2 — Provisionner l'infrastructure avec Terraform

```bash
cd infra/azure
terraform init
terraform plan
terraform apply
```

Cela crée : un groupe de ressources, un Azure Container Registry, un compte
de stockage + conteneur `models`, un environnement Container Apps, et deux
Container Apps (`backend`/`frontend`) avec une **image placeholder** — le
premier vrai déploiement se fera via la CI/CD (étape 4).

Récupérez les valeurs utiles :

```bash
terraform output
terraform output -raw storage_sas_token   # sensible, ne pas committer
```

---

## Étape 3 — Uploader le modèle ML sur Azure Blob Storage

Après avoir généré les artefacts en local (`python train_model.py` puis
`python scripts/create_lookup_table.py`, voir le README principal) :

```bash
STORAGE_ACCOUNT=$(terraform -chdir=infra/azure output -raw storage_account_name)

az storage blob upload-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  -d models \
  -s backend/model
```

Redémarrez ensuite la Container App backend (`az containerapp revision restart`
ou un simple push CI/CD) pour qu'elle retélécharge les fichiers.

---

## Étape 4 — Configurer le repository GitHub

### Secrets (`Settings → Secrets and variables → Actions → Secrets`)

| Nom | Valeur |
|-----|--------|
| `AZURE_CREDENTIALS` | La sortie JSON complète de `az ad sp create-for-rbac --sdk-auth` (étape 1) |

### Variables (`Settings → Secrets and variables → Actions → Variables`)

| Nom | Valeur | Source |
|-----|--------|--------|
| `AZURE_RESOURCE_GROUP` | `rg-estimia-prod` | `terraform output resource_group_name` |
| `AZURE_ACR_NAME` | ex. `acrestimiaprod` | `terraform output acr_name` |
| `AZURE_BACKEND_APP_NAME` | `estimia-prod-backend` | `terraform output backend_app_name` |
| `AZURE_FRONTEND_APP_NAME` | `estimia-prod-frontend` | `terraform output frontend_app_name` |

---

## Étape 5 — Déclencher le déploiement

Un simple `git push` sur `main` touchant `backend/**` ou `frontend/**`
déclenche `.github/workflows/cd-azure.yml` :

1. build + push de l'image backend sur ACR, puis `az containerapp update`
2. récupération du FQDN public du backend
3. build de l'image frontend avec `NEXT_PUBLIC_API_URL=<fqdn backend>`, push sur ACR
4. `az containerapp update` du frontend

Vous pouvez aussi le lancer manuellement depuis l'onglet **Actions** du repo
(`workflow_dispatch`).

---

## Vérifier le déploiement

### 1. L'infrastructure Terraform est-elle conforme à ce qui est déclaré ?

```bash
cd infra/azure
terraform validate      # vérifie la syntaxe/schéma (ne nécessite pas d'être connecté)
terraform plan           # nécessite `az login` au préalable
```

Après un `apply` réussi, un `terraform plan` derrière doit répondre
**"No changes."** Si Terraform détecte un écart (ex: quelqu'un a modifié une
ressource à la main dans le portail Azure), il apparaîtra ici — c'est le
signal de "drift" à surveiller.

```bash
terraform show                 # état complet tel que Terraform le connaît
terraform state list           # liste des ressources gérées
```

### 2. Les Container Apps tournent-elles avec la bonne image ?

```bash
RG=$(terraform -chdir=infra/azure output -raw resource_group_name)
BACKEND=$(terraform -chdir=infra/azure output -raw backend_app_name)
FRONTEND=$(terraform -chdir=infra/azure output -raw frontend_app_name)

az containerapp show -n "$BACKEND" -g "$RG" \
  --query "{image:properties.template.containers[0].image, fqdn:properties.configuration.ingress.fqdn, provisioningState:properties.provisioningState}"

az containerapp revision list -n "$BACKEND" -g "$RG" \
  --query "[].{name:name, active:properties.active, replicas:properties.replicas, created:properties.createdTime}" -o table
```

`provisioningState` doit valoir `Succeeded`, et la révision active doit
correspondre au tag d'image poussé par le dernier run GitHub Actions.

### 3. L'application répond-elle vraiment ?

```bash
curl -s "$(terraform -chdir=infra/azure output -raw backend_fqdn)/"
curl -s -o /dev/null -w "%{http_code}\n" "$(terraform -chdir=infra/azure output -raw frontend_fqdn)/"
```

Le premier doit renvoyer le JSON de statut avec `"modele_ml_idf": "Charge avec succes"`
(si l'upload du modèle en étape 3 a bien eu lieu) ; le second doit renvoyer `200`.

### 4. En cas d'échec — logs

```bash
az containerapp logs show -n "$BACKEND" -g "$RG" --follow
```

Cible en particulier les messages `[WARNING]`/`[ERROR]` de
`backend/scripts/download_model.py` (échec de téléchargement SAS = token
expiré ou variables d'environnement mal renseignées) et les erreurs
`ImagePullBackOff` côté `az containerapp revision list` (droits ACR/registry
secret mal configurés).

### 5. Le pipeline CI/CD lui-même

```bash
gh run list --workflow=cd-azure.yml --limit 5
gh run view <run-id> --log
```

---

## Notes

- **État Terraform** : stocké en local (`infra/azure/terraform.tfstate`,
  gitignored) par défaut. Pour un travail à plusieurs, migrez vers un backend
  `azurerm` distant (voir le commentaire dans `infra/azure/providers.tf`) une
  fois le storage account créé.
- **SAS token** : expire le 31/12/2030 par défaut (`infra/azure/variables.tf`,
  `sas_expiry`). À renouveler avant cette date via `terraform apply` avec une
  nouvelle valeur.
- **Coûts** : ACR Basic (~5€/mois), Container Apps en scale-to-zero
  (`min_replicas = 0`, quasi gratuit au repos), Storage Account LRS (quelques
  centimes). Pensez à `terraform destroy` en fin de projet si besoin.
