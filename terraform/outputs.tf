output "ecr_repository_name" {
  value = aws_ecr_repository.agent.name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.agent.repository_url
}

output "agent_execution_role_arn" {
  value = aws_iam_role.agent.arn
}

output "agent_log_group_name" {
  value = aws_cloudwatch_log_group.agent.name
}

output "incident_table_name" {
  value = aws_dynamodb_table.incidents.name
}

output "evidence_bucket_name" {
  value = aws_s3_bucket.evidence.bucket
}
