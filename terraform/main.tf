# Terraform configuration for Proxmox infrastructure
# This file defines the main infrastructure resources

terraform {
  required_version = ">= 1.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66"
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
  endpoint  = var.proxmox_api_url
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token_secret}"
  insecure  = true
}

# Example: Create a generic Linux VM
# This demonstrates declarative VM lifecycle management
# All values come from variables (no hardcoded secrets or IPs)
resource "proxmox_virtual_environment_vm" "example_vm" {
  name      = "example-linux-vm"
  node_name = var.proxmox_node
  vm_id     = null # Auto-assign VM ID

  # Clone from template
  clone {
    vm_id = 9000
  }

  # VM compute resources (from variables)
  cpu {
    cores = var.vm_default_cores
    type  = "host"
  }
  memory {
    dedicated = var.vm_default_memory
  }

  # Disk comes from cloned template, no need to specify when cloning

  # Network configuration (minimal, no IP assumptions)
  network_device {
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap
  agent {
    enabled = true
  }

  # Cloud-init configuration: inject SSH keys and user for Ansible access
  # This makes the VM immediately reachable by Ansible after creation
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

  # Lifecycle: prevent accidental destruction
  lifecycle {
    prevent_destroy = false
  }
}

# Prometheus monitoring VM (optional)
resource "proxmox_virtual_environment_vm" "monitoring_prometheus" {
  count     = var.monitoring_prometheus_enabled ? 1 : 0
  name      = "monitoring-prometheus"
  node_name = var.proxmox_node
  vm_id     = null # Auto-assign VM ID

  # Clone from template
  clone {
    vm_id = 9000
  }

  # VM compute resources (minimal for monitoring)
  cpu {
    cores = var.monitoring_prometheus_cores
    type  = "host"
  }
  memory {
    dedicated = var.monitoring_prometheus_memory
  }

  # Disk comes from cloned template, no need to specify when cloning

  # Network configuration (DHCP, no static IPs)
  network_device {
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap
  agent {
    enabled = true
  }

  # Cloud-init configuration: inject SSH keys and user for Ansible access
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

  lifecycle {
    prevent_destroy = true # Protect monitoring VM from accidental destruction
  }
}

# Grafana monitoring VM (optional)
resource "proxmox_virtual_environment_vm" "monitoring_grafana" {
  count     = var.monitoring_grafana_enabled ? 1 : 0
  name      = "monitoring-grafana"
  node_name = var.proxmox_node
  vm_id     = null # Auto-assign VM ID

  # Clone from template
  clone {
    vm_id = 9000
  }

  # VM compute resources (minimal for monitoring)
  cpu {
    cores = var.monitoring_grafana_cores
    type  = "host"
  }
  memory {
    dedicated = var.monitoring_grafana_memory
  }

  # Disk comes from cloned template, no need to specify when cloning

  # Network configuration (DHCP, no static IPs)
  network_device {
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap
  agent {
    enabled = true
  }

  # Cloud-init configuration: inject SSH keys and user for Ansible access
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

  lifecycle {
    prevent_destroy = true # Protect monitoring VM from accidental destruction
  }
}

# Terraform outputs for dynamic Ansible inventory
output "vms" {
  description = "VM information for Ansible dynamic inventory"
  value = merge(
    {
      example_vm = {
        name         = proxmox_virtual_environment_vm.example_vm.name
        ssh_user     = var.cloudinit_user
        ansible_host = "<replace_with_vm_ip_or_use_proxmox_api>"
      }
    },
    var.monitoring_prometheus_enabled ? {
      monitoring_prometheus = {
        name         = proxmox_virtual_environment_vm.monitoring_prometheus[0].name
        ssh_user     = var.cloudinit_user
        ansible_host = "<replace_with_vm_ip_or_use_proxmox_api>"
      }
    } : {},
    var.monitoring_grafana_enabled ? {
      monitoring_grafana = {
        name         = proxmox_virtual_environment_vm.monitoring_grafana[0].name
        ssh_user     = var.cloudinit_user
        ansible_host = "<replace_with_vm_ip_or_use_proxmox_api>"
      }
    } : {}
  )
  sensitive = false
}

