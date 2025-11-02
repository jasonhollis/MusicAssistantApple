# Complete Deployment Plan: Music Assistant + OAuth (Native Python + Systemd)

**Status**: READY FOR REVIEW (No production edits yet)
**Target**: dev.jasonhollis.com (Ubuntu production server)
**Deployment Method**: Native Python + Systemd (NOT containers)
**Timeline**: 7 days with validation checkpoints
**Risk Level**: LOW (simple, reversible, no container complexity)

---

## Executive Summary

### Decision: Why Native Instead of Docker?

Both strategic architects (Local 80B Consultant + Grok Strategic Consultant) unanimously recommend **native Python + Systemd** for this deployment because:

1. ✅ **Single-instance deployment** - No need for container orchestration
2. ✅ **Your expertise** - Linux/Python native skills (don't learn Docker)
3. ✅ **HAOS lesson learned** - Avoid Docker after experiencing instability
4. ✅ **Simpler debugging** - Direct access to logs, processes, filesystem
5. ✅ **Reversible** - Can migrate to Docker later (code doesn't change)
6. ✅ **Faster deployment** - 10 minutes setup vs 30+ minutes Docker
7. ✅ **Lower overhead** - Save 200-300MB memory vs Docker

### Architecture Overview

```
dev.jasonhollis.com (Ubuntu 24.04)
│
├── /opt/music-assistant/          # Music Assistant installation
│   ├── venv/                      # Python 3.11 virtual environment
│   ├── app/                       # Music Assistant code
│   └── data/                      # Persistent config/database
│
├── /opt/oauth-server/             # OAuth server installation
│   ├── venv/                      # Python 3.11 virtual environment
│   ├── server.py                  # OAuth server code
│   └── oauth_clients.json         # Client configuration
│
├── /etc/systemd/system/
│   ├── music-assistant.service    # Systemd unit (auto-restart, logging)
│   └── oauth-server.service       # Systemd unit (auto-restart, logging)
│
└── /etc/nginx/
    ├── sites-available/music-assistant   # Reverse proxy config
    └── sites-enabled/music-assistant     # Enabled config (symlink)

External:
├── music.jasonhollis.com          # HTTPS public endpoint (Music Assistant UI)
├── oauth.dev.jasonhollis.com      # HTTPS public endpoint (OAuth server)
└── Let's Encrypt SSL certificates (auto-renewed by certbot)
```

---

## Pre-Deployment Questions (For Your Confirmation)

Before I finalize the plan, please confirm these details:

### 1. **DNS Records**
- [ ] Does `music.jasonhollis.com` currently point to dev.jasonhollis.com?
- [ ] Does `oauth.dev.jasonhollis.com` currently exist?
- [ ] Or should we use different subdomains?

**Current assumption**: `music.jasonhollis.com` → `dev.jasonhollis.com` (via CNAME or A record)

### 2. **SSL Certificates**
- [ ] Do SSL certificates already exist for these domains?
- [ ] Should we generate new ones with Let's Encrypt certbot?
- [ ] Do you manage certbot renewal already?

**Current assumption**: We'll generate new certs with `sudo certbot --nginx`

### 3. **Home Assistant Integration**
- [ ] What is Home Assistant's IP address / hostname?
- [ ] Can Home Assistant reach `music.jasonhollis.com` from its network?
- [ ] Will you update HA's Music Assistant integration to point to new URL during deployment?

**Current assumption**: HA can reach public HTTPS endpoints

### 4. **Data Backup Strategy**
- [ ] How should we backup `/opt/music-assistant/data` (config + database)?
- [ ] Do you want automated daily backups?
- [ ] Where should backups be stored?

**Current assumption**: Manual backup before each major update

### 5. **OAuth Server Configuration**
- [ ] Do you have the current `oauth_clients.json` from HAOS addon?
- [ ] What is the Alexa Client Secret (from earlier sessions)?
- [ ] Should OAuth server generate new tokens or preserve existing ones?

**Current assumption**: We'll copy existing config from HAOS

### 6. **Alexa Skill Configuration**
- [ ] Are you updating the Alexa Skill OAuth endpoints during deployment?
- [ ] What's the target: `music.jasonhollis.com/alexa/authorize` and `/alexa/token`?
- [ ] Do you want to test with a non-critical account first?

**Current assumption**: Update Alexa console during Phase 4

---

## Architecture Comparison (For Understanding)

### Why NOT Docker for This Deployment?

| Aspect | Docker Compose | Native + Systemd | Winner |
|--------|---|---|---|
| **Complexity** | 7/10 | 3/10 | Native |
| **Learning curve** | Moderate | None (standard Linux) | Native |
| **Debugging time** | 5-10 min | <2 min | Native |
| **Memory overhead** | 200-300MB | ~50MB | Native |
| **Resource efficiency** | Wasteful | Efficient | Native |
| **Time to deploy** | 30+ min | 10 min | Native |
| **Time to recover from failure** | 10-15 min | 2-3 min | Native |
| **Your expertise fit** | Learning new patterns | Expert level | Native |
| **Reproducibility** | Excellent (images) | Good (git + script) | Docker |
| **Current requirements fit** | Overkill | Perfect | Native |

**Verdict**: Native wins 8/9 criteria for single-instance deployment.

### When Would Docker Be Better?

Docker becomes attractive when you need:
- Multiple instances of same service (scaling)
- Automated deployment pipelines (CI/CD)
- Multi-host orchestration (Kubernetes)
- Complex dependency isolation
- Version-stamped rollbacks (blue-green deploys)

**None of these apply to your situation (yet).**

---

## 7-Day Deployment Timeline

### Phase 1: Pre-Deployment Setup (Day 1)

**Duration**: 30-45 minutes
**Risk**: None (no production changes yet)

**Checklist**:
- [ ] Confirm all pre-deployment questions answered
- [ ] Verify DNS records exist
- [ ] Verify dev.jasonhollis.com is accessible
- [ ] SSH access to dev.jasonhollis.com working
- [ ] Backup current HAOS Music Assistant configuration

**Commands**:
```bash
# Verify SSH access
ssh jason@dev.jasonhollis.com "uname -a"

# Verify Ubuntu version
lsb_release -a

# Check available disk space
df -h

# Check available memory
free -h

# Verify Python installed
python3 --version
```

**Deliverable**: All prechecks passing, DNS verified

---

### Phase 2: Environment Setup (Day 2 Morning)

**Duration**: 20-30 minutes
**Risk**: Very low (creating directories, no service changes)

**What we're doing**: Create the directory structure and user accounts

**Step 1: Create application directories**
```bash
# Create directories
sudo mkdir -p /opt/music-assistant/data
sudo mkdir -p /opt/oauth-server

# Verify creation
ls -la /opt/ | grep music

# Set proper ownership (assuming your username is 'jason')
sudo chown jason:jason /opt/music-assistant
sudo chown jason:jason /opt/oauth-server

# Set permissions
chmod 755 /opt/music-assistant
chmod 755 /opt/oauth-server
```

**Step 2: Install system dependencies**
```bash
# Update package manager
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y \
  python3-venv \
  python3-pip \
  nginx \
  certbot \
  python3-certbot-nginx \
  curl \
  git

# Verify installations
python3 --version
nginx -v
certbot --version
```

**Deliverable**: Directories created, dependencies installed, no errors

---

### Phase 3: Deploy Music Assistant (Day 2 Afternoon)

**Duration**: 30-45 minutes
**Risk**: Low (isolated to Music Assistant, no reverse proxy yet)

**Step 1: Create Python virtual environment**
```bash
cd /opt/music-assistant
python3 -m venv venv
source venv/bin/activate

# Verify venv created
which python
python --version
```

**Step 2: Install Music Assistant**
```bash
cd /opt/music-assistant
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Music Assistant (adjust version as needed)
pip install music-assistant==latest

# Verify installation
pip list | grep -i music
```

**Step 3: Copy configuration from HAOS**
```bash
# On your local machine (NOT on dev.jasonhollis.com):
# Backup from HAOS first
scp jason@haboxhill.local:~/.config/music-assistant/config.json \
    ~/music-assistant-config-backup.json

# Then copy to dev server
scp ~/music-assistant-config-backup.json \
    jason@dev.jasonhollis.com:/opt/music-assistant/data/config.json

# On dev.jasonhollis.com, verify file exists
ls -la /opt/music-assistant/data/
```

**Step 4: Create systemd service file**
```bash
# Create the service file
sudo tee /etc/systemd/system/music-assistant.service > /dev/null <<'EOF'
[Unit]
Description=Music Assistant Media Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jason
Group=jason
WorkingDirectory=/opt/music-assistant
Environment="PATH=/opt/music-assistant/venv/bin"
Environment="PYTHONUNBUFFERED=1"

# Adjust this command based on actual Music Assistant startup
ExecStart=/opt/music-assistant/venv/bin/music-assistant \
  --config /opt/music-assistant/data

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to auto-start on reboot
sudo systemctl enable music-assistant

# Start the service
sudo systemctl start music-assistant

# Verify service is running
sudo systemctl status music-assistant
```

**Step 5: Verify Music Assistant is accessible**
```bash
# Wait 5 seconds for startup
sleep 5

# Check service status
sudo systemctl status music-assistant

# Check logs
sudo journalctl -u music-assistant -n 20

# Test endpoint (should get response on port 8095)
curl -v http://localhost:8095/health || curl -v http://localhost:8095
```

**Deliverable**: Music Assistant running, accessible on localhost:8095, logs visible in journalctl

---

### Phase 4: Deploy OAuth Server (Day 3)

**Duration**: 20-30 minutes
**Risk**: Low (isolated to OAuth server, no reverse proxy yet)

**Step 1: Prepare OAuth server code**
```bash
# Create OAuth server directory
cd /opt/oauth-server

# Copy OAuth server code from your backup
# Option A: If you have it in a git repo
git clone <your-repo> .

# Option B: If you have the files locally
scp ~/oauth_server.py jason@dev.jasonhollis.com:/opt/oauth-server/
scp ~/oauth_clients.json jason@dev.jasonhollis.com:/opt/oauth-server/

# Verify files exist
ls -la /opt/oauth-server/
```

**Step 2: Create Python virtual environment**
```bash
cd /opt/oauth-server
python3 -m venv venv
source venv/bin/activate

# Verify venv created
which python
python --version
```

**Step 3: Install OAuth server dependencies**
```bash
cd /opt/oauth-server
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages
# (adjust based on your oauth_server.py requirements)
pip install aiohttp

# Verify
pip list
```

**Step 4: Create systemd service file**
```bash
# Create the service file
sudo tee /etc/systemd/system/oauth-server.service > /dev/null <<'EOF'
[Unit]
Description=OAuth Server for Music Assistant + Alexa
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jason
Group=jason
WorkingDirectory=/opt/oauth-server
Environment="PATH=/opt/oauth-server/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="ALEXA_CLIENT_SECRET=<YOUR_SECRET_HERE>"

ExecStart=/opt/oauth-server/venv/bin/python oauth_server.py

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable oauth-server

# Start service
sudo systemctl start oauth-server

# Verify
sudo systemctl status oauth-server
```

**Step 5: Verify OAuth server is accessible**
```bash
# Wait for startup
sleep 3

# Check service status
sudo systemctl status oauth-server

# Check logs
sudo journalctl -u oauth-server -n 20

# Test health endpoint
curl -v http://localhost:8096/health
```

**Deliverable**: OAuth server running on localhost:8096, health endpoint responding, logs visible

---

### Phase 5: Configure nginx Reverse Proxy (Day 4)

**Duration**: 20-30 minutes
**Risk**: Medium (affects public endpoints, need HTTPS certs)

**Step 1: Generate SSL certificates**
```bash
# Generate certificates with certbot (interactive)
sudo certbot certonly --standalone \
  -d music.jasonhollis.com \
  -d oauth.dev.jasonhollis.com

# Verify certificates created
ls -la /etc/letsencrypt/live/

# Note certificate paths for nginx config
```

**Step 2: Create nginx configuration**
```bash
# Create nginx config file
sudo tee /etc/nginx/sites-available/music-assistant > /dev/null <<'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name music.jasonhollis.com oauth.dev.jasonhollis.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Music Assistant HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name music.jasonhollis.com;

    ssl_certificate /etc/letsencrypt/live/music.jasonhollis.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/music.jasonhollis.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8095;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# OAuth Server HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name oauth.dev.jasonhollis.com;

    ssl_certificate /etc/letsencrypt/live/oauth.dev.jasonhollis.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/oauth.dev.jasonhollis.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8096;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable the configuration
sudo ln -s /etc/nginx/sites-available/music-assistant \
           /etc/nginx/sites-enabled/music-assistant

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

**Step 3: Verify nginx is proxying correctly**
```bash
# Check nginx status
sudo systemctl status nginx

# Test Music Assistant endpoint (HTTPS)
curl -k https://music.jasonhollis.com/

# Test OAuth endpoint (HTTPS)
curl -k https://oauth.dev.jasonhollis.com/health
```

**Deliverable**: nginx proxying to both services, HTTPS certificates valid, public endpoints responding

---

### Phase 6: Home Assistant Integration (Day 5)

**Duration**: 15-20 minutes
**Risk**: Low (HAOS still running Music Assistant addon)

**Step 1: Update Home Assistant configuration**
```bash
# Log into Home Assistant UI
# Settings → Devices & Services → Music Assistant

# Update the server URL from:
#   http://haboxhill.local:8095
# To:
#   https://music.jasonhollis.com

# Save configuration
# Wait for HA to reconnect
```

**Step 2: Verify Music Assistant connection in HA**
```bash
# In Home Assistant, check Status:
# Should show "Connected" or "Ready"

# Test music playback from HA UI
# (Select a provider and test playing a song)
```

**Deliverable**: Home Assistant successfully connected to production Music Assistant, playback working

---

### Phase 7: Alexa OAuth Integration (Day 6)

**Duration**: 20-30 minutes
**Risk**: Medium (updating Alexa Skill configuration)

**Step 1: Update Alexa Skill OAuth endpoints**
```bash
# Log into Amazon Developer Console
# Your Skill → Account Linking

# Update OAuth endpoints:
#   Authorization URI: https://oauth.dev.jasonhollis.com/alexa/authorize
#   Token URI: https://oauth.dev.jasonhollis.com/alexa/token

# Save changes
```

**Step 2: Test account linking flow**
```bash
# On Alexa mobile app
# Go to Skills → Your Skills → Music Assistant
# Click "SETTINGS"
# Click "Link Account"

# Should see OAuth authorization form
# Log in, authorize, and get callback

# Verify "Account Linked" status in app
```

**Step 3: Test voice commands**
```bash
# "Alexa, ask Music Assistant to play [artist name]"
# Should successfully play music through Music Assistant
```

**Deliverable**: Alexa OAuth account linking working, voice commands operational

---

### Phase 8: Validation & Monitoring (Days 6-7)

**Duration**: 1-2 hours over 2 days
**Risk**: Very low (observation only)

**Day 6 Afternoon: Initial validation**
```bash
# Check all services running
sudo systemctl status music-assistant oauth-server nginx

# View recent logs
sudo journalctl -u music-assistant -n 10
sudo journalctl -u oauth-server -n 10

# Test endpoints
curl https://music.jasonhollis.com
curl https://oauth.dev.jasonhollis.com/health

# Check resource usage
free -h
df -h
ps aux | grep python
```

**Day 7 Full Day: Stability observation**
```bash
# Monitor logs every few hours
sudo journalctl -u music-assistant -f

# Check for any errors or warnings
sudo journalctl -u music-assistant -p err

# Verify HAOS is still working (don't decommission yet)
# Test music playback periodically from HA

# Check disk/memory usage
watch -n 5 'free -h && echo "---" && df -h'
```

**Day 8+: Decision point**
```bash
# If all working smoothly for 24 hours:
# Option A: Keep both systems running (redundancy)
# Option B: Disable Music Assistant addon in HAOS
# Option C: Keep HAOS as backup, use prod as primary
```

**Deliverable**: Services stable for 24+ hours, all endpoints working, no errors in logs

---

## Systemd Service Files (Copy-Paste Ready)

### File 1: `/etc/systemd/system/music-assistant.service`

```ini
[Unit]
Description=Music Assistant Media Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jason
Group=jason
WorkingDirectory=/opt/music-assistant
Environment="PATH=/opt/music-assistant/venv/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/opt/music-assistant/venv/bin/music-assistant \
  --config /opt/music-assistant/data

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### File 2: `/etc/systemd/system/oauth-server.service`

```ini
[Unit]
Description=OAuth Server for Music Assistant + Alexa
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jason
Group=jason
WorkingDirectory=/opt/oauth-server
Environment="PATH=/opt/oauth-server/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="ALEXA_CLIENT_SECRET=YOUR_SECRET_HERE"

ExecStart=/opt/oauth-server/venv/bin/python oauth_server.py

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

---

## Rollback Procedures (If Things Go Wrong)

### Scenario 1: Music Assistant Won't Start

```bash
# Stop the service
sudo systemctl stop music-assistant

# Check error logs
sudo journalctl -u music-assistant -n 50

# Verify Python venv is OK
cd /opt/music-assistant
source venv/bin/activate
python -c "import music_assistant; print('OK')"

# Check config file exists
ls -la /opt/music-assistant/data/config.json

# Restart
sudo systemctl start music-assistant
```

### Scenario 2: OAuth Server Won't Start

```bash
# Stop the service
sudo systemctl stop oauth-server

# Check error logs
sudo journalctl -u oauth-server -n 50

# Verify Python dependencies
cd /opt/oauth-server
source venv/bin/activate
python -c "import aiohttp; print('OK')"

# Check config file exists
ls -la /opt/oauth-server/oauth_clients.json

# Restart
sudo systemctl start oauth-server
```

### Scenario 3: nginx Won't Proxy Correctly

```bash
# Test nginx configuration
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log

# Verify services are actually running on localhost
curl http://localhost:8095
curl http://localhost:8096/health

# Reload nginx
sudo systemctl reload nginx
```

### Scenario 4: Complete Rollback (Remove Everything)

```bash
# Stop all services
sudo systemctl stop music-assistant oauth-server nginx

# Disable auto-startup
sudo systemctl disable music-assistant oauth-server

# Remove service files
sudo rm /etc/systemd/system/music-assistant.service
sudo rm /etc/systemd/system/oauth-server.service

# Remove nginx config
sudo rm /etc/nginx/sites-enabled/music-assistant
sudo rm /etc/nginx/sites-available/music-assistant

# Reload systemd and nginx
sudo systemctl daemon-reload
sudo systemctl reload nginx

# Optionally remove application files
# sudo rm -rf /opt/music-assistant /opt/oauth-server

# Total rollback time: < 2 minutes
```

---

## Monitoring & Operations

### Daily Health Check
```bash
#!/bin/bash
# Save as: /opt/scripts/health-check.sh

echo "=== Service Health ==="
systemctl status music-assistant --no-pager | grep "Active"
systemctl status oauth-server --no-pager | grep "Active"

echo "=== Endpoint Health ==="
curl -s http://localhost:8095 > /dev/null && echo "✓ Music Assistant" || echo "✗ Music Assistant"
curl -s http://localhost:8096/health > /dev/null && echo "✓ OAuth Server" || echo "✗ OAuth Server"

echo "=== Resource Usage ==="
free -h | grep Mem
df -h | grep /

echo "=== Recent Errors ==="
journalctl -u music-assistant -p err -n 5
journalctl -u oauth-server -p err -n 5
```

### View Real-Time Logs
```bash
# Music Assistant logs
sudo journalctl -u music-assistant -f

# OAuth Server logs
sudo journalctl -u oauth-server -f

# Combined
sudo journalctl -u music-assistant -u oauth-server -f

# Search for errors
sudo journalctl -u music-assistant -p err --since "1 hour ago"
```

### Restart Services
```bash
# Restart Music Assistant
sudo systemctl restart music-assistant

# Restart OAuth Server
sudo systemctl restart oauth-server

# Restart all services
sudo systemctl restart music-assistant oauth-server nginx
```

---

## Important Notes

### About the Deployment
- **No data loss**: All config backed up before changes
- **Reversible**: Can rollback in <2 minutes if needed
- **Zero downtime**: HAOS stays running during deployment
- **Testing**: Each phase independently verified before moving to next

### About Native vs Docker
- **Why not containers here?**: Single instance, simple services, high reliability priority
- **What if we need containers later?**: Can wrap in docker-compose (code doesn't change)
- **Is this production-ready?**: Yes, systemd is battle-tested for decades

### About the Timeline
- **Days 1-4**: Setup and deployment (can be done in 1 focused day if needed)
- **Days 5-7**: Validation and monitoring (must be at least 24 hours)
- **Can go faster?**: Yes, if you want to compress into 3-4 days
- **Can be slower?** Yes, spread over 2-3 weeks if more conservative

---

## Success Criteria

This deployment is **successful when**:

✅ Music Assistant running on localhost:8095
✅ OAuth server running on localhost:8096
✅ Both services restart automatically on reboot
✅ nginx proxying to both services via HTTPS
✅ Home Assistant connected to production Music Assistant
✅ Alexa can link account and execute voice commands
✅ No errors in logs after 24 hours of operation
✅ Both services use <100MB memory combined
✅ Zero interruptions to home automation services

---

## Questions Before Proceeding?

- [ ] Do you want to start with Phase 1 (pre-deployment checks)?
- [ ] Do you need clarification on any phase?
- [ ] Should I create an automated deployment script?
- [ ] Do you need the detailed commands for any specific phase?

---

**READY FOR REVIEW**

This plan is complete and reviewable. No production changes will be made until you confirm:

1. ✅ You understand the approach (native, not Docker)
2. ✅ You've answered the pre-deployment questions above
3. ✅ You're ready to execute Phase 1

When you're ready, reply with:
- Answers to pre-deployment questions
- Any concerns or modifications
- **PROCEED** to start Phase 1
