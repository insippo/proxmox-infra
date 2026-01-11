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

### Dynamic Inventory (Terraform Output)

**Optional alternative to static inventory:**

**How it works:**
- Terraform outputs VM information (name, SSH user, IP address)
- Dynamic inventory script (`ansible/inventory/terraform.py`) reads Terraform outputs
- Generates Ansible JSON inventory automatically
- VMs are grouped under `vms` group

**When to use:**
- **Many VMs**: Managing dozens or hundreds of VMs
- **Frequent changes**: VMs are created/destroyed frequently
- **Terraform-managed**: All VMs are created via Terraform
- **Automation**: Part of automated CI/CD pipeline

**When NOT to use:**
- **Small scale**: Few VMs, static inventory is simpler
- **Mixed sources**: VMs created manually or by other tools
- **IP discovery needed**: Terraform outputs don't include IPs (requires Proxmox API)
- **Explicit control needed**: Want to manually control which VMs are managed

**Requirements:**
- Terraform must be initialized (`terraform init`)
- Terraform outputs must be available (`terraform output -json`)
- VM IP addresses must be in Terraform outputs (or use Proxmox API for discovery)

**Limitations:**
- Requires Terraform state to be accessible
- IP addresses must be known (DHCP requires additional discovery)
- Less explicit than static inventory (harder to audit)
- Static inventory remains as fallback

**Usage:**
```bash
# View dynamic inventory
ansible-inventory -i ansible/inventory/terraform.py --list

# Use with playbooks
ansible-playbook -i ansible/inventory/terraform.py playbooks/vm-base.yml --limit vms
```

**Note**: Static inventory (`inventory.yml`) remains the default and recommended approach. Dynamic inventory is optional and can be used alongside static inventory.

## Directory Structure

```
proxmox-infra/
├── ansible/          # Configuration management (first)
│   ├── inventory.example.yml  # Example static inventory (committed)
│   ├── inventory.yml          # Actual static inventory (not committed)
│   ├── inventory/
│   │   └── terraform.py      # Dynamic inventory script (Terraform-based)
│   ├── playbooks/             # Playbooks for hosts and VMs
│   ├── roles/                  # Reusable roles
│   └── group_vars/             # Group-specific variables
├── terraform/        # Infrastructure provisioning (second)
│   └── main.tf       # Contains VM outputs for dynamic inventory
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

## Service Roles vs Base Roles

### Base Roles (Always Applied)

**Purpose**: Essential infrastructure and security configuration
- Applied to all VMs by default
- No opt-in required
- Examples: base packages, timezone, SSH safety, qemu-guest-agent

**Characteristics:**
- Minimal and essential
- Safe defaults
- No external dependencies
- Required for VM operation

### Service Roles (Optional)

**Purpose**: Additional services and tools
- Applied conditionally via variables
- Disabled by default (opt-in)
- Examples: Docker, monitoring agents, application runtimes

**Characteristics:**
- **Safe by default**: Disabled unless explicitly enabled
- **Configurable**: Controlled via group_vars
- **Reusable**: Can be enabled per-VM or per-group
- **Isolated**: Service roles don't depend on each other

### Docker Role Example

**Configuration** (`group_vars/vms.yml`):
```yaml
docker_enabled: false  # Safe default - disabled
docker_users: []       # Optional: users to add to docker group
```

**Usage**:
- Set `docker_enabled: true` to enable Docker on VMs
- Add users to `docker_users` list to grant Docker access
- Role installs Docker Engine and docker-compose plugin
- Idempotent and distro-aware (Debian/Ubuntu)

**Why separate:**
- Not all VMs need Docker
- Keeps base configuration minimal
- Allows selective service deployment
- Easy to enable/disable per environment

## Environments (lab vs prod)

### Value-Only Separation

**Key principle**: Same codebase, different values.

**Why value-only, not code forks:**
- **Single source of truth**: One set of playbooks and roles
- **Consistency**: Same logic across all environments
- **Maintainability**: Changes apply to all environments
- **Auditability**: Easy to see what differs between environments
- **No duplication**: Playbooks are not copied or forked

### Environment Files

**`group_vars/vms.yml`** - Default values (safe, conservative)
- Base configuration for all VMs
- Docker disabled by default
- Minimal, essential settings

**`group_vars/lab.yml`** - Lab environment overrides
- More permissive settings for testing
- Docker enabled by default
- Example values for experimentation

**`group_vars/prod.yml`** - Production environment overrides
- Stricter, conservative defaults
- Docker disabled by default
- Production-specific hardening

### How It Works

**Variable precedence** (lowest to highest):
1. Defaults (`group_vars/vms.yml`)
2. Environment (`group_vars/lab.yml` or `group_vars/prod.yml`)
3. Host-specific (inventory host vars)
4. Command-line (`--extra-vars`)

**Example:**
- Default: `docker_enabled: false` (in `vms.yml`)
- Lab override: `docker_enabled: true` (in `lab.yml`)
- Result in lab: Docker is enabled
- Result in prod: Docker is disabled (uses default)

### Usage Patterns

**Method 1: Extra Variables**
```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms --extra-vars "env=lab"
```

**Method 2: Inventory Grouping**
- Group VMs by environment in inventory
- Ansible automatically loads matching `group_vars/*.yml` files
- No extra flags needed

**Method 3: Direct Group Assignment**
- Assign hosts to `lab` or `prod` groups in inventory
- Ansible merges variables from matching group_vars files

### Benefits

- **Explicit**: All environment differences are visible in group_vars files
- **Auditable**: Easy to compare lab vs prod settings
- **Safe**: Production defaults are conservative
- **Flexible**: Easy to add new environments (e.g., `staging.yml`)
- **No secrets**: Environment files contain only configuration values, not secrets

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

