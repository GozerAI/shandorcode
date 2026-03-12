# ShandorCode VPS Deployment Guide

## 🎯 Overview

This guide will help you deploy ShandorCode to your VPS at **shandor.gozerai.com**.

## 📋 Prerequisites

- VPS with Ubuntu 22.04+ (any provider)
- Domain: shandor.gozerai.com (already configured)
- SSH access to VPS
- Root or sudo privileges

## 🚀 Quick Start

### Step 1: Configure DNS

Point your domain to your VPS:

```
A Record: shandor.gozerai.com → YOUR_VPS_IP
```

### Step 2: Initial VPS Setup

SSH into your VPS:
```bash
ssh root@YOUR_VPS_IP
```

Run the setup script:
```bash
# Download setup script
curl -o /tmp/vps-setup.sh https://raw.githubusercontent.com/yourusername/shandorcode/main/deployment/vps-setup.sh

# Make executable
chmod +x /tmp/vps-setup.sh

# Run setup
sudo /tmp/vps-setup.sh
```

**Or manually:**
```bash
# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Create directories
mkdir -p /opt/shandorcode
mkdir -p /var/shandorcode/repos
```

### Step 3: Upload ShandorCode

From your local machine:
```bash
# Create deployment archive
cd C:\dev\shandorcode
tar -czf shandorcode.tar.gz src/ deployment/ pyproject.toml LICENSE.txt README.md

# Upload to VPS
scp shandorcode.tar.gz root@YOUR_VPS_IP:/opt/shandorcode/

# SSH and extract
ssh root@YOUR_VPS_IP
cd /opt/shandorcode
tar -xzf shandorcode.tar.gz
```

**Or use Git (recommended):**
```bash
# On VPS
cd /opt/shandorcode
git clone https://github.com/yourusername/shandorcode.git .
```

### Step 4: Configure Environment

```bash
# On VPS
cd /opt/shandorcode/deployment
cp .env.example .env

# Edit .env with your settings
nano .env
```

Update these values:
```env
DOMAIN=shandor.gozerai.com
ANALYSIS_PATH=/var/shandorcode/repos
LETSENCRYPT_EMAIL=your-email@example.com
```

### Step 5: Deploy

```bash
cd /opt/shandorcode/deployment
docker-compose up -d
```

### Step 6: Verify

```bash
# Check status
docker-compose ps

# Check logs
docker-compose logs -f shandorcode

# Test the site
curl -I https://shandor.gozerai.com
```

Visit: **https://shandor.gozerai.com**

---

## 🔧 Management Commands

### View Logs
```bash
cd /opt/shandorcode/deployment
docker-compose logs -f shandorcode
```

### Restart Service
```bash
docker-compose restart shandorcode
```

### Update Deployment
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Stop Everything
```bash
docker-compose down
```

### Check Resource Usage
```bash
docker stats
```

---

## 📊 Analyzing Projects

### Option 1: Upload via Web UI
1. Visit https://shandor.gozerai.com
2. Enter path: `/repos/your-project`
3. Upload project to VPS at `/var/shandorcode/repos/your-project`

### Option 2: Clone Directly on VPS
```bash
# Clone a repo to analyze
cd /var/shandorcode/repos
git clone https://github.com/username/project.git

# Then analyze via web UI
# Path: /repos/project
```

### Option 3: SCP Upload
```bash
# From your local machine
scp -r C:\dev\my-project root@YOUR_VPS_IP:/var/shandorcode/repos/
```

---

## 🔒 Security Considerations

### Current Setup (Phase 1)
- ✅ HTTPS via Let's Encrypt (automatic)
- ✅ Firewall configured (UFW)
- ✅ Rate limiting (Caddy)
- ✅ Security headers
- ⚠️ No authentication yet

### Phase 2 (Add Later with Zuultimate)
- OAuth/OIDC authentication
- API key management
- User sessions
- Role-based access control

### Temporary Security

Until Zuultimate is ready, you can add basic auth:

Edit `Caddyfile`:
```
shandor.gozerai.com {
    basicauth {
        admin $2a$14$your_bcrypt_hash
    }
    
    reverse_proxy shandorcode:8765
}
```

Generate password hash:
```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'your-password'
```

---

## 🌐 DNS Configuration

### Cloudflare Setup (Recommended)

1. **Add domain to Cloudflare**
2. **Create A records:**
   ```
   Type: A
   Name: shandor
   Value: YOUR_VPS_IP
   Proxy: Enabled (orange cloud)
   ```

3. **SSL/TLS Settings:**
   - Mode: Full (strict)
   - Always Use HTTPS: On
   - Minimum TLS Version: 1.2

4. **Security:**
   - Enable "Under Attack Mode" if needed
   - Configure WAF rules
   - Enable DDoS protection

### Direct DNS (No Cloudflare)

Just create A record at your registrar:
```
shandor.gozerai.com → YOUR_VPS_IP
```

---

## 📈 Monitoring

### Health Checks
```bash
# Application health
curl https://shandor.gozerai.com/api/current

# Container health
docker ps
```

### Set Up Monitoring (Optional)

Install Prometheus + Grafana:
```bash
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

---

## 🐛 Troubleshooting

### Site Not Loading

1. **Check DNS:**
   ```bash
   dig shandor.gozerai.com
   nslookup shandor.gozerai.com
   ```

2. **Check containers:**
   ```bash
   docker-compose ps
   docker-compose logs caddy
   docker-compose logs shandorcode
   ```

3. **Check firewall:**
   ```bash
   ufw status
   ```

### SSL Certificate Issues

```bash
# Check Caddy logs
docker-compose logs caddy

# Restart Caddy
docker-compose restart caddy
```

### Application Crashes

```bash
# Check logs
docker-compose logs shandorcode

# Restart app
docker-compose restart shandorcode

# Full restart
docker-compose down && docker-compose up -d
```

---

## 📝 Next Steps

After ShandorCode is running:

1. **Add Vinzy-Engine:**
   - Deploy to: vinzy.gozerai.com
   - Add to docker-compose.yml
   - Update Caddyfile

2. **Add Zuultimate:**
   - Deploy to: zuul.gozerai.com
   - Configure OAuth for ShandorCode
   - Add authentication layer

3. **Add monitoring:**
   - Uptime monitoring (UptimeRobot, etc.)
   - Log aggregation
   - Performance metrics

4. **Backup strategy:**
   - Database backups
   - Configuration backups
   - Automated backups to S3/Backblaze

---

## 💡 Tips

- Keep `.env` file secure and backed up
- Use `docker-compose logs -f` to watch real-time logs
- Set up automated backups of `/var/shandorcode`
- Use Git tags for versioning deployments
- Consider adding CI/CD with GitHub Actions

---

## 📞 Support

- GitHub Issues: https://github.com/yourusername/shandorcode/issues
- Documentation: https://shandor.gozerai.com/docs (once deployed)
- Email: chris@gozerai.com

---

**Status**: Ready for deployment 🚀
**Version**: 0.1.0
**Last Updated**: December 14, 2024
