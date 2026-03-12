#!/bin/bash
# ShandorCode Deployment Script for Hostinger VPS
# IP: 72.61.76.32
# Ubuntu 22.04 LTS

set -e

echo "🏗️  ShandorCode - Hostinger VPS Deployment"
echo "==========================================="
echo ""
echo "VPS IP: 72.61.76.32"
echo "Domain: shandor.gozerai.com"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Step 1: System Update${NC}"
apt-get update
apt-get upgrade -y

echo ""
echo -e "${BLUE}📦 Step 2: Installing Dependencies${NC}"
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw \
    htop \
    vim

echo ""
echo -e "${BLUE}🐳 Step 3: Installing Docker${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker installed${NC}"
else
    echo -e "${GREEN}✅ Docker already installed${NC}"
fi

echo ""
echo -e "${BLUE}🐙 Step 4: Installing Docker Compose${NC}"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✅ Docker Compose already installed${NC}"
fi

# Verify Docker installation
docker --version
docker-compose --version

echo ""
echo -e "${BLUE}🔥 Step 5: Configuring Firewall${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 443/udp comment 'HTTP/3'
echo -e "${GREEN}✅ Firewall configured${NC}"

echo ""
echo -e "${BLUE}📁 Step 6: Creating Directories${NC}"
mkdir -p /opt/shandorcode
mkdir -p /var/shandorcode/repos
mkdir -p /var/log/shandorcode
chmod 755 /opt/shandorcode
chmod 755 /var/shandorcode/repos
echo -e "${GREEN}✅ Directories created${NC}"

echo ""
echo -e "${BLUE}📝 Step 7: Creating Environment File${NC}"
cat > /opt/shandorcode/.env << 'EOF'
# ShandorCode Production Environment
DOMAIN=shandor.gozerai.com
ANALYSIS_PATH=/var/shandorcode/repos
LETSENCRYPT_EMAIL=chris@gozerai.com
DEPLOY_ENV=production
DEPLOY_VERSION=0.1.0
EOF
echo -e "${GREEN}✅ Environment file created${NC}"

echo ""
echo -e "${BLUE}🔧 Step 8: System Optimizations${NC}"
# Increase file descriptors
echo "fs.file-max = 65536" >> /etc/sysctl.conf
sysctl -p

# Docker log rotation
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker
echo -e "${GREEN}✅ Optimizations applied${NC}"

echo ""
echo -e "${GREEN}✅ VPS Setup Complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "   1. Upload ShandorCode files to /opt/shandorcode/"
echo "   2. Configure DNS: shandor.gozerai.com → 72.61.76.32"
echo "   3. Deploy: cd /opt/shandorcode/deployment && docker-compose up -d"
echo ""
echo -e "${BLUE}🔍 Useful Commands:${NC}"
echo "   Check Docker: docker ps"
echo "   Check logs: docker-compose logs -f"
echo "   Check firewall: ufw status"
echo "   System resources: htop"
echo ""
echo -e "${GREEN}🎉 Your VPS is ready for deployment!${NC}"
