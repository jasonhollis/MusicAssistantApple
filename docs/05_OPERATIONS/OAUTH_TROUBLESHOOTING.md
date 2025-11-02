# OAuth Server Troubleshooting Guide
**Purpose**: Operational procedures for diagnosing and resolving OAuth server issues
**Audience**: DevOps engineers, system administrators, on-call support
**Layer**: 05_OPERATIONS
**Related**: [04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md](../04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md)

## Intent

This guide provides step-by-step procedures for diagnosing and resolving common OAuth server issues in production. It covers server crashes, authentication failures, and integration problems.

## Quick Diagnostic Commands

### Check Server Status

**Verify OAuth server is running**:
```bash
# On haboxhill.local
docker exec addon_d5369777_music_assistant ps aux | grep oauth

# Expected output:
# python3 /data/start_oauth_server.py
```

**Health check endpoint**:
```bash
curl http://192.168.130.147:8096/health

# Expected response:
# {"status": "ok", "message": "Music Assistant OAuth Server"}
```

**Check from internet (via reverse proxy)**:
```bash
curl https://dev.jasonhollis.com/health

# Expected: Same as above (proxied through nginx)
```

### Check Logs

**OAuth debug log**:
```bash
docker exec addon_d5369777_music_assistant cat /data/oauth_debug.log

# Shows: Authorization requests, token exchanges, timestamps
```

**OAuth server output**:
```bash
docker exec addon_d5369777_music_assistant cat /data/oauth_output.log

# Shows: Python stdout/stderr, server startup, errors
```

**Music Assistant logs**:
```bash
docker logs addon_d5369777_music_assistant | tail -50

# Shows: General addon logs (if OAuth integrated)
```

**Real-time monitoring**:
```bash
# Watch OAuth debug log live
docker exec addon_d5369777_music_assistant tail -f /data/oauth_debug.log
```

## Common Issues and Solutions

### Issue 1: Server Crashes on Startup

**Symptoms**:
- OAuth server starts but immediately exits
- No output in oauth_output.log
- Health check returns connection refused

**Diagnostic Steps**:

**1. Check for Python errors**:
```bash
# Run in foreground to see errors
docker exec -it addon_d5369777_music_assistant \
  python3 /data/start_oauth_server.py

# Watch for import errors, syntax errors
```

**2. Verify dependencies installed**:
```bash
docker exec addon_d5369777_music_assistant sh -c "
  source /app/venv/bin/activate
  python3 -c 'import aiohttp; import cryptography; print(\"Dependencies OK\")'
"

# Expected output: "Dependencies OK"
# If error: Missing dependency
```

**3. Check Python version**:
```bash
docker exec addon_d5369777_music_assistant python3 --version

# Expected: Python 3.11 or higher
```

**Solutions**:

**Missing dependencies**:
```bash
docker exec addon_d5369777_music_assistant sh -c "
  source /app/venv/bin/activate
  pip install aiohttp cryptography
"

# Then restart OAuth server
```

**Syntax errors in code**:
```bash
# Validate Python syntax
docker exec addon_d5369777_music_assistant \
  python3 -m py_compile /data/alexa_oauth_endpoints.py

# If errors: Re-deploy clean version from source
scp alexa_oauth_endpoints.py jason@haboxhill.local:/tmp/
ssh jason@haboxhill.local
docker cp /tmp/alexa_oauth_endpoints.py addon_d5369777_music_assistant:/data/
```

**Port already in use**:
```bash
# Check if port 8096 occupied
docker exec addon_d5369777_music_assistant netstat -tlnp | grep 8096

# If occupied: Kill existing process or use different port
docker exec addon_d5369777_music_assistant pkill -f start_oauth_server
```

---

### Issue 2: 502 Bad Gateway from Reverse Proxy

**Symptoms**:
- https://dev.jasonhollis.com/alexa/authorize returns 502
- nginx error log shows "Connection refused"
- OAuth server not running or not listening on port 8096

