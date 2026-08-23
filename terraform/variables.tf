# Variable definitions for Terraform Proxmox configuration

variable "proxmox_api_url" {
  description = "Proxmox API base URL, without the /api2/json path (e.g. https://proxmox.example.com:8006/)"
  type        = string
  # Set via environment variable TF_VAR_proxmox_api_url or terraform.tfvars

  # The bpg/proxmox provider appends /api2/json itself. Passing a URL that
  # already contains it produces requests to .../api2/json/api2/json/... which
  # fail at apply time with a confusing 404.
  validation {
    condition     = can(regex("^https://[^/]+(:[0-9]+)?/?$", var.proxmox_api_url))
    error_message = "Use the base URL (https://host:8006/), not the /api2/json path."
  }
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID (e.g., terraform@pam!terraform)"
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

variable "proxmox_tls_insecure" {
  description = "Skip verification of the Proxmox TLS certificate. Leave false and trust the CA instead; only enable for a throwaway lab."
  type        = bool
  default     = false
}

variable "proxmox_node" {
  description = "Proxmox node name where resources will be created"
  type        = string
  default     = "pve"
}

variable "base_template_vm_id" {
  description = "VM ID of the template to clone from. Created by scripts/create-debian12-template.sh."
  type        = number
  default     = 9000

  validation {
    condition     = var.base_template_vm_id >= 100 && var.base_template_vm_id <= 999999999
    error_message = "Proxmox VM IDs must be between 100 and 999999999."
  }
}

# VM default configuration
variable "vm_default_cores" {
  description = "Default number of CPU cores per VM"
  type        = number
  default     = 2
}

variable "vm_default_sockets" {
  description = "Default number of CPU sockets per VM"
  type        = number
  default     = 1
}

variable "vm_default_memory" {
  description = "Default memory allocation per VM (in MB)"
  type        = number
  default     = 2048
}

variable "vm_default_storage" {
  description = "Default storage pool for VM disks"
  type        = string
  default     = "local-lvm"
}

variable "vm_default_bridge" {
  description = "Default network bridge for VM network interfaces"
  type        = string
  default     = "vmbr0"
}

# Cloud-init configuration for VM bootstrap
variable "cloudinit_user" {
  description = "Username for cloud-init (will be created with sudo access)"
  type        = string
  default     = "admin"
}

variable "cloudinit_ssh_keys" {
  description = "SSH public keys to inject via cloud-init. Required: without a real key the VM is created but nobody can log in."
  type        = list(string)
  # No default on purpose. The previous default was a pair of example keys, so
  # a VM built without setting this looked provisioned but was unreachable.

  validation {
    condition     = length(var.cloudinit_ssh_keys) > 0
    error_message = "At least one SSH public key is required, or the VM will be unreachable."
  }

  validation {
    condition = alltrue([
      for k in var.cloudinit_ssh_keys : !can(regex("(?i)example", k))
    ])
    error_message = "cloudinit_ssh_keys still contains an example key. Replace it with a real public key."
  }
}

# Monitoring VM configuration
variable "monitoring_prometheus_enabled" {
  description = "Enable Prometheus monitoring VM"
  type        = bool
  default     = false
}

variable "monitoring_prometheus_cores" {
  description = "Number of CPU cores for Prometheus VM"
  type        = number
  default     = 2
}

variable "monitoring_prometheus_memory" {
  description = "Memory allocation for Prometheus VM (in MB)"
  type        = number
  default     = 4096
}

variable "monitoring_grafana_enabled" {
  description = "Enable Grafana monitoring VM"
  type        = bool
  default     = false
}

variable "monitoring_grafana_cores" {
  description = "Number of CPU cores for Grafana VM"
  type        = number
  default     = 2
}

variable "monitoring_grafana_memory" {
  description = "Memory allocation for Grafana VM (in MB)"
  type        = number
  default     = 4096
}
