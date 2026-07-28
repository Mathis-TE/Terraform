# EstimIA — Infra Azure (Terraform)

Provisionne une VM Ubuntu unique (Standard_B1s, éligible Free Tier Azure 12 mois) qui installe Docker + Docker Compose + git au premier démarrage et clone ce repo.

## Prérequis

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- Une clé SSH locale (`ssh-keygen -t rsa -b 4096` si tu n'en as pas)
- Un compte Azure actif

## Étape 1 — Authentification

```bash
az login
```

## Étape 2 — Provisionner l'infrastructure

```bash
cd terraform/azure
terraform init
terraform plan      # vérifie ce qui va être créé, ne provisionne rien
terraform apply      # crée réellement les ressources Azure
```

À la fin, `terraform output public_ip_address` donne l'IP publique de la VM.

## Étape 3 — Copier les artefacts du modèle ML

Les fichiers `.pkl` (`backend/model/`) sont volontairement absents du repo Git (gitignorés, ~140 Mo). Une fois la VM prête (laisser 1-2 minutes après `apply` pour que le cloud-init termine), les copier manuellement :

```bash
scp backend/model/*.pkl estimia@<public_ip_address>:~/EstimIA_PA/backend/model/
```

## Étape 4 — Lancer l'application

```bash
ssh estimia@<public_ip_address>
cd EstimIA_PA
docker compose up -d --build
```

L'application est alors accessible sur `http://<public_ip_address>` (port 80, via nginx).

## Nettoyage

```bash
terraform destroy
```

Détruit toutes les ressources Azure créées — à faire pour ne pas consommer inutilement le quota Free Tier.
