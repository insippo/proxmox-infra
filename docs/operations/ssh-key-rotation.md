# SSH Key Rotation

This guide explains how to safely rotate SSH keys for Proxmox hosts and VMs.

## Overview

SSH key rotation involves:
1. Adding a new SSH key
2. Testing access with the new key
3. Removing the old key
4. (Optional) Enforcing key list

## Prerequisites

- Existing SSH access to the host/VM
- New SSH key pair generated
- Ansible access configured

## Step 1: Generate New SSH Key

### On Your Workstation

```bash
# Generate new key pair
ssh-keygen -t ed25519 -f ~/.ssh/proxmox_new_key -C "proxmox_new_key_$(date +%Y%m%d)"

# Display public key
cat ~/.ssh/proxmox_new_key.pub
```

**Note**: Use a descriptive comment to identify the key and date.

## Step 2: Add New Key

### Method A: Using Ansible (Recommended)

#### For Proxmox Hosts

1. **Add Key to Group Vars**

   Edit `ansible/group_vars/proxmox_hosts.yml`:
   ```yaml
   ssh_allowed_keys:
     - "ssh-ed25519 AAAA... old_key_here comment@old"
     - "ssh-ed25519 AAAA... new_key_here comment@new"  # Add new key
   ```

2. **Run SSH Keys Role**
   ```bash
   ansible-playbook -i ansible/inventory.yml ansible/playbooks/proxmox-host.yml
   ```

   The `ssh_keys` role will add the new key to `/root/.ssh/authorized_keys`.

#### For VMs

1. **Update Terraform Variables**

   Edit `terraform/terraform.tfvars`:
   ```hcl
   cloudinit_ssh_keys = [
     "ssh-ed25519 AAAA... old_key comment@old",
     "ssh-ed25519 AAAA... new_key comment@new"  # Add new key
   ]
   ```

2. **Re-apply Terraform** (if needed)
   ```bash
   cd terraform
   terraform apply
   ```

   **Note**: Existing VMs won't be updated. Add key manually or recreate VM.

3. **Add Key Manually to Existing VMs**

   ```bash
   ssh admin@<vm_ip>
   echo "ssh-ed25519 AAAA... new_key" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

### Method B: Manual Addition

1. **SSH into Host/VM** (using existing key)

2. **Add New Key**
   ```bash
   echo "ssh-ed25519 AAAA... new_key_here" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

## Step 3: Test New Key

### Test SSH Access

```bash
# Test with new key
ssh -i ~/.ssh/proxmox_new_key root@<host_ip>

# Or for VMs
ssh -i ~/.ssh/proxmox_new_key admin@<vm_ip>
```

**Expected**: You should be able to login without password.

### Test Ansible Access

```bash
# Test Ansible connectivity with new key
ansible -i ansible/inventory.yml <host_name> -m ping --private-key ~/.ssh/proxmox_new_key
```

**Expected**: `SUCCESS` response.

### Verify Key is Active

```bash
# Check authorized_keys file
ssh -i ~/.ssh/proxmox_new_key root@<host_ip> "cat ~/.ssh/authorized_keys | grep new_key"
```

**Expected**: New key appears in the file.

## Step 4: Remove Old Key

### Method A: Using Ansible (Recommended)

#### For Proxmox Hosts

1. **Update Group Vars**

   Edit `ansible/group_vars/proxmox_hosts.yml`:
   ```yaml
   ssh_allowed_keys:
     # Remove old key, keep only new key
     - "ssh-ed25519 AAAA... new_key_here comment@new"
   ```

2. **Enable Enforcement** (optional, see cautions below)
   ```yaml
   ssh_keys_enforce: true  # WARNING: See cautions below
   ```

3. **Run Playbook**
   ```bash
   ansible-playbook -i ansible/inventory.yml ansible/playbooks/proxmox-host.yml
   ```

### Method B: Manual Removal

1. **SSH into Host/VM** (using new key)

2. **Edit authorized_keys**
   ```bash
   vi ~/.ssh/authorized_keys
   ```

