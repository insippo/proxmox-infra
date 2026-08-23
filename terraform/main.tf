# Terraform configuration for Proxmox infrastructure
# This file defines the main infrastructure resources

terraform {
  # Upper bound included deliberately: a future Terraform 2.x may break this
  # configuration, and CI pins 1.6.0.
  required_version = ">= 1.5, < 2.0"

  required_providers {
    proxmox = {
      source = "bpg/proxmox"
      # bpg/proxmox is pre-1.0 and makes breaking schema changes in minor
      # releases, so allow patch updates only.
      version = "~> 0.66.0"
    }
  }

  # Backend configuration
  # State is local and unlocked until this is configured. Uncomment and fill in
  # before more than one person runs apply against the same infrastructure.
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
  insecure  = var.proxmox_tls_insecure
}

# Reads the IPv4 address the guest agent reports, skipping loopback. Returns null
# until the agent has reported, so consumers must tolerate a null ansible_host.
locals {
  vm_ipv4 = {
    example_vm = try([
      for ips in proxmox_virtual_environment_vm.example_vm.ipv4_addresses :
      ips[0] if length(ips) > 0 && ips[0] != "127.0.0.1"
    ][0], null)

    monitoring_prometheus = var.monitoring_prometheus_enabled ? try([
      for ips in proxmox_virtual_environment_vm.monitoring_prometheus[0].ipv4_addresses :
      ips[0] if length(ips) > 0 && ips[0] != "127.0.0.1"
    ][0], null) : null

    monitoring_grafana = var.monitoring_grafana_enabled ? try([
      for ips in proxmox_virtual_environment_vm.monitoring_grafana[0].ipv4_addresses :
      ips[0] if length(ips) > 0 && ips[0] != "127.0.0.1"
    ][0], null) : null
  }
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
    vm_id = var.base_template_vm_id
  }

  # VM compute resources (from variables)
  cpu {
    cores   = var.vm_default_cores
    sockets = var.vm_default_sockets
    type    = "host"
  }
  memory {
    dedicated = var.vm_default_memory
  }

  # Disk comes from cloned template, no need to specify when cloning

  # Network configuration (minimal, no IP assumptions)
  network_device {
    bridge = var.vm_default_bridge
  }

  # Cloud-init enabled for bootstrap. Also required for the ipv4_addresses
  # attribute that the Ansible inventory reads.
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
}

# Prometheus monitoring VM (optional)
resource "proxmox_virtual_environment_vm" "monitoring_prometheus" {
  count     = var.monitoring_prometheus_enabled ? 1 : 0
  name      = "monitoring-prometheus"
  node_name = var.proxmox_node
  vm_id     = null # Auto-assign VM ID

  # Clone from template
  clone {
    vm_id = var.base_template_vm_id
  }

  # VM compute resources (minimal for monitoring)
  cpu {
    cores   = var.monitoring_prometheus_cores
    sockets = var.vm_default_sockets
    type    = "host"
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

  # No prevent_destroy here: it cannot be made conditional, so combining it with
  # the count toggle above produces a plan that cannot be applied or reverted
  # without editing this file. Setting monitoring_prometheus_enabled = false is
  # the supported way to remove this VM, and review of `terraform plan` is what
  # guards against doing it by accident.
}

# Grafana monitoring VM (optional)
resource "proxmox_virtual_environment_vm" "monitoring_grafana" {
  count     = var.monitoring_grafana_enabled ? 1 : 0
  name      = "monitoring-grafana"
  node_name = var.proxmox_node
  vm_id     = null # Auto-assign VM ID

  # Clone from template
  clone {
    vm_id = var.base_template_vm_id
  }

  # VM compute resources (minimal for monitoring)
  cpu {
    cores   = var.monitoring_grafana_cores
    sockets = var.vm_default_sockets
    type    = "host"
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

  # See the note on monitoring_prometheus above for why prevent_destroy is absent.
}

# Terraform outputs for dynamic Ansible inventory.
#
# ansible_host is null until the guest agent reports an address. The inventory
# script (ansible/inventory/terraform.py) skips hosts whose address is null
# rather than emitting an unreachable entry.
output "vms" {
  description = "VM information for Ansible dynamic inventory"
  value = merge(
    {
      example_vm = {
        name         = proxmox_virtual_environment_vm.example_vm.name
        ssh_user     = var.cloudinit_user
        ansible_host = local.vm_ipv4.example_vm
      }
    },
    var.monitoring_prometheus_enabled ? {
      monitoring_prometheus = {
        name         = proxmox_virtual_environment_vm.monitoring_prometheus[0].name
        ssh_user     = var.cloudinit_user
        ansible_host = local.vm_ipv4.monitoring_prometheus
      }
    } : {},
    var.monitoring_grafana_enabled ? {
      monitoring_grafana = {
        name         = proxmox_virtual_environment_vm.monitoring_grafana[0].name
        ssh_user     = var.cloudinit_user
        ansible_host = local.vm_ipv4.monitoring_grafana
      }
    } : {}
  )
  sensitive = false
}
