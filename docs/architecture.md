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
3. **Ansible** configures the provisioned VMs
4. **Packer** (optional) creates new templates as needed

## Directory Structure

```
proxmox-infra/
├── ansible/          # Configuration management (first)
├── terraform/        # Infrastructure provisioning (second)
└── docs/            # Documentation
```

