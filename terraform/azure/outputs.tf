output "public_ip_address" {
  description = "Adresse IP publique de la VM EstimIA"
  value       = azurerm_public_ip.this.ip_address
}
