# Install Control Panels on Hostinger VPS

## Option 1: Portainer (Docker Management) - RECOMMENDED

### Install:
```bash
# Create volume
docker volume create portainer_data

# Run Portainer
docker run -d \
  -p 9443:9443 \
  -p 8000:8000 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

### Access:
```
https://72.61.76.32:9443
```

### First Login:
1. Create admin password (must be 12+ characters)
2. Select "Get Started" → Local environment
3. You'll see all your containers!

### Firewall:
```bash
ufw allow 9443/tcp comment 'Portainer'
```

---

## Option 2: Cockpit (System Management)

### Install:
```bash
sudo apt update
sudo apt install cockpit cockpit-docker -y
sudo systemctl enable --now cockpit.socket
```

### Access:
```
https://72.61.76.32:9090
```

### Login:
- Username: `root`
- Password: Your VPS root password

### Firewall:
```bash
ufw allow 9090/tcp comment 'Cockpit'
```

---

## Option 3: CasaOS (Modern UI)

### Install:
```bash
curl -fsSL https://get.casaos.io | sudo bash
```

### Access:
```
http://72.61.76.32:80
```

### Setup:
Follow on-screen wizard

---

## Recommended: Portainer + Cockpit

Install both for complete coverage:

```bash
# Portainer (Docker)
docker volume create portainer_data
docker run -d \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# Cockpit (System)
apt install cockpit -y
systemctl enable --now cockpit.socket

# Firewall
ufw allow 9443/tcp comment 'Portainer'
ufw allow 9090/tcp comment 'Cockpit'
```

### Access:
- **Portainer**: https://72.61.76.32:9443 (Docker management)
- **Cockpit**: https://72.61.76.32:9090 (System management)

---

## Add to ShandorCode Deployment

### Update docker-compose.yml:

```yaml
version: '3.8'

services:
  # ... existing services ...

  # Portainer
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    ports:
      - "9443:9443"
      - "8000:8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    networks:
      - shandor_net

volumes:
  # ... existing volumes ...
  portainer_data:
```

Then:
```bash
cd /opt/shandorcode/deployment
docker-compose up -d
```

---

## Access via Subdomain (Optional)

Add to Caddyfile:

```
portainer.gozerai.com {
    reverse_proxy portainer:9443 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}

cockpit.gozerai.com {
    reverse_proxy localhost:9090 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}
```

Then add DNS:
- `portainer.gozerai.com` → `72.61.76.32`
- `cockpit.gozerai.com` → `72.61.76.32`

---

## Comparison

| Feature | Portainer | Cockpit | CasaOS |
|---------|-----------|---------|---------|
| Docker Management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| System Management | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| UI/UX | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Maturity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Learning Curve | Easy | Medium | Very Easy |

---

## My Recommendation

**Start with Portainer:**
- Easiest to install
- Perfect for managing ShandorCode + future services
- Non-invasive
- Can add Cockpit later if needed

**Commands:**
```bash
# SSH to VPS
ssh root@72.61.76.32

# Install Portainer
docker volume create portainer_data
docker run -d \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# Allow port
ufw allow 9443/tcp

# Access
# https://72.61.76.32:9443
```

**Takes 2 minutes!** 🚀
