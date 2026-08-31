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
- **Never start an update you cannot wait out.** Every step below finishes on
  its own schedule, not yours. See *Time budget*.
- **One update session, one log entry.** See
  `docs/operations/home-assistant-update-log.md`.

## Time budget

**Plan a half-day window, not an hour.** These updates are slow, and most of
the elapsed time is waiting, not clicking. Rushing is what turns a routine
update into an outage: the common failure is an operator who decides something
is stuck, restarts or power-cycles mid-operation, and breaks it for real.

| Step | Realistic time | What drives it |
| --- | --- | --- |
| 0 – Backup + snapshot | 10–30 min | Backup size; copying it off the VM |
| 1 – Core | 10–20 min, **plus DB migration** | See below — migration can run for hours |
| 2 – OS | 15–30 min | Download, reboot, slower first boot |
| 3 – Add-ons | 5–15 min each | Z2M network settling is extra, see below |
| 4 – Better Thermostat | 5 min, plus a heating cycle | Calibration re-establishes over time |
| 5 – Shelly firmware | 5–10 min per device | Reboot and Wi-Fi reconnect per device |

Full settling — every device reporting normally again — can take **up to 24
hours** after the last change. Do not judge the result on the first ten
minutes.

**Splitting the batch across several days is normal and preferred.** There is
no requirement to clear all pending updates in one sitting. Core and OS in one
session, add-ons in another, device firmware in a third is a perfectly good
plan, and it makes it obvious which change caused a problem.

Do not start on an evening when the garage is needed the next morning, and do
not start remotely.

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

**The recorder database migration is the slow part.** Some Core releases
change the recorder schema and migrate the database *after* HA has already
started. During that migration HA is reachable but sluggish, and history and
the logbook are incomplete. On a long-lived database this runs for anything
from a few minutes to several hours. **Do not restart HA, and do not reboot the
VM, while it is running** — an interrupted migration is how the database gets
corrupted. Watch the log for the migration to report finished; only then judge
whether the update worked.

Verify: HA restarts, Settings → System → Repairs is clean, the garage
automations still show as available (no `unavailable` entities). Give entities
a few minutes to repopulate before treating an `unavailable` one as broken.

## Step 2 – Home Assistant Operating System

Settings → System → Updates → *Home Assistant Operating System* → Update.

This reboots the whole appliance. Expect the VM to be unreachable for several
minutes — the download runs first, then the reboot, and the first boot on a new
OS version is slower than usual. **Do not force-stop the VM from Proxmox
because the UI has not come back yet**; give it a good 15 minutes before
treating it as hung. Do not run this step remotely unless you can reach the
Proxmox console.

Verify: VM boots, HA UI returns, Settings → System → Hardware still lists the
Zigbee coordinator (a USB passthrough that silently drops after a reboot is the
failure mode to watch for here).

## Step 3 – Add-ons

Update one at a time, verifying between each:

1. **Zigbee2MQTT** — the highest-risk add-on. Confirm `coordinator_backup.json`
   is current (Step 0), read the Z2M release notes for configuration migrations,
   then update. Verify: add-on starts, and a round-trip works (toggle one
   mains-powered device from HA and see the state come back).

   **Do not expect the whole Zigbee network back immediately.** Mains-powered
   routers rejoin within minutes. Battery devices only report when they next
   wake up, which can be hours — a battery sensor still showing as unavailable
   the same evening is normal and is not evidence that the update failed. Do
   not re-pair anything on day one; re-pairing a device that was going to come
   back on its own only makes the mesh worse.
2. **Grafana** — low risk. Verify: dashboards render and the Prometheus data
   source is still connected (see `monitoring/grafana/README.md`).
3. **Home Assistant MCP Server** — verify the MCP client can still list tools
   after the restart.

## Step 4 – Custom integrations (HACS)

**Better Thermostat**: update via HACS, then restart Home Assistant. Verify the
climate entities are back and are not stuck in `unavailable`.

Better Thermostat holds calibration state that is re-established after a
restart, and that takes a full heating cycle — the valve position looking wrong
in the first minutes after the restart is expected, not a fault. Check that the
target temperature actually reaches the valve, then leave it alone for a cycle
before concluding anything.

## Step 5 – Shelly device firmware (last, one at a time)

Device firmware is updated **after** the platform is confirmed healthy, never
in the same pass. A failed flash leaves the device offline until it is power
cycled by hand.

For each device: check what it controls, confirm the load is idle, update,
wait for it to come back, verify it responds from HA. Then move to the next.

**Wait out each device before starting the next one.** A Shelly reboots and
reconnects to Wi-Fi after flashing, which takes a few minutes; a Gen3 doing a
two-stage update takes longer and can look dead in between. **Never cut power
to a Shelly that is mid-update** — that is the one reliable way to brick it.
Budget 5–10 minutes per device and do not batch them.

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

## Slow is not broken

Most "the update broke everything" reports are an operator intervening too
early. Before acting, check whether what you are seeing is on this list:

| What you see | Normal wait before it is a problem |
| --- | --- |
| HA sluggish, history gaps after a Core update | Until the recorder migration finishes — minutes to hours. Do not restart |
| VM unreachable after the OS update | ~15 min, including download and a slow first boot |
| Entities `unavailable` right after a restart | A few minutes while they repopulate |
| Battery Zigbee devices missing after a Z2M update | Until they next wake — often hours. Do not re-pair |
| Valve position looks wrong after Better Thermostat | One full heating cycle |
| A Shelly offline right after flashing | Several minutes. Never cut its power meanwhile |

If it is still wrong after the wait, then it is a fault — see below.

## If it breaks

| Symptom | Action |
| --- | --- |
| HA does not start after Core update | Restore the HA backup, or roll back Core from the CLI: `ha core update --version <previous>` |
| Whole appliance unreachable after OS update | Proxmox console; if unrecoverable, restore the snapshot from Step 0 |
| Zigbee devices all gone after Z2M update | Restore `coordinator_backup.json` and pin the previous Z2M version |
| Zigbee coordinator missing after reboot | Check USB passthrough on the VM in Proxmox before re-pairing anything |
| Shelly offline after firmware update | Power cycle at the breaker; if still dead, factory reset and re-adopt |