**Diagnostic Steps**:

**1. Verify OAuth server listening**:
```bash
docker exec addon_d5369777_music_assistant netstat -tlnp | grep 8096

# Expected output:
# tcp 0 0 0.0.0.0:8096 0.0.0.0:* LISTEN 1234/python3
```

**2. Test from haboxhill.local**:
```bash
ssh jason@haboxhill.local
curl http://localhost:8096/health

# Should return: {"status": "ok", ...}
```

**3. Test from Sydney server**:
```bash
# On Sydney server
curl http://haboxhill.local:8096/health

# Should return: {"status": "ok", ...}
# If connection refused: Network issue or firewall
```

**4. Check nginx error log**:
```bash
# On Sydney server
sudo tail -50 /var/log/nginx/error.log | grep alexa

# Look for: "connect() failed (111: Connection refused)"
```

**Solutions**:

**OAuth server not running**:
```bash
# Start OAuth server
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"

# Verify started
curl http://haboxhill.local:8096/health
```

**Wrong port in nginx config**:
```bash
# On Sydney server
sudo nano /etc/nginx/sites-available/jasonhollis-dev

# Verify proxy_pass points to correct port
location /alexa/ {
    proxy_pass http://haboxhill.local:8096/alexa/;  # Correct
    # NOT: http://haboxhill.local:8095/alexa/     # Wrong
}

# Reload nginx
sudo nginx -t && sudo systemctl reload nginx
```

**Firewall blocking port**:
```bash
# On haboxhill.local
ssh jason@haboxhill.local
sudo iptables -L -n | grep 8096

# If blocked: Add firewall rule (usually not needed on internal network)
```

---

### Issue 3: "redirect_uri mismatch" Error

**Symptoms**:
- Alexa account linking fails
- Token endpoint returns: `"redirect_uri does not match authorization request"`
- User sees "Unable to link the skill at this time"

**Diagnostic Steps**:

**1. Check Alexa's redirect URI in logs**:
```bash
docker exec addon_d5369777_music_assistant cat /data/oauth_debug.log | grep redirect_uri

# Look for Alexa's actual redirect_uri
# Example: "redirect_uri": "https://layla.amazon.com/api/skill/link/MKXZK47785HJ2"
```

**2. Check registered redirect URIs**:
```bash
docker exec addon_d5369777_music_assistant cat /data/oauth_clients.json

# Verify Alexa's redirect_uri is in the list
```

**3. Compare authorization vs token request**:
```bash
# Find both requests in debug log
docker exec addon_d5369777_music_assistant grep -A 10 "AUTHORIZE ENDPOINT" /data/oauth_debug.log
docker exec addon_d5369777_music_assistant grep -A 10 "TOKEN REQUEST" /data/oauth_debug.log

# redirect_uri must be IDENTICAL (exact byte-for-byte match)
```

**Solutions**:

**Add missing redirect URI**:
```bash
# Edit oauth_clients.json
docker exec -it addon_d5369777_music_assistant nano /data/oauth_clients.json

# Add Alexa's redirect URI to the array:
{
  "amazon-alexa": {
    "client_type": "public",
    "redirect_uris": [
      "https://pitangui.amazon.com/auth/o2/callback",
      "https://layla.amazon.com/api/skill/link/MKXZK47785HJ2",
      "https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2",
      "https://NEW_REDIRECT_URI_HERE"  # Add this line
    ]
  }
}

# Restart OAuth server to reload config
docker exec addon_d5369777_music_assistant pkill -f start_oauth_server
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"
```

**Remove oauth_clients.json to use defaults**:
```bash
# If config file corrupted, delete it to use code defaults
docker exec addon_d5369777_music_assistant rm /data/oauth_clients.json

# Restart OAuth server
docker exec addon_d5369777_music_assistant pkill -f start_oauth_server
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"

# Default redirect URIs will be used
```

---

### Issue 4: "PKCE verification failed" Error

