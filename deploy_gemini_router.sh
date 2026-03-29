#!/bin/bash
# Deploy Gemini Router integration to cloud VM
# Run this once the VM is accessible again

set -e

VM_IP="144.24.159.95"
VM_USER="ubuntu"
SSH_KEY="$HOME/.ssh/cloud_vm_key"
SSH_OPTS="-o ConnectTimeout=30 -o StrictHostKeyChecking=no -o ServerAliveInterval=10"
REMOTE_DIR="/home/ubuntu/Personal-AI-Employee-Hackathon-0"

# Load API key from .env file or environment
if [ -z "$GOOGLE_API_KEY" ] && [ -f "$(dirname "$0")/.env" ]; then
    GOOGLE_API_KEY=$(grep '^GOOGLE_API_KEY=' "$(dirname "$0")/.env" | cut -d'=' -f2)
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: GOOGLE_API_KEY not set. Set it in .env or export it."
    exit 1
fi

echo "=== Step 1: Upload updated claude_processor.py ==="
scp -i "$SSH_KEY" $SSH_OPTS "$(dirname "$0")/claude_processor.py" \
    "$VM_USER@$VM_IP:$REMOTE_DIR/claude_processor.py"
echo "OK"

echo ""
echo "=== Step 2: Create CCR Router systemd service ==="
ssh -i "$SSH_KEY" $SSH_OPTS "$VM_USER@$VM_IP" 'sudo tee /etc/systemd/system/ccr-router.service > /dev/null << '\''SVCEOF'\''
[Unit]
Description=Claude Code Router (Gemini Proxy)
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="HOME=/home/ubuntu"
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="GOOGLE_API_KEY=$GOOGLE_API_KEY"
ExecStart=/usr/bin/ccr start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF'
echo "OK"

echo ""
echo "=== Step 3: Update AI Employee service with Gemini env vars ==="
ssh -i "$SSH_KEY" $SSH_OPTS "$VM_USER@$VM_IP" 'sudo tee /etc/systemd/system/ai-employee.service > /dev/null << '\''SVCEOF'\''
[Unit]
Description=AI Employee Orchestrator (Cloud Agent)
After=network.target ccr-router.service
Requires=ccr-router.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Personal-AI-Employee-Hackathon-0
Environment="PATH=/home/ubuntu/Personal-AI-Employee-Hackathon-0/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="ANTHROPIC_BASE_URL=http://127.0.0.1:3456"
Environment="CLAUDE_CONFIG_DIR=/home/ubuntu/.claude-gemini"
Environment="GOOGLE_API_KEY=$GOOGLE_API_KEY"
ExecStart=/home/ubuntu/Personal-AI-Employee-Hackathon-0/venv/bin/python3 orchestrator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF'
echo "OK"

echo ""
echo "=== Step 4: Reload and start services ==="
ssh -i "$SSH_KEY" $SSH_OPTS "$VM_USER@$VM_IP" '
    sudo systemctl daemon-reload
    sudo systemctl enable ccr-router ai-employee
    sudo systemctl start ccr-router
    sleep 3
    echo "CCR status:"
    sudo systemctl is-active ccr-router
    sudo systemctl restart ai-employee
    sleep 2
    echo "AI Employee status:"
    sudo systemctl is-active ai-employee
'
echo "OK"

echo ""
echo "=== Step 5: Verify Claude can use Gemini ==="
ssh -i "$SSH_KEY" $SSH_OPTS "$VM_USER@$VM_IP" '
    sleep 5
    echo "Testing Claude via Gemini router..."
    CLAUDE_CONFIG_DIR=~/.claude-gemini ANTHROPIC_BASE_URL=http://127.0.0.1:3456 claude --print "Say hello" 2>&1 | head -5
    echo ""
    echo "Recent service logs:"
    sudo journalctl -u ai-employee --no-pager -n 10
'

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo "CCR Router + Gemini integration deployed successfully!"
