locals {
  name_prefix = "${var.project}-${var.environment}"
  # Le nom d'un storage account doit être global, 3-24 caractères, alphanumérique minuscule.
  storage_name = substr(replace("${var.project}st${var.environment}", "-", ""), 0, 24)
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name_prefix}"
  location = var.location
}

# ---------------------------------------------------------------------------
# Registre de conteneurs (images backend/frontend poussées par la CI/CD)
# ---------------------------------------------------------------------------
resource "azurerm_container_registry" "this" {
  name                = replace("acr${local.name_prefix}", "-", "")
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "Basic"
  admin_enabled       = true
}

# ---------------------------------------------------------------------------
# Stockage du modèle ML (.pkl) — téléchargé par le backend au démarrage
# ---------------------------------------------------------------------------
resource "azurerm_storage_account" "models" {
  name                     = local.storage_name
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "models" {
  name                  = "models"
  storage_account_name  = azurerm_storage_account.models.name
  container_access_type = "private"
}

# SAS de lecture seule sur le conteneur "models", consommée par
# backend/scripts/download_model.py au démarrage du conteneur.
data "azurerm_storage_account_sas" "models_ro" {
  connection_string = azurerm_storage_account.models.primary_connection_string
  https_only        = true

  resource_types {
    service   = false
    container = false
    object    = true
  }

  services {
    blob  = true
    queue = false
    table = false
    file  = false
  }

  start  = var.sas_start
  expiry = var.sas_expiry

  permissions {
    read    = true
    write   = false
    delete  = false
    list    = false
    add     = false
    create  = false
    update  = false
    process = false
    tag     = false
    filter  = false
  }
}

# ---------------------------------------------------------------------------
# Environnement Azure Container Apps
# ---------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${local.name_prefix}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
}

# ---------------------------------------------------------------------------
# Container App — Backend FastAPI
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "backend" {
  name                         = "${local.name_prefix}-backend"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"

  template {
    container {
      name  = "backend"
      image = var.backend_placeholder_image
      # Plan Consumption (serverless, scale-to-zero) : pas de VM à choisir,
      # 0.25 vCPU / 0.5Gi est le plus petit palier autorisé par Azure Container Apps.
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "AZURE_STORAGE_ACCOUNT_URL"
        value = azurerm_storage_account.models.primary_blob_endpoint
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = azurerm_storage_container.models.name
      }
      env {
        name        = "AZURE_STORAGE_SAS_TOKEN"
        secret_name = "storage-sas-token"
      }
    }

    min_replicas = 0
    max_replicas = 2
  }

  secret {
    name  = "storage-sas-token"
    value = data.azurerm_storage_account_sas.models_ro.sas
  }

  secret {
    name  = "registry-password"
    value = azurerm_container_registry.this.admin_password
  }

  registry {
    server               = azurerm_container_registry.this.login_server
    username             = azurerm_container_registry.this.admin_username
    password_secret_name = "registry-password"
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # L'image est mise à jour par la CI/CD (az containerapp update), pas par Terraform.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# ---------------------------------------------------------------------------
# Container App — Frontend Next.js
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "frontend" {
  name                         = "${local.name_prefix}-frontend"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"

  template {
    container {
      name   = "frontend"
      image  = var.frontend_placeholder_image
      cpu    = 0.25
      memory = "0.5Gi"
    }

    min_replicas = 0
    max_replicas = 2
  }

  secret {
    name  = "registry-password"
    value = azurerm_container_registry.this.admin_password
  }

  registry {
    server               = azurerm_container_registry.this.login_server
    username             = azurerm_container_registry.this.admin_username
    password_secret_name = "registry-password"
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # L'image (buildée avec NEXT_PUBLIC_API_URL=<fqdn backend>) est mise à jour par la CI/CD.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}
