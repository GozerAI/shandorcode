# ⏱️ ShandorCode Deployment Timeline - Complete Walkthrough

## 🎯 Overview

**Total Time**: 30-40 minutes active work + 10-30 min DNS propagation (in background)

**Your Setup:**
- Domain: gozerai.com (Namecheap)
- VPS: Hostinger KVM4 (72.61.76.32)
- Target: shandor.gozerai.com

---

## 📅 Complete Timeline

### Phase 1: DNS Setup (10 minutes)
**What**: Configure Namecheap DNS
**When**: Do this FIRST, before anything else
**Why**: DNS takes time to propagate, so start it early

**Steps:**
1. Login to Namecheap (2 min)
2. Navigate to gozerai.com → Advanced DNS (1 min)
3. Add A Record: `shandor` → `72.61.76.32` (2 min)
4. Save changes (1 min)
5. Test DNS: `nslookup shandor.gozerai.com` (1 min)

**File**: `NAMECHEAP_DNS_SETUP.md`

**Status**: ⏳ DNS propagating (happens in background)

---

### Phase 2: Start VPS (5 minutes)
**What**: Boot your Hostinger VPS
**When**: Right after DNS setup (while DNS propagates)
**Why**: VPS needs to be running to SSH to it

**Steps:**
1. Login to Hostinger control panel (1 min)
2. Find your VPS (KVM4) (1 min)
3. Click "Start" or "Power On" (1 min)
4. Wait for status "Running" (2 min)

**Status**: ✅ VPS ready for connection

---

### Phase 3: Test Connectivity (2 minutes)
**What**: Verify you can SSH to VPS
**When**: After VPS shows "Running"

**Steps:**
```powershell
# Test ping
ping 72.61.76.32

# Test SSH
ssh root@72.61.76.32
# Password: Lh9vW(+fb)5x.c,V
```

**Expected**: You get a command prompt on the VPS

**Status**: ✅ Can connect to VPS

---

### Phase 4: VPS Initial Setup (5 minutes)
**What**: Install Docker, configure firewall, create directories
**When**: After successful SSH connection

**Option A - Automated (Recommended):**
```powershell
# From Windows
cd C:\dev\shandorcode\deployment
.\deploy-helper.ps1
# Select option 2: Upload setup script

# Then on VPS
ssh root@72.61.76.32
chmod +x /tmp/setup.sh
/tmp/setup.sh
```

**Option B - Manual:**
Follow steps in `hostinger-setup.sh`

**What happens:**
- Updates Ubuntu
- Installs Docker & Docker Compose
- Configures firewall (UFW)
- Creates directories
- Optimizes system

**Status**: ✅ VPS ready for ShandorCode

---

### Phase 5: Upload ShandorCode (3 minutes)
**What**: Transfer code from Windows to VPS
**When**: After VPS setup completes

**Option A - PowerShell Helper:**
```powershell
cd C:\dev\shandorcode\deployment
.\deploy-helper.ps1
# Select option 3: Upload ShandorCode files
```

**Option B - Manual:**
```powershell
cd C:\dev\shandorcode
tar -czf shandorcode.tar.gz src deployment pyproject.toml LICENSE.txt README.md
scp shandorcode.tar.gz root@72.61.76.32:/opt/shandorcode/

# Then on VPS
ssh root@72.61.76.32
cd /opt/shandorcode
tar -xzf shandorcode.tar.gz
```

**Status**: ✅ Code on VPS

---

### Phase 6: Configure Environment (2 minutes)
**What**: Set up environment variables
**When**: After files uploaded

**On VPS:**
```bash
cd /opt/shandorcode/deployment
cp .env.example .env
nano .env
# Verify settings look correct
# Press Ctrl+X, Y, Enter to save
```

**What to verify:**
```env
DOMAIN=shandor.gozerai.com
ANALYSIS_PATH=/var/shandorcode/repos
LETSENCRYPT_EMAIL=chris@gozerai.com
```

**Status**: ✅ Environment configured

---

### Phase 7: Deploy Docker Containers (3 minutes)
**What**: Start ShandorCode and Caddy
**When**: After environment configured

**On VPS:**
```bash
cd /opt/shandorcode/deployment
docker-compose up -d
```

**Watch it start:**
```bash
docker-compose logs -f
```

**Look for:**
- "Uvicorn running on http://127.0.0.1:8765"
- "Application startup complete"
- Caddy certificate messages

**Press Ctrl+C** when you see these

**Status**: ✅ Containers running

---

### Phase 8: Verify Deployment (5 minutes)
**What**: Check everything is working
**When**: After containers start

**Tests to run:**

1. **Check containers:**
```bash
docker-compose ps
# Both should show "Up"
```

2. **Test local access:**
```bash
curl -I http://localhost:8765
# Should return: HTTP/1.1 200 OK
```

