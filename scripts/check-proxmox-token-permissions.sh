#!/bin/bash
# Check Proxmox API token permissions.
# Helps identify missing permissions for Terraform.

# shellcheck source=scripts/lib/proxmox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/proxmox.sh"

echo "Checking Proxmox API token permissions..."
echo "Token ID: $PROXMOX_API_TOKEN_ID"
echo "API URL:  $PROXMOX_API_URL"
echo ""

echo "Testing API connection..."
STATUS=$(proxmox_api_status GET "/version")

case "$STATUS" in
    200)
        echo "OK: API connection successful"
        ;;
    401)
        echo "ERROR: Authentication failed (HTTP 401). Check token ID and secret." >&2
        exit 1
        ;;
    403)
        echo "ERROR: Token authenticated but lacks permissions (HTTP 403)." >&2
        exit 1
        ;;
    000)
        echo "ERROR: Could not reach $PROXMOX_API_URL." >&2
        echo "       If this is a self-signed certificate, point PROXMOX_CA_BUNDLE at the CA," >&2
        echo "       or set PROXMOX_TLS_INSECURE=1 to skip verification deliberately." >&2
        exit 1
        ;;
    *)
        echo "ERROR: Unexpected HTTP status $STATUS from /version." >&2
        exit 1
        ;;
esac

# A token with privilege separation (privsep=1) only gets the permissions granted to
# the token itself, not those of its owning user. That distinction is the most common
# cause of "works in the UI, fails in Terraform".
echo ""
echo "Token privilege separation:"
TOKEN_USER="${PROXMOX_API_TOKEN_ID%%!*}"
TOKEN_NAME="${PROXMOX_API_TOKEN_ID#*!}"
if TOKEN_INFO=$(proxmox_api GET "/access/users/${TOKEN_USER}/token/${TOKEN_NAME}" 2>/dev/null); then
    case "$TOKEN_INFO" in
        *'"privsep":1'*)
            echo "  privsep=1 — permissions must be granted to the TOKEN, not just the user."
            ;;
        *'"privsep":0'*)
            echo "  privsep=0 — the token inherits its owning user's permissions."
            ;;
        *)
            echo "  could not determine privsep from the API response."
            ;;
    esac
else
    echo "  could not read token metadata (needs User.Modify or Sys.Audit on /access)."
fi

echo ""
echo "Effective permissions reported by the API:"
if PERMS=$(proxmox_api GET "/access/permissions" 2>/dev/null); then
    echo "$PERMS"
else
    echo "  could not read /access/permissions with this token."
fi

echo ""
echo "Required permissions for Terraform:"
echo "  - VM.Allocate"
echo "  - VM.Clone"
echo "  - VM.Config.Disk"
echo "  - VM.Config.Network"
echo "  - VM.Config.Options"
echo "  - VM.Config.Cloudinit"
echo "  - VM.Monitor (CRITICAL - often missing)"
echo "  - VM.PowerMgmt"
echo "  - Datastore.Allocate"
echo "  - Datastore.AllocateSpace"
echo "  - Datastore.Audit"
echo ""
echo "To add missing permissions:"
echo "1. Login to the Proxmox web UI: https://${PROXMOX_HOST}:8006"
echo "2. Go to: Datacenter -> Permissions -> API Tokens"
echo "3. Find token: $PROXMOX_API_TOKEN_ID"
echo "4. Grant a role with the permissions above. With privsep=1 the grant must be"
echo "   made for the token itself, not only for its owning user."
echo ""
echo "See docs/terraform-proxmox-api-token.md for detailed instructions."
