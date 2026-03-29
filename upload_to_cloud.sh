#!/bin/bash
# Upload necessary files from local to cloud VM
# Run this on your LOCAL machine

VM_IP="144.24.159.95"
VM_USER="ubuntu"
VM_PATH="/home/opc/Personal-AI-Employee-Hackathon-0"
SSH_KEY="$HOME/.ssh/cloud_vm_key"

echo "=========================================="
echo "Uploading files to Cloud VM"
echo "VM: $VM_USER@$VM_IP"
echo "=========================================="

# Check if files exist
if [ ! -f "credentials.json" ]; then
    echo "❌ credentials.json not found!"
    exit 1
fi

if [ ! -f "token.json" ]; then
    echo "❌ token.json not found!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ .env not found!"
    exit 1
fi

echo "📤 Uploading credentials.json..."
scp -i "$SSH_KEY" credentials.json $VM_USER@$VM_IP:$VM_PATH/

echo "📤 Uploading token.json..."
scp -i "$SSH_KEY" token.json $VM_USER@$VM_IP:$VM_PATH/

echo "📤 Uploading .env..."
scp -i "$SSH_KEY" .env $VM_USER@$VM_IP:$VM_PATH/

echo "📤 Uploading deployment script..."
scp -i "$SSH_KEY" deploy_to_cloud.sh $VM_USER@$VM_IP:~/

echo ""
echo "✅ All files uploaded successfully!"
echo ""
echo "Next: SSH to VM and run deployment script"
echo "  ssh $VM_USER@$VM_IP"
echo "  cd $VM_PATH"
echo "  chmod +x deploy_to_cloud.sh"
echo "  ./deploy_to_cloud.sh"
