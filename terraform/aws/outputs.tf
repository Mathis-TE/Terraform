output "public_ip_address" {
  description = "Adresse IP publique (Elastic IP) de la VM EstimIA"
  value       = aws_eip.this.public_ip
}
