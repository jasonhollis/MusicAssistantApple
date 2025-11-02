# Tailscale Funnel Configuration for Home Assistant
**Purpose**: Step-by-step procedures for configuring Tailscale Funnel in Home Assistant environment to expose Music Assistant OAuth server
**Audience**: System administrators, DevOps engineers
**Layer**: 05_OPERATIONS
**Related**: [HABOXHILL_NETWORK_TOPOLOGY](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md), [TAILSCALE_OAUTH_ROUTING](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md)

## Intent

This document provides concrete operational procedures for configuring Tailscale Funnel in a Home Assistant environment where Tailscale runs as a separate add-on container. These procedures account for the unique architecture where Tailscale and Music Assistant are in different containers and must communicate across the Docker bridge network.

**Critical Context**: Unlike standard Tailscale installations, Home Assistant runs Tailscale as a containerized add-on. This means:
- Tailscale CLI is inside the `addon_a0d7b954_tailscale` container
- All `tailscale` commands must be run via `docker exec`
- Funnel must forward traffic to a different container (music-assistant)
- Standard Tailscale Funnel tutorials don't account for this architecture

## Prerequisites

### Required Information

**Before starting, gather this information**:

1. **Tailscale Container Details**:
   - Container ID: `addon_a0d7b954_tailscale` ✅ KNOWN
   - Tailscale hostname: `a0d7b954-tailscale` ✅ KNOWN
   - Public URL: `https://a0d7b954-tailscale.ts.net` ✅ KNOWN

2. **Music Assistant Details**:
   - Container name: `music-assistant` ✅ KNOWN
   - OAuth server port: `8096` ✅ KNOWN
   - Docker DNS name: `music-assistant` ✅ VERIFIED

3. **Network Verification**:
   - Tailscale can reach Music Assistant: ✅ VERIFIED
   - OAuth server is running: ✅ VERIFIED
   - Health endpoint responds: ✅ VERIFIED

### Required Access

**You must have**:
- SSH/console access to HABoxHill host
- Docker command access (usually via `docker` command)
- Home Assistant add-on management access (optional, for troubleshooting)

### System Requirements

**HABoxHill System**:
- Home Assistant OS or Supervised installation
- Tailscale add-on installed and configured
- Music Assistant add-on installed and running
- Docker engine running (automatic with HA)

## Verification Before Configuration

**Run these checks BEFORE attempting Funnel configuration**:

### Check 1: Verify OAuth Server Running

```bash
# From HABoxHill host
curl http://localhost:8096/health
```

**Expected Output**:
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": [
    "/health",
    "/alexa/authorize",
    "/alexa/token"
  ]
}
```

**If this fails**: Stop here and fix OAuth server first. See troubleshooting section.

### Check 2: Verify Tailscale Container Access

```bash
# From HABoxHill host
docker exec addon_a0d7b954_tailscale /bin/sh -c "echo 'Tailscale container accessible'"
```

**Expected Output**:
```
Tailscale container accessible
```

**If this fails**: Tailscale container is not running. Restart it via Home Assistant UI (Settings → Add-ons → Tailscale → Restart).

### Check 3: Verify Container Communication

```bash
# From HABoxHill host
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health
```

**Expected Output**:
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  ...
}
```

**If this fails**: DNS resolution or network issue. See troubleshooting section.

### Check 4: Verify Tailscale Funnel Feature Available

```bash
# From HABoxHill host
docker exec addon_a0d7b954_tailscale tailscale funnel status
```

**Expected Output** (one of these):
- `Funnel not running` (good - ready to configure)
- `Serving https://a0d7b954-tailscale.ts.net/` (Funnel already configured - check config)
- `Funnel is not enabled for this account` (BAD - need to enable Funnel in Tailscale admin)

**If Funnel not available**: Go to Tailscale admin console → Settings → Enable Funnel feature.

## Funnel Configuration Procedures

### Procedure A: Configure Funnel with Direct Port Forward

