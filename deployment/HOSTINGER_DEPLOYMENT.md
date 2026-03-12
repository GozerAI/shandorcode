# ShandorCode Deployment to Hostinger VPS
# Step-by-Step Guide

## ✅ What You Have

- **VPS**: Hostinger KVM4, Ubuntu 22.04 LTS
- **IP**: 72.61.76.32
- **Domain**: gozerai.com
- **SSH**: root@72.61.76.32
- **Status**: Currently stopped

---

## 🚀 Deployment Steps

### Step 1: Start Your VPS (1 minute)

1. Login to Hostinger control panel
2. Navigate to your VPS
3. Click **Start** or **Power On**
4. Wait for boot (30-60 seconds)

---

### Step 2: Configure DNS (5 minutes)

1. Login to your domain registrar (where gozerai.com is registered)
2. Go to DNS settings
3. Add A record:
   ```
   Type: A
   Name: shandor
   Value: 72.61.76.32
   TTL: 3600
   ```
4. Save changes

**Test DNS** (wait 5-10 minutes, then):
```bash
ping shandor.gozerai.com
# Should return: 72.61.76.32
```

---

### Step 3: Connect to VPS (1 minute)

From your Windows machine:

```bash
ssh root@72.61.76.32
# Password: Lh9vW(+fb)5x.c,V
```

**First time?** Type `yes` when asked about fingerprint.

---

### Step 4: Run Setup Script (5 minutes)

Copy the setup script to VPS:

**Option A: Manual paste**
```bash
# On VPS
nano /tmp/setup.sh
# Paste the hostinger-setup.sh content
# Press Ctrl+X, then Y, then Enter

chmod +x /tmp/setup.sh
/tmp/setup.sh
```

**Option B: Upload from Windows**
```powershell
# From Windows (PowerShell)
scp C:\dev\shandorcode\deployment\hostinger-setup.sh root@72.61.76.32:/tmp/setup.sh

# Then on VPS
ssh root@72.61.76.32
chmod +x /tmp/setup.sh
/tmp/setup.sh
```

**What this does:**
- Updates Ubuntu
- Installs Docker & Docker Compose
- Configures firewall
- Creates directories
- Optimizes system

---

### Step 5: Upload ShandorCode (3 minutes)

**From your Windows machine:**

```powershell
# Navigate to ShandorCode directory
cd C:\dev\shandorcode

# Create deployment archive
tar -czf shandorcode.tar.gz src/ deployment/ pyproject.toml LICENSE.txt README.md

# Upload to VPS
scp shandorcode.tar.gz root@72.61.76.32:/opt/shandorcode/

# Connect to VPS and extract
ssh root@72.61.76.32
cd /opt/shandorcode
tar -xzf shandorcode.tar.gz
rm shandorcode.tar.gz
```

---

### Step 6: Configure Environment (2 minutes)

On VPS:
```bash
cd /opt/shandorcode/deployment
cp .env.example .env
nano .env
```

Verify these settings:
```env
DOMAIN=shandor.gozerai.com
ANALYSIS_PATH=/var/shandorcode/repos
LETSENCRYPT_EMAIL=chris@gozerai.com
DEPLOY_ENV=production
DEPLOY_VERSION=0.1.0
```

Save: `Ctrl+X`, then `Y`, then `Enter`

---

### Step 7: Deploy! (2 minutes)

```bash
cd /opt/shandorcode/deployment
docker-compose up -d
```

**Watch it work:**
```bash
docker-compose logs -f
```

Press `Ctrl+C` to stop watching logs.

---

### Step 8: Verify Deployment (1 minute)

**Check containers:**
```bash
docker-compose ps
```

Should show:
```
NAME                STATUS              PORTS
shandor_caddy      Up 30 seconds       0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
shandor_app        Up 30 seconds       8765/tcp
```

**Test the site:**
```bash
curl -I https://shandor.gozerai.com
```

Should return: `HTTP/2 200`

---

### Step 9: Visit Your Site! 🎉

Open browser:
```
https://shandor.gozerai.com
```

You should see the ShandorCode UI!

---

## 🔧 Management Commands

