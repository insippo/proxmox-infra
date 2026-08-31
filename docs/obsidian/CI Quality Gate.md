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
status: failing
---

# CI Quality Gate

The reviewer in the [[Agent Environment]] model. Without one, an environment-driven agent
optimises for volume.

Defined in `.github/workflows/ci.yml`: `ansible-lint`, `terraform fmt -check`,
`terraform validate`. Runs on every push and pull request. Deploys nothing.

> [!note] The reviewer is a machine, not the agent's own judgement.
> An agent may not merge on the grounds that it believes the work is correct.

## Current state: broken since inception

> [!bug] `Ansible Lint` has failed on every run of the quality gate
> All 19 runs on `master`, from run #1 (`Add basic CI quality gate for Ansible and Terraform`)
> onward. The `terraform fmt` and `terraform validate` jobs pass.

A gate that rejects everything gates nothing. It cannot distinguish a good change from a bad one,
so nobody can use it as a merge condition, and in practice it is ignored.

### Known causes

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

### Proposed fix

- [ ] Add `ansible/ansible.cfg` with `roles_path = roles`
- [ ] Add `ansible-galaxy collection install ansible.posix` to the lint job, ideally via a
      committed `requirements.yml` so local runs match CI
- [ ] Decide explicitly on the profile: fix the findings, or drop to `profile: moderate` and
      re-add rules as the roles are cleaned up
- [ ] Fix trailing whitespace and blank lines regardless — mechanical, no judgement needed

> [!warning] This blocks everything else
> Until the gate is green on `master`, "CI is green" is not a usable metric and no automated
> identity should be granted anything beyond read access.

## Related

- [[Agent Environment]]
- [[Agent Environment Gaps]]