**Symptoms**:
- Token endpoint returns: `"PKCE verification failed: code_verifier does not match code_challenge"`
- Alexa account linking fails at final step
- Authorization code generated successfully, but token exchange fails

**Diagnostic Steps**:

**1. Extract PKCE parameters from logs**:
```bash
docker exec addon_d5369777_music_assistant grep -A 20 "AUTHORIZE ENDPOINT" /data/oauth_debug.log | grep code_challenge

# Example output:
# "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
```

```bash
docker exec addon_d5369777_music_assistant grep -A 20 "TOKEN REQUEST" /data/oauth_debug.log | grep code_verifier

# Example output:
# "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
```

**2. Manually verify PKCE hash**:
```bash
# On your Mac (has Python)
python3 << 'EOF'
import hashlib
import base64

# From logs above
code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

# Compute challenge
digest = hashlib.sha256(code_verifier.encode()).digest()
computed_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

print(f"Expected:  {expected_challenge}")
print(f"Computed:  {computed_challenge}")
print(f"Match:     {computed_challenge == expected_challenge}")
EOF

# If mismatch: PKCE implementation bug
```

**Solutions**:

**PKCE hash function incorrect**:
```python
# Verify hash_code_verifier() in alexa_oauth_endpoints.py
def hash_code_verifier(verifier: str) -> str:
    """MUST use SHA-256 and URL-safe base64 without padding."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')

# Ensure:
# 1. Using SHA-256 (not SHA-1 or MD5)
# 2. Using urlsafe_b64encode (not standard b64encode)
# 3. Stripping '=' padding with .rstrip('=')
```

**Code challenge stored incorrectly**:
```bash
# Check authorization code metadata
docker exec -it addon_d5369777_music_assistant python3 << 'EOF'
import sys
sys.path.insert(0, '/data')
from alexa_oauth_endpoints import auth_codes

# Print all authorization codes and their metadata
for code, data in auth_codes.items():
    print(f"Code: {code[:20]}...")
    print(f"  code_challenge: {data.get('code_challenge')}")
    print(f"  client_id: {data['client_id']}")
    print()
EOF

# If code_challenge is None: Authorization endpoint not storing it
```

---

### Issue 5: Authorization Code Expired

**Symptoms**:
- Token endpoint returns: `"Authorization code has expired"`
- User approved authorization but waited >5 minutes
- Alexa shows "Account linking failed"

**Diagnostic Steps**:

**1. Check authorization code timestamps**:
```bash
docker exec -it addon_d5369777_music_assistant python3 << 'EOF'
import sys
import time
sys.path.insert(0, '/data')
from alexa_oauth_endpoints import auth_codes

now = time.time()

for code, data in auth_codes.items():
    expires_at = data['expires_at']
    age_seconds = now - (expires_at - 300)  # 300 = 5 minute lifetime
    print(f"Code: {code[:20]}...")
    print(f"  Age: {age_seconds:.1f} seconds")
    print(f"  Expires in: {expires_at - now:.1f} seconds")
    print(f"  Expired: {now > expires_at}")
    print()
EOF
```

**2. Check for clock skew**:
```bash
# On haboxhill.local
docker exec addon_d5369777_music_assistant date +"%Y-%m-%d %H:%M:%S %Z"

# On your Mac
date +"%Y-%m-%d %H:%M:%S %Z"

# Times should be within ~1 second
# If >5 minutes difference: Clock skew issue
```

**Solutions**:

**User took too long**:
- **Not a bug**: This is expected behavior
- User must complete linking within 5 minutes
- Tell user to retry: "Please try again and complete within 5 minutes"

**Clock skew between servers**:
```bash
# On haboxhill.local
ssh jason@haboxhill.local
sudo systemctl restart systemd-timesyncd
sudo timedatectl set-ntp true

# Verify time synced
timedatectl status | grep "NTP synchronized"
# Should show: "NTP synchronized: yes"
```

