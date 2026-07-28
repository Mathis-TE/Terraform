# EstimIA — Infra cloud (Terraform)

Deux configurations Terraform indépendantes, une par cloud — chacune avec son propre état, jamais appliquées ensemble automatiquement :

- **[`aws/`](aws/README.md)** — instance EC2 (`t3.micro`, Free Tier), le déploiement cible actuel.
- **[`azure/`](azure/README.md)** — VM Azure (`Standard_B1s`, Free Tier), conservée en option/backup.

Les deux provisionnent la même architecture (une VM Ubuntu, Docker + Docker Compose + git installés via cloud-init, sécurisée par SSH + HTTP uniquement) — seul le provider cloud change. Va dans le sous-dossier correspondant et suis son `README.md` pour déployer.
