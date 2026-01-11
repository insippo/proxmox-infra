# Storage Policy

## Purpose

This document defines storage architecture boundaries and safety rules for Proxmox infrastructure. It must be reviewed before any storage configuration changes, Terraform provisioning, or VM storage allocation.

**This policy prevents unsafe storage architectures and documents lessons learned from production incidents.**

## Supported Storage Types

### Proxmox Host OS Filesystem

**Allowed:**
- ext4 (default, recommended for simplicity)
- xfs (acceptable alternative)

**Rationale:**
- Proxmox VE installer defaults to ext4
- Both filesystems are stable and well-tested
- No special requirements or tuning needed

**Forbidden:**
- ZFS as root filesystem (see ZFS boundaries below)
- Btrfs (not officially supported by Proxmox)

### VM/LXC Storage Options

**Supported:**
- LVM (local-lvm, default)
- Directory storage (local, for ISOs/templates)
- NFS (shared storage)
- CIFS/SMB (shared storage)
- ZFS (with restrictions, see below)

**Selection Criteria:**
- **Local VMs**: Use LVM (local-lvm) by default
- **Shared storage**: Use NFS for multi-host clusters
- **Templates/ISOs**: Use directory storage (local)
- **ZFS**: Only when explicitly approved per policy below

## ZFS Usage Boundaries

### When ZFS is Allowed

ZFS may be used for VM/LXC storage when **all** of the following conditions are met:

1. **Enterprise-grade storage hardware**
   - Enterprise NVMe drives with power-loss protection (PLP)
   - Enterprise SATA/SAS SSDs with PLP
   - Hardware RAID controllers with battery-backed cache (BBWC)

2. **Adequate system resources**
   - Minimum 1GB RAM per 1TB storage (ZFS ARC)
   - Sufficient CPU for checksum calculations
   - Dedicated storage pool (not root filesystem)

3. **Explicit use case justification**
   - Data integrity requirements (checksums)
   - Snapshot/clone requirements
   - Compression benefits outweigh complexity

4. **Operational readiness**
   - Team has ZFS operational experience
   - Monitoring and alerting in place
   - Backup and recovery procedures documented

### When ZFS is Forbidden

ZFS must **never** be used in the following scenarios:

1. **Consumer-grade NVMe drives**
   - Consumer NVMe drives lack power-loss protection
   - I/O stalls can cause system-wide hangs
   - ZFS write transactions amplify stall impact

2. **Root filesystem**
   - Proxmox installer does not support ZFS root
   - Complex recovery procedures
   - Not officially supported

3. **Mixed consumer/enterprise hardware**
   - Cannot reliably detect drive capabilities
   - Risk of consumer drives in critical pools

4. **Insufficient resources**
   - Less than 1GB RAM per 1TB storage
   - Limited CPU capacity
   - No dedicated storage hardware

## Consumer NVMe vs Enterprise NVMe

### Consumer NVMe Behavior

**Characteristics:**
- No power-loss protection (PLP)
- DRAM cache without protection
- Aggressive power management
- Variable I/O latency under load

**Failure Modes:**
- **I/O stalls**: Drive firmware operations (garbage collection, wear leveling) can pause I/O for seconds
- **Data loss risk**: Unprotected cache can lose data on power loss
- **Latency spikes**: Background operations cause unpredictable delays

**Why This Matters:**
- ZFS write transactions wait for all I/O to complete
- A single stalled drive can block the entire pool
- System appears hung while waiting for I/O

### Enterprise NVMe Behavior

**Characteristics:**
- Power-loss protection (PLP) with capacitors
- Protected write cache
- Predictable I/O latency
- Enterprise firmware with QoS guarantees

**Benefits:**
- I/O stalls are rare and brief (<100ms)
- Data integrity guaranteed even on power loss
- Consistent performance under load

### Why Mirrors Do Not Protect Against NVMe I/O Stalls

**Critical Understanding:**

ZFS mirrors (or RAID-1) provide redundancy for **drive failures**, not **I/O stalls**.

**What Mirrors Protect Against:**
- Complete drive failure
- Permanent media errors
- Physical drive damage

**What Mirrors Do NOT Protect Against:**
- Simultaneous I/O stalls on both drives
- Firmware operations blocking I/O
- Power-loss data corruption (if consumer drives)

**The Problem:**
- ZFS write transactions require I/O to all mirrors
- If both drives stall simultaneously (common during garbage collection), writes block
- System waits for I/O completion, appearing hung
- VMs may continue running (buffered I/O) while host becomes unresponsive

