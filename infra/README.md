# Pitchcraft AWS infrastructure

This Terraform stack creates one development environment:

- A dedicated VPC and public subnet
- One Amazon Linux 2023 x86 EC2 instance for the API and audio worker
- Nginx on ports 80/443, with a `GET /health` response immediately after boot
- A private, encrypted S3 bucket for uploads and generated PDFs/MIDI/MusicXML
- A least-privilege EC2 IAM role that can list, read, and write S3 artifacts
- SSH access limited to one public IP address supplied by you

It deliberately does **not** create an API Gateway, a database, a load balancer,
or a domain name. One EC2 API host is the right first deployment for Pitchcraft;
add those services after the frontend and API have real usage.

## Before you run Terraform

1. Install the AWS CLI and Terraform on your Mac:

   ```bash
   brew install awscli terraform
   ```

2. In the AWS console, create an IAM user for local Terraform administration.
   Enable MFA and create access keys only for that user. Do not use root-account
   keys. For this first environment, attach `AdministratorAccess`; reduce this
   to a Terraform-specific policy once the infrastructure stops changing.

3. Configure the CLI profile and verify it:

   ```bash
   aws configure --profile pitchcraft
   aws sts get-caller-identity --profile pitchcraft
   export AWS_PROFILE=pitchcraft
   ```

4. Create a dedicated SSH key, then capture your current public IP. Keep the
   private key on your Mac and never commit it.

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/pitchcraft_ec2 -C "pitchcraft-ec2"
   curl https://checkip.amazonaws.com
   ```

## Create the infrastructure

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set the SSH public-key path and the IP from the last step.
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

Terraform prints the API health URL, S3 bucket name, and SSH command. Wait two
or three minutes for cloud-init, then check the host:

```bash
curl "$(terraform output -raw api_health_url)"
$(terraform output -raw ssh_command)
```

The health route works immediately. All other paths are reserved for the
FastAPI service, which should bind to `127.0.0.1:8000`; Nginx proxies public
traffic to it.

## Frontend and API contract

Have the frontend read its API base URL from an environment variable such as
`VITE_API_BASE_URL`. Initially it should be Terraform's `api_base_url` output.
The API should expose asynchronous jobs, not hold an HTTP connection while
Demucs runs:

- `POST /jobs` uploads or receives an S3 object key and starts work
- `GET /jobs/{id}` returns queued/running/failed/completed state
- `GET /jobs/{id}/outputs` returns signed S3 download URLs

The EC2 role can access only the private artifact bucket; create presigned URLs
from the API for browser downloads. Do not make the bucket public.

## Cost and cleanup

`t3.small` is appropriate only for an early prototype and may still be slow or
memory-constrained for Demucs. Monitor the AWS billing/credits dashboard and
set a budget alert before applying.

Destroy everything when you are not actively testing:

```bash
terraform destroy
```

S3 objects are retained for the configured lifecycle window. Terraform will
not delete a non-empty bucket by default; allow the lifecycle rule to expire
objects first, or empty it intentionally before running `destroy`.
