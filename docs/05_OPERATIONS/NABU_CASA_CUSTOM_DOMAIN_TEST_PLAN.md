# Nabu Casa Custom Domain Port 8096 Testing Plan
**Purpose**: Validate if Nabu Casa custom domain routing supports non-standard ports (8096) for Music Assistant OAuth exposure
**Audience**: System administrator testing Nabu Casa custom domain configuration
**Layer**: 05_OPERATIONS
**Related**:
- [Nabu Casa vs Tailscale Decision Tree](NABU_CASA_VS_TAILSCALE_DECISION_TREE.md)
- [Nabu Casa Port Routing Architecture](../02_REFERENCE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md)
- [Alexa OAuth Setup Progress](ALEXA_OAUTH_SETUP_PROGRESS.md)

---

## Intent

Test whether Nabu Casa's custom domain feature can route HTTPS requests to Music Assistant's OAuth server running on non-standard port 8096 inside Home Assistant. This test determines the viability of using Nabu Casa for Alexa Skill OAuth integration without additional reverse proxy configuration.

---

## Current Status

### Configuration Completed
- **Custom domain**: `boxhillsouth.jasonhollis.com`
- **Target**: `0gdzommh4w1tug2s97xnn9spylzmkkbs.ui.nabu.casa` (Nabu Casa proxy)
- **DNS propagation**: Complete (verified CNAME resolution)
- **Home Assistant status**: REBOOTING (SSL certificate generation in progress)

### Expected Boot Timeline
| Phase | Duration | Status |
|-------|----------|--------|
| HA Core restart | 2-3 minutes | In progress |
| SSL certificate generation | 1-2 minutes | Pending |
| Container services startup | 1-2 minutes | Pending |
| **Total expected wait** | **5-7 minutes** | Est. ready by 18:50 |

### Music Assistant OAuth Server
- **Container**: `music-assistant`
- **Internal port**: 8096
- **OAuth endpoints**:
  - Authorization: `http://music-assistant:8096/authorize`
  - Token: `http://music-assistant:8096/token`
  - User info: `http://music-assistant:8096/userinfo`
- **Status**: Will auto-start with HA (if configured in `configuration.yaml`)

---

## Critical Unknown: Port 8096 Routing

### What We're Testing

**Question**: Does Nabu Casa custom domain routing support arbitrary ports (8096)?

**Known behavior**:
- Nabu Casa proxies standard port 8123 (HA web UI) → Works perfectly
- Custom domains alias to `*.ui.nabu.casa` proxy endpoint
- Nabu Casa uses nginx reverse proxy (configuration not publicly exposed)

**Unknown behavior**:
- Can we access port 8096 via custom domain?
- Does Nabu Casa proxy forward port-specific requests?
- Is port routing configurable in Nabu Casa UI?

### Why This Matters

**If port 8096 works**:
- ✅ Nabu Casa is sufficient for Alexa OAuth (no additional config)
- ✅ Implementation time: ~5 minutes
- ✅ Zero maintenance burden
- ✅ Community funding continues ($6.50/month well-spent)

**If port 8096 blocked**:
- ⚠️ Need reverse proxy within HA (nginx/Caddy add-on)
- ⚠️ OR fallback to Tailscale Funnel approach
- ⚠️ Implementation time: 15-20 minutes
- ⚠️ Additional configuration complexity

---

## Test Procedures

### Prerequisites
Wait for Home Assistant to complete reboot and SSL certificate generation (~5-7 minutes from 18:44).

**Verification Commands** (run from Mac terminal):
```bash
# 1. Check if HA is responding
curl -I https://boxhillsouth.jasonhollis.com/

# Expected: 200 OK (or 401 Unauthorized if auth required)
# If timeout/connection refused: HA still booting, wait 2 more minutes
```

---

### Test 1: Standard Port 8123 Verification (Baseline)

**Purpose**: Confirm custom domain routing works for standard HA port

**Command**:
```bash
curl -I https://boxhillsouth.jasonhollis.com/

# OR in browser
open https://boxhillsouth.jasonhollis.com/
```

