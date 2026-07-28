variable "location" {
  description = "Région Azure de déploiement. Restreint par la politique 'Allowed resource deployment regions' de cet abonnement (Azure for Students) à : swedencentral, italynorth, spaincentral, norwayeast, germanywestcentral."
  type        = string
  default     = "italynorth"
}

variable "vm_size" {
  description = "Taille de la VM (Standard_B1s = éligible Free Tier Azure 12 mois)"
  type        = string
  default     = "Standard_B1s"
}

variable "admin_username" {
  description = "Nom d'utilisateur admin de la VM"
  type        = string
  default     = "estimia"
}

variable "ssh_public_key_path" {
  description = "Chemin vers la clé publique SSH locale. Azure exige une clé RSA (ed25519 non supporté) — clé dédiée générée dans ~/.ssh/estimia_azure_rsa.pub"
  type        = string
  default     = "~/.ssh/estimia_azure_rsa.pub"
}

variable "repo_url" {
  description = "URL du repo Git à cloner sur la VM"
  type        = string
  default     = "https://github.com/Diane2909/EstimIA_PA.git"
}
