# Home Assistant Update Log — Garaaž HA

One entry per update session. Procedure:
`docs/operations/home-assistant-updates.md`.

Record what was applied, what was held back and why, and anything that broke.
An update that is not logged did not happen.

Entry template:

```
## YYYY-MM-DD

**Pending:** <count> — <list>
**Applied:** <list, in order>
**Held:** <list + reason>
**Notes:** <what broke, what was verified, snapshot deleted y/n>
```

---

## 2026-08-31 — pending, not yet applied

Notification: *"🔧 Garaaž HA — uuendusi ootel — 11 uuendust"*.

**Pending (11):**

| # | Update | Layer | Risk | Order |
| --- | --- | --- | --- | --- |
| 1 | Home Assistant Core | Core | High — breaking changes, custom integrations | Step 1 |
| 2 | Home Assistant Operating System | OS | Medium — full reboot, USB passthrough | Step 2 |
| 3 | Zigbee2MQTT | Add-on | High — config migrations, Zigbee network | Step 3 |
| 4 | Grafana | Add-on | Low | Step 3 |
| 5 | Home Assistant MCP Server | Add-on | Low — check Core compatibility first | Step 3 |
| 6 | Better Thermostat | HACS custom integration | High — breaks on Core upgrades | Step 4 (check before Step 1) |
| 7 | `K1 Max – kapi vent` (Shelly 1 Mini) | Device firmware | Medium | Step 5 |
| 8 | `K1 Max – printeri toide` (Shelly 1PM) | Device firmware | **High — printer mains power** | Step 5, printer idle only |
| 9 | `Kapi all lambid` (Shelly 1 Mini) | Device firmware | Medium | Step 5 |
| 10 | `shelly1minig3-54320468c06c` | Device firmware | Unknown load | Step 5, identify first |
| 11 | `shelly1minig3-dcda0ce25a78` | Device firmware | Unknown load | Step 5, identify first |

**Applied:** none yet.

**Blockers / prerequisites:**

- Backup + Proxmox snapshot not yet taken (Step 0).
- Better Thermostat compatibility with the target Core version not yet
  verified. Verify before applying #1.
- Devices #10 and #11 still carry factory hostnames. Identify and rename them
  in Home Assistant before flashing.

**Planned sessions:** not one sitting. Suggested split — session A: #1–#2
(Core + OS, the long ones, budget a half-day for the recorder migration alone);
session B: #3–#6 (add-ons + Better Thermostat); session C: #7–#11 (Shelly
firmware, on site, one device at a time). Splitting makes it obvious which
change caused a problem.

**Notes:** Physical access to the garage is required for the Shelly firmware
updates (#7–#11). Do not start that step remotely. Allow up to 24 hours after
the last change before calling the batch done — battery Zigbee devices only
report when they next wake.