3. **Test HTTPS (wait 2-3 min for SSL):**
```bash
curl -I https://shandor.gozerai.com
# Should return: HTTP/2 200
```

4. **Check logs for errors:**
```bash
docker-compose logs --tail=50
```

**Status**: ✅ Deployment verified

---

### Phase 9: Browser Test (2 minutes)
**What**: Visit the actual website
**When**: After HTTPS verification passes

**Open browser:**
```
https://shandor.gozerai.com
```

**Should see:**
- ShandorCode UI
- Path input field
- Stats dashboard
- Green "Connected" status

**Test it:**
1. Enter path: `/repos/test`
2. Click "Analyze"
3. (Will fail since no files, but UI should respond)

**Status**: ✅ Website live!

---

### Phase 10: Create Test Project (3 minutes)
**What**: Upload sample code to analyze
**When**: After site is working

**On VPS:**
```bash
# Create test directory
mkdir -p /var/shandorcode/repos/test-project
cd /var/shandorcode/repos/test-project

# Create test files
cat > hello.py << 'EOF'
def greet(name):
    """Greet someone by name"""
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, greeting="Hello"):
        self.greeting = greeting
    
    def greet(self, name):
        return f"{self.greeting}, {name}!"

if __name__ == "__main__":
    print(greet("World"))
EOF

cat > utils.py << 'EOF'
def calculate(a, b):
    """Simple calculator"""
    return a + b

class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
EOF
```

**Then in browser:**
1. Enter: `/repos/test-project`
2. Click "Analyze"
3. Should see: 2 files, 6 entities, dependencies

**Status**: ✅ Analysis working!

---

## 📊 Timeline Summary

| Phase | Task | Time | Cumulative |
|-------|------|------|------------|
| 1 | DNS Setup | 10 min | 10 min |
| 2 | Start VPS | 5 min | 15 min |
| 3 | Test SSH | 2 min | 17 min |
| 4 | VPS Setup | 5 min | 22 min |
| 5 | Upload Code | 3 min | 25 min |
| 6 | Configure | 2 min | 27 min |
| 7 | Deploy | 3 min | 30 min |
| 8 | Verify | 5 min | 35 min |
| 9 | Browser Test | 2 min | 37 min |
| 10 | Test Project | 3 min | 40 min |

**Total Active Time**: ~40 minutes
**DNS Propagation**: 10-30 minutes (parallel)

---

## ✅ Success Checklist

After completing all phases, you should have:

- [x] DNS resolves: `shandor.gozerai.com` → `72.61.76.32`
- [x] VPS running and accessible
- [x] Docker installed and running
- [x] Firewall configured (22, 80, 443 open)
- [x] ShandorCode containers running
- [x] HTTPS working with valid certificate
- [x] Website accessible in browser
- [x] Can analyze test project
- [x] WebSocket connection working
- [x] No errors in logs

---

## 🎯 Recommended Order

**Best practice:**

1. **Start DNS first** (Phase 1)
   - Takes time to propagate
   - Can work in background

2. **Do VPS work** (Phases 2-7)
   - While DNS propagates
   - 30 minutes of work

3. **Test everything** (Phases 8-10)
   - DNS should be ready by now
   - Verify all systems working

---

## ⏰ If You Need to Stop and Resume

**Safe stopping points:**

**After Phase 4**: VPS is set up
- Can stop here for days
- Resume anytime at Phase 5

**After Phase 7**: Docker deployed
- Containers running
- Resume at Phase 8 anytime

**Auto-restart**: Containers configured to restart automatically, so if VPS reboots, ShandorCode starts automatically.

---

## 🚨 If Something Goes Wrong

### Phase 1 (DNS) Issues
- Check Namecheap DNS settings
- Wait longer (can take hours)
- Use `NAMECHEAP_DNS_SETUP.md`

### Phase 4 (Setup) Issues
- Check VPS has internet
- Verify Ubuntu version: `lsb_release -a`
- Run setup script line by line

### Phase 7 (Deploy) Issues
- Check logs: `docker-compose logs`
- Verify disk space: `df -h`
- Check memory: `free -h`

### Phase 8 (HTTPS) Issues
- Wait 5 more minutes
- Check port 80 is open
- Restart Caddy: `docker-compose restart caddy`

**Use**: `DEPLOYMENT_CHECKLIST.md` for troubleshooting

---

## 📞 Ready to Start?

**Option 1: Do it all now** (~1 hour)
- Follow this timeline
- I can help if you get stuck

**Option 2: Phase 1 now, rest later**
- Set up DNS (10 min)
- Let it propagate overnight
- Deploy tomorrow

**Option 3: Guided deployment**
- Tell me when you're ready
- I'll walk you through each phase

**What do you want to do?** 🚀
