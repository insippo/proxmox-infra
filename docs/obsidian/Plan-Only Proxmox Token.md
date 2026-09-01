---
title: Plan-Only Proxmox Token
aliases:
  - Agent token
  - terraform-planner role
tags:
  - howto
  - proxmox
  - security
  - ai-agents
repo: insippo/proxmox-infra
source: docs/agent-environment.md
up: "[[Agent Environment]]"
---

# Plan-Only Proxmox Token

The repository's `docs/terraform-proxmox-api-token.md` describes **one** token holding the full
write set: `VM.Allocate`, `VM.Clone`, `VM.Config.*`, `VM.PowerMgmt`, `Datastore.Allocate`,
`Datastore.AllocateSpace`.

That token is correct for an operator running `terraform apply`.

> [!danger] It must never be the token an agent holds.

## The second token

Create a separate token for agent and CI use:

- **User:** a dedicated `agent@pve` — not `root@pam`, not the Terraform user
- **Privilege separation:** enabled
- **Role:** custom, e.g. `terraform-planner`, holding only:
  - `VM.Audit`
  - `Datastore.Audit`
  - `Sys.Audit`
- **Path:** scope the ACL to the VM pool in use, not to `/`
- **Expiration:** set one — a non-expiring agent token is a permanent liability

This is enough for `terraform plan` and for reading state. It cannot create, clone, reconfigure,
power-cycle, or delete anything.

> [!info] When an apply is needed
> If an agent's plan requires an apply, a human runs the apply with the operator token. That is
> the gate, and it is the point.

## Verify which token you are holding

```bash
./scripts/check-proxmox-token-permissions.sh
```

## Related

- [[Rights Not Prompts]]
- [[Agent Permission Matrix]]
- [[Agent Environment Gaps]]
