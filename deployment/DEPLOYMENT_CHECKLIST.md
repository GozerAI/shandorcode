# ✅ ShandorCode Hostinger Deployment Checklist

## 📋 Pre-Deployment (Do These First)

### 1. Start VPS
- [ ] Login to Hostinger control panel
- [ ] Find your VPS (KVM4)
- [ ] Click "Start" or "Power On"
- [ ] Wait for status to show "Running"

### 2. Configure DNS
- [ ] Login to domain registrar
- [ ] Navigate to DNS settings for gozerai.com
- [ ] Add A record:
  - Type: `A`
  - Name: `shandor`
  - Value: `72.61.76.32`
  - TTL: `3600`
- [ ] Save changes
- [ ] Wait 5-10 minutes for propagation

### 3. Test Connectivity
- [ ] Open PowerShell
- [ ] Run: `ping 72.61.76.32`
- [ ] Verify it responds
- [ ] Run: `ssh root@72.61.76.32`
- [ ] Enter password: `Lh9vW(+fb)5x.c,V`
- [ ] Verify you can login

---

## 🚀 Deployment Steps

### 4. Run Setup Script
- [ ] From Windows: `cd C:\dev\shandorcode\deployment`
- [ ] Run PowerShell helper: `.\deploy-helper.ps1`
- [ ] Select option 2 (Upload setup script)
- [ ] SSH to VPS: `ssh root@72.61.76.32`
- [ ] Run: `chmod +x /tmp/setup.sh && /tmp/setup.sh`
- [ ] Wait for completion (~5 minutes)
- [ ] Verify Docker installed: `docker --version`

### 5. Upload ShandorCode Files
- [ ] From Windows PowerShell helper, select option 3
- [ ] OR manually: `scp -r * root@72.61.76.32:/opt/shandorcode/`
- [ ] Verify upload: SSH to VPS and run `ls /opt/shandorcode/`

### 6. Configure Environment
- [ ] SSH to VPS
- [ ] Run: `cd /opt/shandorcode/deployment`
- [ ] Run: `cp .env.example .env`
- [ ] Edit if needed: `nano .env`
- [ ] Verify settings are correct

### 7. Deploy Docker Containers
- [ ] Still on VPS: `cd /opt/shandorcode/deployment`
- [ ] Run: `docker-compose up -d`
- [ ] Watch logs: `docker-compose logs -f`
- [ ] Wait for "Application startup complete"
- [ ] Press Ctrl+C to exit logs

### 8. Verify Deployment
- [ ] Check containers: `docker-compose ps`
- [ ] Both should show "Up"
- [ ] Test locally on VPS: `curl -I http://localhost:8765`
- [ ] Should return HTTP 200

### 9. Test HTTPS
- [ ] Wait 2-3 minutes for Let's Encrypt
- [ ] From VPS: `curl -I https://shandor.gozerai.com`
- [ ] Should return HTTP/2 200
- [ ] Check certificate: `curl -vI https://shandor.gozerai.com 2>&1 | grep -i cert`

### 10. Visit Website
- [ ] Open browser
- [ ] Go to: `https://shandor.gozerai.com`
- [ ] Should see ShandorCode UI
- [ ] Test path input field
- [ ] Verify WebSocket connection (green status)

---

## 🔍 Post-Deployment Verification

### 11. Test Analysis
- [ ] SSH to VPS
- [ ] Create test directory: `mkdir -p /var/shandorcode/repos/test`
- [ ] Add test file: `echo "print('hello')" > /var/shandorcode/repos/test/test.py`
- [ ] In browser, enter path: `/repos/test`
- [ ] Click "Analyze"
- [ ] Should see 1 file, 1 entity

### 12. Check Security
- [ ] Verify firewall: `ufw status`
- [ ] Should show ports 22, 80, 443 allowed
- [ ] Test HTTPS redirect: `curl -I http://shandor.gozerai.com`
- [ ] Should redirect to HTTPS

### 13. Monitor Resources
- [ ] Check disk: `df -h`
- [ ] Check memory: `free -h`
- [ ] Check Docker: `docker stats --no-stream`
- [ ] All should be normal

---

## 📱 Ongoing Management

### Daily
- [ ] Check if site is up: Visit URL
- [ ] Monitor resource usage: `htop` on VPS

### Weekly
- [ ] Check logs: `docker-compose logs --tail=100`
- [ ] Check for updates: `docker-compose pull`
- [ ] Update if needed: `docker-compose up -d`

### Monthly
- [ ] System updates: `apt update && apt upgrade`
- [ ] Clear old Docker images: `docker system prune -a`
- [ ] Review logs for errors
- [ ] Backup configuration

---

## 🐛 Troubleshooting Checklist

### If site won't load:
- [ ] VPS is running (Hostinger panel)
- [ ] DNS is configured correctly (`dig shandor.gozerai.com`)
- [ ] Firewall allows 443 (`ufw status`)
- [ ] Docker containers running (`docker-compose ps`)
- [ ] Check Caddy logs (`docker-compose logs caddy`)

### If SSL certificate fails:
- [ ] DNS points to correct IP
- [ ] Port 80 is open (needed for Let's Encrypt)
- [ ] Caddy logs show certificate request
- [ ] Wait a few minutes and try again
- [ ] Restart Caddy: `docker-compose restart caddy`

### If analysis fails:
- [ ] Path is correct (must start with `/repos/`)
- [ ] Files exist in `/var/shandorcode/repos/`
- [ ] Check app logs: `docker-compose logs shandorcode`
- [ ] Restart app: `docker-compose restart shandorcode`

---

## 🎯 Success Criteria

All of these should be ✅ when complete:

- [x] VPS is running
- [x] DNS configured (shandor.gozerai.com → 72.61.76.32)
- [x] SSH access works
- [x] Docker installed
- [x] Firewall configured
- [x] ShandorCode files uploaded
- [x] Environment configured
- [x] Docker containers running
- [x] HTTPS certificate valid
- [x] Site accessible via browser
- [x] Can analyze test project
- [x] WebSocket connection works
- [x] No errors in logs

---

## 📊 Time Tracking

Estimated times for each step:

| Step | Time | Cumulative |
|------|------|------------|
| 1. Start VPS | 2 min | 2 min |
| 2. Configure DNS | 5 min | 7 min |
| 3. Test connectivity | 2 min | 9 min |
| 4. Run setup script | 5 min | 14 min |
| 5. Upload files | 3 min | 17 min |
| 6. Configure env | 2 min | 19 min |
| 7. Deploy containers | 3 min | 22 min |
| 8. Verify deployment | 2 min | 24 min |
| 9. Test HTTPS | 3 min | 27 min |
| 10. Visit website | 1 min | 28 min |
| DNS propagation | varies | +0-60 min |

**Total Active Time**: ~28 minutes
**Total with DNS wait**: ~30-90 minutes

---

## 📝 Notes Section

Use this space to track your deployment:

**Started at**: __________
**Completed at**: __________
**Issues encountered**: 
- 
- 
- 

**Solutions**: 
- 
- 
- 

**Final URL**: https://shandor.gozerai.com
**Status**: ☐ Success ☐ Partial ☐ Issues

---

## 🎉 You're Done When...

✅ You can visit https://shandor.gozerai.com  
✅ You see the ShandorCode interface  
✅ You can enter a path and analyze code  
✅ Real-time updates work (WebSocket connected)  
✅ No errors in browser console  
✅ SSL certificate is valid (green padlock)  

**Congratulations! ShandorCode is live!** 🏗️👻
