---
title: CI Quality Gate
aliases:
  - The reviewer
  - Ansible Lint failure
tags:
  - ci
  - status
  - proxmox
  - blocker
repo: insippo/proxmox-infra
source: docs/agent-environment.md
workflow: .github/workflows/ci.yml
up: "[[Agent Environment]]"
status: fixed-pending-merge
---

# CI Quality Gate

The reviewer in the [[Agent Environment]] model. Without one, an environment-driven agent
optimises for volume.

Defined in `.github/workflows/ci.yml`: `ansible-lint`, `terraform fmt -check`,
`terraform validate`. Runs on every push and pull request. Deploys nothing.

> [!note] The reviewer is a machine, not the agent's own judgement.
> An agent may not merge on the grounds that it believes the work is correct.

## Was broken since inception — now fixed, pending merge

> [!bug] `Ansible Lint` failed on every run of the quality gate
> All 19 runs on `master`, from run #1 (`Add basic CI quality gate for Ansible and Terraform`)
> onward. The `terraform fmt` and `terraform validate` jobs always passed.

A gate that rejects everything gates nothing. It cannot distinguish a good change from a bad one,
so nobody can use it as a merge condition, and in practice it was ignored.

### Causes

1. **Roles cannot be resolved.** `roles_path` is not configured, so `ansible-lint` looks under
   `ansible/playbooks/roles` and never finds `ansible/roles/`.
   - `syntax-check[specific]: the role 'ssh_keys' was not found` — `ansible/playbooks/proxmox-host.yml:29`
   - `syntax-check[specific]: the role 'docker' was not found` — `ansible/playbooks/vm-base.yml:15`
2. **Missing collection.** `ansible.posix` is not installed in the CI job, so
   `ansible.posix.authorized_key` does not resolve — `roles/admin_user/tasks/main.yml:24`,
   `roles/ssh_keys/tasks/main.yml:20`.
3. **`profile: production`** in `.ansible-lint` enforces rules the roles do not satisfy:
   `var-naming[no-role-prefix]`, `no-handler`, `command-instead-of-module`, plus
   `yaml[trailing-spaces]` and `yaml[empty-lines]`.

### The fix

- [x] `ansible.cfg` at the repository root with `roles_path = ansible/roles`
- [x] `ansible/requirements.yml` declaring `ansible.posix` and `community.general`, installed
      by the lint job so local runs match CI
- [x] `production` profile findings resolved: `--fix` formatting, the role-prefix rename, and
      two deviations annotated with `noqa` and a stated reason rather than silently relaxed
- [x] `ansible.builtin.timezone` → `community.general.timezone` — it is not in ansible-core and
      would have failed at runtime, not only in the linter

Verified: `Profile 'production' was required, and it passed`, 0 failures. All three playbooks
now pass `--syntax-check`; none did before.

> [!warning] Still blocks everything else until merged
> Until the gate is green on `master`, "CI is green" is not a usable metric and no automated
> identity should be granted anything beyond read access.

> [!tip] Worth adding
> The lint job installs `ansible-lint` unpinned. A future release adding rules can turn the gate
> red again with no change to this repository. Pinning it removes that failure mode.

## Related

- [[Agent Environment]]
- [[Agent Environment Gaps]]
