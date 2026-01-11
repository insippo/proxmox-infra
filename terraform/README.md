# Terraform Configuration

This directory contains Terraform configurations for managing Proxmox infrastructure as code.

## Purpose

Terraform is used **second** (after Ansible) to:
- Provision and manage VM resources declaratively
- Maintain infrastructure state
- Enable version-controlled infrastructure changes
- Support infrastructure lifecycle management

## Setup

1. Install Terraform (>= 1.0)
2. Configure provider credentials via variables
3. Initialize: `terraform init`
4. Plan: `terraform plan`
5. Apply: `terraform apply`

## Variables

Create a `terraform.tfvars` file (not committed) with your configuration:

```hcl
proxmox_api_url          = "https://proxmox.example.com:8006/api2/json"
proxmox_api_token_id     = "root@pam!terraform"
proxmox_api_token_secret = "your-secret-here"
proxmox_node             = "pve"
```

## State Management

Configure a remote backend (S3, Azure Storage, etc.) for state management in production.

## Security

- Never commit `terraform.tfvars` or `.tfstate` files
- Use environment variables or secret management for sensitive values
- Consider using Terraform Cloud or similar for team collaboration

