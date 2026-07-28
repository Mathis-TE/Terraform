variable "aws_region" {
  description = "Région AWS de déploiement"
  type        = string
  default     = "eu-west-3" # Paris
}

variable "instance_type" {
  description = "Type d'instance EC2 (t3.micro = éligible Free Tier 12 mois)"
  type        = string
  default     = "t3.micro"
}

variable "admin_username" {
  description = "Utilisateur SSH de la VM. Fixé par l'AMI Ubuntu Canonical (toujours 'ubuntu') — ce champ ne fait que paramétrer le cloud-init (chemin du clone, permissions), il ne crée pas d'utilisateur custom."
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key_path" {
  description = "Chemin vers la clé publique SSH locale (ssh-keygen si besoin d'en générer une)"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "repo_url" {
  description = "URL du repo Git à cloner sur la VM"
  type        = string
  default     = "https://github.com/Diane2909/EstimIA_PA.git"
}
