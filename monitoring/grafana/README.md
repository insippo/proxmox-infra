# Grafana Configuration

Grafana visualizes metrics collected by Prometheus.

## Grafana Role Purpose

The Grafana Ansible role (`ansible/roles/grafana/`):
- Installs Grafana from official repository
- Configures Prometheus as default datasource
- Enables and starts Grafana service
- Provides read-only visualization of metrics

## Architecture

**Read-only visualization:**
- Grafana queries Prometheus (read-only)
- No direct access to Proxmox hosts
- Dashboards display metrics only
- No write operations

## Prometheus Datasource Explanation

**How Grafana connects to Prometheus:**

1. **Datasource Configuration**
   - File: `/etc/grafana/provisioning/datasources/prometheus.yml`
   - Automatically provisioned by Ansible role
   - URL: `http://monitoring-prometheus:9090` (example, update with actual hostname)

2. **Connection Type**
   - **Proxy mode**: Grafana queries Prometheus on behalf of users
   - No direct browser access to Prometheus needed
   - Centralized through Grafana

3. **Query Flow**
   ```
   User → Grafana UI → Prometheus API → Metrics
   ```
   - User creates dashboard in Grafana
   - Grafana sends PromQL queries to Prometheus
   - Prometheus returns metrics
   - Grafana visualizes results

4. **Why this is safe:**
   - Grafana only reads from Prometheus (read-only)
   - No write operations to Prometheus
   - No direct Proxmox access
   - No credentials in datasource config (internal network)

## Data Source

**Prometheus:**
- Primary data source for all dashboards
- Connection: `http://monitoring-prometheus:9090` (update with actual hostname)
- No authentication required (internal network)
- Automatically configured by Ansible role

## Dashboards

**Location**: `dashboards/`

Dashboards will be added here for:
- Proxmox host metrics (CPU, memory, disk, network)
- VM status and resource usage
- Storage pool utilization
- Cluster health

## Setup

1. Configure Prometheus as data source in Grafana UI
2. Import dashboards from `dashboards/` directory
3. Dashboards use Prometheus queries (read-only)

## Security Notes

**Read-only operation:**
- Grafana queries Prometheus only (read-only)
- No write operations to Prometheus or Proxmox
- Cannot modify metrics or configuration
- Cannot start/stop VMs or change Proxmox settings

**No writes:**
- Grafana does not write data to Prometheus
- Grafana does not write to Proxmox API
- All operations are read-only queries
- Dashboards are stored locally in Grafana database

**Network isolation:**
- Should only be accessible from monitoring network
- No direct Proxmox API access
- Authentication configured separately (not in this repo)
- Default admin password should be changed on first login

**Data flow safety:**
```
Proxmox Hosts → node_exporter → Prometheus ← Grafana (read-only queries)
```

Grafana is the final read-only layer in the monitoring stack.

