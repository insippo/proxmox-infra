# Recovery Plan

## Overview

This document outlines procedures for recovering from infrastructure failures.

## Recovery Scenarios

### Proxmox Host Failure

1. **Identify the failure**
   - Check host connectivity
   - Review Proxmox logs
   - Verify storage accessibility

2. **Recovery steps**
   - Restore from backup if available
   - Rebuild host using Ansible playbooks
   - Restore VM configurations from Terraform state
   - Verify network and storage configuration

3. **Verification**
   - Test VM connectivity
   - Verify storage pools
   - Check backup systems

### VM Failure

1. **Identify the failure**
   - Check VM status in Proxmox
   - Review VM logs
   - Test network connectivity

2. **Recovery options**
   - Restore from snapshot
   - Rebuild using Terraform
   - Restore from backup
   - Reconfigure using Ansible

3. **Verification**
   - Test application functionality
   - Verify data integrity
   - Check monitoring alerts

### Data Loss

1. **Immediate actions**
   - Stop writes to affected systems
   - Identify scope of data loss
   - Check backup availability

2. **Recovery process**
   - Restore from most recent backup
   - Verify data integrity
   - Test application functionality

3. **Prevention**
   - Review backup procedures
   - Implement additional safeguards
   - Update documentation

## Backup Strategy

- **Frequency**: Define backup frequency for each component
- **Retention**: Specify retention policies
- **Testing**: Regular restore testing
- **Documentation**: Keep backup procedures documented

## Disaster Recovery

- **RTO (Recovery Time Objective)**: Target recovery time
- **RPO (Recovery Point Objective)**: Acceptable data loss window
- **Failover Procedures**: Document failover steps
- **Communication Plan**: Define notification procedures

## SSH Hardening Rollback (Proxmox hosts)

- Keep console/ILO open before making SSH changes to avoid lockout
- Restore `/etc/ssh/sshd_config` from last known-good backup or remove the hardened directives (PermitRootLogin, PasswordAuthentication, ClientAlive settings) if they caused an issue
- Ensure an `authorized_keys` file exists before re-enabling strict settings
- Restart sshd gracefully: `systemctl restart ssh`
- Test a new SSH session while keeping the current session open; if successful, close the console session

## Testing

- Regular disaster recovery drills
- Document test results
- Update procedures based on findings

