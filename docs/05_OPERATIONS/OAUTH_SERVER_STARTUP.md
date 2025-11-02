# OAuth Server Startup and Verification
**Purpose**: Step-by-step operational procedures for deploying and verifying the OAuth server
**Audience**: System operators, deployment engineers
**Layer**: 05_OPERATIONS
**Related**:
- docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md (implementation details)
- docs/03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md (endpoint specifications)

**Date**: 2025-10-26

---

## Intent

This document provides operational procedures for starting, verifying, and troubleshooting the OAuth 2.0 authorization server that enables Alexa account linking with Music Assistant. These procedures are designed for first-time deployment, routine restarts, and operational troubleshooting.

**Time Estimate**: 10-15 minutes for complete startup and verification sequence

---

## Prerequisites

Before starting the OAuth server, verify these prerequisites are met:

### System Access
- SSH access to haboxhill.local (192.168.130.147)
- Root access to Docker host
- Network connectivity to internal services

### Container Status
```bash
# Verify Music Assistant container is running
docker ps | grep music_assistant

# Expected output:
# addon_d5369777_music_assistant  Up X hours  8095/tcp, 8096/tcp
```

### File Deployment
Verify these files exist in the container:

```bash
# Check OAuth endpoint implementation
docker exec addon_d5369777_music_assistant ls -lh /data/alexa_oauth_endpoints.py

# Check registration script
docker exec addon_d5369777_music_assistant ls -lh /data/register_oauth_routes.py

# Expected: Both files present, ~16KB and ~4KB respectively
```

---

## Step 1: SSH into Container Host

**Duration**: 1 minute

### Procedure

```bash
ssh root@haboxhill.local
```

### Verification

```bash
# You should see prompt:
root@haboxhill:~#
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Verify host is online: `ping 192.168.130.147` |
| Authentication failed | Verify SSH key or password |
| Wrong host | Verify IP address in `/etc/hosts` or DNS |

---

## Step 2: Start OAuth Server

**Duration**: 2 minutes

### Procedure

Start the OAuth server in background (daemon) mode:

```bash
docker exec -d addon_d5369777_music_assistant \
  python3 /data/register_oauth_routes.py --standalone
```

### What This Does

1. **Starts standalone web server** on port 8096 (separate from Music Assistant port 8095)
2. **Registers three endpoints**:
   - `/alexa/authorize` - Authorization request handler
   - `/alexa/token` - Token exchange and refresh handler
   - `/health` - Server health check
3. **Runs in background** (`-d` flag) - does not block terminal
4. **Logs to stdout** - viewable via `docker logs`

### Process Verification

```bash
# Check if process is running
docker exec addon_d5369777_music_assistant ps aux | grep register_oauth_routes

# Expected output (process running):
# root  1234  0.1  0.3  45678  12345  ?  Sl  12:34  0:00  python3 /data/register_oauth_routes.py --standalone
```

### Log Access

```bash
# View OAuth server logs (real-time)
docker logs -f addon_d5369777_music_assistant

# View last 50 lines
docker logs --tail 50 addon_d5369777_music_assistant

# Expected log messages:
# ======== Running on http://0.0.0.0:8096 ========
# (Press CTRL+C to quit)
```

### Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| Port already in use | Error: `Address already in use` | Stop existing process or use different port |
| Module not found | Error: `ModuleNotFoundError` | Verify file deployment in Prerequisites |
| Python version | Error: `SyntaxError` or feature errors | Verify Python 3.7+ with `python3 --version` |
| Permission denied | Error: `PermissionError` | Check file permissions: `chmod +x /data/register_oauth_routes.py` |

---

## Step 3: Health Check Verification

**Duration**: 2 minutes

### Procedure

Test the health endpoint to verify server is responding:

```bash
curl http://192.168.130.147:8096/health
```

### Expected Response

**HTTP Status**: 200 OK

**Response Body** (JSON):
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": [
    "/alexa/authorize",
    "/alexa/token",
    "/health"
  ]
}
```

### Response Validation

| Field | Expected Value | Meaning |
|-------|---------------|----------|
| `status` | `"ok"` | Server is running and healthy |
| `message` | `"Music Assistant OAuth Server"` | Correct service identifier |
| `endpoints` | Array with 3 endpoints | All OAuth endpoints registered |

### Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| Connection refused | `curl: (7) Failed to connect` | Server not started or wrong port - check Step 2 |
| Timeout | `curl: (28) Operation timed out` | Network issue or firewall blocking port 8096 |
| HTTP 404 | `404 Not Found` | Health endpoint not registered - check logs |
| HTTP 500 | `500 Internal Server Error` | Server error - check logs: `docker logs addon_d5369777_music_assistant` |
| Empty response | No JSON output | Server crashed after startup - check logs |

### Advanced Diagnostics

```bash
# Check if port is listening
docker exec addon_d5369777_music_assistant netstat -tlnp | grep 8096

# Expected output:
# tcp  0  0  0.0.0.0:8096  0.0.0.0:*  LISTEN  1234/python3

# Test from inside container
docker exec addon_d5369777_music_assistant curl http://localhost:8096/health

# Test with verbose output
curl -v http://192.168.130.147:8096/health
```

---

## Step 4: Full Endpoint Verification

**Duration**: 5 minutes

### Test Authorization Endpoint

**Purpose**: Verify OAuth authorization flow is working

```bash
curl -i 'http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=test_client&redirect_uri=http://localhost/callback&state=test_state&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256'
```

### Expected Response

**HTTP Status**: 302 Found (redirect)

**Response Headers**:
```
HTTP/1.1 302 Found
Location: http://localhost/callback?code=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX&state=test_state
Content-Length: 0
```

### Response Validation

| Component | Expected | Meaning |
|-----------|----------|---------|
| Status Code | `302` | Authorization succeeded, redirecting |
| Location header | Present | Contains redirect URL |
| `code` parameter | 43-character string | Authorization code generated |
| `state` parameter | `test_state` | State echoed back (CSRF protection) |

### Test Token Endpoint

**Purpose**: Verify token exchange is working

**Step 1**: Extract authorization code from previous response:
```bash
# From Location header, copy the value after "code="
# Example: abc123def456...xyz
```

**Step 2**: Exchange code for access token:
```bash
curl -X POST 'http://192.168.130.147:8096/alexa/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=authorization_code' \
  -d 'code=YOUR_CODE_HERE' \
  -d 'redirect_uri=http://localhost/callback' \
  -d 'client_id=test_client' \
  -d 'code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'
```

### Expected Token Response

**HTTP Status**: 200 OK

**Response Body** (JSON):
```json
{
  "access_token": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",
  "scope": "music.read music.control"
}
```

### Troubleshooting Endpoints

| Issue | HTTP Status | Solution |
|-------|-------------|----------|
| Missing required parameter | 400 Bad Request | Check all required parameters present |
| Invalid code | 400 Bad Request | Code may be expired (5min lifetime) or already used |
| PKCE validation failed | 400 Bad Request | Verify code_verifier matches code_challenge |
| Invalid grant_type | 400 Bad Request | Must be `authorization_code` or `refresh_token` |
| Server error | 500 Internal Server Error | Check logs for Python exceptions |

### Common Error Responses

**Missing Parameter**:
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: client_id"
}
```

**Invalid Code**:
```json
{
  "error": "invalid_grant",
  "error_description": "Invalid or expired authorization code"
}
```

**PKCE Failure**:
```json
{
  "error": "invalid_grant",
  "error_description": "Invalid code_verifier"
}
```

---

## Verification Checklist

Use this checklist to confirm successful deployment:

- [ ] **SSH Connection**: Successfully connected to haboxhill.local
- [ ] **Container Running**: Music Assistant container status is "Up"
- [ ] **Files Deployed**: Both Python files present in `/data/`
- [ ] **Server Started**: OAuth server process running (visible in `ps aux`)
- [ ] **Port Listening**: Port 8096 shows in `netstat` output
- [ ] **Health Check**: `/health` returns HTTP 200 with valid JSON
- [ ] **Endpoints Listed**: All three endpoints in health response
- [ ] **Authorization Works**: `/alexa/authorize` returns 302 redirect
- [ ] **Code Generated**: Authorization code present in Location header
- [ ] **Token Exchange Works**: `/alexa/token` returns access token
- [ ] **Internal Access**: Server accessible from container host
- [ ] **Network Access**: Server accessible from your workstation

---

## Operational Status Monitoring

### Quick Status Check

```bash
# One-command health check
curl -s http://192.168.130.147:8096/health | python3 -m json.tool
```

### Expected Uptime Behavior

**Normal Operation**:
- Server starts in < 2 seconds
- Health checks respond in < 100ms
- Authorization requests complete in < 200ms
- Token exchanges complete in < 300ms

**Resource Usage** (typical):
- Memory: ~50-100 MB
- CPU: < 1% idle, < 5% under load
- Network: Minimal (only responds to requests)

### Restart Procedure

If server needs to be restarted:

```bash
# 1. Find the process ID
docker exec addon_d5369777_music_assistant ps aux | grep register_oauth_routes