**Real-World Scenario:**
1. Consumer NVMe drives in ZFS mirror
2. Both drives enter garbage collection cycle
3. I/O stalls for 2-5 seconds
4. ZFS write transaction blocks waiting for I/O
5. Host becomes unresponsive (SSH hangs, Proxmox API hangs)
6. VMs continue running (they have buffered I/O)
7. Host recovers when drives complete garbage collection

## Failure Modes

### Storage I/O Stall

**What Happens:**
- Storage device firmware operation (garbage collection, wear leveling) pauses I/O
- ZFS write transactions wait for I/O completion
- Host kernel I/O subsystem blocks on storage operations
- System appears hung: SSH connections hang, Proxmox API unresponsive, console freezes

**Why VMs Keep Running:**
- VMs have their own I/O buffers and queues
- Guest OS I/O is buffered by hypervisor
- VM processes continue executing (CPU not blocked)
- Only new I/O requests from host or VMs queue up

**Recovery:**
- System recovers automatically when storage I/O resumes
- No data loss (if enterprise drives with PLP)
- Potential data loss (if consumer drives without PLP)

**Prevention:**
- Use enterprise storage with PLP
- Avoid ZFS on consumer drives
- Use LVM instead of ZFS for consumer hardware
- Monitor storage latency and alert on spikes

### Power Loss During Write

**Consumer Drives (No PLP):**
- Data in DRAM cache is lost
- In-flight writes may be incomplete
- ZFS transaction groups may be corrupted
- Requires pool recovery (scrub, potentially import)

**Enterprise Drives (With PLP):**
- Capacitors power cache flush
- All in-flight writes complete
- Data integrity maintained
- No pool recovery needed

### ZFS Pool Corruption

**Causes:**
- Power loss on consumer drives
- Multiple drive failures (beyond redundancy)
- Memory corruption affecting ZFS metadata
- Firmware bugs in storage devices

**Impact:**
- Pool may become unimportable
- Data may be partially or fully lost
- Recovery requires backups or professional data recovery

**Prevention:**
- Use enterprise drives with PLP
- Maintain regular backups
- Monitor pool health (scrub regularly)
- Use appropriate redundancy (mirrors or RAID-Z)

## Rules

### What Must Never Be Done Again

1. **Never use ZFS with consumer NVMe drives**
   - Consumer drives lack PLP
   - I/O stalls cause system hangs
   - Mirrors do not protect against stalls

2. **Never use ZFS as root filesystem**
   - Not officially supported by Proxmox
   - Complex recovery procedures
   - Installer does not support it

3. **Never mix consumer and enterprise drives in same pool**
   - Cannot reliably detect drive capabilities
   - Risk of consumer drive causing pool-wide issues

4. **Never provision storage without reviewing this policy**
   - Storage decisions are difficult to reverse
   - Mistakes cause production incidents
   - Always verify hardware capabilities first

### What Must Be Reviewed Before Changes

1. **Before adding new storage:**
   - Verify drive type (consumer vs enterprise)
   - Check for power-loss protection
   - Review ZFS eligibility per policy
   - Document storage architecture decision

2. **Before changing storage configuration:**
   - Review impact on running VMs
   - Verify backup procedures
   - Plan migration during maintenance window
   - Update documentation

3. **Before using ZFS:**
   - Verify all hardware meets enterprise requirements
   - Confirm adequate system resources
   - Document use case justification
   - Review operational procedures

4. **Before Terraform provisioning:**
   - Review storage policy compliance
   - Verify storage type matches hardware
   - Document storage architecture
   - Test in non-production first

### Storage Selection Decision Tree

```
Start: Need storage for VMs/LXCs
│
├─ Is this root filesystem?
│  └─ YES → Use ext4 (default) or xfs
│
├─ Is this shared storage (multi-host)?
│  └─ YES → Use NFS or CIFS
│
├─ Is this for templates/ISOs?
│  └─ YES → Use directory storage (local)
│
├─ Is this local VM storage?
│  ├─ Consumer hardware?
│  │  └─ YES → Use LVM (local-lvm) [ZFS FORBIDDEN]
│  │
│  └─ Enterprise hardware with PLP?
│     ├─ Meets ZFS requirements?
│     │  ├─ YES → ZFS allowed (with approval)
│     │  └─ NO → Use LVM (local-lvm)
│     │
│     └─ NO → Use LVM (local-lvm)
```

## References

- Proxmox VE Storage Documentation
- ZFS Best Practices Guide
- NVMe Power-Loss Protection (PLP) specifications
- Enterprise vs Consumer SSD characteristics

## Document Control

**Last Updated:** [Auto-generated on commit]

**Review Frequency:** Before any storage architecture changes

**Approval Required:** For ZFS usage or deviations from this policy

