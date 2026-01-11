# Terraform Configuration

This directory contains Terraform configurations for managing Proxmox infrastructure as code.

## Purpose

Terraform is used **second** (after Ansible) to:
- **Provision and manage VM resources declaratively** - Create, update, and destroy VMs
- **Maintain infrastructure state** - Track what exists and what should exist
- **Enable version-controlled infrastructure changes** - Infrastructure changes go through code review
- **Support infrastructure lifecycle management** - Consistent VM provisioning across environments

## Separation of Concerns: Terraform vs Ansible

### Terraform (This Directory)
- **What**: Infrastructure provisioning (VMs, storage volumes, network resources)
- **When**: First, to create the infrastructure resources
- **State**: Maintains state of what resources exist
- **Scope**: Resource lifecycle (create, modify, destroy)

### Ansible (../ansible/)
- **What**: Configuration management (OS settings, packages, services)
- **When**: After Terraform, to configure the provisioned resources
- **State**: Stateless, ensures desired configuration
- **Scope**: Configuration and application deployment

**Workflow:**
1. Terraform creates VMs
2. Ansible configures the VMs (users, packages, security)

## Setup

1. Install Terraform (>= 1.0)
2. Create `terraform.tfvars` file (see Variables section below)
3. Initialize: `terraform init`
4. Plan: `terraform plan`
5. Apply: `terraform apply`

## Variables

**All configuration values come from variables or `.tfvars` files.**

Create a `terraform.tfvars` file (not committed to git) with your configuration:

```hcl
# Proxmox API connection
proxmox_api_url          = "https://proxmox.example.com:8006/api2/json"
proxmox_api_token_id     = "root@pam!terraform"
proxmox_api_token_secret = "your-secret-here"

# Proxmox node
proxmox_node = "pve"

# VM defaults (adjust as needed)
vm_default_cores    = 2
vm_default_sockets  = 1
vm_default_memory   = 2048
vm_default_disk_size = "20G"
vm_default_storage  = "local-lvm"
vm_default_bridge   = "vmbr0"

# Base template (must exist in Proxmox)
base_template = "ubuntu-cloud-template"

# Cloud-init configuration (for Ansible access)
cloudinit_user = "admin"
cloudinit_ssh_keys = [
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAYourRealKeyHere comment@yourhost",
  "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQYourRealKeyHere comment@yourhost"
]
```

**Important:**
- `terraform.tfvars` is in `.gitignore` (never commit secrets)
- Use environment variables (`TF_VAR_*`) for sensitive values
- Example values in `variables.tf` are defaults only

## VM Bootstrap Flow: Terraform → cloud-init → Ansible

**The complete lifecycle:**

1. **Terraform creates VM** with cloud-init enabled
   - VM is cloned from template
   - cloud-init injects SSH keys and creates user
   - VM boots and applies cloud-init configuration

2. **cloud-init bootstraps access**
   - Creates user account (from `cloudinit_user` variable)
   - Injects SSH public keys (from `cloudinit_ssh_keys` variable)
   - Configures network (DHCP by default, no static IPs)
   - VM becomes SSH-accessible immediately after boot

3. **Ansible configures VM**
   - Ansible connects via SSH using the injected keys
   - Applies configuration (packages, security, services)
   - VM is fully configured and ready for use

**Why this works:**
- Terraform provisions infrastructure (VM exists)
- cloud-init provides initial access (SSH keys, user)
- Ansible manages configuration (no manual steps needed)

**SSH Keys:**
- SSH public keys are provided via `cloudinit_ssh_keys` variable
- Keys come from your `terraform.tfvars` file (not committed)
- Same keys used for Ansible access
- No passwords needed (key-based only)

**Important:**
- `terraform.tfvars` is in `.gitignore` (never commit secrets or keys)
- Replace example keys in `variables.tf` with your real keys in `.tfvars`
- The `cloudinit_ssh_keys` default values are examples only

## Example Resources

The `main.tf` file includes an example VM resource demonstrating:
- Declarative VM definition
- Variable-based configuration (no hardcoded values)
- cloud-init bootstrap for immediate Ansible access
- Minimal configuration (name, cores, memory, disk)
- No network IP assumptions (uses DHCP)

## State Management

Configure a remote backend (S3, Azure Storage, etc.) for state management in production:

```hcl
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "proxmox-infra/terraform.tfstate"
    region = "us-east-1"
  }
}
```

## Safety Rules

**⚠️ CRITICAL: Follow these rules to prevent accidental VM duplication or destruction**

### Never Run `terraform apply` Twice in a Row

**Always follow this sequence:**

1. **Check existing resources first:**
   ```bash
   # Verify what exists in Proxmox
   # Check for duplicate VMs
   ```

2. **Review Terraform state:**
   ```bash
   terraform state list
   # Verify expected resources are tracked
   ```

3. **Always run plan first:**
   ```bash
   terraform plan
   # READ THE OUTPUT CAREFULLY
   # Verify: no unexpected creates, no unexpected destroys
   ```

4. **Only then apply:**
   ```bash
   terraform apply
   # Review plan output again before confirming
   ```

### Always Run `terraform plan` and Read Output

**Before every `terraform apply`:**
- Run `terraform plan` first
- Read the entire plan output
- Verify the plan matches your expectations
- Check for unexpected resource creation or destruction
- If plan shows unexpected changes, **STOP** and investigate

### Terraform Does Not Auto-Detect Existing VMs

**Critical**: Terraform only knows about resources in its state file. If a VM exists in Proxmox but not in Terraform state, Terraform will try to create it again, resulting in duplicates.

**Solution**: Always import existing VMs before applying:
```bash
terraform import proxmox_virtual_environment_vm.monitoring_prometheus[0] proxmox/123
```

### Manual Proxmox Changes Must Be Documented

If you make changes in Proxmox Web UI or CLI:
1. **Document the change** - What was changed and why
2. **Update Terraform state** - Use `terraform import` or `terraform state rm` as appropriate
3. **Verify with plan** - Run `terraform plan` to ensure state matches reality

**Never** make manual Proxmox changes without updating Terraform state.

## Security

- **Never commit** `terraform.tfvars` or `.tfstate` files
- Use environment variables or secret management for sensitive values
- Consider using Terraform Cloud or similar for team collaboration
- Review storage policy (`../docs/storage-policy.md`) before provisioning storage