# 2. Kill the process
docker exec addon_d5369777_music_assistant kill <PID>

# 3. Wait 2 seconds for cleanup
sleep 2

# 4. Start new instance (same command as Step 2)
docker exec -d addon_d5369777_music_assistant \
  python3 /data/register_oauth_routes.py --standalone

# 5. Verify with health check
curl http://192.168.130.147:8096/health
```

---

## Next Steps

After successful OAuth server deployment and verification:

### 1. Configure Public HTTPS Access

The OAuth server is currently only accessible on the internal network (192.168.130.147). For Alexa integration, you need public HTTPS endpoints.

**Options**:
- **Tailscale Funnel** (recommended): See docs/05_OPERATIONS/TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md
- **Cloudflare Tunnel**: Alternative public access method
- **Reverse Proxy**: nginx or Apache with Let's Encrypt SSL

### 2. Create Alexa Skill

Once public HTTPS endpoints are available:
1. Register Amazon Developer account
2. Create new Alexa Skill in developer console
3. Configure account linking with OAuth endpoints
4. Create Lambda function for intent handling
5. Test account linking flow

### 3. Test with Echo Device

After Alexa Skill is configured:
1. Enable skill for testing in Alexa Developer Console
2. Link account in Alexa mobile app
3. Test voice commands with Echo Dot 5th gen
4. Verify OAuth tokens in server logs

---

## Emergency Procedures

### Server Won't Start

**Symptom**: Process exits immediately after starting

**Diagnosis**:
```bash
# Run in foreground to see errors
docker exec -it addon_d5369777_music_assistant \
  python3 /data/register_oauth_routes.py --standalone

# Check for Python syntax errors or import failures
```

**Common Causes**:
- Python version incompatibility (requires 3.7+)
- Missing dependencies (asyncio, aiohttp)
- File corruption during deployment
- Port already in use

**Resolution**:
1. Check Python version: `docker exec addon_d5369777_music_assistant python3 --version`
2. Re-deploy files from source
3. Change port if 8096 is occupied (edit script)
4. Review full error traceback in logs

### Server Stops Responding

**Symptom**: Health checks fail after working previously

**Diagnosis**:
```bash
# Check if process is still running
docker exec addon_d5369777_music_assistant ps aux | grep register_oauth_routes

# Check container logs for crashes
docker logs --tail 100 addon_d5369777_music_assistant
```

**Common Causes**:
- Container restarted (process not auto-started)
- Memory exhaustion (OOM killer)
- Unhandled exception crashed server
- Network connectivity lost

**Resolution**:
1. Restart server using restart procedure above
2. Check container resources: `docker stats addon_d5369777_music_assistant`
3. Review logs for Python exceptions
4. Consider adding systemd service for auto-restart

### Authorization Codes Not Working

**Symptom**: Token exchange returns "invalid_grant"

**Diagnosis**:
```bash
# Check server logs during token exchange
docker logs -f addon_d5369777_music_assistant

# Look for:
# - Code expiration messages
# - PKCE validation failures
# - Code already used errors
```

**Common Causes**:
- Authorization code expired (5-minute lifetime)
- Code already exchanged (one-time use)
- PKCE code_verifier doesn't match code_challenge
- Server restarted (in-memory storage cleared)

**Resolution**:
1. Generate fresh authorization code
2. Exchange within 5 minutes of generation
3. Verify PKCE parameters match exactly
4. For production, implement persistent storage (Redis)

---

## See Also

**Architecture & Design**:
- docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md - Technical implementation details
- docs/00_ARCHITECTURE/OAUTH_SECURITY_PRINCIPLES.md - Security architecture

**Contracts & Specifications**:
- docs/03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md - Endpoint specifications
- docs/02_REFERENCE/OAUTH_RFC_7636_PKCE.md - PKCE standard reference

**Related Operations**:
- docs/05_OPERATIONS/TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md - Public HTTPS exposure
- docs/05_OPERATIONS/CONTAINER_MANAGEMENT.md - Docker container operations
- docs/05_OPERATIONS/TROUBLESHOOTING_GUIDE.md - General troubleshooting

**Implementation Files**:
- `/data/alexa_oauth_endpoints.py` (container) - OAuth endpoint implementation
- `/data/register_oauth_routes.py` (container) - Route registration and standalone server