**Expected Result**:
- **Status**: 200 OK (or 401 Unauthorized)
- **Headers**: `Server: nginx` (Nabu Casa proxy)
- **SSL**: Valid certificate for `boxhillsouth.jasonhollis.com`

**What This Confirms**:
- ✅ DNS resolution working
- ✅ Nabu Casa proxy forwarding to HA instance
- ✅ SSL certificate generated and applied
- ✅ Custom domain routing functional for port 8123

**If This Fails**:
- Check DNS propagation: `dig boxhillsouth.jasonhollis.com CNAME`
- Wait 2 more minutes for HA boot completion
- Check Nabu Casa dashboard for connection status

---

### Test 2: Music Assistant OAuth Port 8096 (Critical Test)

**Purpose**: Test if custom domain can route to non-standard port 8096

**Attempt A: Direct Port Specification**
```bash
curl -I https://boxhillsouth.jasonhollis.com:8096/authorize

# Expected outcomes:
# - Success: 200/401 response from OAuth server
# - Failure: Connection refused, timeout, or 502 Bad Gateway
```

**Attempt B: Path-Based Routing (If Nabu Casa supports it)**
```bash
curl -I https://boxhillsouth.jasonhollis.com/api/music_assistant/authorize

# Some proxies map paths to internal ports
# Expected: 404 if not configured (most likely)
```

**Attempt C: Query Parameter Port Hint**
```bash
curl -I https://boxhillsouth.jasonhollis.com/authorize?port=8096

# Very unlikely to work, but worth testing
```

**Interpretation**:

| Result | Meaning | Next Action |
|--------|---------|-------------|
| **200/401 on :8096** | ✅ Port routing works! | Proceed with Nabu Casa implementation |
| **Connection refused** | ❌ Port blocked by proxy | Implement reverse proxy OR Tailscale |
| **502 Bad Gateway** | ⚠️ Proxy forwards but target unreachable | Check Music Assistant OAuth server status |
| **Timeout** | ❌ Firewall blocking non-standard port | Implement reverse proxy OR Tailscale |
| **SSL error on :8096** | ❌ Certificate not valid for port | Implement reverse proxy OR Tailscale |

---

### Test 3: Internal Connectivity Verification (Fallback Diagnosis)

**Purpose**: If Test 2 fails, verify Music Assistant OAuth server is actually running

**Command** (from HA container):
```bash
# SSH to Home Assistant host, then:
docker exec -it homeassistant bash

# Inside HA container:
curl -I http://music-assistant:8096/authorize

# Expected: 200/401 from OAuth server
# If fails: Music Assistant OAuth not running (check configuration.yaml)
```

**Alternative** (from Music Assistant container):
```bash
docker exec -it addon_xxx_music_assistant bash

# Check if OAuth server is listening
netstat -tuln | grep 8096

# Expected: tcp 0.0.0.0:8096 LISTEN
```

**What This Confirms**:
- If internal test succeeds but external fails → Nabu Casa port routing limitation
- If internal test fails → Music Assistant OAuth server configuration issue

---

## Decision Tree

### Scenario A: Test 2 Succeeds (Port 8096 Accessible)

**Next Actions** (5 minutes):
1. Update Alexa Skill configuration with custom domain URLs:
   - Authorization URL: `https://boxhillsouth.jasonhollis.com:8096/authorize`
   - Token URL: `https://boxhillsouth.jasonhollis.com:8096/token`
   - Client ID/Secret: (from Music Assistant OAuth config)

2. Test OAuth flow:
   ```bash
   # Initiate OAuth authorization
   open "https://boxhillsouth.jasonhollis.com:8096/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&state=test123"
   ```

3. Complete Alexa Skill account linking in Amazon Developer Console

4. Document success in `ALEXA_OAUTH_SETUP_PROGRESS.md`

**Timeline**: 5 minutes to working OAuth flow

---

### Scenario B: Test 2 Fails (Port 8096 Blocked)

