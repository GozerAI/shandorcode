# 🚀 Simple Manual Deployment Guide

No scripts, no automation - just simple copy/paste commands.

---

## Phase 1: DNS Setup (Do First!)

### Namecheap DNS:
1. Go to: https://ap.www.namecheap.com/domains/list/
2. Find **gozerai.com** → Click **Manage**
3. Click **Advanced DNS** tab
4. Click **ADD NEW RECORD**
5. Fill in:
   - Type: `A Record`
   - Host: `shandor`
   - Value: `72.61.76.32`
   - TTL: `Automatic`
6. Click **Save** (green checkmark)

**Wait 10 minutes for DNS to propagate**

---

## Phase 2: Start VPS

1. Login to Hostinger: https://hpanel.hostinger.com/
2. Find your VPS (KVM4)
3. Click **Start** or **Power On**
4. Wait for status: **Running**

---

## Phase 3: Test SSH Connection

Open PowerShell:
```powershell
ssh root@72.61.76.32
```

Password: `Lh9vW(+fb)5x.c,V`

You should get a command prompt on the VPS.

---

## Phase 4: Setup VPS (One-time)

**Still connected via SSH**, run these commands one at a time:

### Update system:
```bash
apt-get update
apt-get upgrade -y
```

### Install Docker:
```bash
curl -fsSL https://get.docker.com | sh
```

### Install Docker Compose:
```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### Configure Firewall:
```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### Create Directories:
```bash
mkdir -p /opt/shandorcode
mkdir -p /var/shandorcode/repos
```

### Verify Docker:
```bash
docker --version
docker-compose --version
```

Should show version numbers.

**Type `exit` to disconnect from VPS**

---

## Phase 5: Upload ShandorCode Files

### From Windows PowerShell:

```powershell
cd C:\dev\shandorcode

# Upload files (this will take a minute)
scp -r src deployment pyproject.toml LICENSE.txt README.md root@72.61.76.32:/opt/shandorcode/
```

Enter password when prompted: `Lh9vW(+fb)5x.c,V`

---

## Phase 6: Configure Environment

**SSH back to VPS:**
```powershell
ssh root@72.61.76.32
```

**On VPS:**
```bash
cd /opt/shandorcode/deployment
cp .env.example .env
```

Environment file is pre-configured, no edits needed!

---

## Phase 7: Deploy!

**Still on VPS:**
```bash
cd /opt/shandorcode/deployment
docker-compose up -d
```

This will:
- Download Docker images (2-3 minutes)
- Build ShandorCode container
- Start Caddy (HTTPS proxy)
- Get SSL certificate from Let's Encrypt

**Watch the startup:**
```bash
docker-compose logs -f
```

Look for:
- `Uvicorn running on http://127.0.0.1:8765`
- `Application startup complete`

**Press Ctrl+C** to stop watching logs

---

## Phase 8: Verify Deployment

### Check containers are running:
```bash
docker-compose ps
```

Should show:
```
NAME              STATUS
shandor_caddy     Up
shandor_app       Up
```

### Test local access:
```bash
curl -I http://localhost:8765
```

Should return: `HTTP/1.1 200 OK`

### Wait 2-3 minutes, then test HTTPS:
```bash
curl -I https://shandor.gozerai.com
```

Should return: `HTTP/2 200`

If you get certificate errors, wait another minute - Let's Encrypt is still working.

---

## Phase 9: Visit Your Site!

Open browser and go to:
```
https://shandor.gozerai.com
```

You should see the ShandorCode interface!

---

## Phase 10: Test Analysis

### Create a test project on VPS:

**Still SSH'd to VPS:**
```bash
mkdir -p /var/shandorcode/repos/test
cd /var/shandorcode/repos/test

cat > hello.py << 'EOF'
def greet(name):
    return f"Hello, {name}!"

class Greeter:
    def __init__(self):
        self.greeting = "Hello"
    
    def greet(self, name):
        return f"{self.greeting}, {name}!"
EOF
```

### In your browser:
1. Go to: `https://shandor.gozerai.com`
2. In the path field, enter: `/repos/test`
3. Click **Analyze**

Should see:
- 1 file analyzed
- 2 entities (function + class)
- Graph visualization

**Success!** 🎉

---

## 🎯 Quick Reference

### SSH to VPS:
```powershell
ssh root@72.61.76.32
```

### View logs:
```bash
cd /opt/shandorcode/deployment
docker-compose logs -f
```

### Check status:
```bash
docker-compose ps
```

### Restart:
```bash
docker-compose restart
```

### Stop:
```bash
docker-compose down
```

### Start:
```bash
docker-compose up -d
```

---

## 🐛 Troubleshooting

### DNS not working:
```bash
# Test DNS
nslookup shandor.gozerai.com

# Should return: 72.61.76.32
# If not, wait longer or check Namecheap
```

### Containers won't start:
```bash
# Check logs
docker-compose logs

# Check disk space
df -h

# Rebuild
docker-compose down
docker-compose up -d --build
```

### HTTPS not working:
```bash
# Check Caddy logs
docker-compose logs caddy

# Restart Caddy
docker-compose restart caddy

# Make sure port 80 is open (needed for Let's Encrypt)
ufw status
```

---

## ✅ Success Checklist

- [x] DNS configured in Namecheap
- [x] VPS running
- [x] Docker installed
- [x] Firewall configured
- [x] Files uploaded
- [x] Containers running
- [x] HTTPS working
- [x] Site loads in browser
- [x] Can analyze code

---

**Total Time**: 30-40 minutes

**You're live at**: https://shandor.gozerai.com 🚀
