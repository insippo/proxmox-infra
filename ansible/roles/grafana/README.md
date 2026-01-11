# Grafana Role

Ansible role to install and configure Grafana on monitoring VMs.

## Purpose

Grafana visualizes metrics collected by Prometheus:
- Queries Prometheus for metrics (read-only)
- Displays dashboards for Proxmox infrastructure
- No direct access to Proxmox hosts or VMs
- Read-only visualization only

## Safety

**Why this is safe:**
- **Read-only**: Grafana only queries Prometheus (read-only)
- **No write operations**: Cannot modify Proxmox hosts or VMs
- **No direct Proxmox access**: Does not connect to Proxmox API
- **No credentials in config**: Prometheus datasource URL only (no auth)
- **No dashboards by default**: Dashboards added separately

## Installation

The role installs Grafana from official Grafana repository.

**Service:**
- Service name: `grafana-server`
- Port: 3000 (default)
- Web UI: `http://grafana-vm:3000`
- Default login: `admin` / `admin` (change on first login)

## Configuration

**Enable the role:**
Set `grafana_enabled: true` in `ansible/group_vars/vms.yml`

**Default:**
- `grafana_enabled: false` (disabled by default, safe)

**Prometheus Datasource:**
- Automatically configured via provisioning
- URL: `http://monitoring-prometheus:9090` (example)
- Update with actual Prometheus VM hostname/IP
- No authentication configured (internal network)

## Usage

The role is integrated into `ansible/playbooks/vm-base.yml` and runs conditionally:

```yaml
roles:
  - role: grafana
    when: grafana_enabled | bool
```

## Prometheus Datasource

Grafana is configured with Prometheus as the default datasource:

**Configuration:**
- File: `/etc/grafana/provisioning/datasources/prometheus.yml`
- Type: Prometheus
- Access: Proxy (Grafana queries Prometheus)
- URL: `http://monitoring-prometheus:9090` (update with actual hostname)

**Why proxy mode:**
- Grafana queries Prometheus on behalf of users
- No direct browser access to Prometheus needed
- Centralized authentication (when configured)

## Web UI Access

After installation:
1. Access Grafana: `http://grafana-vm:3000`
2. Default login: `admin` / `admin`
3. Change password on first login
4. Prometheus datasource is pre-configured

## Dashboards

**Not included in this role:**
- Dashboards are added separately
- Import from `monitoring/grafana/dashboards/` (when available)
- Or create custom dashboards in Grafana UI

## Security

- **Read-only**: Grafana queries Prometheus only (no writes)
- **No Proxmox access**: Does not connect to Proxmox API
- **Internal network**: Should only be accessible from monitoring network
- **Default auth**: Change default admin password
- **No secrets**: Configuration contains no credentials

## Idempotency

The role is idempotent:
- Safe to run multiple times
- Only installs if not present
- Only starts service if not running
- Configuration updates trigger service restart

## Verification

After installation, verify Grafana is running:

```bash
systemctl status grafana-server
curl http://localhost:3000/api/health
```

Access web UI:
```bash
# From monitoring network
http://grafana-vm:3000
```

