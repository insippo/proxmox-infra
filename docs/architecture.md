# Architecture Documentation

## Overview

This document describes the architecture and design decisions for the Proxmox infrastructure-as-code setup.

## Tool Order and Rationale

### 1. Ansible (First)

**Why Ansible comes first:**

- **Configuration Management**: Ansible excels at configuring existing systems and ensuring desired state
- **Idempotency**: Safe to run multiple times without side effects
- **Host Configuration**: Perfect for setting up Proxmox hosts, installing packages, configuring storage and networks
- **VM Post-Provisioning**: Ideal for configuring VMs after they're created (users, packages, security)
- **No State Management**: Stateless execution - no state files to manage
- **Agentless**: Works over SSH, no agents required

**Use Cases:**
- Configure Proxmox host settings
- Install and configure software on VMs
- Apply security hardening
- Manage users and permissions
- Configure services and applications

### 2. Terraform (Second)

**Why Terraform comes second:**

- **Resource Provisioning**: Terraform is designed for creating and managing cloud/infrastructure resources
- **State Management**: Tracks infrastructure state and enables change management
- **Declarative Infrastructure**: Define what you want, Terraform figures out how to create it
- **VM Lifecycle**: Create, modify, and destroy VMs declaratively
- **Dependencies**: Handles resource dependencies automatically

**Use Cases:**
- Create and manage VMs
- Allocate storage volumes
- Configure network resources
- Manage infrastructure lifecycle (create, update, destroy)

**Why not first:**
- Requires infrastructure to exist first (Proxmox host must be configured)
- Better for resource provisioning than configuration
- State management adds complexity

### 3. Packer (Optional)

**Why Packer is optional:**

- **Image Building**: Creates VM templates/images for consistent VM provisioning
- **Template Management**: Build standardized base images with pre-installed software
- **Not Always Needed**: If using existing templates or manual image creation, Packer may not be necessary
- **Useful for Scale**: Becomes more valuable when creating many similar VMs

**Use Cases:**
- Build custom VM templates
- Standardize base images
- Automate template creation with specific configurations
- Create golden images for faster VM provisioning

## Workflow

1. **Ansible** configures the Proxmox host
2. **Terraform** provisions VMs using templates
3. **cloud-init** bootstraps VM access (SSH keys, user)
4. **Ansible** configures the provisioned VMs
5. **Packer** (optional) creates new templates as needed

## VM Bootstrap Lifecycle

**Complete flow from creation to configuration:**

### Step 1: Terraform Creates VM
- Terraform clones VM from template
- VM is created with cloud-init enabled
- VM boots and starts cloud-init process

### Step 2: cloud-init Injects Access
- cloud-init creates user account (from `cloudinit_user` variable)
- cloud-init injects SSH public keys (from `cloudinit_ssh_keys` variable)
- Network is configured (DHCP by default)
- VM becomes SSH-accessible immediately after boot

### Step 3: Ansible Configures VM
- Ansible connects via SSH using the injected keys
- Ansible applies configuration (packages, security, services)
- VM is fully configured and ready for use

**Key Benefits:**
- **No manual steps**: VM is immediately accessible by Ansible
- **Key-based only**: No passwords, secure by default
- **Declarative**: All configuration in code (Terraform + Ansible)
- **Idempotent**: Safe to run multiple times

**Configuration Sources:**
- Terraform variables come from `terraform.tfvars` (not committed)
- SSH keys are provided via Terraform variables
- Ansible uses the same SSH keys for access
- No hardcoded values in code

## Inventory & Lifecycle Wiring

### Static Inventory Approach

**Why static inventory first:**
- **Explicit and auditable**: All hosts are visible in one file
- **Simple and obvious**: Easy to understand and maintain
- **No dependencies**: Works without Terraform outputs or API access
- **Version controlled**: Inventory changes go through code review
- **Safe**: No risk of accidentally managing wrong hosts

**Future enhancement:**
- Dynamic inventory from Terraform outputs (planned)
- Automatic VM discovery via Proxmox API (optional)

### Inventory Groups

**`proxmox_hosts`** group:
- Contains Proxmox VE hypervisor hosts
- Used by `ansible/playbooks/proxmox-host.yml`
- Root SSH access (LAN-only)
- Configured first, before VM creation