**Increase code lifetime (NOT RECOMMENDED)**:
```python
# Only if absolutely necessary (reduces security)
# In alexa_oauth_endpoints.py:
AUTH_CODE_EXPIRY = 600  # 10 minutes (was 300)

# Restart OAuth server after change
```

---

### Issue 6: Client Validation Failed

**Symptoms**:
- Token endpoint returns: `"Client authentication failed (invalid client_id)"`
- Authorization works but token exchange fails
- Logs show: `"client_id 'amazon-alexa' NOT FOUND in config"`

**Diagnostic Steps**:

**1. Check client configuration**:
```bash
docker exec addon_d5369777_music_assistant cat /data/oauth_clients.json

# Verify amazon-alexa entry exists
# Verify client_type is "public" (not "confidential")
```

**2. Check client_id in requests**:
```bash
docker exec addon_d5369777_music_assistant grep -A 10 "AUTHORIZE ENDPOINT" /data/oauth_debug.log | grep client_id
docker exec addon_d5369777_music_assistant grep -A 10 "TOKEN REQUEST" /data/oauth_debug.log | grep client_id

# client_id MUST be exactly "amazon-alexa" (case-sensitive)
```

**3. Test client validation directly**:
```bash
docker exec -it addon_d5369777_music_assistant python3 << 'EOF'
import sys
sys.path.insert(0, '/data')
from alexa_oauth_endpoints import validate_client, load_oauth_clients

# Load config
clients = load_oauth_clients()
print(f"Registered clients: {list(clients.keys())}")

# Test validation
result = validate_client('amazon-alexa', None)
print(f"validate_client('amazon-alexa', None) = {result}")
EOF

# Expected output:
# Registered clients: ['amazon-alexa']
# validate_client('amazon-alexa', None) = True
```

**Solutions**:

**Missing oauth_clients.json**:
```bash
# Create default configuration
docker exec -it addon_d5369777_music_assistant tee /data/oauth_clients.json << 'EOF'
{
  "amazon-alexa": {
    "client_type": "public",
    "redirect_uris": [
      "https://pitangui.amazon.com/auth/o2/callback",
      "https://layla.amazon.com/api/skill/link/MKXZK47785HJ2",
      "https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2"
    ]
  }
}
EOF

# Restart OAuth server
docker exec addon_d5369777_music_assistant pkill -f start_oauth_server
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"
```

**Wrong client_type**:
```bash
# Edit oauth_clients.json
docker exec -it addon_d5369777_music_assistant nano /data/oauth_clients.json

# Change:
"client_type": "confidential"   # WRONG - requires client_secret

# To:
"client_type": "public"         # CORRECT - uses PKCE instead

# Save and restart OAuth server
```

---

### Issue 7: User Sees "Unable to link the skill at this time"

**Symptoms**:
- Generic error message in Alexa app
- No specific error details shown to user
- Account linking fails but unclear why

**Diagnostic Steps**:

**1. Check OAuth debug log for actual error**:
```bash
docker exec addon_d5369777_music_assistant tail -100 /data/oauth_debug.log

# Look for most recent error response
# Example: "invalid_grant", "redirect_uri mismatch", etc.
```

**2. Check Alexa app logs (if accessible)**:
```
On iPhone:
- Settings → Privacy → Analytics → Analytics Data
- Search for: com.amazon.echo
- Look for recent crash logs or error messages
```

**3. Trace full authorization flow**:
```bash
# Find authorization request
docker exec addon_d5369777_music_assistant grep -A 20 "AUTHORIZE ENDPOINT" /data/oauth_debug.log | tail -25

# Find approval
docker exec addon_d5369777_music_assistant grep -A 20 "CONSENT APPROVAL" /data/oauth_debug.log | tail -25

# Find token exchange
docker exec addon_d5369777_music_assistant grep -A 20 "TOKEN REQUEST" /data/oauth_debug.log | tail -25

# Identify where flow breaks
```

