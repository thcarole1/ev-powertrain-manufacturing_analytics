output "msk_cluster_arn" {
  value = aws_msk_serverless_cluster.this.arn
}

output "msk_bootstrap_brokers" {
  value       = aws_msk_serverless_cluster.this.bootstrap_brokers_sasl_iam
  description = "Adresse de connexion IAM, à utiliser depuis le bastion uniquement (pas d'accès public)"
}

output "bastion_instance_id" {
  value       = aws_instance.bastion.id
  description = "Utilisé pour se connecter via : aws ssm start-session --target <id>"
}
