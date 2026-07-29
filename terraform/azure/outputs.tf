output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "backend_app_name" {
  value = azurerm_container_app.backend.name
}

output "frontend_app_name" {
  value = azurerm_container_app.frontend.name
}

output "backend_fqdn" {
  value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "frontend_fqdn" {
  value = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "storage_account_name" {
  value = azurerm_storage_account.models.name
}

output "storage_container_name" {
  value = azurerm_storage_container.models.name
}

output "storage_sas_token" {
  value     = data.azurerm_storage_account_sas.models_ro.sas
  sensitive = true
}

output "key_vault_name" {
  value = azurerm_key_vault.this.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.this.vault_uri
}
