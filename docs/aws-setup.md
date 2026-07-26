# EstimIA — Déploiement AWS (Terraform + GitHub Actions)

Ce guide décrit la mise en place **une seule fois** de l'infrastructure AWS,
puis comment le pipeline CI/CD prend le relais à chaque push sur `main`.

> Le projet peut être déployé sur AWS **ou** Azure (voir [docs/azure-setup.md](azure-setup.md)) —
> les deux infras cohabitent dans des dossiers séparés (`infra/aws/`, `infra/azure/`)
> et ne dépendent pas l'une de l'autre.

## Architecture cible

```
GitHub Actions (cd-aws.yml)
   │
   ├─ build & push ──► Amazon ECR (backend + frontend)
   │
   └─ aws ecs update-service ──► ECS Cluster (Fargate)
                                     ├─ estimia-prod-backend   (FastAPI, port 8000)
                                     │      └─ télécharge les .pkl depuis ─┐
                                     └─ estimia-prod-frontend  (Next.js, port 3000)
                                                                          │
                                                                  Bucket S3 (rôle IAM de tâche)
                                     ▲
                                     │
                        Application Load Balancer (1 ALB, 2 listeners)
                          :80   → frontend
                          :8080 → backend
```

Pas de nom de domaine ni de certificat ACM dans cette configuration : l'ALB
n'est joignable qu'en **HTTP** sur son DNS auto-généré
(`xxx.eu-west-3.elb.amazonaws.com`). Pour du HTTPS, il faudrait un domaine
Route 53 + un certificat ACM sur l'ALB — non couvert ici.

L'agent conversationnel Ollama/LangChain n'est **pas déployé** dans le cloud
(trop lourd pour un service Fargate 0.25 vCPU) : en production, `/agent/chat`
bascule automatiquement sur le `FallbackAgent` déterministe (voir
`backend/agent.py`). C'est déjà le comportement par défaut car
`langchain`/`langchain-community` sont commentés dans `requirements.txt`.

---

## Prérequis

- Un compte AWS actif
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (`aws`)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.7
- `jq` (utilisé par le workflow CD pour patcher les task definitions)
- Droits suffisants pour créer VPC/ECR/ECS/IAM/S3/ALB (ex: `AdministratorAccess`
  pour un compte de projet étudiant, ou une policy plus restreinte en prod)

---

## Étape 1 — Se connecter et créer un utilisateur IAM pour GitHub Actions

```bash
aws configure   # ou aws sso login, selon votre setup
aws sts get-caller-identity
```

Créez un utilisateur IAM dédié à la CI/CD (accès programmatique uniquement) :

```bash
aws iam create-user --user-name estimia-github-actions

aws iam attach-user-policy \
  --user-name estimia-github-actions \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-user-policy \
  --user-name estimia-github-actions \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

aws iam create-access-key --user-name estimia-github-actions
```

Conservez `AccessKeyId` et `SecretAccessKey` — ils ne seront plus jamais
réaffichés. (Alternative plus sûre : OIDC avec `aws-actions/configure-aws-credentials`
et un rôle à assumer, sans clé longue durée — non détaillé ici pour rester simple.)

---

## Étape 2 — Provisionner l'infrastructure avec Terraform

```bash
cd infra/aws
terraform init
terraform plan
terraform apply
```

Cela crée : ECR (2 dépôts), un bucket S3, un cluster ECS Fargate, les 2
services (backend/frontend) avec une **image placeholder**, un ALB avec 2
listeners, les security groups et rôles IAM. Le premier vrai déploiement se
fera via la CI/CD (étape 4).

```bash
terraform output
```

Notez `backend_url` (ex: `http://estimia-prod-alb-xxxx.eu-west-3.elb.amazonaws.com:8080`)
— cette URL est stable, elle ne changera plus.

---

## Étape 3 — Uploader le modèle ML sur S3

Après avoir généré les artefacts en local (`python train_model.py` puis
`python scripts/create_lookup_table.py`, voir le README principal) :

```bash
BUCKET=$(terraform -chdir=infra/aws output -raw s3_bucket_name)

aws s3 cp backend/model/ "s3://$BUCKET/" --recursive
```

Redéployez ensuite le service ECS backend (`aws ecs update-service --cluster ... --service ... --force-new-deployment`,
ou un simple push CI/CD) pour qu'il retélécharge les fichiers au démarrage.

---

## Étape 4 — Configurer le repository GitHub

### Secrets (`Settings → Secrets and variables → Actions → Secrets`)

| Nom | Valeur |
|-----|--------|
| `AWS_ACCESS_KEY_ID` | Clé d'accès de l'utilisateur `estimia-github-actions` (étape 1) |
| `AWS_SECRET_ACCESS_KEY` | Secret associé |

### Variables (`Settings → Secrets and variables → Actions → Variables`)