**`vms`** group:
- Contains Linux VMs created via Terraform + cloud-init
- Used by `ansible/playbooks/vm-base.yml`
- User SSH access (injected via cloud-init)
- Configured after VM creation

### VM Lifecycle Wiring

**Complete workflow:**

1. **Terraform creates VM**
   - VM is provisioned with cloud-init
   - SSH keys and user are injected
   - VM becomes SSH-accessible

2. **Operator adds VM to inventory**
   - Add VM entry to `ansible/inventory.yml`
   - Use VM's IP address or hostname
   - Set `ansible_user` to match `cloudinit_user` from Terraform

3. **Ansible applies base configuration**
   - Run `ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms`
   - Ansible connects via SSH (using keys from cloud-init)
   - Base configuration is applied (packages, timezone, qemu-guest-agent)

**Why manual inventory step:**
- Operator verifies VM is accessible before Ansible runs
- Explicit control over which VMs are managed
- Easy to audit what's in inventory
- No risk of managing unintended VMs

## Directory Structure

```
proxmox-infra/
├── ansible/          # Configuration management (first)
│   ├── inventory.example.yml  # Example inventory (committed)
│   ├── inventory.yml          # Actual inventory (not committed)
│   ├── playbooks/             # Playbooks for hosts and VMs
│   ├── roles/                  # Reusable roles
│   └── group_vars/             # Group-specific variables
├── terraform/        # Infrastructure provisioning (second)
└── docs/            # Documentation
```

## VM Base vs Proxmox Host Configuration

### Separation of Concerns

**Proxmox Host Configuration** (`ansible/playbooks/proxmox-host.yml`):
- **Target**: Proxmox VE hypervisor hosts
- **Purpose**: Configure the infrastructure layer
- **Scope**: 
  - Host OS hardening (SSH, sysctl, journald)
  - Base packages for host management
  - Time synchronization (chrony)
  - Storage and network configuration (not in this playbook)
- **Access**: Root SSH access (LAN-only)
- **When**: First, before any VMs are created

**VM Base Configuration** (`ansible/playbooks/vm-base.yml`):
- **Target**: Linux VMs created via Terraform + cloud-init
- **Purpose**: Configure the guest OS layer
- **Scope**:
  - Essential packages (vim, curl, ca-certificates)
  - QEMU Guest Agent (enables Proxmox features)
  - Timezone configuration
  - Basic SSH safety (key-only, no root login)
- **Access**: User SSH access (injected via cloud-init)
- **When**: After Terraform creates VMs and cloud-init bootstraps access

### Why Separate?

1. **Different Targets**: Hosts vs VMs have different requirements
2. **Different Access**: Root on hosts vs regular user on VMs
3. **Different Lifecycle**: Hosts are long-lived, VMs are ephemeral
4. **Different Hardening**: Hosts need hypervisor-level security, VMs need guest OS security
5. **Reusability**: VM playbook can be used for any Terraform-created VM

### Workflow

1. **Ansible** configures Proxmox host (host hardening, packages)
2. **Terraform** creates VMs (infrastructure provisioning)
3. **cloud-init** bootstraps VM access (SSH keys, user)
4. **Ansible** configures VMs (guest OS configuration)

## SSH Policy (Proxmox hosts)

- Key-based only; password authentication disabled (LAN-only access assumed)
- Root login allowed only with keys (`PermitRootLogin prohibit-password`)
- Keep `authorized_keys` present before applying hardening to avoid lockout
- Client keepalives enabled (300s interval, 2 attempts) to avoid stale sessions
- X11 and agent forwarding disabled by default

## SSH Policy (VMs)

- Key-based only; password authentication disabled
- Root login disabled (use regular user with sudo)
- SSH keys injected via cloud-init (from Terraform)
- LAN-friendly configuration (not over-hardened)

## Admin User Policy

- Optional admin user (disabled by default) with key-only access
- Passwordless sudo via `/etc/sudoers.d/<user>`; idempotent management
- Root remains as fallback for LAN/console recovery and Proxmox cluster maintenance
- Before enabling, populate example keys in `admin_user_ssh_keys` with real keys and set `admin_user_enabled: true`

