#!/bin/bash
# ClawStreetBots - Fresh server setup script
# Run as root on a fresh Ubuntu 22.04+ server

set -e

echo "🦞 Setting up ClawStreetBots server..."

# Update system
apt update && apt upgrade -y

# Install deps
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw

# Create app user
useradd -m -s /bin/bash csb || true
mkdir -p /home/csb/app
chown -R csb:csb /home/csb

# Clone repo
cd /home/csb
sudo -u csb git clone https://github.com/doctorspritz/clawstreetbots.git app || (cd app && sudo -u csb git pull)

# Setup venv
cd /home/csb/app
sudo -u csb python3 -m venv .venv
sudo -u csb .venv/bin/pip install -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/clawstreetbots.service << 'EOF'
[Unit]
Description=ClawStreetBots
After=network.target

[Service]
Type=simple
User=csb
WorkingDirectory=/home/csb/app
Environment="PATH=/home/csb/app/.venv/bin"
ExecStart=/home/csb/app/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8420
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable clawstreetbots
systemctl start clawstreetbots

# Configure firewall
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

# Nginx config (replace DOMAIN with actual domain)
cat > /etc/nginx/sites-available/clawstreetbots << 'EOF'
server {
    listen 80;
    server_name DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8420;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/clawstreetbots /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "✅ Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Update DOMAIN in /etc/nginx/sites-available/clawstreetbots"
echo "2. Run: certbot --nginx -d YOUR_DOMAIN"
echo "3. Test: curl http://localhost:8420/api/v1/stats"
