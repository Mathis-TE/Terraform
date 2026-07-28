# EstimIA — Infra AWS (Terraform)

Provisionne une instance EC2 Ubuntu unique (`t3.micro`, éligible Free Tier 12 mois) qui installe Docker + Docker Compose + git au premier démarrage et clone ce repo.

## Prérequis

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Une clé SSH locale (`ssh-keygen -t rsa -b 4096` si tu n'en as pas)
- Un compte AWS actif (carte bancaire requise pour activer le Free Tier, même si l'usage prévu reste dans les limites gratuites)

## Étape 1 — Authentification

```bash
aws configure
```

Renseigne ta clé d'accès AWS (Access Key ID / Secret Access Key), créées depuis la console AWS (IAM).

## Étape 2 — Provisionner l'infrastructure

```bash
cd terraform/aws
terraform init
terraform plan      # vérifie ce qui va être créé, ne provisionne rien
terraform apply      # crée réellement les ressources AWS
```

À la fin, `terraform output public_ip_address` donne l'IP publique (Elastic IP) de l'instance.

## Étape 3 — Copier les artefacts du modèle ML

Les fichiers `.pkl` (`backend/model/`) sont volontairement absents du repo Git (gitignorés, ~140 Mo). Une fois l'instance prête (laisser 1-2 minutes après `apply` pour que le cloud-init termine), les copier manuellement :

```bash
scp backend/model/*.pkl ubuntu@<public_ip_address>:~/EstimIA_PA/backend/model/
```

## Étape 4 — Lancer l'application

```bash
ssh ubuntu@<public_ip_address>
cd EstimIA_PA
docker compose up -d --build
```

L'application est alors accessible sur `http://<public_ip_address>` (port 80, via nginx).

## Nettoyage

```bash
terraform destroy
```

Détruit toutes les ressources AWS créées (instance EC2, Elastic IP, security group) — à faire pour ne pas consommer inutilement le quota Free Tier ni risquer des frais après les 12 mois.
