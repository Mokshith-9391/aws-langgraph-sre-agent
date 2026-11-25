provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "Terraform"
      Purpose   = "SRE-Agent"
    }
  }
}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
resource "random_id" "suffix" {
  byte_length = 3
}

resource "aws_ecr_repository" "agent" {
  name                 = var.project_name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}
resource "aws_cloudwatch_log_group" "agent" {
  name              = "/aws/bedrock-agentcore/${var.project_name}"
  retention_in_days = 90
}
resource "aws_s3_bucket" "evidence" {
  bucket        = "${var.project_name}-evidence-${data.aws_caller_identity.current.account_id}-${random_id.suffix.hex}"
  force_destroy = false
}
resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Suspended"
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket                  = aws_s3_bucket.evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_dynamodb_table" "incidents" {
  name         = "${var.project_name}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "incident_id"
  attribute {
    name = "incident_id"
    type = "S"
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = true
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "agent" {
  name               = "${var.project_name}-runtime"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}
data "aws_iam_policy_document" "agent" {
  statement {
    sid       = "BedrockModelInvoke"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = var.allowed_bedrock_model_arns
  }
  statement {
    sid = "CloudWatchReadOnlyInvestigation"
    actions = [
      "cloudwatch:DescribeAlarms", "cloudwatch:DescribeAlarmsForMetric",
      "cloudwatch:GetMetricData", "cloudwatch:GetMetricStatistics",
      "logs:StartQuery", "logs:GetQueryResults", "logs:DescribeLogGroups",
      "logs:FilterLogEvents", "logs:GetLogEvents"
    ]
    resources = var.allowed_log_group_arns
  }
  statement {
    sid       = "WriteAgentLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.agent.arn}:*"]
  }
  statement {
    sid       = "IncidentTableAccess"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.incidents.arn]
  }
  statement {
    sid       = "EvidenceBucketAccess"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.evidence.arn}/*"]
  }
}
resource "aws_iam_role_policy" "agent" {
  name   = "${var.project_name}-runtime-policy"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent.json
}
