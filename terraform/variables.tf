variable "enable_briefings" {
  description = "Whether to enable scheduled daily and weekly briefing EventBridge rules"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
}

variable "environment" {
  description = "Deployment environment: personal or demo"
  type        = string
  validation {
    condition     = contains(["personal", "demo"], var.environment)
    error_message = "Environment must be 'personal' or 'demo'."
  }
}

variable "sheets_url" {
  description = "Google Sheets CSV export URL for the life log"
  type        = string
  sensitive   = true
}

variable "ses_sender" {
  description = "Verified SES sender email address"
  type        = string
}

variable "ses_recipient" {
  description = "Email address to receive briefings"
  type        = string
}

variable "dashboard_name" {
  description = "Display name for the dashboard (used in email subjects)"
  type        = string
}

variable "daily_briefing_schedule" {
  description = "EventBridge cron schedule for daily briefing (UTC)"
  type        = string
  default     = "cron(0 11 * * ? *)"  # 7 AM ET
}

variable "weekly_briefing_schedule" {
  description = "EventBridge cron schedule for weekly briefing (UTC)"
  type        = string
  default     = "cron(0 22 ? * SUN *)"  # 6 PM ET Sunday
}

variable "refresh_schedule" {
  description = "EventBridge cron schedule for data refresh (UTC)"
  type        = string
  default     = "cron(0 10 * * ? *)"  # 6 AM ET daily
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "lambda_timeout" {
  description = "Default Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "agent_lambda_timeout" {
  description = "Timeout for agent Lambda in seconds (longer due to multi-agent calls)"
  type        = number
  default     = 900
}
