terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }

  # État Terraform stocké en local par défaut (terraform.tfstate, gitignored).
  # Pour un travail en équipe, migrer vers un backend distant une fois le
  # storage account créé (voir docs/azure-setup.md) :
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-estimia-tfstate"
  #   storage_account_name = "<nom-unique>"
  #   container_name       = "tfstate"
  #   key                  = "estimia.tfstate"
  # }
}

provider "azurerm" {
  features {}
}
