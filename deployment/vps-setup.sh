#!/bin/bash
# ShandorCode VPS Initial Setup Script
# Run this on your fresh VPS to set up everything

set -e  # Exit on error

echo "🏗️  ShandorCode VPS Setup Script"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Configuration
DOMAIN="${DOMAIN:-shandor.gozerai.com}"
REPOS_DIR="/var/shandorcode/repos"
INSTALL_DIR="/opt/shandorcode"

echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   Install directory: $INSTALL_DIR"
echo "   Analysis repos: $REPOS_DIR"
echo ""

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "📦 Installing Docker and dependencies..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw

# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker already installed"
fi

# Configure firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 443/udp  # HTTP/3

# Create directories
echo "📁 Creating directories..."
mkdir -p $INSTALL_DIR
mkdir -p $REPOS_DIR
mkdir -p /var/log/shandorcode

# Set permissions
chmod 755 $REPOS_DIR
chmod 755 $INSTALL_DIR

# Create .env file
echo "📝 Creating environment file..."
cat > $INSTALL_DIR/.env << EOF
DOMAIN=$DOMAIN
ANALYSIS_PATH=$REPOS_DIR
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-admin@$DOMAIN}
DEPLOY_ENV=production
DEPLOY_VERSION=0.1.0
EOF

echo ""
echo "✅ VPS setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Copy your ShandorCode files to: $INSTALL_DIR"
echo "   2. Update DNS: shandor.gozerai.com → $(curl -s ifconfig.me)"
echo "   3. Run: cd $INSTALL_DIR/deployment && docker-compose up -d"
echo ""
echo "🔍 Useful commands:"
echo "   Check status: docker-compose ps"
echo "   View logs: docker-compose logs -f"
echo "   Restart: docker-compose restart"
echo "   Stop: docker-compose down"
echo ""
