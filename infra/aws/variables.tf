variable "project" {
  description = "Préfixe utilisé pour nommer toutes les ressources AWS."
  type        = string
  default     = "estimia"
}

variable "environment" {
  description = "Nom de l'environnement (suffixe des ressources)."
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "Région AWS de déploiement."
  type        = string
  default     = "eu-west-3" # Paris
}

variable "backend_placeholder_image" {
  description = "Image utilisée à la création du service ECS backend, avant le premier déploiement CI/CD."
  type        = string
  default     = "public.ecr.aws/docker/library/hello-world:latest"
}

variable "frontend_placeholder_image" {
  description = "Image utilisée à la création du service ECS frontend, avant le premier déploiement CI/CD."
  type        = string
  default     = "public.ecr.aws/docker/library/hello-world:latest"
}

variable "backend_container_port" {
  description = "Port exposé par le conteneur backend (FastAPI/uvicorn)."
  type        = number
  default     = 8000
}

variable "frontend_container_port" {
  description = "Port exposé par le conteneur frontend (Next.js standalone)."
  type        = number
  default     = 3000
}

variable "alb_backend_listener_port" {
  description = "Port public de l'ALB routé vers le backend (pas de nom de domaine, donc pas de routage par host)."
  type        = number
  default     = 8080
}

variable "alb_frontend_listener_port" {
  description = "Port public de l'ALB routé vers le frontend."
  type        = number
  default     = 80
}
