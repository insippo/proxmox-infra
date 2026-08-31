# How to Update the Garage Home Assistant Stack

Runbook for applying updates to the **Garaaž HA** instance (Home Assistant OS
running as a VM on Proxmox) and to the Zigbee/Wi-Fi devices it manages.

Home Assistant announces pending updates as a single notification, e.g.:

> 🔧 Garaaž HA — uuendusi ootel
> 11 uuendust: Home Assistant Core, Home Assistant Operating System, Zigbee2MQTT, …

That notification is **not** an instruction to press "Update all". Updates are
applied in a fixed order, one layer at a time, with a rollback path in place
before the first one starts.

## Rules

- **Never bulk-update.** One layer at a time, verify, then continue.
- **Never update device firmware you cannot physically reach.** A failed Shelly
  flash can require a power cycle or a factory reset at the device.
- **Never update while the load is in use.** The printer power switch is not
  touched during a print job.
- **Read release notes before Core and Zigbee2MQTT.** Both ship breaking
  changes in normal releases.
- **One update session, one log entry.** See
  `docs/operations/home-assistant-update-log.md`.

## Step 0 – Rollback path (mandatory)

Do this before touching anything.

1. **Home Assistant backup**: Settings → System → Backups → *Create backup*
   (full). Confirm it completed and note the size.
2. **Copy the backup off the VM**. A backup that only exists inside the VM you
   are about to break is not a backup.
3. **Proxmox snapshot** of the HA VM, taken while the VM is running:

   ```bash
   # on the Proxmox host, <vmid> = the Home Assistant VM
   qm snapshot <vmid> pre-ha-update-$(date +%Y%m%d) --description "before HA update batch"
   ```

4. **Zigbee2MQTT coordinator backup**: Z2M writes `coordinator_backup.json`
   into its data directory on every start. Confirm it exists and is current
   before updating Z2M.

Rollback = restore the Proxmox snapshot (whole appliance) or restore the HA
backup (configuration only). Delete the snapshot once the stack is verified
healthy — snapshots left on disk grow and violate `docs/storage-policy.md`.

## Step 1 – Home Assistant Core

Read the release notes for **every** version between the installed one and the
target, specifically the "Breaking changes" section.

Settings → System → Updates → *Home Assistant Core* → Update.
Leave "Create backup before updating" enabled.

**Before updating Core, check custom integrations.** Custom components are the
usual cause of a broken start after a Core upgrade. For this instance that
means **Better Thermostat** (HACS) and the **Home Assistant MCP Server**:
confirm the version you are moving to supports the target Core release. If it
does not, update the integration first, or hold Core back.

Verify: HA restarts, Settings → System → Repairs is clean, the garage
automations still show as available (no `unavailable` entities).

## Step 2 – Home Assistant Operating System

Settings → System → Updates → *Home Assistant Operating System* → Update.

This reboots the whole appliance. Expect the VM to be unreachable for a few
minutes. Do not run it remotely unless you can reach the Proxmox console.

Verify: VM boots, HA UI returns, Settings → System → Hardware still lists the
Zigbee coordinator (a USB passthrough that silently drops after a reboot is the
failure mode to watch for here).

## Step 3 – Add-ons

Update one at a time, verifying between each:

1. **Zigbee2MQTT** — the highest-risk add-on. Confirm `coordinator_backup.json`
   is current (Step 0), read the Z2M release notes for configuration migrations,
   then update. Verify: add-on starts, all Zigbee devices report in, and a
   round-trip works (toggle one device from HA and see the state come back).
2. **Grafana** — low risk. Verify: dashboards render and the Prometheus data
   source is still connected (see `monitoring/grafana/README.md`).
3. **Home Assistant MCP Server** — verify the MCP client can still list tools
   after the restart.

## Step 4 – Custom integrations (HACS)

**Better Thermostat**: update via HACS, then restart Home Assistant. Verify the
climate entities are back and are not stuck in `unavailable`; Better Thermostat
holds calibration state that is re-established on restart, so check the target
temperature actually applies to the valve.

## Step 5 – Shelly device firmware (last, one at a time)

Device firmware is updated **after** the platform is confirmed healthy, never
in the same pass. A failed flash leaves the device offline until it is power
cycled by hand.

For each device: check what it controls, confirm the load is idle, update,
wait for it to come back, verify it responds from HA. Then move to the next.

Current garage devices:

| Device | Model | Controls | Precondition |
| --- | --- | --- | --- |
| `K1 Max – kapi vent` | Shelly 1 Mini | Cabinet fan | Printer idle and cool |
| `K1 Max – printeri toide` | Shelly 1PM | Printer mains power | **No print running.** Cutting power mid-print destroys the job |
| `Kapi all lambid` | Shelly 1 Mini | Under-cabinet lights | Nobody working in the cabinet |
| `shelly1minig3-54320468c06c` | Shelly 1 Mini Gen3 | Unidentified — **identify before updating** | Load known and idle |
| `shelly1minig3-dcda0ce25a78` | Shelly 1 Mini Gen3 | Unidentified — **identify before updating** | Load known and idle |

Two devices still carry factory hostnames. Name them in Home Assistant before
updating them — an unnamed relay is an unknown load, and updating an unknown
load is how the printer loses power mid-print.

## Step 6 – Close out

1. Confirm Settings → System → Updates is empty (or that anything left is
   deliberately held, with the reason logged).
2. Check Settings → System → Repairs and the error log.
3. Delete the Proxmox snapshot from Step 0.
4. Add an entry to `docs/operations/home-assistant-update-log.md`.

## If it breaks

| Symptom | Action |
| --- | --- |
| HA does not start after Core update | Restore the HA backup, or roll back Core from the CLI: `ha core update --version <previous>` |
| Whole appliance unreachable after OS update | Proxmox console; if unrecoverable, restore the snapshot from Step 0 |
| Zigbee devices all gone after Z2M update | Restore `coordinator_backup.json` and pin the previous Z2M version |
| Zigbee coordinator missing after reboot | Check USB passthrough on the VM in Proxmox before re-pairing anything |
| Shelly offline after firmware update | Power cycle at the breaker; if still dead, factory reset and re-adopt |
