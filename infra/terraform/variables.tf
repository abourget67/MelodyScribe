variable "aws_region" {
  description = "AWS region for the initial Pitchcraft environment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for AWS resource names."
  type        = string
  default     = "pitchcraft"
}

variable "ssh_public_key_path" {
  description = "Absolute path to the public SSH key on your Mac."
  type        = string
}

variable "ssh_private_key_path" {
  description = "Absolute path to the matching private SSH key on your Mac."
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "Your public IPv4 address in CIDR format, for example 203.0.113.10/32."
  type        = string

  validation {
    condition     = can(cidrhost(var.ssh_allowed_cidr, 0))
    error_message = "ssh_allowed_cidr must be a valid CIDR block."
  }
}

variable "instance_type" {
  description = "x86 EC2 size. t3.small is a practical minimum for an early prototype."
  type        = string
  default     = "t3.small"
}

variable "root_volume_size_gb" {
  description = "Size of the encrypted root EBS volume."
  type        = number
  default     = 30
}

variable "artifact_retention_days" {
  description = "Days to retain uploaded audio and generated files in S3."
  type        = number
  default     = 7
}