### View Logs
```bash
cd /opt/shandorcode/deployment
docker-compose logs -f shandorcode
```

### Check Status
```bash
docker-compose ps
```

### Restart Service
```bash
docker-compose restart shandorcode
```

### Stop Everything
```bash
docker-compose down
```

### Update Deployment
```bash
# Upload new files
# Then:
docker-compose down
docker-compose up -d --build
```

---

## 🐛 Troubleshooting

### Issue: Can't SSH to VPS
**Solution:** Make sure VPS is started in Hostinger panel

### Issue: DNS not resolving
**Solution:** 
```bash
# Check DNS propagation
dig shandor.gozerai.com
nslookup shandor.gozerai.com
```
Wait up to 1 hour for global propagation.

### Issue: Docker containers won't start
**Solution:**
```bash
# Check logs
docker-compose logs

# Check disk space
df -h

# Check memory
free -h
```

### Issue: Site shows "Connection refused"
**Solution:**
```bash
# Check firewall
ufw status

# Check containers
docker-compose ps

# Check Caddy logs
docker-compose logs caddy
```

### Issue: SSL certificate errors
**Solution:**
```bash
# Check Caddy logs
docker-compose logs caddy

# Restart Caddy
docker-compose restart caddy
```

---

## 📊 Your VPS Specs (Hostinger KVM4)

Based on typical Hostinger KVM4:
- **CPU**: 2-4 cores
- **RAM**: 4-8 GB
- **Storage**: 50-100 GB SSD
- **Bandwidth**: Unmetered

**Perfect for:**
- Running ShandorCode
- Adding Vinzy-Engine later
- Adding Zuultimate later
- Small to medium project analysis

---

## 🔒 Security Notes

**What's Configured:**
- ✅ Firewall (UFW) - only ports 22, 80, 443 open
- ✅ HTTPS automatic (Let's Encrypt)
- ✅ Security headers in Caddy
- ✅ Rate limiting

**What's NOT Configured Yet:**
- ⚠️ Authentication (add when Zuultimate ready)
- ⚠️ Fail2ban (optional, for SSH brute force protection)
- ⚠️ Automated backups

**Optional: Add Fail2ban**
```bash
apt-get install fail2ban -y
systemctl enable fail2ban
systemctl start fail2ban
```

---

## 📋 Post-Deployment Checklist

- [ ] VPS started
- [ ] DNS configured (shandor.gozerai.com → 72.61.76.32)
- [ ] SSH access working
- [ ] Setup script completed
- [ ] ShandorCode files uploaded
- [ ] Docker containers running
- [ ] Site accessible via HTTPS
- [ ] SSL certificate valid
- [ ] Can analyze a test project

---

## 🎯 What's Next?

### Test It Out
1. Upload a small project to `/var/shandorcode/repos/`
2. Visit https://shandor.gozerai.com
3. Enter path: `/repos/your-project`
4. Click Analyze

### Add More Services (Later)
```bash
# Add to docker-compose.yml
vinzy:
  build: ../vinzy-engine
  
zuultimate:
  build: ../zuultimate
```

### Set Up Monitoring
- Add UptimeRobot for uptime monitoring
- Set up log aggregation
- Configure alerts

---

## ⏱️ Time Estimate

Total deployment time: **20-30 minutes**

- Step 1 (Start VPS): 1 min
- Step 2 (DNS): 5 min
- Step 3 (SSH): 1 min
- Step 4 (Setup): 5 min
- Step 5 (Upload): 3 min
- Step 6 (Config): 2 min
- Step 7 (Deploy): 2 min
- Step 8 (Verify): 1 min
- DNS propagation: 10-60 min (in background)

---

## 📞 Ready to Deploy?

**I can help with:**
1. Walking through each step
2. Troubleshooting any issues
3. Optimizing configuration
4. Adding more features

**Just let me know when you want to start!** 🚀

---

## 📝 Quick Command Reference

```bash
# SSH to VPS
ssh root@72.61.76.32

# Navigate to app
cd /opt/shandorcode/deployment

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart
docker-compose restart

# Stop
docker-compose down

# Start
docker-compose up -d
```

---

**Everything is ready to go!** ✨