**When to use**: If Tailscale Funnel supports direct port forwarding to another container

**Steps**:

#### Step 1: Access Tailscale Container Shell

```bash
docker exec -it addon_a0d7b954_tailscale /bin/sh
```

**Result**: You should see a shell prompt inside the Tailscale container.

#### Step 2: Enable Funnel on Port 443 (HTTPS)

```bash
# Inside Tailscale container
tailscale funnel on 443
```

**Expected Output**:
```
Funnel started and running at:
  https://a0d7b954-tailscale.ts.net/

Available commands:
  tailscale funnel <port>  - Add a port to funnel
  tailscale funnel status  - Check funnel status
  tailscale funnel off     - Stop funnel
```

**If this fails**: See troubleshooting section "Funnel Enable Fails".

#### Step 3: Configure Funnel to Forward to Music Assistant

**Option 3A: Using Tailscale Serve (Recommended)**

```bash
# Inside Tailscale container
tailscale serve https / http://music-assistant:8096
```

**Expected Output**:
```
Serving http://music-assistant:8096 at https://a0d7b954-tailscale.ts.net/
```

**What this does**:
- Public HTTPS request → `https://a0d7b954-tailscale.ts.net/[path]`
- Funnel forwards to → `http://music-assistant:8096/[path]`
- Preserves full path (health, /alexa/authorize, /alexa/token)

**Option 3B: Using Tailscale Funnel with Path Mapping**

```bash
# Inside Tailscale container
tailscale funnel on 8096
tailscale serve --bg http://music-assistant:8096
```

**Expected Output**:
```
Funnel is now serving:
  https://a0d7b954-tailscale.ts.net:8096 → http://music-assistant:8096
```

**Difference from Option 3A**:
- Uses port 8096 in public URL (non-standard HTTPS port)
- Some corporate firewalls may block port 8096
- Alexa may not accept non-443 HTTPS ports
- **Recommendation**: Use Option 3A (port 443) instead

#### Step 4: Verify Funnel Configuration

```bash
# Inside Tailscale container
tailscale funnel status
```

**Expected Output**:
```
Funnel on:
  https://a0d7b954-tailscale.ts.net/
    ↳ http://music-assistant:8096

Funnel is enabled and serving.
```

**If output differs**: Check for errors in configuration. See troubleshooting section.

#### Step 5: Exit Tailscale Container

```bash
exit
```

**Result**: You're back on the HABoxHill host shell.

### Procedure B: Configure Funnel with Reverse Proxy (If Option A Fails)

**When to use**: If Tailscale Funnel doesn't support direct container forwarding

**Alternative Approach**: Use a lightweight reverse proxy (nginx, caddy) in Tailscale container

**Steps**:

#### Step 1: Install nginx in Tailscale Container

```bash
docker exec addon_a0d7b954_tailscale /bin/sh -c "apk add nginx"
```

**Expected Output**:
```
Installing nginx...
nginx installed successfully
```

**If this fails**: Tailscale container may not have `apk` (Alpine package manager). Check container base image.

#### Step 2: Create nginx Configuration

```bash
# Create nginx config inside Tailscale container
docker exec addon_a0d7b954_tailscale /bin/sh -c "cat > /tmp/oauth-proxy.conf <<'EOF'
server {
    listen 127.0.0.1:9096;

    location / {
        proxy_pass http://music-assistant:8096;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
"
```

**What this does**:
- nginx listens on localhost:9096 (inside Tailscale container)
- Forwards all requests to music-assistant:8096
- Preserves headers for OAuth flow

#### Step 3: Start nginx

```bash
docker exec addon_a0d7b954_tailscale /bin/sh -c "nginx -c /tmp/oauth-proxy.conf"
```

**Expected Output**:
```
nginx started
```

#### Step 4: Configure Funnel to Forward to nginx

```bash
docker exec addon_a0d7b954_tailscale tailscale serve https / http://127.0.0.1:9096
docker exec addon_a0d7b954_tailscale tailscale funnel on 443
```

