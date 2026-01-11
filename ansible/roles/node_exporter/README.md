# Node Exporter Role

Ansible role to install and configure prometheus-node-exporter on Proxmox hosts.

## Purpose

Node Exporter exposes host-level metrics for Prometheus monitoring:
- CPU usage and load average
- Memory usage (total, free, cached, buffers)
- Disk I/O (read/write operations, throughput)
- Disk space usage (per filesystem)
- Network I/O (bytes sent/received, errors)
- System uptime and boot time

## Safety

**Why this is safe:**
- **Read-only**: Only reads `/proc` and `/sys` filesystems
- **No authentication**: Metrics endpoint is public (internal network only)
- **No write operations**: Cannot modify system state
- **No credentials**: Does not access Proxmox API or sensitive data
- **Standard metrics**: Same as any Linux monitoring tool
- **No firewall changes**: Does not open firewall ports (configure separately if needed)

## Installation

The role installs `prometheus-node-exporter` from system package manager (apt).

**Service:**
- Service name: `prometheus-node-exporter`
- Port: 9100 (default)
- Metrics path: `/metrics`
- Example: `http://proxmox-host:9100/metrics`

## Configuration

**Enable the role:**
Set `node_exporter_enabled: true` in `ansible/group_vars/proxmox_hosts.yml`

**Default:**
- `node_exporter_enabled: false` (disabled by default, safe)

## Usage

The role is integrated into `ansible/playbooks/proxmox-host.yml` and runs conditionally:

```yaml
roles:
  - role: node_exporter
    when: node_exporter_enabled | bool
```

## Firewall

**Important**: This role does NOT configure firewall rules.

If you need to allow access to port 9100:
- Configure firewall separately
- Restrict access to monitoring network only
- Do not expose to public internet

## Verification

After installation, verify node_exporter is running:

```bash
systemctl status prometheus-node-exporter
curl http://localhost:9100/metrics
```

## Metrics Examples

Typical metrics exposed:
- `node_cpu_seconds_total` - CPU time by mode
- `node_memory_MemTotal_bytes` - Total memory
- `node_filesystem_size_bytes` - Filesystem sizes
- `node_disk_io_time_seconds_total` - Disk I/O time
- `node_network_receive_bytes_total` - Network receive

## Integration with Prometheus

Prometheus scrapes metrics from node_exporter:

```yaml
- job_name: 'node-exporter'
  static_configs:
    - targets: ['proxmox-host:9100']
```

See `monitoring/prometheus/prometheus.yml.example` for configuration.

## Idempotency

The role is idempotent:
- Safe to run multiple times
- Only installs if not present
- Only starts service if not running
- No side effects on repeated runs

