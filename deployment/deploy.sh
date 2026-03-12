#!/bin/bash
# Quick deployment script
# Run this to deploy/update ShandorCode on your VPS

set -e

INSTALL_DIR="/opt/shandorcode"

echo "🚀 Deploying ShandorCode..."

# Navigate to install directory
cd $INSTALL_DIR/deployment

# Pull latest images
echo "📦 Pulling latest images..."
docker-compose pull

# Build ShandorCode image
echo "🏗️  Building ShandorCode..."
docker-compose build --no-cache

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start services
echo "▶️  Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your site should be available at:"
echo "   https://shandor.gozerai.com"
echo ""
echo "📋 Quick commands:"
echo "   Logs: docker-compose logs -f shandorcode"
echo "   Restart: docker-compose restart shandorcode"
echo "   Status: docker-compose ps"
echo ""
