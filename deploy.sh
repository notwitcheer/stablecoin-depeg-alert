#!/bin/bash
# Production deployment script

set -e

echo "🚀 Deploying DepegAlert Bot..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3 python3-pip python3-venv git -y

# Clone repository
git clone https://github.com/your-username/depeg-alert.git
cd depeg-alert

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
echo "⚠️  Edit .env file with your bot token and channel ID"
echo "⚠️  Run: nano .env"
read -p "Press enter when .env is configured..."

# Test configuration
python3 config.py

# Create systemd service
sudo tee /etc/systemd/system/depegalert.service > /dev/null <<EOF
[Unit]
Description=DepegAlert Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable depegalert
sudo systemctl start depegalert

echo "✅ Bot deployed successfully!"
echo "📋 Management commands:"
echo "  Status: sudo systemctl status depegalert"
echo "  Logs:   sudo journalctl -u depegalert -f"
echo "  Stop:   sudo systemctl stop depegalert"
echo "  Start:  sudo systemctl start depegalert"