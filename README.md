# Proxmox Infrastructure as Code

This repository provides a complete, opinionated, and safe way to build and operate Proxmox-based infrastructure from absolute zero.

## It uses:

- **Ansible** – host and VM configuration
- **Terraform** – VM lifecycle management
- **cloud-init** – initial VM access
- **GitHub Actions** – basic quality checks

**No magic. No shortcuts. Everything is explicit and auditable.**

## Who this is for

This repository is for people who want to:

- rebuild a Proxmox host without guessing what was done last time
- create VMs repeatedly in a predictable way
- avoid storage-related disasters
- stop doing infrastructure "by memory"
- understand exactly what happens first, second, and last

**This is not beginner material, but it assumes zero prior state.**

## What this repository is NOT

- Not a tutorial series
- Not a one-click installer
- Not a demo
- Not opinion-free

**You are expected to:**

- read instructions
- run commands intentionally
- understand that infrastructure changes have consequences

## The full flow (read once)

1. Prepare Proxmox hosts with Ansible
2. Lock storage rules before creating any VMs
3. Create VMs using Terraform
4. Bootstrap access via cloud-init
5. Configure VMs with Ansible
6. Enable services explicitly (Docker, etc.)
7. Operate using documented procedures

**No step is skipped.**

## Repository structure (important)

```
proxmox-infra/
├── ansible/          – all configuration logic
├── terraform/        – VM lifecycle (create / destroy)
├── docs/             – architecture, policy, operations
├── .github/          – CI (lint + validate)
└── README.md
```

**If you don't know where something belongs, stop and look here again.**

## Step 0 – Requirements (do this first)

You need one control machine (laptop or server):

- Linux (recommended)
- Ansible installed
- Terraform installed
- SSH access to Proxmox hosts
- GitHub access (to clone the repo)

**Nothing runs directly from Proxmox.**

## Step 1 – Clone the repository

```bash
git clone https://github.com/insippo/proxmox-infra.git
cd proxmox-infra
```

**Do not change anything yet.**

## Step 2 – Prepare Proxmox hosts (mandatory)

This step configures:

- SSH safety
- logging
- sysctl baseline
- optional admin user

**Create inventory (never committed):**

```bash
cp ansible/inventory.example.yml ansible/inventory.yml
nano ansible/inventory.yml
```

Add your Proxmox hosts.

**Always dry-run first:**

```bash
ansible-playbook -i ansible/inventory.yml ansible/playbooks/proxmox-host.yml --check --diff
```

**If this fails, do not continue.**

**Apply for real:**

```bash
ansible-playbook -i ansible/inventory.yml ansible/playbooks/proxmox-host.yml
```

## Step 3 – Read the storage policy (do not skip)

Before creating any VM, read:

**`docs/storage-policy.md`**

This document exists because storage mistakes are expensive.

**If you disagree with it, change the document before changing infrastructure.**

## Step 4 – Create VMs with Terraform

Terraform defines what exists, not how it is configured.

**Prepare variables (never committed):**

```bash
cd terraform
cp example.tfvars terraform.tfvars
nano terraform.tfvars
```

**Validate first:**

```bash
terraform init -backend=false
terraform validate
```

**Create VM(s):**

```bash
terraform apply
```

VMs are now created with:

- cloud-init user
- SSH keys injected
- DHCP networking

## Step 5 – Configure VMs with Ansible

Add VMs to inventory (static or dynamic).

**Static inventory (recommended initially):**

```bash
nano ansible/inventory.yml
```

Add VMs under the `vms` group.

**Apply VM base configuration:**

```bash
ansible-playbook -i ansible/inventory.yml ansible/playbooks/vm-base.yml --limit vms
```

**At this point, VMs are ready but do nothing. That is intentional.**

## Step 6 – Enable services (explicit opt-in)

Nothing runs unless you enable it on purpose.

**Example: enable Docker in lab only.**

In `ansible/group_vars/lab.yml`:

```yaml
docker_enabled: true
```

**Apply:**

```bash
ansible-playbook -i ansible/inventory.yml ansible/playbooks/vm-base.yml --limit vms --extra-vars "env=lab"
```

**Production defaults remain conservative.**

## Daily operations (read later)

All operational procedures live under:

**`docs/operations/`**

Start with:

- `how-to-add-vm.md`
- `how-to-enable-docker.md`
- `ssh-key-rotation.md`
- `host-recovery.md`

**If it is not written there, it is not supported.**

## CI / Quality Gate

Every push runs:

- `ansible-lint`
- `terraform fmt -check`
- `terraform validate`

**CI never deploys anything.**

**Broken code should never reach production.**

## Automation and AI agents

If anything other than a human ever runs against this infrastructure — CI, a script on a
timer, or an AI agent — read:

**`docs/agent-environment.md`**

It defines what an automated identity is allowed to do and, more importantly, how that is
enforced: a plan-only Proxmox token, an unprivileged SSH user, branch protection.

**Boundaries belong in permissions, not in prompts.**

**An instruction is not a control. A missing credential is.**

## Final rule

If you catch yourself thinking:

> "I'll just do this one thing manually"

**Stop.**

Either:

- document it
- automate it
- or accept that it will break later

**This repository is designed to age well. Treat it accordingly.**

