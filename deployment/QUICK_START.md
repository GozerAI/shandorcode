# 🚀 ShandorCode VPS Deployment - Quick Reference

## ⚡ Super Quick Start (15 minutes)

### 1️⃣ DNS Setup (5 min)
```
Login to your domain registrar → Add A record:
shandor.gozerai.com → YOUR_VPS_IP
```

### 2️⃣ VPS Setup (5 min)
```bash
# SSH to VPS
ssh root@YOUR_VPS_IP

# One-liner setup
curl -fsSL https://get.docker.com | sh && \
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
chmod +x /usr/local/bin/docker-compose && \
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw --force enable && \
mkdir -p /opt/shandorcode /var/shandorcode/repos
```

### 3️⃣ Upload Code (3 min)
```bash
# From your Windows machine
cd C:\dev\shandorcode
scp -r deployment src pyproject.toml LICENSE.txt README.md root@YOUR_VPS_IP:/opt/shandorcode/

# OR clone from GitHub (once pushed)
ssh root@YOUR_VPS_IP
cd /opt/shandorcode
git clone https://github.com/yourusername/shandorcode.git .
```

### 4️⃣ Deploy (2 min)
```bash
# On VPS
cd /opt/shandorcode/deployment
cp .env.example .env
nano .env  # Set your email

# Start everything
docker-compose up -d

# Check status
docker-compose ps
```

### 5️⃣ Visit Your Site
```
https://shandor.gozerai.com
```

---

## 📋 Essential Commands

```bash
# View logs
docker-compose logs -f shandorcode

# Restart
docker-compose restart

# Update
git pull && docker-compose down && docker-compose up -d --build

# Stop
docker-compose down

# Status
docker-compose ps
```

---

## 🔧 Common Tasks

### Analyze a Project
```bash
# Clone to VPS
cd /var/shandorcode/repos
git clone https://github.com/user/project.git

# Visit web UI, enter: /repos/project
```

### Check Logs
```bash
cd /opt/shandorcode/deployment
docker-compose logs -f
```

### Update Deployment
```bash
cd /opt/shandorcode
git pull
docker-compose down
docker-compose up -d --build
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Site not loading | Check `docker-compose ps` and `ufw status` |
| SSL errors | Check `docker-compose logs caddy` |
| App crashes | Check `docker-compose logs shandorcode` |
| Can't connect | Verify DNS with `dig shandor.gozerai.com` |

---

## 📁 File Locations

```
/opt/shandorcode/          # Application code
/var/shandorcode/repos/    # Projects to analyze
/var/log/shandorcode/      # Logs
```

---

## 🔒 Security Checklist

- [x] Firewall enabled (ports 22, 80, 443)
- [x] HTTPS with Let's Encrypt
- [x] Security headers configured
- [x] Rate limiting enabled
- [ ] Add authentication (when Zuultimate ready)
- [ ] Set up backups
- [ ] Configure monitoring

---

## 📞 Get Help

- Logs: `docker-compose logs -f`
- Status: `docker-compose ps`
- Rebuild: `docker-compose up -d --build`

**Everything you need is in `/opt/shandorcode/deployment/`**
