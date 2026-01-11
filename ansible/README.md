# Ansible Configuration

This directory contains Ansible playbooks and roles for managing Proxmox infrastructure.

## Inventory Structure

### Groups

**`proxmox_hosts`** - Proxmox VE hypervisor hosts
- **Playbook**: `playbooks/proxmox-host.yml`
- **Purpose**: Configure the infrastructure layer (host OS, SSH hardening, sysctl)
- **Access**: Root SSH (LAN-only)
- **When**: First, before any VMs are created

**`vms`** - Linux VMs created via Terraform + cloud-init
- **Playbook**: `playbooks/vm-base.yml`
- **Purpose**: Configure the guest OS layer (packages, timezone, qemu-guest-agent)
- **Access**: User SSH (injected via cloud-init)
- **When**: After Terraform creates VMs and cloud-init bootstraps access

### Inventory Options

**Static Inventory** (recommended for most cases):
- **`inventory.example.yml`** - Example inventory (copy to `inventory.yml`)
  - Contains example groups and hosts (placeholders only)
  - No real IPs, hostnames, or credentials
  - Copy to `inventory.yml` and populate with your actual hosts
- **`inventory.yml`** - Your actual inventory (not committed)
  - Add your real Proxmox hosts and VMs here
  - Keep secrets in Ansible Vault or environment variables
  - This file is in `.gitignore`
- **When to use**: Explicit control, easy to audit, no dependencies

**Dynamic Inventory** (optional, Terraform-based):
- **`inventory/terraform.py`** - Dynamic inventory script
  - Reads Terraform outputs to discover VMs
  - Generates Ansible JSON inventory automatically
  - Groups VMs under `vms` group
- **When to use**: Many VMs, frequent changes, Terraform-managed infrastructure
- **Requirements**: Terraform initialized, outputs available
- **Limitation**: Requires IP addresses in Terraform outputs (or use Proxmox API)

## Workflow: VM Lifecycle

### Step 1: Terraform Creates VM
```bash
cd terraform
terraform apply
```
- Terraform creates VM from template
- cloud-init injects SSH keys and creates user
- VM boots and becomes SSH-accessible

### Step 2: Operator Adds VM to Inventory
- Add VM entry to `ansible/inventory.yml`:
```yaml
vms:
  hosts:
    my_vm:
      ansible_host: "192.168.1.100"  # VM's IP address
```
- Use the same username as `cloudinit_user` in Terraform (default: `admin`)

### Step 3: Ansible Applies Base Configuration
```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms
```
- Ansible connects via SSH (using keys from cloud-init)
- Applies base configuration (packages, timezone, qemu-guest-agent)
- VM is ready for application deployment

## Playbooks

### `playbooks/proxmox-host.yml`
- **Target**: `proxmox_hosts` group
- **Purpose**: Configure Proxmox hypervisor hosts
- **Scope**: Host OS hardening, base packages, SSH, sysctl, journald

### `playbooks/vm-base.yml`
- **Target**: `vms` group
- **Purpose**: Configure Linux VMs
- **Scope**: Base packages, qemu-guest-agent, timezone, basic SSH safety
- **Optional roles**: Docker (enabled via `docker_enabled: true`)

## Roles

### `roles/ssh_keys/`
- Manages SSH authorized keys on Proxmox hosts
- Safe by default (does not remove existing keys)

### `roles/admin_user/`
- Creates optional admin user on Proxmox hosts
- Disabled by default (set `admin_user_enabled: true` to enable)

### `roles/docker/`
- Installs Docker Engine and docker-compose plugin on VMs
- Disabled by default (set `docker_enabled: true` in `group_vars/vms.yml` to enable)
- Adds users to docker group (optional, via `docker_users` variable)
- Idempotent and distro-aware (Debian/Ubuntu)

## Variables

### `group_vars/proxmox_hosts.yml`
- Variables for Proxmox host configuration
- SSH hardening settings, sysctl, journald, etc.

### `group_vars/vms.yml`
- Variables for VM configuration (defaults)
- Timezone, base packages list
- Docker configuration (enabled flag, users list)
- Safe defaults (Docker disabled, minimal configuration)

### Environment-Specific Variables

**`group_vars/lab.yml`** - Lab environment overrides
- More permissive settings for testing
- Docker enabled by default
- Example values for testing

**`group_vars/prod.yml`** - Production environment overrides
- Stricter, conservative defaults
- Docker disabled by default
- Production-specific hardening

**How environments work:**
- Same playbooks and roles for all environments
- Environment-specific values override defaults
- Use `--extra-vars "env=lab"` or inventory grouping
- No code duplication - only values differ

## Environments

### Using Environments

**Method 1: Extra Variables**
```bash
# Run with lab environment
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms --extra-vars "env=lab"

# Run with prod environment
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms --extra-vars "env=prod"
```

**Method 2: Inventory Grouping**
```yaml
# In inventory.yml, group VMs by environment
all:
  children:
    lab:
      children:
        vms:
          hosts:
            lab_vm_1:
              ansible_host: "<lab_vm_ip>"
    prod:
      children:
        vms:
          hosts:
            prod_vm_1:
              ansible_host: "<prod_vm_ip>"
```

**Method 3: Direct Group Vars**
- Ansible automatically loads `group_vars/lab.yml` for hosts in `lab` group
- Ansible automatically loads `group_vars/prod.yml` for hosts in `prod` group
- Variables are merged with defaults from `group_vars/vms.yml`

### Environment Variable Precedence

1. **Defaults** (`group_vars/vms.yml`) - Safe, conservative values
2. **Environment** (`group_vars/lab.yml` or `group_vars/prod.yml`) - Overrides defaults
3. **Host-specific** (inventory host vars) - Overrides everything
4. **Command-line** (`--extra-vars`) - Highest precedence

## Usage Examples

### Static Inventory

**Configure Proxmox Hosts:**
```bash
ansible-playbook -i inventory.yml playbooks/proxmox-host.yml
```

**Configure All VMs:**
```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms
```

**Configure Single VM:**
```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vm_example_1
```

**Test Connectivity:**
```bash
ansible -i inventory.yml proxmox_hosts -m ping
ansible -i inventory.yml vms -m ping
```

### Dynamic Inventory (Terraform-based)

**Prerequisites:**
1. Terraform must be initialized: `cd terraform && terraform init`
2. Terraform outputs must be available: `terraform output -json`
3. Update Terraform outputs with actual VM IP addresses (or use Proxmox API)

**View Dynamic Inventory:**
```bash
ansible-inventory -i inventory/terraform.py --list
```

**Configure All VMs (from Terraform):**
```bash
ansible-playbook -i inventory/terraform.py playbooks/vm-base.yml --limit vms
```

**Test Connectivity:**
```bash
ansible -i inventory/terraform.py vms -m ping
```

**Note**: If Terraform outputs contain placeholder IPs (`<replace_with_vm_ip_or_use_proxmox_api>`), the dynamic inventory will skip those VMs. Use static inventory or update Terraform outputs with real IPs.

## Security

- **Never commit** `inventory.yml` (contains real IPs/hostnames)
- Use Ansible Vault for sensitive variables
- SSH keys come from Terraform (via cloud-init)
- All playbooks are idempotent (safe to run multiple times)

## Future Enhancements

- Proxmox API integration for automatic IP discovery
- More granular VM configuration options
- Inventory caching for better performance