**Expected Output**:
```
Funnel serving https://a0d7b954-tailscale.ts.net/ → http://127.0.0.1:9096
```

**Request Flow**:
```
Internet → Tailscale Funnel → nginx:9096 → music-assistant:8096
```

#### Step 5: Verify Configuration

```bash
# Test nginx locally
docker exec addon_a0d7b954_tailscale wget -O- http://127.0.0.1:9096/health

# Test Funnel publicly (from external network)
curl https://a0d7b954-tailscale.ts.net/health
```

**Expected Output** (both commands):
```json
{"status":"ok", "message":"Music Assistant OAuth Server", ...}
```

## Testing and Verification

### Test 1: Local Health Check (Baseline)

**From HABoxHill host**:
```bash
curl http://localhost:8096/health
```

**Expected**: `{"status":"ok", ...}`
**If fails**: OAuth server not running (fix before continuing)

### Test 2: Container-to-Container (Network Verification)

**From HABoxHill host**:
```bash
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health
```

**Expected**: `{"status":"ok", ...}`
**If fails**: Docker DNS issue or network problem (see troubleshooting)

### Test 3: Funnel Status Check (Configuration Verification)

**From HABoxHill host**:
```bash
docker exec addon_a0d7b954_tailscale tailscale funnel status
```

**Expected**:
```
Funnel on:
  https://a0d7b954-tailscale.ts.net/
    ↳ http://music-assistant:8096
```

**If fails**: Funnel not configured or stopped (rerun Procedure A)

### Test 4: Public Access from Tailscale Network (Tailnet Test)

**From another device on your Tailscale network** (not HABoxHill):
```bash
curl https://a0d7b954-tailscale.ts.net/health
```

**Expected**: `{"status":"ok", ...}`
**If fails**: Funnel routing issue (see troubleshooting)

### Test 5: Public Access from Internet (Final Test)

**From a device NOT on your Tailscale network** (use mobile data, external server, etc.):
```bash
curl https://a0d7b954-tailscale.ts.net/health
```

**Expected**: `{"status":"ok", ...}`
**If fails**: Funnel may not be public-facing (check Tailscale admin settings)

**Alternative Test** (use browser):
- Open browser on external network
- Go to: `https://a0d7b954-tailscale.ts.net/health`
- Should see JSON response

### Test 6: OAuth Authorization Endpoint

**From external network**:
```bash
curl -v "https://a0d7b954-tailscale.ts.net/alexa/authorize?client_id=test&response_type=code&redirect_uri=https://example.com"
```

**Expected**:
- HTTP 200 OK or 302 Redirect (depending on OAuth implementation)
- HTML page or redirect to authorization page
- NOT: 404 Not Found, 502 Bad Gateway, Connection Refused

### Test 7: OAuth Token Endpoint

**From external network**:
```bash
curl -v -X POST https://a0d7b954-tailscale.ts.net/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=test&client_secret=test"
```

**Expected**:
- HTTP 200 OK or 401 Unauthorized (depending on credentials)
- JSON response with OAuth error or token
- NOT: 404 Not Found, 502 Bad Gateway, Connection Refused

## Persistence and Reliability

### Making Funnel Configuration Persistent

**Problem**: Tailscale Funnel configuration may reset when container restarts

**Solution 1: Auto-start Script in Tailscale Container**

```bash
# Create startup script on host
cat > /tmp/funnel-autostart.sh <<'EOF'
#!/bin/sh
# Wait for Tailscale to be ready
sleep 10

# Start Funnel and serve Music Assistant OAuth
tailscale serve https / http://music-assistant:8096
tailscale funnel on 443

echo "Tailscale Funnel configured for Music Assistant OAuth"
EOF

# Copy script into Tailscale container
docker cp /tmp/funnel-autostart.sh addon_a0d7b954_tailscale:/usr/local/bin/funnel-autostart.sh

# Make executable
docker exec addon_a0d7b954_tailscale chmod +x /usr/local/bin/funnel-autostart.sh

# Test script
docker exec addon_a0d7b954_tailscale /usr/local/bin/funnel-autostart.sh
```

