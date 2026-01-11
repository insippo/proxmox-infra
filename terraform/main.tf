# Terraform configuration for Proxmox infrastructure
# This file defines the main infrastructure resources

terraform {
  required_version = ">= 1.0"

  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = "~> 2.9"
    }
  }

  # Backend configuration
  # Uncomment and configure your backend
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "proxmox-infra/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# Configure the Proxmox Provider
provider "proxmox" {
  pm_api_url      = var.proxmox_api_url
  pm_api_token_id = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret

  # Optional: Skip TLS verification (not recommended for production)
  # pm_tls_insecure = true
}

# Example: Create a generic Linux VM
# This demonstrates declarative VM lifecycle management
# All values come from variables (no hardcoded secrets or IPs)
resource "proxmox_vm_qemu" "example_vm" {
  name        = "example-linux-vm"
  target_node = var.proxmox_node
  clone       = var.base_template

  # VM compute resources (from variables)
  cores   = var.vm_default_cores
  sockets = var.vm_default_sockets
  cpu     = "host"
  memory  = var.vm_default_memory

  # VM storage (from variables)
  disk {
    storage = var.vm_default_storage
    type    = "scsi"
    size    = var.vm_default_disk_size
  }

  # Network configuration (minimal, no IP assumptions)
  network {
    model  = "virtio"
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap
  agent    = 1
  os_type  = "cloud-init"

  # Cloud-init configuration: inject SSH keys and user for Ansible access
  # This makes the VM immediately reachable by Ansible after creation
  ciuser     = var.cloudinit_user
  sshkeys    = join("\n", var.cloudinit_ssh_keys)
  ipconfig0  = "ip=dhcp"  # Use DHCP, no static IP assumptions

  # Lifecycle: prevent accidental destruction
  lifecycle {
    prevent_destroy = false
  }
}

# Prometheus monitoring VM (optional)
resource "proxmox_vm_qemu" "monitoring_prometheus" {
  count       = var.monitoring_prometheus_enabled ? 1 : 0
  name        = "monitoring-prometheus"
  target_node = var.proxmox_node
  clone       = var.base_template

  # VM compute resources (minimal for monitoring)
  cores   = var.monitoring_prometheus_cores
  sockets = var.vm_default_sockets
  cpu     = "host"
  memory  = var.monitoring_prometheus_memory

  # VM storage (from variables)
  disk {
    storage = var.vm_default_storage
    type    = "scsi"
    size    = var.monitoring_prometheus_disk_size
  }

  # Network configuration (DHCP, no static IPs)
  network {
    model  = "virtio"
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap
  agent    = 1
  os_type  = "cloud-init"

  # Cloud-init configuration: inject SSH keys and user for Ansible access
  ciuser     = var.cloudinit_user
  sshkeys    = join("\n", var.cloudinit_ssh_keys)
  ipconfig0  = "ip=dhcp"

  lifecycle {
    prevent_destroy = false
  }
}

# Grafana monitoring VM (optional)
resource "proxmox_vm_qemu" "monitoring_grafana" {
  count       = var.monitoring_grafana_enabled ? 1 : 0
  name        = "monitoring-grafana"
  target_node = var.proxmox_node
  clone       = var.base_template

  # VM compute resources (minimal for monitoring)
  cores   = var.monitoring_grafana_cores
  sockets = var.vm_default_sockets
  cpu     = "host"
  memory  = var.monitoring_grafana_memory

  # VM storage (from variables)
  disk {
    storage = var.vm_default_storage
    type    = "scsi"
    size    = var.monitoring_grafana_disk_size
  }

  # Network configuration (DHCP, no static IPs)
  network {
    model  = "virtio"
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap
  agent    = 1
  os_type  = "cloud-init"

  # Cloud-init configuration: inject SSH keys and user for Ansible access
  ciuser     = var.cloudinit_user
  sshkeys    = join("\n", var.cloudinit_ssh_keys)
  ipconfig0  = "ip=dhcp"

  lifecycle {
    prevent_destroy = false
  }
}

# Terraform outputs for dynamic Ansible inventory
output "vms" {
  description = "VM information for Ansible dynamic inventory"
  value = merge(
    {
      example_vm = {
        name        = proxmox_vm_qemu.example_vm.name
        ssh_user    = var.cloudinit_user
        ansible_host = "<replace_with_vm_ip_or_use_proxmox_api>"
      }
    },
    var.monitoring_prometheus_enabled ? {
      monitoring_prometheus = {
        name        = proxmox_vm_qemu.monitoring_prometheus[0].name
        ssh_user    = var.cloudinit_user
        ansible_host = "<replace_with_vm_ip_or_use_proxmox_api>"
      }
    } : {},
    var.monitoring_grafana_enabled ? {
      monitoring_grafana = {
        name        = proxmox_vm_qemu.monitoring_grafana[0].name
        ssh_user    = var.cloudinit_user
        ansible_host = "<replace_with_vm_ip_or_use_proxmox_api>"
      }
    } : {}
  )
  sensitive = false
}

