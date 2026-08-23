#!/usr/bin/env python3
"""
Dynamic Ansible inventory script that reads Terraform outputs.

VMs are grouped under the 'vms' group. A VM whose IP address the Proxmox guest
agent has not reported yet is left out of the inventory rather than added with
an unusable address, so `--limit vms` acts on reachable hosts only.

Usage:
    ansible-inventory -i ansible/inventory/terraform.py --list
    ansible-playbook -i ansible/inventory/terraform.py playbooks/vm-base.yml --limit vms

Requirements:
    - Terraform must be initialised and `terraform output -json` must work
    - Override the Terraform directory with TERRAFORM_DIR if it is not <repo>/terraform
"""

import json
import os
import subprocess
import sys

SSH_COMMON_ARGS = '-o StrictHostKeyChecking=accept-new'

# <repo>/ansible/inventory/terraform.py -> <repo>
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def warn(message):
    """Report a problem on stderr.

    Ansible reads stdout as inventory JSON, so a silent empty inventory used to be
    indistinguishable from "no VMs exist". These warnings make the difference
    visible without breaking the contract on stdout.
    """
    print('terraform.py: {}'.format(message), file=sys.stderr)


def get_terraform_outputs(terraform_dir=None):
    """Return `terraform output -json` as a dict, or None if unavailable."""
    if terraform_dir is None:
        terraform_dir = os.environ.get('TERRAFORM_DIR') or os.path.join(REPO_ROOT, 'terraform')

    if not os.path.isdir(terraform_dir):
        warn('Terraform directory not found: {}'.format(terraform_dir))
        return None

    try:
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        warn('could not run terraform: {}'.format(exc))
        return None

    if result.returncode != 0:
        warn('terraform output failed in {}: {}'.format(
            terraform_dir, result.stderr.strip() or 'no stderr'))
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        warn('could not parse terraform output as JSON: {}'.format(exc))
        return None


def empty_inventory():
    return {
        '_meta': {'hostvars': {}},
        'vms': {'hosts': [], 'vars': {'ansible_ssh_common_args': SSH_COMMON_ARGS}},
        'all': {'children': ['vms']},
    }


def generate_inventory(terraform_outputs):
    """Build an Ansible inventory from the `vms` Terraform output."""
    inventory = empty_inventory()

    if not terraform_outputs or 'vms' not in terraform_outputs:
        warn("no 'vms' output found; is terraform apply complete?")
        return inventory

    vms_output = terraform_outputs['vms'].get('value') or {}
    skipped = []

    for vm_name, vm_data in vms_output.items():
        ansible_host = (vm_data or {}).get('ansible_host')

        # ansible_host is null until the guest agent reports an address, and older
        # states may still hold the "<replace_with...>" placeholder. Neither is
        # connectable, so leave the host out instead of guaranteeing an SSH failure.
        if not ansible_host or (ansible_host.startswith('<') and ansible_host.endswith('>')):
            skipped.append(vm_name)
            continue

        inventory['vms']['hosts'].append(vm_name)
        inventory['_meta']['hostvars'][vm_name] = {
            'ansible_host': ansible_host,
            'ansible_user': (vm_data or {}).get('ssh_user', 'admin'),
            'ansible_port': 22,
            'ansible_ssh_common_args': SSH_COMMON_ARGS,
        }

    if skipped:
        warn('no IP address yet, skipping: {}'.format(', '.join(sorted(skipped))))
        warn('the Proxmox guest agent must be running in the VM for its address to appear')

    return inventory


def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--list':
        outputs = get_terraform_outputs()
        inventory = empty_inventory() if outputs is None else generate_inventory(outputs)
        print(json.dumps(inventory, indent=2))
        return

    # --host is required by the inventory script contract; all host variables are
    # returned in _meta by --list, so there is nothing further to report here.
    if len(sys.argv) == 3 and sys.argv[1] == '--host':
        print(json.dumps({}))
        return

    if len(sys.argv) == 2 and sys.argv[1].startswith('--host='):
        print(json.dumps({}))
        return

    print('Usage: terraform.py --list | --host <hostname>', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main()
