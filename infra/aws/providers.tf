terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # État Terraform stocké en local par défaut (terraform.tfstate, gitignored).
  # Pour un travail en équipe, migrer vers un backend distant une fois le
  # bucket S3 créé (voir docs/aws-setup.md) :
  #
  # backend "s3" {
  #   bucket = "<nom-unique>"
  #   key    = "estimia.tfstate"
  #   region = "eu-west-3"
  # }
}

provider "aws" {
  region = var.aws_region
}
