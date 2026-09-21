# Proxmox Template Creation Scripts

Scripts for creating Debian 12 cloud-init template in Proxmox using CLI/API.

## Prerequisites

- Proxmox API access (token or credentials)
- Debian 12 ISO uploaded to Proxmox storage (local:iso/debian-12*.iso)
- Environment variables set (see below)

## Setup

Set environment variables:

```bash
export PROXMOX_HOST="192.168.150.75"
export PROXMOX_API_TOKEN_ID="root@pam!terraform"
export PROXMOX_API_TOKEN_SECRET="your-secret-here"
export PROXMOX_NODE="pve"  # Optional, defaults to "pve"
export VM_DEFAULT_STORAGE="local-lvm"  # Optional
export VM_DEFAULT_BRIDGE="vmbr0"  # Optional
```

## Scripts

### 1. create-debian12-template.sh

Creates VM 9000 and configures it for Debian 12 installation.

**Usage:**
```bash
./scripts/create-debian12-template.sh
```

**What it does:**
- Creates VM 9000 with Debian 12 ISO attached
- Adds cloud-init drive
- Configures cloud-init settings
- Does NOT install Debian (manual installation required)

### 2. install-and-template-debian12.sh

Starts VM 9000 for installation.

**Usage:**
```bash
./scripts/install-and-template-debian12.sh
```

**What it does:**
- Starts VM 9000
- You need to connect to console and install Debian 12 manually
- Install with SSH server and qemu-guest-agent

### 3. convert-to-template.sh

Converts VM 9000 to template after installation.

**Usage:**
```bash
./scripts/convert-to-template.sh
```

**What it does:**
- Checks if VM is stopped
- Converts VM 9000 to template
- Template can then be used in Terraform (clone = "9000")

## Complete Workflow

1. **Create VM:**
   ```bash
   ./scripts/create-debian12-template.sh
   ```

2. **Start installation:**
   ```bash
   ./scripts/install-and-template-debian12.sh
   ```

3. **Install Debian 12:**
   - Connect to VM console (via Proxmox web UI or SSH to Proxmox host: `qm terminal 9000`)
   - Install Debian 12 with:
     - SSH server enabled
     - qemu-guest-agent package installed
   - Shutdown VM after installation

4. **Convert to template:**
   ```bash
   ./scripts/convert-to-template.sh
   ```

5. **Use in Terraform:**
   - Monitoring VMs are already configured to clone from template 9000
   - Run `terraform apply` to create monitoring VMs

## Notes

- All scripts use Proxmox API (work from remote machine)
- No GUI interaction required
- Template ID 9000 is hardcoded (matches Terraform configuration)
- Storage and bridge names come from environment variables (no hardcoding)


## dify-query.py

Queries a self-hosted Dify app (chat or workflow) from the command line. Standard
library only, so it runs on any host that can reach the Dify instance -- a
workstation, a VM on the Proxmox cluster, or a cron job.

**Setup:**

```bash
export DIFY_API_BASE="https://dify.example.ee/v1"
export DIFY_API_KEY="app-..."        # app API key, not a workspace token
```

**Usage:**

```bash
# Chat app
./scripts/dify-query.py "Which invoices are still unpaid?"

# Workflow app with input variables
./scripts/dify-query.py --mode workflow --input question="300l buffer" --input mailbox=arved

# Raw JSON response
./scripts/dify-query.py --json "last invoices" > answer.json
```

Options: `--mode chat|workflow`, `--input KEY=VALUE` (repeatable),
`--conversation-id`, `--timeout`, `--json`, `--base`, `--key`, `--user`.

**Note:** a sandboxed session whose egress policy does not allow the Dify host
gets a proxy `403` on CONNECT. Run the script where the host is reachable, or
add the host to the environment's network allowlist.
