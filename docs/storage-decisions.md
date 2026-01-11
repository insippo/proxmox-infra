# Storage Decisions

## Overview

This document captures storage architecture decisions and rationale.

## Storage Types

### Local Storage

**Use Cases:**
- Fast local storage for VMs
- Temporary files
- Local backups

**Considerations:**
- Limited by host capacity
- No redundancy without RAID
- Fastest performance

### Network Storage (NFS/CIFS)

**Use Cases:**
- Shared storage across hosts
- Centralized backups
- Template storage

**Considerations:**
- Network dependency
- Potential performance impact
- Centralized management

### ZFS Storage

**Use Cases:**
- High-performance storage
- Data integrity (checksums)
- Snapshots and clones

**Considerations:**
- Requires ZFS support
- Memory requirements
- Complex configuration

## Storage Pool Configuration

### Example Configuration

```yaml
storage_pools:
  - name: "local-lvm"
    type: "lvm"
    path: "/var/lib/vz"
  
  - name: "nfs-shared"
    type: "nfs"
    server: "nas.example.com"
    export: "/volume1/vm-storage"
  
  - name: "zfs-pool"
    type: "zfs"
    pool: "tank/vm"
```

## Decision Criteria

When choosing storage:

1. **Performance Requirements**
   - IOPS needs
   - Latency tolerance
   - Throughput requirements

2. **Availability Requirements**
   - Redundancy needs
   - Backup requirements
   - Disaster recovery

3. **Cost Considerations**
   - Hardware costs
   - Maintenance overhead
   - Scalability

4. **Operational Complexity**
   - Management overhead
   - Monitoring requirements
   - Troubleshooting complexity

## Best Practices

- Separate OS and data disks
- Use appropriate storage types for workload
- Implement regular backups
- Monitor storage usage and performance
- Plan for growth and expansion

## Migration Strategy

When changing storage:

1. Plan migration during maintenance window
2. Backup all VMs
3. Migrate VMs to new storage
4. Verify functionality
5. Update documentation

