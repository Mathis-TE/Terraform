output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "backend_url" {
  value = "http://${aws_lb.this.dns_name}:${var.alb_backend_listener_port}"
}

output "frontend_url" {
  value = "http://${aws_lb.this.dns_name}:${var.alb_frontend_listener_port}"
}

output "ecr_backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecs_backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecs_frontend_service_name" {
  value = aws_ecs_service.frontend.name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.models.bucket
}

output "backend_task_family" {
  value = aws_ecs_task_definition.backend.family
}

output "frontend_task_family" {
  value = aws_ecs_task_definition.frontend.family
}
