---
title: Rights Not Prompts
aliases:
  - Piirid on õigustes
  - Boundaries in permissions
tags:
  - principle
  - security
  - ai-agents
  - proxmox
repo: insippo/proxmox-infra
source: docs/agent-environment.md
up: "[[Agent Environment]]"
---

# Rights Not Prompts

> [!quote] The principle
> An instruction is not a control. A missing credential is.

A prompt is a suggestion the model may reinterpret. It is not a boundary. The only boundary
that holds under an agent that works in parallel, does not ask, and reads whatever it is
allowed to read is **what the credentials permit**.

So every "no" in [[Agent Permission Matrix]] is a credential that does not exist for the agent,
not a rule it was asked to follow.

## Blast radius

Damage is not evenly spread. Three areas cause real, expensive loss:

> [!danger] Storage changes
> Governed by the repository's storage policy, which exists because of a production incident.
> Storage decisions are hard to reverse.

> [!danger] VM destruction
> `terraform apply` can destroy a VM and its disk in one step.

> [!danger] SSH key enforcement
> `ssh_keys_enforce: true` rewrites `authorized_keys`. On a Proxmox cluster that is the shared
> `/etc/pve/priv/authorized_keys`. A wrong key list locks every administrator out of every node.

Everything else — linting, docs, monitoring dashboards, role refactors — is cheap to get wrong
and cheap to revert.

That asymmetry is the whole design input:

> [!tip] The rule that falls out of it
> The read and plan plane stays wide open. The write plane stays narrow.

## How each boundary is drawn

### Proxmox API

Two tokens, never one. The operator token holds the full write set; the agent holds an
audit-only token that cannot create, clone, reconfigure, power-cycle, or delete anything.
See [[Plan-Only Proxmox Token]].

### SSH

The agent connects as an unprivileged user with **no** `sudo` rights — enough for `--check` runs
and fact gathering. `root` on Proxmox hosts stays with humans and console recovery.

`ssh_keys_enforce` stays `false` for every agent-reachable path. Enforcement is a human action,
performed with a console session already open.

> [!success] Why this is sufficient
> An agent that cannot become root cannot lock anyone out, regardless of what it decides to do.

### Terraform

`prevent_destroy = true` on every VM that holds state or that something depends on. It is not a
substitute for token scoping — an agent with an apply token could remove the guard and then
apply — but combined with an audit-only token it makes destruction unreachable from two
directions.

### Secrets

`terraform.tfvars`, `ansible/inventory.yml`, and token secrets are not committed and must not be
readable by an agent that opens pull requests. An agent's run environment carries the plan token
and nothing else.

> [!warning] Anything an agent can read, it can inadvertently write into a diff or a PR description.

## Related

- [[Agent Environment]]
- [[Agent Permission Matrix]]
- [[Plan-Only Proxmox Token]]
