#!/bin/bash
# Create a Debian 12 cloud-init template VM using the Proxmox API.
# Runs from a remote machine; no shell access to the Proxmox host required.

# shellcheck source=scripts/lib/proxmox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/proxmox.sh"

STORAGE="${VM_DEFAULT_STORAGE:-local-lvm}"
BRIDGE="${VM_DEFAULT_BRIDGE:-vmbr0}"
VM_ID="${VM_ID:-9000}"
VM_NAME="${VM_NAME:-debian-12-cloudinit-template}"

echo "Finding Debian 12 ISO in storage..."
ISO_LIST=$(proxmox_api GET "/storage/local/content?content=iso")
ISO_FILE=$(echo "$ISO_LIST" | grep -o '"volid":"[^"]*debian-12[^"]*"' | head -1 | cut -d'"' -f4 || true)

if [ -z "$ISO_FILE" ]; then
    echo "Error: no Debian 12 ISO found in Proxmox storage 'local'" >&2
    echo "Available ISOs:" >&2
    echo "$ISO_LIST" | grep -o '"volid":"[^"]*"' | cut -d'"' -f4 >&2 || echo "  (none found)" >&2
    exit 1
fi

echo "Using ISO: $ISO_FILE"
echo "Node:      $PROXMOX_NODE"
echo "Storage:   $STORAGE"
echo "Bridge:    $BRIDGE"

# Existence is decided by the HTTP status code, not by grepping the error text.
# Proxmox error wording is not a stable API, and a reworded message previously
# meant this check could fall through to the destructive branch.
VM_HTTP_STATUS=$(proxmox_api_status GET "/nodes/$PROXMOX_NODE/qemu/$VM_ID/status/current")

case "$VM_HTTP_STATUS" in
    200)
        echo ""
        echo "  VM $VM_ID already exists on node '$PROXMOX_NODE' at $PROXMOX_HOST."
        echo "  Continuing will DESTROY it and purge its disks. This cannot be undone."
        echo ""
        proxmox_api GET "/nodes/$PROXMOX_NODE/qemu/$VM_ID/config" || true
        echo ""
        if ! proxmox_confirm "Destroy VM $VM_ID on $PROXMOX_HOST/$PROXMOX_NODE?"; then
            echo "Aborted; nothing was changed." >&2
            exit 1
        fi
        echo "Removing VM $VM_ID..."
        proxmox_api DELETE "/nodes/$PROXMOX_NODE/qemu/$VM_ID?destroy-unreferenced-disks=1&purge=1"
        echo "Waiting for VM removal..."
        sleep 3
        ;;
    404|500)
        # Proxmox answers 500 for "Configuration file does not exist" on some versions.
        echo "VM $VM_ID does not exist yet; creating it."
        ;;
    *)
        echo "Error: unexpected HTTP status $VM_HTTP_STATUS when checking VM $VM_ID." >&2
        echo "       Refusing to continue rather than risk destroying the wrong VM." >&2
        exit 1
        ;;
esac

echo "Creating VM $VM_ID..."
proxmox_api POST "/nodes/$PROXMOX_NODE/qemu" \
    -d "vmid=$VM_ID" \
    -d "name=$VM_NAME" \
    -d "memory=2048" \
    -d "cores=2" \
    -d "net0=virtio,bridge=$BRIDGE" \
    -d "scsihw=virtio-scsi-pci" \
    -d "scsi0=$STORAGE:32,format=raw" \
    -d "boot=order=scsi0" \
    -d "agent=1" \
    -d "serial0=socket" \
    -d "vga=serial0" > /dev/null

echo "VM created successfully"

echo "Attaching Debian 12 ISO..."
proxmox_api POST "/nodes/$PROXMOX_NODE/qemu/$VM_ID/config" \
    -d "ide2=$ISO_FILE,media=cdrom" > /dev/null

echo "Adding cloud-init drive..."
proxmox_api POST "/nodes/$PROXMOX_NODE/qemu/$VM_ID/config" \
    -d "ide0=$STORAGE:cloudinit" > /dev/null

echo "Configuring cloud-init..."
proxmox_api POST "/nodes/$PROXMOX_NODE/qemu/$VM_ID/config" \
    -d "ciuser=root" \
    -d "ipconfig0=ip=dhcp" > /dev/null

echo ""
echo "VM $VM_ID created and configured successfully."
echo ""
echo "Next steps:"
echo "1. Start the VM and install Debian 12 with SSH server and qemu-guest-agent:"
echo "     ./scripts/install-and-template-debian12.sh"
echo "2. After the installation finishes, shut the VM down."
echo "3. Convert it to a template:"
echo "     ./scripts/convert-to-template.sh"