3. **Remove Old Key**
   - Delete the line containing the old key
   - Save and exit

4. **Verify**
   ```bash
   # Old key should fail
   ssh -i ~/.ssh/proxmox_old_key root@<host_ip>
   # Should be denied
   
   # New key should work
   ssh -i ~/.ssh/proxmox_new_key root@<host_ip>
   # Should succeed
   ```

## Step 5: Update Configuration Files

### Update Ansible Configuration

1. **Remove Old Key from Group Vars**
   - Edit `ansible/group_vars/proxmox_hosts.yml`
   - Remove old key from `ssh_allowed_keys`

2. **Update Terraform Variables** (for VMs)
   - Edit `terraform/terraform.tfvars`
   - Remove old key from `cloudinit_ssh_keys`

3. **Commit Changes**

   `terraform.tfvars` holds the Proxmox API token secret and must never be
   committed. `.gitignore` blocks it; do not work around that with `git add -f`.
   Commit only the Ansible key list:

   ```bash
   git add ansible/group_vars/proxmox_hosts.yml
   git commit -m "Rotate SSH keys: remove old key, add new key"
   ```

   Keep the updated `cloudinit_ssh_keys` in your local `terraform.tfvars`. If the
   key list needs to be shared, put it in `keys.auto.tfvars.example`, which is
   exempt from the ignore rule and holds public keys only.

## Enforcement Mode: Cautions

### What is Enforcement Mode?

When `ssh_keys_enforce: true`:
- The role **replaces** `authorized_keys` with only the keys in `ssh_allowed_keys`
- **All other keys are removed**
- If `ssh_allowed_keys` is empty, access will be locked out

### When to Use

**Use enforcement mode when:**
- You want strict control over authorized keys
- You have verified all keys in the list work
- You have console access as backup
- You're confident in the key list

### When NOT to Use

**Do NOT use enforcement mode when:**
- You're not certain all keys in the list work
- You don't have console access
- Multiple people need access and you're not sure of all keys
- You're rotating keys for the first time

### Safe Approach

1. **First rotation**: Keep `ssh_keys_enforce: false`
   - Add new key
   - Test thoroughly
   - Remove old key manually

2. **Subsequent rotations**: Can use enforcement
   - After you're confident in the process
   - When you have console access
   - When key list is well-documented

## Verification Checklist

After key rotation, verify:

- [ ] New key works for SSH access
- [ ] New key works for Ansible
- [ ] Old key no longer works
- [ ] All authorized users can access
- [ ] Ansible playbooks run successfully
- [ ] Configuration files updated
- [ ] Changes committed to version control

## Troubleshooting

### New Key Not Working

1. **Check key format**: Ensure public key format is correct
2. **Check permissions**: `~/.ssh` should be 700, `authorized_keys` should be 600
3. **Check SSH logs**: `journalctl -u ssh` or `/var/log/auth.log`
4. **Test manually**: Try SSH with verbose output: `ssh -vvv -i key user@host`

### Old Key Still Works

1. **Verify removal**: Check `authorized_keys` file manually
2. **Check enforcement**: If using enforcement mode, verify it's enabled
3. **Re-run playbook**: Ensure Ansible applied changes

### Locked Out

1. **Use console access**: See `docs/operations/host-recovery.md`
2. **Add key via console**: Manually add new key via console
3. **Review process**: Identify what went wrong

## Best Practices

1. **Rotate Regularly**: Rotate keys every 90-180 days
2. **Keep Backup Keys**: Always have at least 2 working keys
3. **Test Thoroughly**: Test new key before removing old
4. **Document Keys**: Keep track of who has which keys
5. **Use Enforcement Carefully**: Only when confident and have backup access
6. **Version Control**: Commit key changes to track rotation history

## References

- **SSH Key Policy**: `docs/ssh-key-policy.md` - SSH key management policy
- **Host Recovery**: `docs/operations/host-recovery.md` - Recovery procedures
- **Architecture**: `docs/architecture.md` - SSH configuration details

