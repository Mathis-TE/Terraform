variable "project" {
  description = "Préfixe utilisé pour nommer toutes les ressources Azure."
  type        = string
  default     = "estimia"
}

variable "environment" {
  description = "Nom de l'environnement (suffixe des ressources)."
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Région Azure de déploiement."
  type        = string
  default     = "francecentral"
}

variable "backend_placeholder_image" {
  description = "Image utilisée à la création de la Container App backend, avant le premier déploiement CI/CD."
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "frontend_placeholder_image" {
  description = "Image utilisée à la création de la Container App frontend, avant le premier déploiement CI/CD."
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "sas_start" {
  description = "Date de début de validité du SAS de lecture sur le conteneur 'models' (RFC3339)."
  type        = string
  default     = "2024-01-01T00:00:00Z"
}

variable "sas_expiry" {
  description = "Date d'expiration du SAS de lecture sur le conteneur 'models' (RFC3339). À renouveler avant cette date."
  type        = string
  default     = "2030-12-31T23:59:59Z"
}
