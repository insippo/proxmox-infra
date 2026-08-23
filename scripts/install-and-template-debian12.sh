#!/bin/bash
# Start the build VM so Debian 12 can be installed interactively.

# shellcheck source=scripts/lib/proxmox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/proxmox.sh"

VM_ID="${VM_ID:-9000}"

echo "Starting VM $VM_ID for installation..."
proxmox_api POST "/nodes/$PROXMOX_NODE/qemu/$VM_ID/status/start" > /dev/null

echo "VM started. Installation in progress."
echo ""
echo "To connect to the console, use the Proxmox web UI, or from the Proxmox host:"
echo "  qm terminal $VM_ID"
echo ""
echo "Install Debian 12 with:"
echo "  - SSH server enabled"
echo "  - the qemu-guest-agent package installed"
echo ""
echo "After the installation completes and the VM shuts down, run:"
echo "  ./scripts/convert-to-template.sh"
