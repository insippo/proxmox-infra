#!/bin/bash
# Convert the build VM into a Proxmox template.

# shellcheck source=scripts/lib/proxmox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/proxmox.sh"

VM_ID="${VM_ID:-9000}"

# The VM must be stopped before it can be templated. Treat anything other than an
# explicit "stopped" as unsafe: an unreadable status is not permission to proceed.
VM_STATUS=$(proxmox_api GET "/nodes/$PROXMOX_NODE/qemu/$VM_ID/status/current")

if ! echo "$VM_STATUS" | grep -q '"status":"stopped"'; then
    echo "Error: VM $VM_ID is not stopped. Shut it down before converting." >&2
    echo "Status reported by the API:" >&2
    echo "$VM_STATUS" >&2
    exit 1
fi

echo "Converting VM $VM_ID to template..."
proxmox_api POST "/nodes/$PROXMOX_NODE/qemu/$VM_ID/template" > /dev/null

echo "Success! VM $VM_ID has been converted to a template."
echo "Set TF_VAR_base_template_vm_id=$VM_ID for Terraform to clone from it."