| Nom | Valeur | Source |
|-----|--------|--------|
| `AWS_REGION` | `eu-west-3` | `infra/aws/variables.tf` (`aws_region`) |
| `AWS_ECS_CLUSTER` | `estimia-prod-cluster` | `terraform output ecs_cluster_name` |
| `AWS_ECR_BACKEND_REPO` | `estimia-prod-backend` | nom du dépôt ECR backend |
| `AWS_ECR_FRONTEND_REPO` | `estimia-prod-frontend` | nom du dépôt ECR frontend |
| `AWS_ECS_BACKEND_TASK_FAMILY` | `estimia-prod-backend` | `terraform output backend_task_family` |
| `AWS_ECS_FRONTEND_TASK_FAMILY` | `estimia-prod-frontend` | `terraform output frontend_task_family` |
| `AWS_ECS_BACKEND_SERVICE` | `estimia-prod-backend` | `terraform output ecs_backend_service_name` |
| `AWS_ECS_FRONTEND_SERVICE` | `estimia-prod-frontend` | `terraform output ecs_frontend_service_name` |
| `AWS_BACKEND_URL` | `terraform output -raw backend_url` | figée au build du frontend (`NEXT_PUBLIC_API_URL`) |

---

## Étape 5 — Déclencher le déploiement

Un simple `git push` sur `main` touchant `backend/**` ou `frontend/**`
déclenche `.github/workflows/cd-aws.yml` : build + push ECR, patch de la task
definition avec la nouvelle image, `aws ecs update-service --force-new-deployment`.
Les deux jobs (`deploy-backend`/`deploy-frontend`) tournent **en parallèle**
puisque `AWS_BACKEND_URL` est une variable statique (contrairement à Azure
Container Apps où le FQDN backend devait être récupéré dynamiquement avant de
builder le frontend).

Vous pouvez aussi le lancer manuellement depuis l'onglet **Actions** du repo
(`workflow_dispatch`).

---

## Vérifier le déploiement

### 1. Terraform reflète-t-il l'état réel ?

```bash
cd infra/aws
terraform plan   # doit répondre "No changes." après un apply propre
terraform state list
```

### 2. Les services ECS tournent-ils avec la bonne image ?

```bash
CLUSTER=$(terraform -chdir=infra/aws output -raw ecs_cluster_name)
BACKEND_SVC=$(terraform -chdir=infra/aws output -raw ecs_backend_service_name)

aws ecs describe-services --cluster "$CLUSTER" --services "$BACKEND_SVC" \
  --query 'services[0].{status:status, running:runningCount, desired:desiredCount, taskDef:taskDefinition}'

aws ecs list-tasks --cluster "$CLUSTER" --service-name "$BACKEND_SVC"
```

`runningCount` doit égaler `desiredCount`, et `taskDefinition` doit pointer
vers la révision créée par le dernier run GitHub Actions.

### 3. L'application répond-elle vraiment ?

```bash
curl -s "$(terraform -chdir=infra/aws output -raw backend_url)/"
curl -s -o /dev/null -w "%{http_code}\n" "$(terraform -chdir=infra/aws output -raw frontend_url)/"
```

Le premier doit renvoyer `"modele_ml_idf": "Charge avec succes"` (une fois
le modèle uploadé sur S3), le second `200`.

### 4. Cibles ALB en bonne santé ?

```bash
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups --names estimia-prod-backend --query 'TargetGroups[0].TargetGroupArn' -o text)
```

### 5. En cas d'échec — logs

```bash
aws logs tail /ecs/estimia-prod-backend --follow
```

Cible en particulier les erreurs de `backend/scripts/download_model.py`
(bucket/permissions IAM mal configurés) et les tâches qui s'arrêtent en
boucle (`aws ecs describe-tasks` → `stoppedReason`).

### 6. Le pipeline CI/CD lui-même

```bash
gh run list --workflow=cd-aws.yml --limit 5
gh run view <run-id> --log
```

---

## Notes

- **État Terraform** : stocké en local (`infra/aws/terraform.tfstate`,
  gitignored) par défaut. Pour un travail à plusieurs, migrez vers un backend
  `s3` distant (voir le commentaire dans `infra/aws/providers.tf`) une fois le
  bucket créé.
- **Pas de scale-to-zero** : contrairement à Azure Container Apps, Fargate ne
  descend pas à 0 tâche automatiquement au repos — `desired_count = 1` sur
  les deux services tourne en continu. Pour couper les coûts pendant les
  périodes d'inactivité, `aws ecs update-service --desired-count 0` (arrêt
  manuel) ou ajoutez de l'auto-scaling planifié (Application Auto Scaling).
- **Coûts approximatifs** : ALB (~16€/mois fixe, poste principal), 2 tâches
  Fargate 0.25 vCPU/0.5 Go en continu (~15€/mois à elles deux), ECR/S3
  (quelques centimes). Pensez à `terraform destroy` en fin de projet.
