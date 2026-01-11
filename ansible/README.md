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

### Inventory File

**`inventory.example.yml`** - Example inventory (copy to `inventory.yml`)
- Contains example groups and hosts (placeholders only)
- No real IPs, hostnames, or credentials
- Copy to `inventory.yml` and populate with your actual hosts

**`inventory.yml`** - Your actual inventory (not committed)
- Add your real Proxmox hosts and VMs here
- Keep secrets in Ansible Vault or environment variables
- This file is in `.gitignore`

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

## Roles

### `roles/ssh_keys/`
- Manages SSH authorized keys on Proxmox hosts
- Safe by default (does not remove existing keys)

### `roles/admin_user/`
- Creates optional admin user on Proxmox hosts
- Disabled by default (set `admin_user_enabled: true` to enable)

## Variables

### `group_vars/proxmox_hosts.yml`
- Variables for Proxmox host configuration
- SSH hardening settings, sysctl, journald, etc.

### `group_vars/vms.yml`
- Variables for VM configuration
- Timezone, base packages list

## Usage Examples

### Configure Proxmox Hosts
```bash
ansible-playbook -i inventory.yml playbooks/proxmox-host.yml
```

### Configure All VMs
```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vms
```

### Configure Single VM
```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit vm_example_1
```

### Test Connectivity
```bash
ansible -i inventory.yml proxmox_hosts -m ping
ansible -i inventory.yml vms -m ping
```

## Security

- **Never commit** `inventory.yml` (contains real IPs/hostnames)
- Use Ansible Vault for sensitive variables
- SSH keys come from Terraform (via cloud-init)
- All playbooks are idempotent (safe to run multiple times)

## Future Enhancements

- Dynamic inventory from Terraform outputs (planned)
- Integration with Proxmox API for automatic discovery
- More granular VM configuration options

