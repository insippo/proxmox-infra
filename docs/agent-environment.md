# Agent Environment Policy

## Why this document exists

Most automation is written as a task list: "clone the template, then add the VM to
inventory, then run the playbook". That model assumes a human executor who works in
sequence and asks before doing anything unusual.

An AI agent is not that executor. It works in parallel, it does not ask, and it reads
whatever it is allowed to read. Telling it what to do in a prompt is not a control —
a prompt is a suggestion the model may reinterpret. **The only real control is what the
credentials permit.**

So this repository takes the opposite approach to agent automation:

- **A human is directed with tasks.**
- **An agent is directed with an environment.**

Give an agent a goal, a way to see the current state, a reviewer that rejects bad work,
and rights that make the destructive paths physically unreachable. Then let it work.

**Boundaries belong in permissions, not in prompts.**

## The four parts of an agent environment

Any usable agent setup needs the same four pieces. This section maps each one onto
things that already exist in this repository.

### 1. Goal and metric

An agent without a measurable goal produces plausible-looking churn. Every agent task
in this repo must state its goal as a checkable condition, not as an activity.

Acceptable goals — each one is a command whose output decides pass/fail:

| Goal | How it is measured |
|---|---|
| Hosts match declared configuration | `ansible-playbook ... --check --diff` reports no changes |
| Infrastructure matches code | `terraform plan` reports no changes |
| Repository is lintable | CI quality gate is green (see `.github/workflows/ci.yml`) |
| Hosts are healthy | Prometheus targets up, no firing alerts (see `monitoring/`) |
| Storage is policy-compliant | No configuration violates `docs/storage-policy.md` |

Unacceptable goals: "improve the Ansible roles", "clean up Terraform", "harden the
hosts". These have no failure condition, so the agent cannot tell when to stop.

### 2. Archive — the agent must be able to see what is already done

An agent picks up work from written state, not from a meeting. If the state is not
written down, the agent will re-derive it, guess it, or rediscover an incident the hard
way. This repository is already built as such an archive; that property is now load-bearing:

- `git log` — what changed, when, and why
- `docs/` — architecture, policies, and decisions (`storage-decisions.md`,
  `storage-policy.md`, `ssh-key-policy.md`)
- `docs/operations/` — the supported procedures; if it is not written there, it is not supported
- `ansible/playbooks/host-audit.yml` — read-only host reality, on demand
- `terraform plan` — the gap between declared and actual infrastructure

The audit playbook and `terraform plan` are the important ones: they are the only way an
agent can learn the *current* state without changing it. Both are read-only by
construction, and must stay that way.

**Rule:** any incident, workaround, or manual fix must land in `docs/` in the same change
that fixes it. An undocumented fix is invisible to the next agent, which means it will be
undone.

### 3. Mailbox — how work is handed over

Agents hand work to each other and to humans through the repository, not through chat:

- A branch and a pull request per unit of work
- Commit messages that state the reason, not the diff
- Documentation updated in the same PR as the change

An agent that finishes half a task must leave the half-finished state readable — an open
PR with a description of what remains — so the next run continues instead of restarting.

### 4. Reviewer — something that rejects bad work

Without a reviewer, an environment-driven agent optimises for volume. The CI quality gate
in `.github/workflows/ci.yml` is that reviewer: `ansible-lint`, `terraform fmt -check`,
`terraform validate`. It runs on every push and pull request, and it deploys nothing.

The reviewer is a machine, not the agent's own judgement. An agent may not merge on the
grounds that it believes the work is correct.