**Root Cause**: Nabu Casa custom domain routing limited to port 8123

**Two Implementation Paths**:

#### Option B1: Reverse Proxy within Home Assistant (15 minutes)

**Approach**: Install nginx/Caddy add-on to proxy `/oauth/*` to `music-assistant:8096`

**Implementation Steps**:
1. Install nginx add-on from HA add-on store (3 min)
2. Configure nginx to proxy `/oauth/*` to `http://music-assistant:8096/*` (5 min)
3. Update Music Assistant OAuth URLs to use proxy paths (2 min)
4. Test OAuth flow through proxy (5 min)

**Result**:
- OAuth accessible at `https://boxhillsouth.jasonhollis.com/oauth/authorize`
- Nabu Casa still handles SSL and external routing
- nginx handles internal port routing

**Pros**:
- Still uses Nabu Casa (community funding)
- Minimal configuration
- Zero additional monthly cost

**Cons**:
- Additional HA add-on to manage
- Slight configuration complexity

#### Option B2: Fallback to Tailscale Funnel (15 minutes)

**Approach**: Use Tailscale Funnel as documented in existing infrastructure

**Implementation Steps**:
1. Follow [Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)
2. Configure socat or nginx in Tailscale container
3. Expose `https://a0d7b954-tailscale.ts.net/oauth` → `http://music-assistant:8096`
4. Update Alexa Skill with Tailscale URLs

**Result**:
- OAuth accessible at `https://a0d7b954-tailscale.ts.net/oauth/authorize`
- Independent of Nabu Casa
- No monthly cost

**Pros**:
- Already researched and documented
- Independent from Nabu Casa
- Proven working in test environment

**Cons**:
- Doesn't utilize Nabu Casa subscription
- Requires socat/proxy process management
- Less aligned with community funding preference

---

## Expected Timeline

### If Port 8096 Works (Scenario A)
| Task | Duration | Running Total |
|------|----------|---------------|
| HA boot completion | 5-7 min | 18:50 |
| Run Test 1 (baseline) | 1 min | 18:51 |
| Run Test 2 (port 8096) | 1 min | 18:52 |
| Update Alexa Skill config | 3 min | 18:55 |
| Test OAuth flow | 2 min | 18:57 |
| **Total** | **12-14 minutes** | **18:57** |

### If Port 8096 Blocked (Scenario B1 - Reverse Proxy)
| Task | Duration | Running Total |
|------|----------|---------------|
| HA boot completion | 5-7 min | 18:50 |
| Run Test 1-3 | 3 min | 18:53 |
| Install nginx add-on | 3 min | 18:56 |
| Configure nginx proxy | 5 min | 19:01 |
| Update Music Assistant URLs | 2 min | 19:03 |
| Update Alexa Skill config | 3 min | 19:06 |
| Test OAuth flow | 5 min | 19:11 |
| **Total** | **26-28 minutes** | **19:11** |

### If Port 8096 Blocked (Scenario B2 - Tailscale Funnel)
| Task | Duration | Running Total |
|------|----------|---------------|
| HA boot completion | 5-7 min | 18:50 |
| Run Test 1-3 | 3 min | 18:53 |
| Configure Tailscale Funnel | 10 min | 19:03 |
| Update Alexa Skill config | 3 min | 19:06 |
| Test OAuth flow | 5 min | 19:11 |
| **Total** | **26-28 minutes** | **19:11** |

---

## Verification

After successful configuration (regardless of path):

### OAuth Flow Test
```bash
# 1. Authorization endpoint accessible
curl -I https://[DOMAIN]/authorize

# Expected: 200 OK or 401 Unauthorized

# 2. Token endpoint accessible
curl -I https://[DOMAIN]/token

# Expected: 405 Method Not Allowed (GET not supported, POST required)

# 3. Complete OAuth flow in Alexa Skill
# Expected: Account linking successful, user authenticated
```

