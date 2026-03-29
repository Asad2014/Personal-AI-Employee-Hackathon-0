#!/bin/bash
# Quick SSH to Cloud VM
# Usage: ./ssh_to_cloud.sh

SSH_KEY="$HOME/.ssh/cloud_vm_key"
VM_IP="144.24.159.95"
VM_USER="ubuntu"

echo "🔌 Connecting to Cloud VM..."
echo "VM: $VM_USER@$VM_IP"
echo "Key: $SSH_KEY"
echo ""

ssh -t -i "$SSH_KEY" $VM_USER@$VM_IP
