# rkhunter role

Installs [rkhunter](https://rkhunter.sourceforge.net/) (Rootkit Hunter) on
Debian-based hosts and deploys `/etc/rkhunter.conf.local` with whitelists for
known-benign findings, so scheduled scans only alert on things worth looking at.

## Why the whitelist exists

A stock rkhunter scan on a host running Podman produces these warnings:

```
Warning: Suspicious file types found in /dev:
         /dev/shm/libpod_rootless_lock_1000: data
         /dev/shm/libpod_lock: data
Warning: Hidden file found: /usr/share/man/man5/.containerignore.5.gz: symbolic link to containerignore.5.gz
```

All three are false positives:

- `/dev/shm/libpod_lock` and `/dev/shm/libpod_rootless_lock_<uid>` are Podman's
  shared-memory lock files. rkhunter flags *any* plain file under `/dev` as
  suspicious; Podman legitimately keeps its locks in `/dev/shm`. The rootless
  variant is named after the UID of the user running rootless containers
  (e.g. `1000`), which is why the whitelist uses a wildcard.
- `/usr/share/man/man5/.containerignore.5.gz` is a hidden symlink shipped by
  the Debian `podman`/`buildah` packages as a man-page alias for
  `containerignore(5)`. Verify with `dpkg -S /usr/share/man/man5/.containerignore.5.gz`.

The role whitelists them via `ALLOWDEVFILE` / `ALLOWHIDDENFILE` in
`/etc/rkhunter.conf.local`, which rkhunter reads automatically after
`/etc/rkhunter.conf` — package upgrades never overwrite it.

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `rkhunter_enabled` | `false` (in `group_vars/vms.yml`) | Enable the role on a host/group |
| `rkhunter_allow_dev_files` | Podman lock files | `ALLOWDEVFILE` entries |
| `rkhunter_allow_hidden_files` | `.containerignore.5.gz` symlink | `ALLOWHIDDENFILE` entries |
| `rkhunter_allow_hidden_dirs` | `[]` | `ALLOWHIDDENDIR` entries |
| `rkhunter_script_whitelist` | `[]` | `SCRIPTWHITELIST` entries |
| `rkhunter_cron_daily_run` | `true` | Daily cron scan (`/etc/default/rkhunter`) |
| `rkhunter_cron_db_update` | `true` | Weekly data-file update via cron |

## Usage

Enable per host or group in the inventory:

```yaml
vms:
  hosts:
    debian:
      rkhunter_enabled: true
```

Then run:

```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit debian
```

After deployment, confirm the warnings are gone:

```bash
sudo rkhunter --check --sk --rwo
```

(`--rwo` prints warnings only; no output for these checks means clean.)
