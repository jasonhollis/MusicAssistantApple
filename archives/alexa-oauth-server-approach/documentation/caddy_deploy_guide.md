# Caddy Reverse Proxy Deployment Guide

## Quick Deploy (7 minutes)

### Step 1: SSH to Sydney Box (30 seconds)

```bash
ssh root@dev.jasonhollis.com
```

### Step 2: Install Caddy (2 minutes)

```bash
# Update package lists
apt update

# Install Caddy
apt install -y caddy

# Verify installation
caddy version
```

### Step 3: Create Caddyfile (1 minute)

**OPTION A: If Music Assistant supports HTTP (RECOMMENDED)**

```bash
cat > /etc/caddy/Caddyfile << 'EOF'
dev.jasonhollis.com {
    reverse_proxy http://haboxhill.tail1cba6.ts.net:8096 {
        # Preserve OAuth headers
        header_up Host {upstream_hostport}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
EOF
```

**OPTION B: If Music Assistant is HTTPS-only with self-signed cert**

```bash
cat > /etc/caddy/Caddyfile << 'EOF'
dev.jasonhollis.com {
    reverse_proxy https://haboxhill.tail1cba6.ts.net:8096 {
        # Preserve OAuth headers
        header_up Host {upstream_hostport}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        # Trust self-signed cert on internal Tailscale network
        transport http {
            tls_insecure_skip_verify
        }
    }
}
EOF
```

### Step 4: Start Caddy (30 seconds)

```bash
# Enable Caddy to start on boot
systemctl enable caddy

# Start Caddy service
systemctl start caddy

# Check status
systemctl status caddy
```

**Expected output**: "Active: active (running)"

### Step 5: Verify SSL Certificate Obtained (30 seconds)

```bash
# Check Caddy logs for Let's Encrypt certificate
journalctl -u caddy -n 50 | grep -i certificate

# Expected: "certificate obtained successfully"
```

### Step 6: Test Connectivity (2 minutes)

**From Sydney box (local test)**:
```bash
# Test health endpoint
curl -I https://dev.jasonhollis.com/health

# Expected: HTTP/2 200 OK
```

**From your Mac (remote test)**:
```bash
# Test from outside the server
curl -I https://dev.jasonhollis.com/health

# Expected: HTTP/2 200 OK with valid SSL
```

**From phone browser** (final validation):
- Open Safari/Chrome
- Navigate to: `https://dev.jasonhollis.com/health`
- Verify: No SSL warnings, valid certificate, 200 OK response

---

## Troubleshooting

### Issue: "Certificate not obtained"

**Check DNS propagation**:
```bash
dig dev.jasonhollis.com +short
# Should return Sydney box public IP
```

**Check port 80/443 availability** (Let's Encrypt needs port 80 for verification):
```bash
# Port 80 check
netstat -tuln | grep :80

# Port 443 check
netstat -tuln | grep :443
```

**Check firewall** (if using ufw):
```bash
ufw status
# Should allow 80/tcp and 443/tcp
```

### Issue: "Connection refused to backend"

**Verify Tailscale connectivity from Sydney box**:
```bash
# Ping Music Assistant via Tailscale
ping -c 3 haboxhill.tail1cba6.ts.net

# Test direct connection to Music Assistant
curl -I -k https://haboxhill.tail1cba6.ts.net:8096/health
```

### Issue: "Bad Gateway (502)"

**Check Music Assistant is running**:
```bash
# SSH to haboxhill (if accessible)
# OR check from Sydney box via Tailscale
curl -v -k https://haboxhill.tail1cba6.ts.net:8096/health
```

**Check Caddy logs**:
```bash
journalctl -u caddy -n 100 -f
# Watch for errors during proxy attempts
```

---

## Configuration Explanation

### Header Preservation for OAuth

```
header_up Host {upstream_hostport}
```
- Preserves original Host header for OAuth redirect URI validation
- Critical for OAuth flow to work correctly

```
header_up X-Forwarded-For {remote_host}
header_up X-Forwarded-Proto {scheme}
```
- Tells Music Assistant the original client IP and protocol
- Required for proper OAuth security checks

### TLS Insecure Skip Verify (HTTPS backend only)

```
transport http {
    tls_insecure_skip_verify
}
```

**Why this is acceptable**:
1. Traffic between Sydney box and Music Assistant is over **Tailscale encrypted mesh network**
2. Self-signed cert verification failure is expected (not a security issue)
3. Tailscale already provides end-to-end encryption
4. This is internal infrastructure, not public internet

**Security posture**:
- Public clients → Sydney box: **Validated Let's Encrypt certificate** ✅
- Sydney box → Music Assistant: **Tailscale encrypted tunnel** ✅
- No unencrypted traffic, no MITM risk

---

## Post-Deployment

### Update Alexa Skill Configuration

**In Amazon Developer Console → Alexa Skills → Your Skill → Account Linking**:

Change from:
```
Authorization URI: https://music.jasonhollis.com:8096/alexa/authorize
Access Token URI: https://music.jasonhollis.com:8096/alexa/token
```

To:
```
Authorization URI: https://dev.jasonhollis.com/alexa/authorize
Access Token URI: https://dev.jasonhollis.com/alexa/token
```

**Save changes** and **test account linking** from Alexa app.

---

## Maintenance

### Certificate Auto-Renewal

Caddy handles this automatically. Verify with:
```bash
# Check certificate expiry
echo | openssl s_client -servername dev.jasonhollis.com -connect dev.jasonhollis.com:443 2>/dev/null | openssl x509 -noout -dates
```

Let's Encrypt certificates are valid for 90 days. Caddy renews at 30 days before expiry.

### Monitoring

**Check Caddy service status**:
```bash
systemctl status caddy
```

**View live logs**:
```bash
journalctl -u caddy -f
```

**Test health endpoint**:
```bash
curl -I https://dev.jasonhollis.com/health
```

---

## Rollback Plan

If issues occur, stop Caddy to restore previous state:

```bash
systemctl stop caddy
systemctl disable caddy
```

This does not affect `dev.jasonhollis.com` DNS or other services. Can re-enable anytime:

```bash
systemctl enable caddy
systemctl start caddy
```