**Solution 2: Systemd Service on Host** (preferred for Home Assistant OS)

```bash
# Create systemd service
sudo tee /etc/systemd/system/tailscale-funnel-oauth.service > /dev/null <<'EOF'
[Unit]
Description=Tailscale Funnel for Music Assistant OAuth
After=docker.service addon_a0d7b954_tailscale.service
Requires=docker.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/docker exec addon_a0d7b954_tailscale /bin/sh -c "tailscale serve https / http://music-assistant:8096 && tailscale funnel on 443"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable tailscale-funnel-oauth.service
sudo systemctl start tailscale-funnel-oauth.service

# Check status
sudo systemctl status tailscale-funnel-oauth.service
```

**Solution 3: Home Assistant Automation** (most HA-native approach)

**Create automation in Home Assistant**:

1. Go to Settings → Automations & Scenes → Create Automation
2. Add trigger: "When Home Assistant starts"
3. Add action: "Call service: `hassio.addon_restart`" with data: `{"addon": "addon_a0d7b954_tailscale"}`
4. Add delay: 30 seconds
5. Add action: "Shell Command" (requires shell_command integration):
   ```yaml
   service: shell_command.configure_tailscale_funnel
   ```

**Add shell command to `configuration.yaml`**:
```yaml
shell_command:
  configure_tailscale_funnel: >
    docker exec addon_a0d7b954_tailscale /bin/sh -c
    "tailscale serve https / http://music-assistant:8096 && tailscale funnel on 443"
```

**Restart Home Assistant** to load configuration.

### Monitoring Funnel Health

**Create monitoring script**:
```bash
# Save as /usr/local/bin/check-funnel-health.sh
#!/bin/bash

# Check 1: Funnel status
STATUS=$(docker exec addon_a0d7b954_tailscale tailscale funnel status 2>&1)
if echo "$STATUS" | grep -q "Funnel on"; then
    echo "✅ Funnel is running"
else
    echo "❌ Funnel is NOT running"
    echo "Attempting to restart..."
    docker exec addon_a0d7b954_tailscale tailscale serve https / http://music-assistant:8096
    docker exec addon_a0d7b954_tailscale tailscale funnel on 443
fi

# Check 2: Public endpoint reachable
if curl -sf https://a0d7b954-tailscale.ts.net/health > /dev/null; then
    echo "✅ Public endpoint is accessible"
else
    echo "❌ Public endpoint is NOT accessible"
fi

# Check 3: OAuth endpoints
for endpoint in /health /alexa/authorize /alexa/token; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://a0d7b954-tailscale.ts.net${endpoint}")
    if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 302 ]; then
        echo "✅ Endpoint ${endpoint} is responsive (HTTP ${HTTP_CODE})"
    else
        echo "❌ Endpoint ${endpoint} returned HTTP ${HTTP_CODE}"
    fi
done
```

**Make executable and schedule**:
```bash
chmod +x /usr/local/bin/check-funnel-health.sh

# Add to crontab (check every 5 minutes)
crontab -e
# Add line:
*/5 * * * * /usr/local/bin/check-funnel-health.sh >> /var/log/funnel-health.log 2>&1
```

## Troubleshooting

### Issue 1: "Funnel Enable Fails"

**Symptom**:
```bash
docker exec addon_a0d7b954_tailscale tailscale funnel on 443
# Error: Funnel is not enabled for this network
```

**Diagnosis**:
1. Check Tailscale admin console → Settings → Funnel feature
2. Verify account has Funnel enabled (free tier may not have access)

**Solutions**:
- Enable Funnel in Tailscale admin console
- Upgrade Tailscale account if needed (some plans required)
- Check Tailscale documentation for current Funnel requirements

