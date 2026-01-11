# Terraform Recovery: Duplicate VM Prevention

## Context

This document explains the recovery process after accidental duplicate VM creation and Terraform state reset.

## What Happened

### Duplicate VMs Created

Multiple monitoring VMs (Prometheus and Grafana) were accidentally created in Proxmox:
- Multiple instances of `monitoring-prometheus` (VMIDs: 108, 112, 116, 121, 123)
- Multiple instances of `monitoring-grafana` (VMIDs: 110, 111, 115, 117, 122, 126)

### Why Duplicates Happened

1. **Terraform state was reset** - State file was cleared or removed
2. **Repeated `terraform apply`** - Each apply created new VMs because Terraform didn't know about existing ones
3. **No `prevent_destroy` protection** - Monitoring VMs lacked lifecycle protection
4. **Storage issues** - ZFS storage problems prevented proper VM deletion, leaving orphaned VMs

### Why Terraform State Was Reset

Terraform state was manually removed (`terraform state rm`) to resolve:
- Tainted resources from failed applies
- Storage-related deletion errors
- State drift from manual Proxmox changes

**Problem**: Removing state without cleaning up Proxmox first caused Terraform to see "no VMs exist" and create new ones on next apply.

## Why Manual Cleanup Was Required

Manual cleanup in Proxmox was necessary because:
1. **Terraform cannot detect existing VMs** - If a VM exists in Proxmox but not in Terraform state, Terraform will try to create it again
2. **Storage errors prevented deletion** - ZFS storage issues (`cannot import 'downloads': no such pool available`) blocked automated cleanup
3. **State reset without cleanup** - Removing Terraform state without first removing VMs from Proxmox left orphaned resources

## Recovery Process

### Step 1: Identify Duplicate VMs

```bash
# List all VMs in Proxmox
curl -k -X GET -H "Authorization: PVEAPIToken=..." \
  "https://proxmox:8006/api2/json/nodes/proxmox/qemu" | \
  jq '.data[] | select(.name | contains("monitoring")) | {vmid, name, status}'
```

### Step 2: Manual Cleanup in Proxmox

Remove duplicate VMs via Proxmox API or Web UI:
- Keep only the latest/working instances
- Remove all duplicates manually
- Ensure no VMs with names `monitoring-prometheus` or `monitoring-grafana` exist (except the intended ones)

### Step 3: Stabilize Terraform Configuration

1. **Add `prevent_destroy = true`** to monitoring VMs
2. **Verify single VM definitions** - Ensure each monitoring VM is defined exactly once
3. **Import existing VMs** (if needed) - Use `terraform import` to sync state with reality

### Step 4: Verify State

```bash
cd terraform
terraform plan
# Should show: "No changes. Infrastructure is up-to-date."
```

## Prevention Measures

### Critical Rule: Never Run `terraform apply` Blindly

**Always follow this sequence:**

1. **Check existing VMs first:**
   ```bash
   # List VMs in Proxmox
   # Verify no duplicates exist
   ```

2. **Review Terraform state:**
   ```bash
   terraform state list
   # Verify expected VMs are tracked
   ```

3. **Always run plan first:**
   ```bash
   terraform plan
   # READ THE OUTPUT CAREFULLY
   # Verify: no unexpected creates, no unexpected destroys
   ```

4. **Only then apply:**
   ```bash
   terraform apply
   # Review plan output again before confirming
   ```

### Terraform Does Not Auto-Detect Existing VMs

**Important**: Terraform only knows about resources in its state file. If a VM exists in Proxmox but not in Terraform state, Terraform will try to create it again.

**Solution**: Always import existing VMs before applying:
```bash
terraform import proxmox_virtual_environment_vm.monitoring_prometheus[0] proxmox/123
```

### Manual Proxmox Changes Must Be Documented

If you make changes in Proxmox Web UI or CLI:
1. **Document the change** - What was changed and why
2. **Update Terraform state** - Use `terraform import` or `terraform state rm` as appropriate
3. **Verify with plan** - Run `terraform plan` to ensure state matches reality

## Current State

After recovery:
- **Single Prometheus VM**: VMID 123 (`monitoring-prometheus`)
- **Single Grafana VM**: VMID 126 (`monitoring-grafana`)
- **Terraform state**: Synced with Proxmox reality
- **Protection**: `prevent_destroy = true` on monitoring VMs

## Lessons Learned

1. **State is critical** - Never reset Terraform state without cleaning up resources first
2. **Plan before apply** - Always review `terraform plan` output
3. **Protect important resources** - Use `prevent_destroy` for production VMs
4. **Manual changes need sync** - Proxmox changes must be reflected in Terraform state
5. **Storage issues compound problems** - Fix storage issues before attempting VM cleanup

## References

- Terraform state management: `terraform/README.md`
- VM lifecycle: `docs/operations/how-to-add-vm.md`
- Storage policy: `docs/storage-policy.md`

