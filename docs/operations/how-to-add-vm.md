# How to Add a VM

This guide walks through the complete process of adding a new VM to the infrastructure.

## Prerequisites

- Terraform initialized and configured
- Proxmox API access configured
- SSH keys available for cloud-init
- Ansible inventory file (`ansible/inventory.yml`) exists

## Step 1: Add VM to Terraform

### 1.1 Edit Terraform Configuration

Open `terraform/main.tf` and add a new VM resource:

```hcl
resource "proxmox_virtual_environment_vm" "my_new_vm" {
  name      = "my-new-vm"
  node_name = var.proxmox_node
  vm_id     = null # Auto-assign VM ID

  # Clone from the template built by scripts/create-debian12-template.sh
  clone {
    vm_id = var.base_template_vm_id
  }

  cpu {
    cores   = var.vm_default_cores
    sockets = var.vm_default_sockets
    type    = "host"
  }

  memory {
    dedicated = var.vm_default_memory
  }

  # The disk comes from the cloned template; do not declare one here.

  network_device {
    bridge = var.vm_default_bridge
  }

  # Required for the guest to report its IP address, which the Ansible
  # inventory reads.
  agent {
    enabled = true
  }

  initialization {
    datastore_id = var.vm_default_storage
    user_account {
      username = var.cloudinit_user
      keys     = var.cloudinit_ssh_keys
    }
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
  }
}
```

### 1.2 Add VM to Terraform Outputs

Add the VM to the `vms` output in `terraform/main.tf`. Read the address from the
guest agent rather than hardcoding one — the Ansible inventory skips hosts whose
address is null, so a VM whose agent has not reported yet is left out instead of
being added unreachable.

First add a `locals` entry alongside the existing ones:

```hcl
locals {
  vm_ipv4 = {
    # ... existing entries ...
    my_new_vm = try([
      for ips in proxmox_virtual_environment_vm.my_new_vm.ipv4_addresses :
      ips[0] if length(ips) > 0 && ips[0] != "127.0.0.1"
    ][0], null)
  }
}
```

Then reference it from the output:

```hcl
output "vms" {
  value = merge(
    {
      # ... existing entries ...
      my_new_vm = {
        name         = proxmox_virtual_environment_vm.my_new_vm.name
        ssh_user     = var.cloudinit_user
        ansible_host = local.vm_ipv4.my_new_vm
      }
    },
    # ... existing conditional blocks ...
  )
}
```

**Note**: `ansible_host` is `null` until the QEMU guest agent inside the VM
reports an address. If the VM never appears in `ansible-inventory --list`, check
that `qemu-guest-agent` is installed and running in the template.

## Step 2: Apply Terraform

### 2.1 Review Changes

```bash
cd terraform
terraform plan
```

Review the plan to ensure:
- VM name is correct
- Resource allocation is appropriate
- No unintended changes

### 2.2 Apply Changes

```bash
terraform apply
```

Confirm when prompted. Terraform will:
- Create the VM from template
- Configure cloud-init
- Inject SSH keys
- Start the VM

## Step 3: Verify cloud-init

### 3.1 Wait for VM Boot

Wait 1-2 minutes for the VM to:
- Boot completely
- Run cloud-init
- Configure network (DHCP)
- Create user account
- Inject SSH keys

### 3.2 Discover VM IP Address

**Option A: Proxmox Web UI**
- Navigate to Proxmox web interface
- Find the VM in the node
- Check network configuration or console

**Option B: Proxmox API**
- Use Proxmox API to query VM network information
- See `ansible/inventory/terraform.py` for example

**Option C: DHCP Server Logs**
- Check DHCP server logs for new lease
- Match by MAC address if known

### 3.3 Test SSH Access

```bash
ssh -i ~/.ssh/your_key admin@<vm_ip_address>
```

Replace:
- `~/.ssh/your_key` with your private key path
- `<vm_ip_address>` with the VM's IP address
- `admin` with the `cloudinit_user` value from Terraform

**Expected**: You should be able to SSH into the VM without password.

## Step 4: Add VM to Ansible Inventory

### Option A: Static Inventory (Recommended)

Edit `ansible/inventory.yml`:

```yaml
all:
  children:
    vms:
      hosts:
        my_new_vm:
          ansible_host: "<vm_ip_address>"
```

**Note**: Use the same username as `cloudinit_user` from Terraform (default: `admin`).

### Option B: Dynamic Inventory (Terraform Output)

If using dynamic inventory:

Nothing to edit by hand: the output added in Step 1.2 reads the address from the
guest agent, so the VM appears in the inventory once it boots and the agent
reports.

1. Refresh the Terraform state so the address is current:
   ```bash
   cd terraform && terraform refresh
   ```

2. Verify dynamic inventory:
   ```bash
   ansible-inventory -i ansible/inventory/terraform.py --list
   ```

   If the VM is missing, the script says why on stderr — usually that the guest
   agent has not reported an address yet. Check `qemu-guest-agent` in the VM.

## Step 5: Run Base Configuration

### 5.1 Test Ansible Connectivity

```bash
ansible -i ansible/inventory.yml my_new_vm -m ping
```

**Expected**: `SUCCESS` response.

### 5.2 Apply Base Configuration

```bash
ansible-playbook -i ansible/inventory.yml ansible/playbooks/vm-base.yml --limit my_new_vm
```

This will:
- Install base packages
- Configure timezone
- Enable qemu-guest-agent
- Apply basic SSH safety

### 5.3 Verify Configuration

```bash
ansible -i ansible/inventory.yml my_new_vm -a "docker --version"  # If Docker enabled
ansible -i ansible/inventory.yml my_new_vm -a "systemctl status qemu-guest-agent"
```

## Troubleshooting

### VM Not Accessible via SSH

1. **Check VM status in Proxmox**: Ensure VM is running
2. **Verify cloud-init completed**: Check VM console for errors
3. **Verify SSH keys**: Ensure keys were injected correctly
4. **Check network**: Verify VM received IP address via DHCP
5. **Check firewall**: Ensure no firewall blocking SSH

### Ansible Cannot Connect

1. **Verify IP address**: Ensure `ansible_host` is correct
2. **Test SSH manually**: `ssh admin@<vm_ip>`
3. **Check username**: Ensure `ansible_user` matches `cloudinit_user`
4. **Verify SSH key**: Ensure your SSH key is in `cloudinit_ssh_keys` in Terraform

### cloud-init Not Running

1. **Check VM console**: Look for cloud-init errors
2. **Verify template**: Ensure base template has cloud-init installed
3. **Check Proxmox logs**: Review Proxmox host logs for issues

## Next Steps

After base configuration:
- Enable optional services (Docker, etc.) via `group_vars`
- Add application-specific configuration
- Add VM to monitoring
- Document VM purpose and configuration