**Solutions**:

- **See specific issue sections above** based on error found in logs
- **Generic retry**: "Close Alexa app completely, reopen, try again"
- **Clear Alexa app cache** (iOS): Uninstall → Reinstall Alexa app
- **Check Amazon status**: https://status.aws.amazon.com/ (Alexa services)

---

## Monitoring and Alerting

### Health Check Monitoring

**Setup health check monitoring**:
```bash
# On Sydney server (or monitoring server)
# Add to cron: */5 * * * * (every 5 minutes)

#!/bin/bash
HEALTH_URL="https://dev.jasonhollis.com/health"
ALERT_EMAIL="admin@example.com"

if ! curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo "OAuth server health check failed" | \
      mail -s "ALERT: OAuth Server Down" "$ALERT_EMAIL"
fi
```

### Log File Size Monitoring

**Prevent log files from growing too large**:
```bash
# Add to cron (daily at 2am)
# 0 2 * * * /usr/local/bin/rotate_oauth_logs.sh

#!/bin/bash
# rotate_oauth_logs.sh

MAX_SIZE_MB=100

for log in /data/oauth_debug.log /data/oauth_output.log; do
  docker exec addon_d5369777_music_assistant sh -c "
    SIZE=\$(stat -f%z '$log' 2>/dev/null || echo 0)
    SIZE_MB=\$((SIZE / 1024 / 1024))

    if [ \$SIZE_MB -gt $MAX_SIZE_MB ]; then
      mv '$log' '$log.old'
      echo 'Log rotated at \$(date)' > '$log'
    fi
  "
done
```

### Performance Monitoring

**Track token issuance rate**:
```bash
# Count tokens issued per hour
docker exec addon_d5369777_music_assistant sh -c "
  grep 'access_token' /data/oauth_debug.log | \
  tail -100 | \
  wc -l
"

# High rate (>100/hour): Possible abuse or attack
# Zero rate: Server not working or no users
```

## Emergency Procedures

### Emergency: OAuth Server Completely Down

**Impact**: Users cannot link Alexa accounts

**Immediate Actions**:

**1. Restart OAuth server**:
```bash
docker exec addon_d5369777_music_assistant pkill -f start_oauth_server
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"

# Wait 5 seconds
sleep 5

# Verify running
curl http://haboxhill.local:8096/health
```

**2. If restart fails, redeploy from source**:
```bash
# On your Mac
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

scp alexa_oauth_endpoints.py jason@haboxhill.local:/tmp/
ssh jason@haboxhill.local

docker cp /tmp/alexa_oauth_endpoints.py addon_d5369777_music_assistant:/data/
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"
```

**3. If Music Assistant container died**:
```bash
# On haboxhill.local
ssh jason@haboxhill.local
ha addons restart d5369777_music_assistant

# Wait for restart (30-60 seconds)
sleep 60

# Restart OAuth server
docker exec -d addon_d5369777_music_assistant \
  sh -c "python3 /data/start_oauth_server.py > /data/oauth_output.log 2>&1"
```

### Emergency: All Tokens Invalid After Restart

**Impact**: All linked Alexa accounts broken

**Cause**: In-memory token storage lost on server restart

**Immediate Actions**:

**1. Notify users**:
- Post announcement: "Please re-link your Alexa account"
- Provide linking instructions

**2. Implement persistent storage** (long-term fix):
```python
# See 04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md
# Migrate to Music Assistant config storage (persists across restarts)
```

### Emergency: Suspected Security Breach

**Symptoms**: Unexpected token generation, strange IP addresses, suspicious activity

**Immediate Actions**:

**1. Revoke all tokens**:
```bash
docker exec -it addon_d5369777_music_assistant python3 << 'EOF'
import sys
sys.path.insert(0, '/data')
from alexa_oauth_endpoints import tokens, auth_codes, pending_auth_codes

# Clear all active sessions
tokens.clear()
auth_codes.clear()
pending_auth_codes.clear()

print("All tokens and codes revoked")
EOF

# All users must re-link
```