Current gaps in the reviewer are listed under [Gaps](#gaps-to-close) below.

## Rights, not prompts

This is the part that actually matters. Everything above shapes what an agent *does*;
this section decides what it *can* do.

### The blast radius in this repository

Damage here is not evenly spread. Three areas cause real, expensive loss:

1. **Storage changes.** Documented in `docs/storage-policy.md`, which exists because of a
   production incident. Storage decisions are hard to reverse.
2. **VM destruction.** `terraform apply` can destroy a VM and its disk in one step.
3. **SSH key enforcement.** `ssh_keys_enforce: true` rewrites `authorized_keys` — on a
   Proxmox cluster that is the shared `/etc/pve/priv/authorized_keys`. A wrong key list
   locks every administrator out of every node.

Everything else — linting, docs, monitoring dashboards, role refactors — is cheap to get
wrong and cheap to revert. That asymmetry is the design input: **the read and plan plane
stays wide open, the write plane stays narrow.**

### Permission matrix

| Action | Agent | Enforced by |
|---|---|---|
| Read the repository, run linters | Yes | No credential needed |
| `ansible-playbook --check --diff` | Yes | Read-only Ansible user (see below) |
| `ansible/playbooks/host-audit.yml` | Yes | Read-only by construction |
| `terraform plan` | Yes | Plan-only Proxmox API token |
| Open a branch and a pull request | Yes | Repository write, no merge |
| Merge to `master` | No | Branch protection + required CI |
| `terraform apply` (create/update) | No | Token lacking `VM.Allocate` / `Datastore.Allocate` |
| `terraform destroy`, any VM deletion | No | Token lacking `VM.Allocate`; `prevent_destroy` |
| Ansible apply run (no `--check`) | No | Read-only SSH user, no sudo |
| Storage configuration changes | No | Not reachable by the token; policy review required |
| `ssh_keys_enforce: true` | No | Human, with console access open |
| API token creation or rotation | No | Human, Proxmox UI |

The right-hand column is the point. Each "No" is a credential that does not exist for the
agent, not an instruction it was asked to follow.

### Proxmox: two tokens, not one

`docs/terraform-proxmox-api-token.md` describes one token holding the full write set
(`VM.Allocate`, `VM.Clone`, `VM.Config.*`, `VM.PowerMgmt`, `Datastore.Allocate`,
`Datastore.AllocateSpace`). That token is correct for an operator running `terraform apply`.
It must never be the token an agent holds.

Create a second, separate token for agent and CI use:

- **User:** a dedicated `agent@pve` user — not `root@pam`, not the Terraform user
- **Privilege separation:** enabled
- **Role:** a custom role, e.g. `terraform-planner`, holding only:
  - `VM.Audit`
  - `Datastore.Audit`
  - `Sys.Audit`
- **Path:** scope the ACL to the VM pool in use, not to `/`
- **Expiration:** set one; a non-expiring agent token is a permanent liability

This is enough for `terraform plan` and for reading state. It cannot create, clone,
reconfigure, power-cycle, or delete anything. If an agent's plan requires an apply, a
human runs the apply with the operator token.

Verify which token you are holding before running anything:

```bash
./scripts/check-proxmox-token-permissions.sh
```

### SSH: the agent is not root

The Ansible path needs the same split:

- The agent connects as an unprivileged user with **no** `sudo` rights, sufficient for
  `--check` runs and fact gathering.
- `root` on Proxmox hosts stays with humans and console recovery. See the SSH policy in
  `docs/architecture.md` and `docs/ssh-key-policy.md`.
- `ssh_keys_enforce` stays `false` for every agent-reachable path. Enforcement is a
  human action, performed with a console session already open, per
  `docs/operations/ssh-key-rotation.md`.

An agent that cannot become root cannot lock anyone out, regardless of what it decides
to do.

### Terraform: guards in code

`prevent_destroy = true` is already set on the monitoring VMs in `terraform/main.tf`.
Set it on every VM that holds state or that something depends on. It is not a substitute
for token scoping — an agent with an apply token could remove the guard and then apply —
but combined with a plan-only token it makes destruction unreachable from two directions.

### Secrets

`terraform.tfvars`, `ansible/inventory.yml`, and API token secrets are not committed and
must not be readable by an agent that opens pull requests. An agent's run environment
should carry the plan token and nothing else. Anything an agent can read, it can
inadvertently write into a diff or a PR description.

## The rest cycle: scheduled read-only runs

Station's agents were given cycles where work was forbidden and only reflection was
allowed. The infrastructure equivalent is a scheduled run that is allowed to look and
report, but not to change:

- `ansible-playbook ... --check --diff` against all hosts → configuration drift
- `terraform plan` → infrastructure drift
- `ansible/playbooks/host-audit.yml` → hardware, storage, and version reality
- A check of monitoring targets and firing alerts

The output is a report or an issue, never a change. Drift found this way is the most
valuable input an agent environment produces, because it is the difference between what
the repository claims and what the hardware is actually doing — and nobody notices it
during normal work.

## Where the analogy breaks

The Station experiment ran in mathematics, where a wrong result costs nothing: the
reviewer rejects it and the agent moves on. Infrastructure is not that domain. A wrong
`terraform apply` destroys a disk; a wrong `authorized_keys` locks out every
administrator. There is no reviewer that catches it after the fact.

So the model is adopted asymmetrically, and deliberately:

- **Exploration is unbounded** in the read and plan plane — reading, auditing, planning,
  linting, drafting documentation and pull requests.
- **The write plane stays narrow and human-gated**, exactly where `docs/storage-policy.md`
  already says the expensive mistakes live.

Autonomy is granted where mistakes are cheap and reversible. It is not granted where they
are not. That boundary is drawn in the Proxmox role and the SSH user — where it can be
verified — and not in an instruction anyone can talk their way past.

## Gaps to close

The environment described above is not fully in place. Current state:

- [ ] **No plan-only Proxmox token documented.** `docs/terraform-proxmox-api-token.md`
      describes only the full-write operator token. Add the `terraform-planner` role and
      the `agent@pve` user.
- [ ] **No branch protection on `master`.** CI runs, but nothing prevents a direct push or
      a merge with a red gate. Require the quality gate and at least one review.
- [ ] **No `CODEOWNERS`.** `docs/storage-policy.md`, `docs/ssh-key-policy.md`, and
      `terraform/` should require named human review on change.
- [ ] **CI checks style, not policy.** `ansible-lint` and `terraform validate` do not
      catch a ZFS datastore on consumer hardware, `ssh_keys_enforce: true`, or a removed
      `prevent_destroy`. These are the changes worth failing a build over — add a policy
      check job.
- [ ] **No scheduled drift run.** The read-only checks above exist but are only run by
      hand, which means they are run after an incident rather than before one.
- [ ] **No read-only Ansible user defined.** `ansible/group_vars/proxmox_hosts.yml`
      configures the admin user; there is no unprivileged, sudo-less agent user.

Close these before granting any agent scheduled or unattended access to the hosts.

## Document control

**Review frequency:** whenever agent access, API tokens, or CI gating changes.

**Approval required:** for any change that widens what an automated identity may do.
