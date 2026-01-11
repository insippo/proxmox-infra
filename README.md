# Proxmox Infrastructure as Code

Infrastructure-as-code repository for managing Proxmox VE environments using Ansible, Terraform, and optionally Packer.

## Overview

This repository provides a structured approach to managing Proxmox infrastructure through code, enabling version control, repeatability, and collaboration.

## Tool Order and Rationale

### 1. Ansible (First) - Configuration Management

**Why Ansible comes first:**

Ansible is used for **configuration management** - setting up and maintaining the desired state of existing systems.

- **Host Configuration**: Configure Proxmox hosts (packages, storage, networking)
- **VM Post-Provisioning**: Configure VMs after creation (users, security, applications)
- **Idempotency**: Safe to run multiple times
- **Agentless**: Works over SSH, no agents needed
- **Stateless**: No state files to manage

**Use Cases:**
- Configure Proxmox host settings and storage
- Install and configure software on VMs
- Apply security hardening
- Manage users and permissions
- Configure services and applications

### 2. Terraform (Second) - Infrastructure Provisioning

**Why Terraform comes second:**

Terraform is used for **infrastructure provisioning** - creating and managing infrastructure resources.

- **Resource Creation**: Create and manage VMs declaratively
- **State Management**: Track infrastructure state and changes
- **Lifecycle Management**: Create, update, and destroy resources
- **Dependencies**: Handle resource dependencies automatically

**Use Cases:**
- Create and manage VMs
- Allocate storage volumes
- Configure network resources
- Manage infrastructure lifecycle

**Why not first:**
- Requires infrastructure to exist first (Proxmox host must be configured)
- Better for resource provisioning than configuration
- State management adds complexity

### 3. Packer (Optional) - Image Building

**Why Packer is optional:**

Packer is used for **building VM templates/images** - creating standardized base images.

- **Template Creation**: Build custom VM templates
- **Standardization**: Create consistent base images
- **Automation**: Automate template creation process

**Use Cases:**
- Build custom VM templates
- Standardize base images
- Create golden images for faster provisioning

**When to use:**
- When you need custom templates
- When creating many similar VMs
- When standardizing base configurations

## Directory Structure

```
proxmox-infra/
├── ansible/              # Configuration management (first)
│   ├── inventory.example.yml
│   ├── playbooks/
│   │   ├── proxmox-host.yml    # Configure Proxmox hosts
│   │   └── vm-base.yml          # Configure base VMs
│   └── roles/                   # Reusable Ansible roles
├── terraform/            # Infrastructure provisioning (second)
│   ├── main.tf                  # Main Terraform configuration
│   ├── variables.tf             # Variable definitions
│   └── README.md                # Terraform-specific docs
├── docs/                 # Documentation
│   ├── architecture.md          # Architecture and design decisions
│   ├── recovery-plan.md         # Disaster recovery procedures
│   └── storage-decisions.md     # Storage architecture decisions
├── .gitignore            # Git ignore patterns
└── README.md             # This file
```

## Quick Start

### Prerequisites

- Proxmox VE host(s)
- Ansible (>= 2.9)
- Terraform (>= 1.0)
- SSH access to Proxmox hosts
- Proxmox API access

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/proxmox-infra.git
   cd proxmox-infra
   ```

2. **Configure Ansible:**
   ```bash
   cp ansible/inventory.example.yml ansible/inventory.yml
   # Edit ansible/inventory.yml with your hosts
   ```

3. **Configure Terraform:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars  # If example exists
   # Edit terraform.tfvars with your configuration
   ```

4. **Run Ansible playbooks:**
   ```bash
   cd ansible
   ansible-playbook -i inventory.yml playbooks/proxmox-host.yml
   ```

5. **Initialize and apply Terraform:**
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

## Workflow

1. **Ansible** configures the Proxmox host (storage, networking, packages)
2. **Terraform** provisions VMs using templates
3. **Ansible** configures the provisioned VMs (users, security, applications)
4. **Packer** (optional) creates new templates as needed

## Security

- **Never commit secrets**: Use Ansible Vault, Terraform variables, or environment variables
- **Use example configs**: All provided configs are examples only
- **Rotate credentials**: Regularly update API tokens and passwords
- **Limit access**: Use least-privilege principles for API access

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## Documentation

- [Architecture Documentation](docs/architecture.md) - Detailed architecture and design decisions
- [Recovery Plan](docs/recovery-plan.md) - Disaster recovery procedures
- [Storage Decisions](docs/storage-decisions.md) - Storage architecture decisions

## License

[Specify your license here]

## Support

[Add support information or issue tracker link]

