# Variable definitions for Terraform Proxmox configuration

variable "proxmox_api_url" {
  description = "Proxmox API URL (e.g., https://proxmox.example.com:8006/api2/json)"
  type        = string
  # Set via environment variable TF_VAR_proxmox_api_url or terraform.tfvars
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID (e.g., root@pam!terraform)"
  type        = string
  sensitive   = true
  # Set via environment variable TF_VAR_proxmox_api_token_id or terraform.tfvars
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
  # Set via environment variable TF_VAR_proxmox_api_token_secret or terraform.tfvars
}

variable "proxmox_node" {
  description = "Proxmox node name where resources will be created"
  type        = string
  default     = "pve"
}

variable "base_template" {
  description = "Base VM template to clone from"
  type        = string
  default     = "ubuntu-cloud-template"
}

# Example: Storage configuration
# variable "storage_pool" {
#   description = "Storage pool name"
#   type        = string
#   default     = "local-lvm"
# }

# Example: Network configuration
# variable "network_bridge" {
#   description = "Network bridge name"
#   type        = string
#   default     = "vmbr0"
# }

