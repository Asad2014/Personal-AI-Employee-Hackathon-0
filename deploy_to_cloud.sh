#!/bin/bash
# Cloud VM Deployment Script for AI Employee
# Run this on your CLOUD VM (68.233.110.60)

set -e  # Exit on error

echo "=========================================="
echo "AI Employee - Cloud Deployment Script"
echo "VM IP: 144.24.136.132"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Updating system...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${YELLOW}Step 2: Installing dependencies...${NC}"
sudo apt install -y python3 python3-pip python3-venv git docker.io docker-compose
sudo usermod -aG docker $USER

echo -e "${YELLOW}Step 3: Installing Playwright dependencies...${NC}"
sudo apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2

echo -e "${YELLOW}Step 4: Cloning project...${NC}"
cd ~
if [ -d "Personal-AI-Employee-Hackathon-0" ]; then
    echo "Project already exists, pulling latest..."
    cd Personal-AI-Employee-Hackathon-0
    git pull origin main
else
    git clone https://github.com/Asad2014/Personal-AI-Employee-Hackathon-0.git
    cd Personal-AI-Employee-Hackathon-0
fi

echo -e "${YELLOW}Step 5: Setting up Python environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

echo -e "${YELLOW}Step 6: Configuring cloud mode...${NC}"
# Add AGENT_MODE=cloud to .env if not present
if grep -q "AGENT_MODE" .env 2>/dev/null; then
    echo "AGENT_MODE already configured"
else
    echo -e "\n# --- Cloud Agent Mode ---\nAGENT_MODE=cloud" >> .env
    echo -e "${GREEN}Added AGENT_MODE=cloud to .env${NC}"
fi

echo -e "${YELLOW}Step 7: Setting up systemd service...${NC}"
sudo tee /etc/systemd/system/ai-employee.service > /dev/null <<EOF
[Unit]
Description=AI Employee Orchestrator (Cloud Agent)
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc/Personal-AI-Employee-Hackathon-0
Environment="PATH=/home/opc/Personal-AI-Employee-Hackathon-0/venv/bin:/usr/bin"
ExecStart=/home/opc/Personal-AI-Employee-Hackathon-0/venv/bin/python3 orchestrator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-employee.service

echo -e "${YELLOW}Step 8: Setting up git auto-sync (every 5 minutes)...${NC}"
(crontab -l 2>/dev/null | grep -v "Personal-AI-Employee-Hackathon-0"; echo "*/5 * * * * cd $HOME/Personal-AI-Employee-Hackathon-0 && git pull origin main >> $HOME/git-sync.log 2>&1") | crontab -

echo -e "${GREEN}=========================================="
echo "Deployment Complete! ✅"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Upload credentials from local:"
echo "   scp credentials.json ubuntu@68.233.110.60:~/Personal-AI-Employee-Hackathon-0/"
echo "   scp token.json ubuntu@68.233.110.60:~/Personal-AI-Employee-Hackathon-0/"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start ai-employee.service"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status ai-employee.service"
echo ""
echo "4. View logs:"
echo "   tail -f ~/Personal-AI-Employee-Hackathon-0/ai_employee.log"
