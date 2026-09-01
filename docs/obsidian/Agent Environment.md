---
title: Agent Environment
aliases:
  - Agent Environment MOC
  - Agendikeskkond
tags:
  - moc
  - proxmox
  - automation
  - ai-agents
  - policy
repo: insippo/proxmox-infra
source: docs/agent-environment.md
status: draft
---

# Agent Environment

> [!abstract] The whole idea in two lines
> **A human is directed with tasks. An agent is directed with an environment.**
> Give it a goal, a way to see the current state, a reviewer that rejects bad work, and
> rights that make the destructive paths unreachable. Then let it work.

This is the map of content for how automated identities — CI, scheduled scripts, AI agents —
are allowed to operate against the Proxmox infrastructure in `insippo/proxmox-infra`.

Canonical version lives in the repository at `docs/agent-environment.md`. These notes are the
vault copy; when they disagree, the repository wins.

## Start here

- [[Rights Not Prompts]] — the core principle and the blast radius it is drawn around
- [[Agent Permission Matrix]] — what an agent may do, and what enforces each "no"
- [[Plan-Only Proxmox Token]] — the concrete credential split
- [[CI Quality Gate]] — the reviewer, and why it does not currently work
- [[Agent Environment Gaps]] — what has to be built before granting unattended access

## The four parts of an agent environment

Any usable agent setup needs the same four pieces. Each maps onto something that already
exists in the repository.

| Part | What it does | Where it lives here |
|---|---|---|
| **Goal and metric** | Gives a checkable stopping condition | See [[#Goals that work]] |
| **Archive** | Lets the agent see what is already done | `git log`, `docs/`, `host-audit.yml`, `terraform plan` |
| **Mailbox** | Hands work between agents and humans | Branches, pull requests, commit messages |
| **Reviewer** | Rejects bad work | [[CI Quality Gate]] |

### Goals that work

A goal must be a command whose output decides pass/fail. Anything else produces
plausible-looking churn.

| Goal | How it is measured |
|---|---|
| Hosts match declared configuration | `ansible-playbook … --check --diff` reports no changes |
| Infrastructure matches code | `terraform plan` reports no changes |
| Repository is lintable | CI quality gate is green — **currently unattainable**, see [[CI Quality Gate]] |
| Hosts are healthy | Prometheus targets up, no firing alerts |
| Storage is policy-compliant | Nothing violates the storage policy |

> [!fail] Not goals
> "Improve the Ansible roles." "Clean up Terraform." "Harden the hosts."
> No failure condition means the agent cannot tell when to stop.

### The archive is load-bearing

An agent picks up work from written state, not from a meeting. If it is not written down,
the agent re-derives it, guesses it, or rediscovers an incident the hard way.

- `git log` — what changed, when, and why
- `docs/` — architecture, storage policy, SSH key policy, storage decisions
- `docs/operations/` — the supported procedures; if it is not written there, it is not supported
- `ansible/playbooks/host-audit.yml` — read-only host reality, on demand
- `terraform plan` — the gap between declared and actual infrastructure

The last two matter most: they are the only way to learn the *current* state without changing
it. Both are read-only by construction and must stay that way.

> [!important] Rule
> Any incident, workaround, or manual fix lands in `docs/` in the same change that fixes it.
> An undocumented fix is invisible to the next agent, which means it will be undone.

## The rest cycle

A scheduled run that may look and report, but not change:

- `ansible-playbook … --check --diff` → configuration drift
- `terraform plan` → infrastructure drift
- `host-audit.yml` → hardware, storage, and version reality
- Monitoring targets and firing alerts

Output is a report or an issue, never a change. Drift found this way is the most valuable
thing the environment produces: it is the difference between what the repository claims and
what the hardware is actually doing, and nobody notices it during normal work.

## Where the analogy breaks

> [!danger] Infrastructure is not mathematics
> The experiment this model comes from ran in maths, where a wrong result costs nothing — the
> reviewer rejects it and the agent moves on. A wrong `terraform apply` destroys a disk. A wrong
> `authorized_keys` locks out every administrator. There is no reviewer that catches it after
> the fact.

So the model is adopted asymmetrically, deliberately:

- **Exploration is unbounded** in the read and plan plane.
- **The write plane stays narrow and human-gated**, exactly where the storage policy already
  says the expensive mistakes live.

Autonomy is granted where mistakes are cheap and reversible, and not where they are not.
See [[Rights Not Prompts]].

## Related

- [[Rights Not Prompts]]
- [[Agent Permission Matrix]]
- [[Plan-Only Proxmox Token]]
- [[CI Quality Gate]]
- [[Agent Environment Gaps]]