**2. Check logs for attack patterns**:
```bash
# Look for repeated failed attempts (brute force)
docker exec addon_d5369777_music_assistant grep "invalid_" /data/oauth_debug.log | wc -l

# Look for requests from unusual IPs
docker exec addon_d5369777_music_assistant grep "remote_addr" /data/oauth_debug.log | \
  grep -v "54.240" | grep -v "52.94" | grep -v "99.77"  # Not Amazon IPs
```

**3. Implement rate limiting** (prevent future attacks):
```python
# Add to alexa_oauth_endpoints.py
from collections import defaultdict
from time import time

# Track failed attempts per IP
failed_attempts = defaultdict(list)
RATE_LIMIT = 10  # Max 10 attempts per hour

async def check_rate_limit(ip: str) -> bool:
    now = time()
    attempts = failed_attempts[ip]

    # Remove attempts older than 1 hour
    attempts[:] = [t for t in attempts if now - t < 3600]

    if len(attempts) >= RATE_LIMIT:
        return False  # Rate limit exceeded

    return True
```

## Validation Checklist

After resolving any issue, verify full OAuth flow:

**Authorization Flow**:
- [ ] Navigate to https://dev.jasonhollis.com/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=https://pitangui.amazon.com/auth/o2/callback&state=test123
- [ ] Verify consent screen appears
- [ ] Verify "Approve & Link Account" button visible
- [ ] Click approve
- [ ] Verify redirects to redirect_uri with code parameter

**Token Exchange Flow**:
- [ ] Extract authorization code from redirect
- [ ] POST to /alexa/token with grant_type=authorization_code
- [ ] Verify response contains access_token, refresh_token, expires_in
- [ ] Verify token_type is "Bearer"
- [ ] Verify scope matches requested scope

**End-to-End Test (Alexa App)**:
- [ ] Open Alexa app on mobile device
- [ ] Navigate to Music Assistant skill
- [ ] Tap "Link Account"
- [ ] Approve authorization
- [ ] Verify "Account Successfully Linked" message
- [ ] Test voice command: "Alexa, play music on Music Assistant"

## Common Diagnostic Patterns

### Pattern: Silent Failures

**Symptom**: No error messages, nothing in logs, process just exits

**Likely Causes**:
1. Import errors before logging starts
2. Syntax errors in Python code
3. Segmentation faults (rare)

**Diagnostic**:
```bash
# Run in foreground with Python -v (verbose imports)
docker exec -it addon_d5369777_music_assistant python3 -v /data/start_oauth_server.py
```

### Pattern: Intermittent Failures

**Symptom**: Works sometimes, fails other times

**Likely Causes**:
1. Race conditions (concurrent requests)
2. Expiring tokens/codes (timing issue)
3. Clock skew
4. Network timeouts

**Diagnostic**:
```bash
# Enable Python warnings
docker exec -it addon_d5369777_music_assistant \
  python3 -W all /data/start_oauth_server.py

# Check NTP sync
docker exec addon_d5369777_music_assistant timedatectl status
```

### Pattern: Works Locally, Fails Through Reverse Proxy

**Likely Causes**:
1. Reverse proxy stripping headers
2. SSL termination issues
3. Timeout too short
4. URL rewriting breaking paths

**Diagnostic**:
```bash
# Compare headers
curl -v http://localhost:8096/health  # Direct
curl -v https://dev.jasonhollis.com/health  # Proxied

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

## See Also

- **[04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md](../04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md)** - Implementation details
- **[03_INTERFACES/OAUTH_ENDPOINTS.md](../03_INTERFACES/OAUTH_ENDPOINTS.md)** - API specifications
- **[05_OPERATIONS/OAUTH_DEPLOYMENT.md](../05_OPERATIONS/OAUTH_DEPLOYMENT.md)** - Deployment procedures
