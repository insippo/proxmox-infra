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

# Example: Create a VM
# resource "proxmox_vm_qemu" "example_vm" {
#   name        = "example-vm"
#   target_node = var.proxmox_node
#   clone       = var.base_template
# 
#   agent    = 1
#   os_type  = "cloud-init"
#   cores    = 2
#   sockets  = 1
#   cpu      = "host"
#   memory   = 2048
# 
#   disk {
#     storage = "local-lvm"
#     type    = "scsi"
#     size    = "20G"
#   }
# 
#   network {
#     model  = "virtio"
#     bridge = "vmbr0"
#   }
# 
#   # Cloud-init configuration
#   ipconfig0 = "ip=dhcp"
# }

