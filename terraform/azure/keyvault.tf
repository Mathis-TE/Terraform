# ---------------------------------------------------------------------------
# Key Vault — centralise les secrets sensibles générés par Terraform
# (mot de passe admin ACR, SAS du conteneur "models"), pour éviter qu'ils ne
# vivent uniquement dans le state et permettre un accès/audit contrôlé.
# ---------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "this" {
  name                = "kv-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled = false

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge", "Recover",
    ]
  }
}

resource "azurerm_key_vault_secret" "acr_admin_password" {
  name         = "acr-admin-password"
  value        = azurerm_container_registry.this.admin_password
  key_vault_id = azurerm_key_vault.this.id
}

resource "azurerm_key_vault_secret" "storage_sas_token" {
  name         = "storage-sas-token"
  value        = data.azurerm_storage_account_sas.models_ro.sas
  key_vault_id = azurerm_key_vault.this.id
}