### Issue 2: "Cannot Reach Music Assistant from Tailscale Container"

**Symptom**:
```bash
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health
# Error: wget: can't connect to remote host (172.17.0.X): Connection refused
```

**Diagnosis**:
```bash
# Check Music Assistant is running
docker ps | grep music-assistant

# Check OAuth server is listening
curl http://localhost:8096/health  # From host

# Check DNS resolution
docker exec addon_a0d7b954_tailscale nslookup music-assistant
```

**Solutions**:

**If Music Assistant not running**:
```bash
# Restart via HA UI or:
docker restart music-assistant
```

**If DNS fails**:
```bash
# Use container IP instead of DNS name
# Find IP:
docker inspect music-assistant | grep IPAddress
# Output: "IPAddress": "172.17.0.3"

# Configure Funnel with IP:
docker exec addon_a0d7b954_tailscale tailscale serve https / http://172.17.0.3:8096
```

**If connection refused**:
```bash
# Check if OAuth server module loaded in Music Assistant
docker logs music-assistant | grep -i oauth

# Restart Music Assistant to reload OAuth module
docker restart music-assistant
```

### Issue 3: "Public Endpoint Returns 502 Bad Gateway"

**Symptom**:
```bash
curl https://a0d7b954-tailscale.ts.net/health
# HTTP 502 Bad Gateway
```

**Diagnosis**:
```bash
# Check Funnel status
docker exec addon_a0d7b954_tailscale tailscale funnel status

# Check if Music Assistant reachable from Tailscale container
docker exec addon_a0d7b954_tailscale wget -O- http://music-assistant:8096/health

# Check Tailscale logs
docker logs addon_a0d7b954_tailscale | tail -50
```

**Solutions**:

**If Funnel misconfigured**:
```bash
# Reset Funnel configuration
docker exec addon_a0d7b954_tailscale tailscale funnel off
docker exec addon_a0d7b954_tailscale tailscale serve https / http://music-assistant:8096
docker exec addon_a0d7b954_tailscale tailscale funnel on 443
```

**If Music Assistant unreachable**:
```bash
# Verify Music Assistant is running
docker ps | grep music-assistant

# Restart if needed
docker restart music-assistant

# Wait 30 seconds for OAuth server to start
sleep 30

# Reconfigure Funnel
docker exec addon_a0d7b954_tailscale tailscale serve https / http://music-assistant:8096
```

### Issue 4: "Funnel Configuration Lost After Restart"

**Symptom**:
- Funnel works initially
- After Tailscale container restart, Funnel stops working
- Must manually reconfigure Funnel after every restart

**Diagnosis**:
```bash
# Check if Funnel persists across restarts
docker exec addon_a0d7b954_tailscale tailscale funnel status

# Restart container
docker restart addon_a0d7b954_tailscale

# Wait 30 seconds
sleep 30

# Check again
docker exec addon_a0d7b954_tailscale tailscale funnel status
# If output is "Funnel not running", configuration was lost
```

**Solutions**:
- Implement auto-start script (see "Persistence and Reliability" section above)
- Use systemd service to reconfigure on boot
- Use Home Assistant automation to reconfigure after restart

### Issue 5: "TLS Certificate Errors"

**Symptom**:
```bash
curl https://a0d7b954-tailscale.ts.net/health
# Error: SSL certificate problem: unable to get local issuer certificate
```

**Diagnosis**:
```bash
# Check certificate details
curl -vI https://a0d7b954-tailscale.ts.net 2>&1 | grep -E "subject|issuer|expire"

# Test with certificate validation disabled (DEBUG ONLY)
curl -k https://a0d7b954-tailscale.ts.net/health
# If this works, certificate issue confirmed
```

**Solutions**:

**If certificate expired**:
- Tailscale auto-renews certificates
- Restart Tailscale Funnel: `docker exec addon_a0d7b954_tailscale tailscale funnel off && tailscale funnel on 443`
- Contact Tailscale support if auto-renewal fails

