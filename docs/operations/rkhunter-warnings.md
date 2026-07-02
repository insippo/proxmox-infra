# RKHunter warnings: Podman false positives

## Symptom

The daily rkhunter scan on a Debian host running Podman reports:

```
Warning: Suspicious file types found in /dev:
         /dev/shm/libpod_rootless_lock_1000: data
         /dev/shm/libpod_lock: data
Warning: Hidden file found: /usr/share/man/man5/.containerignore.5.gz: symbolic link to containerignore.5.gz
```

## Diagnosis

All three warnings are benign and caused by the Podman container runtime:

1. **`/dev/shm/libpod_lock` and `/dev/shm/libpod_rootless_lock_<uid>`** —
   Podman's shared-memory lock files. rkhunter treats any plain (non-device)
   file under `/dev` as suspicious, but Podman legitimately stores its locks
   in `/dev/shm`. The `_1000` suffix is the UID of the user running rootless
   containers.
2. **`/usr/share/man/man5/.containerignore.5.gz`** — a hidden symlink shipped
   by the Debian `podman`/`buildah` packages as a man-page alias for
   `containerignore(5)`.

Verify before whitelisting (the point of rkhunter is to notice when these
files are *not* what they claim to be):

```bash
# The man-page symlink should belong to a package:
dpkg -S /usr/share/man/man5/.containerignore.5.gz
# Expected: buildah (or podman): /usr/share/man/man5/.containerignore.5.gz

# The lock files should be plain data files owned by root / the rootless user:
ls -l /dev/shm/libpod_lock /dev/shm/libpod_rootless_lock_*
```

If `dpkg -S` says "no path found matching pattern", or the lock files look
executable, stop and investigate instead of whitelisting.

## Fix (via Ansible — preferred)

The `rkhunter` role deploys `/etc/rkhunter.conf.local` with the needed
whitelists. Enable it for the host and run the base playbook:

```yaml
# inventory.yml
vms:
  hosts:
    debian:
      rkhunter_enabled: true
```

```bash
ansible-playbook -i inventory.yml playbooks/vm-base.yml --limit debian
```

See `ansible/roles/rkhunter/README.md` for the role's variables.

## Fix (manual, one-off)

Append to `/etc/rkhunter.conf.local` (created if missing; rkhunter reads it
automatically after `/etc/rkhunter.conf`, so package upgrades keep it intact):

```
ALLOWDEVFILE=/dev/shm/libpod_lock
ALLOWDEVFILE=/dev/shm/libpod_rootless_lock_*
ALLOWHIDDENFILE=/usr/share/man/man5/.containerignore.5.gz
```

Then validate the config and re-run the scan:

```bash
sudo rkhunter --config-check
sudo rkhunter --check --sk --rwo   # --rwo = report warnings only
```

No output from the second command means the warnings are resolved.