### End-to-End Test
1. Open Alexa app
2. Navigate to Skills → Your Skills → MusicAssistantApple
3. Enable skill
4. Click "Link Account"
5. Redirected to Music Assistant OAuth login
6. Authenticate successfully
7. Redirected back to Alexa app
8. Skill shows "Linked"

**Success Criteria**:
- All OAuth endpoints return expected responses
- Alexa Skill can complete account linking flow
- User can control Music Assistant via Alexa voice commands

---

## Troubleshooting

### Test 1 Fails (Custom Domain Not Working)

**Symptom**: `https://boxhillsouth.jasonhollis.com/` returns timeout or connection refused

**Diagnosis**:
1. Check DNS: `dig boxhillsouth.jasonhollis.com CNAME`
   - Expected: `0gdzommh4w1tug2s97xnn9spylzmkkbs.ui.nabu.casa`
2. Check Nabu Casa connection in HA Settings → Home Assistant Cloud
   - Expected: Connected, green status
3. Check SSL certificate in HA logs: `ha core logs | grep -i certificate`

**Solutions**:
- DNS not propagated → Wait 15 more minutes, check TTL
- Nabu Casa disconnected → Restart HA, check subscription status
- SSL cert generation failed → Check HA logs, manually trigger renewal

---

### Test 2 Fails (Port 8096 Blocked)

**Symptom**: `:8096` requests timeout or return 502 Bad Gateway

**Root Cause**: Nabu Casa nginx proxy only forwards port 8123 traffic

**Solutions**:
- **Recommended**: Implement reverse proxy (Option B1 above)
- **Alternative**: Use Tailscale Funnel (Option B2 above)

**Decision Criteria**:
- Value community funding? → Reverse proxy (keeps Nabu Casa in use)
- Want simplest path? → Tailscale Funnel (already documented)
- Need immediate fix? → Tailscale Funnel (faster implementation)

---

### Test 3 Fails (OAuth Server Not Running)

**Symptom**: Internal `curl http://music-assistant:8096/authorize` returns connection refused

**Root Cause**: Music Assistant OAuth server not started

**Solutions**:
1. Check Music Assistant logs:
   ```bash
   docker logs addon_xxx_music_assistant | grep -i oauth
   ```

2. Verify OAuth configuration in Music Assistant settings:
   - Check `configuration.yaml` for OAuth provider config
   - Verify port 8096 is configured and enabled

3. Restart Music Assistant container:
   ```bash
   docker restart addon_xxx_music_assistant
   ```

4. Check if OAuth server process is running:
   ```bash
   docker exec -it addon_xxx_music_assistant ps aux | grep oauth
   ```

---

## Next Steps

### After Test Completion

1. **Document results** in `SESSION_LOG.md`:
   ```markdown
   2025-10-25 [TIME]: Nabu Casa port 8096 test - [RESULT]
   - Test 1: [PASS/FAIL]
   - Test 2: [PASS/FAIL]
   - Decision: [Proceed with Nabu Casa / Implement reverse proxy / Use Tailscale]
   ```

2. **Update decision log** in `DECISIONS.md`:
   - Record test results
   - Document chosen implementation path
   - Capture rationale for fallback (if needed)

3. **Follow implementation guide**:
   - If Scenario A: Update Alexa Skill configuration
   - If Scenario B1: Follow reverse proxy setup guide
   - If Scenario B2: Follow [Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)

4. **Update progress tracker**: `ALEXA_OAUTH_SETUP_PROGRESS.md`
   - Mark Nabu Casa test as complete
   - Update blocker status
   - Record next actions

---

## See Also

- [Nabu Casa vs Tailscale Decision Tree](NABU_CASA_VS_TAILSCALE_DECISION_TREE.md) - Implementation paths based on test results
- [Nabu Casa Port Routing Architecture](../02_REFERENCE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md) - How Nabu Casa routing works
- [Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md) - Fallback implementation (Scenario B2)
- [Alexa OAuth Setup Progress](ALEXA_OAUTH_SETUP_PROGRESS.md) - Overall project status
- [Home Assistant Container Topology](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md) - Network architecture reference
