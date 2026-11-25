variable "project_name" {
  type        = string
  description = "Lowercase resource prefix."
  default     = "aws-sre-agent"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,25}$", var.project_name))
    error_message = "project_name must be 3-26 lowercase letters, digits, or hyphens."
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "allowed_bedrock_model_arns" {
  type        = list(string)
  description = "Restrict to approved Bedrock model/inference profile ARNs."
  default     = ["*"]
}

variable "allowed_log_group_arns" {
  type        = list(string)
  description = "CloudWatch log group ARNs the agent may read."
  default     = ["arn:aws:logs:*:*:log-group:/aws/*"]
}

variable "enable_s3_versioning" {
  type    = bool
  default = true
}