**If certificate not trusted**:
- Tailscale uses Let's Encrypt certificates (trusted by default)
- Update system CA certificates: `sudo update-ca-certificates` (on client)
- Check if corporate proxy/firewall intercepting TLS

### Issue 6: "Alexa Cannot Reach OAuth Server"

**Symptom**:
- Manual testing works (`curl` succeeds)
- Alexa skill configuration fails with "Unable to reach authorization URL"

**Diagnosis**:
```bash
# Test from external network (not Tailscale)
curl -v https://a0d7b954-tailscale.ts.net/alexa/authorize

# Check response headers
curl -I https://a0d7b954-tailscale.ts.net/alexa/authorize

# Check if Alexa can resolve DNS
nslookup a0d7b954-tailscale.ts.net 8.8.8.8
```

**Solutions**:

**If Alexa blocked by Tailscale ACLs**:
- Check Tailscale admin console → Access Controls
- Ensure Funnel is publicly accessible (not restricted to Tailnet)
- Add rule to allow public internet access

**If Alexa requires specific headers**:
- Check Alexa documentation for required headers
- May need to modify OAuth server to include headers
- Common requirements: CORS headers, specific User-Agent handling

**If Alexa requires specific URL format**:
- Verify URL in Alexa Developer Console matches exactly
- Check for trailing slash differences (`/alexa/authorize` vs `/alexa/authorize/`)
- Ensure URL encoding is correct

### Issue 7: "High Latency on Public Endpoint"

**Symptom**:
```bash
curl -w "@curl-format.txt" https://a0d7b954-tailscale.ts.net/health
# time_total: 5.432s  (too slow!)
```

**Diagnosis**:
```bash
# Test local latency (baseline)
time curl http://localhost:8096/health
# Should be < 100ms

# Test Tailscale Funnel latency
time curl https://a0d7b954-tailscale.ts.net/health

# Check if Music Assistant is slow
docker exec music-assistant ps aux
docker stats music-assistant --no-stream
```

**Solutions**:

**If Music Assistant is slow**:
```bash
# Check resource usage
docker stats music-assistant --no-stream

# Restart if memory leak suspected
docker restart music-assistant
```

**If Tailscale Funnel routing is slow**:
- Funnel routes through Tailscale infrastructure (adds latency)
- Consider alternative: Nabu Casa proxy (direct connection)
- Check Tailscale status page for outages

**If network issue**:
```bash
# Check if HABoxHill network is slow
ping -c 10 8.8.8.8

# Check if Docker network is slow
docker exec addon_a0d7b954_tailscale ping -c 10 music-assistant
```

## Rollback Procedures

### Rollback 1: Disable Funnel Completely

**When to use**: If Funnel causing issues and need to revert to local-only access

**Steps**:
```bash
# Disable Funnel
docker exec addon_a0d7b954_tailscale tailscale funnel off

# Verify disabled
docker exec addon_a0d7b954_tailscale tailscale funnel status
# Expected: "Funnel not running"
```

