---
title: Agent Permission Matrix
aliases:
  - Õiguste maatriks
tags:
  - reference
  - security
  - ai-agents
  - proxmox
repo: insippo/proxmox-infra
source: docs/agent-environment.md
up: "[[Agent Environment]]"
---

# Agent Permission Matrix

What an automated identity may do, and — the part that matters — what enforces each answer.

| Action | Agent | Enforced by |
|---|---|---|
| Read the repository, run linters | ✅ | No credential needed |
| `ansible-playbook --check --diff` | ✅ | Read-only Ansible user |
| `ansible/playbooks/host-audit.yml` | ✅ | Read-only by construction |
| `terraform plan` | ✅ | [[Plan-Only Proxmox Token]] |
| Open a branch and a pull request | ✅ | Repository write, no merge |
| Merge to `master` | ❌ | Branch protection + required CI |
| `terraform apply` (create/update) | ❌ | Token lacking `VM.Allocate` / `Datastore.Allocate` |
| `terraform destroy`, any VM deletion | ❌ | Token lacking `VM.Allocate`; `prevent_destroy` |
| Ansible apply run (no `--check`) | ❌ | Read-only SSH user, no sudo |
| Storage configuration changes | ❌ | Not reachable by the token; policy review required |
| `ssh_keys_enforce: true` | ❌ | Human, with console access open |
| API token creation or rotation | ❌ | Human, Proxmox UI |

> [!important] Read the right-hand column
> Every ❌ is a credential the agent does not hold, not an instruction it was asked to follow.
> See [[Rights Not Prompts]].

## Related

- [[Agent Environment]]
- [[Rights Not Prompts]]
- [[Plan-Only Proxmox Token]]
