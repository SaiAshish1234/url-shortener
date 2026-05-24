variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "urlshortener"
}

variable "env" {
  description = "Deployment environment (staging | prod)"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["staging", "prod"], var.env)
    error_message = "env must be 'staging' or 'prod'"
  }
}

variable "base_url" {
  description = "Base URL for short links. Leave empty to use the CloudFront URL."
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email address to receive CloudWatch alarm notifications"
  type        = string
  default     = ""
}