**Result**: OAuth server only accessible locally (http://localhost:8096)

### Rollback 2: Reset Funnel Configuration

**When to use**: If Funnel configuration is broken and need clean slate

**Steps**:
```bash
# Stop Funnel
docker exec addon_a0d7b954_tailscale tailscale funnel off

# Clear serve configuration
docker exec addon_a0d7b954_tailscale /bin/sh -c "rm -f /var/lib/tailscale/serve-config.json"

# Restart Tailscale container
docker restart addon_a0d7b954_tailscale

# Wait for restart
sleep 30

# Reconfigure from scratch (follow Procedure A)
```

### Rollback 3: Switch to Alternative Public Endpoint

**When to use**: If Tailscale Funnel completely fails and need backup

**Alternative**: Nabu Casa Proxy (if available)

**Steps**:
1. Disable Tailscale Funnel: `docker exec addon_a0d7b954_tailscale tailscale funnel off`
2. Configure Nabu Casa nginx proxy (see ALEXA_OAUTH_SETUP_PROGRESS.md for details)
3. Update Alexa skill OAuth URLs to use Nabu Casa endpoint
4. Test OAuth flow with Nabu Casa

**Alternative**: Direct port forwarding + Dynamic DNS (NOT RECOMMENDED - security risk)

## Security Considerations

### What Funnel Exposes

**Publicly Accessible**:
- OAuth health endpoint (`/health`)
- OAuth authorization endpoint (`/alexa/authorize`)
- OAuth token endpoint (`/alexa/token`)

**NOT Exposed**:
- Music Assistant web UI (port 8095)
- Home Assistant UI (port 8123)
- Other internal services

**Access Control**:
- Funnel only forwards specific paths (/, /health, /alexa/*)
- OAuth server enforces client authentication
- TLS encryption for all public traffic

### Firewall Rules

**Tailscale Funnel Automatic Firewall Rules**:
- Allows inbound HTTPS (port 443) to Tailscale container
- Blocks all other inbound traffic
- Outbound traffic unrestricted

**Home Assistant Firewall** (if using UFW):
```bash
# Allow HTTPS for Funnel (if needed)
sudo ufw allow 443/tcp comment "Tailscale Funnel"

# Check rules
sudo ufw status verbose
```

### Logging and Auditing

**Enable Funnel Access Logging** (if supported by Tailscale):
```bash
# Check if logging available
docker exec addon_a0d7b954_tailscale tailscale funnel --help | grep log

# View Tailscale logs
docker logs addon_a0d7b954_tailscale | grep funnel
```

**Monitor OAuth Access**:
```bash
# Monitor Music Assistant OAuth logs
docker logs -f music-assistant | grep -i oauth

# Monitor for suspicious activity
docker logs music-assistant | grep -E "failed|error|unauthorized" | tail -50
```

**Set up Alerts** (optional):
```bash
# Alert on failed OAuth attempts (example with email)
docker logs music-assistant | grep "OAuth authorization failed" | mail -s "OAuth Security Alert" admin@example.com
```

## Next Steps After Configuration

### Step 1: Update Alexa Skill Configuration

**In Amazon Developer Console**:
1. Go to Alexa Skills → Your Skill → Account Linking
2. Update OAuth URLs:
   - Authorization URI: `https://a0d7b954-tailscale.ts.net/alexa/authorize`
   - Token URI: `https://a0d7b954-tailscale.ts.net/alexa/token`
3. Save and test account linking

### Step 2: Test Complete OAuth Flow

**From Alexa App**:
1. Go to Skills & Games → Your Skills → Your Skill
2. Click "Enable to Use"
3. Should redirect to authorization page
4. Approve authorization
5. Should redirect back to Alexa with success message

### Step 3: Monitor Initial Production Use

**For first 24 hours**:
```bash
# Monitor Funnel status
watch -n 60 'docker exec addon_a0d7b954_tailscale tailscale funnel status'

# Monitor OAuth access
docker logs -f music-assistant | grep -i oauth

# Monitor errors
docker logs -f addon_a0d7b954_tailscale | grep -i error
```

### Step 4: Document Final Configuration

**Update project documentation** with:
- Final public URL
- Funnel configuration details
- Any issues encountered and solutions
- Performance metrics observed

## See Also

- [HABOXHILL_NETWORK_TOPOLOGY](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md) - Infrastructure overview
- [TAILSCALE_OAUTH_ROUTING](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md) - Routing contract
- [HOME_ASSISTANT_CONTAINER_TOPOLOGY](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md) - Container reference
- [ALEXA_OAUTH_ENDPOINTS_CONTRACT](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md) - OAuth API specification
- [ALEXA_OAUTH_SETUP_PROGRESS](ALEXA_OAUTH_SETUP_PROGRESS.md) - Current implementation status
