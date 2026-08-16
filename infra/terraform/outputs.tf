output "api_base_url" {
  description = "Temporary HTTP API base URL. Point the frontend here during development."
  value       = "http://${aws_instance.api.public_dns}"
}

output "api_health_url" {
  description = "Health endpoint served by Nginx after cloud-init completes."
  value       = "http://${aws_instance.api.public_dns}/health"
}

output "ec2_public_ip" {
  description = "Public IPv4 address for SSH and troubleshooting."
  value       = aws_instance.api.public_ip
}

output "artifact_bucket_name" {
  description = "Private S3 bucket for uploaded audio and generated files."
  value       = aws_s3_bucket.artifacts.bucket
}

output "ssh_command" {
  description = "Command to connect to the instance from the Mac that owns the key."
  value       = "ssh -i ${var.ssh_private_key_path} ec2-user@${aws_instance.api.public_dns}"
}
