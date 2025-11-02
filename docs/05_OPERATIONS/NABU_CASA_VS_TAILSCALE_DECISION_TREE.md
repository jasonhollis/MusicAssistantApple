# Nabu Casa vs Tailscale OAuth Routing Decision Tree
**Purpose**: Structured decision framework for choosing OAuth exposure method based on Nabu Casa port routing test results
**Audience**: System administrator implementing Alexa OAuth integration
**Layer**: 05_OPERATIONS
**Related**:
- [Nabu Casa Custom Domain Test Plan](NABU_CASA_CUSTOM_DOMAIN_TEST_PLAN.md)
- [Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)
- [Nabu Casa Port Routing Architecture](../02_REFERENCE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md)

---

## Intent

Provide actionable implementation paths for exposing Music Assistant OAuth server (port 8096) based on empirical test results. This decision tree eliminates guesswork and provides concrete next steps for each outcome.

---

## Decision Point: Nabu Casa Port 8096 Test Result

**Pre-Requisite**: Complete [Nabu Casa Custom Domain Test Plan](NABU_CASA_CUSTOM_DOMAIN_TEST_PLAN.md) - Test 2

**Test Command**:
```bash
curl -I https://boxhillsouth.jasonhollis.com:8096/authorize
```

**Interpretation**:
- **200/401 response** → PORT ROUTING WORKS → Proceed to Scenario A
- **Connection refused/timeout/502** → PORT BLOCKED → Proceed to Scenario B

---

## Scenario A: Port 8096 Works Via Nabu Casa

**Test Result**: `curl https://boxhillsouth.jasonhollis.com:8096/authorize` returns 200 or 401

**Meaning**: Nabu Casa custom domain routing supports arbitrary ports (unexpected but excellent!)

### Implementation Path (5 Minutes)

#### Step 1: Update Alexa Skill OAuth Configuration (3 minutes)

**Action**: Configure Alexa Skill with Nabu Casa custom domain URLs

**Login to Amazon Developer Console**:
1. Navigate to: https://developer.amazon.com/alexa/console/ask
2. Select your Alexa Skill (or create new skill)
3. Go to **Account Linking** section

**OAuth Configuration**:
```
Authorization URI: https://boxhillsouth.jasonhollis.com:8096/authorize
Access Token URI: https://boxhillsouth.jasonhollis.com:8096/token

Client ID: [From Music Assistant OAuth config]
Client Secret: [From Music Assistant OAuth config]

Scopes: openid profile email
Authorization Grant Type: Auth Code Grant

Domain List:
- boxhillsouth.jasonhollis.com

Redirect URLs (provided by Amazon):
- [Copy these to Music Assistant OAuth allowed redirect URIs]
```

**Save Configuration**: Click "Save" in Amazon Developer Console

---

#### Step 2: Update Music Assistant OAuth Allowed Redirects (1 minute)

**Action**: Allow Alexa redirect URIs in Music Assistant OAuth server

**Location**: Home Assistant → Music Assistant → Settings → OAuth Server

**Add Allowed Redirect URIs**:
```
https://pitangui.amazon.com/spa/skill/account-linking-status.html
https://layla.amazon.com/spa/skill/account-linking-status.html
https://alexa.amazon.co.jp/spa/skill/account-linking-status.html
```

*(These are standard Alexa OAuth redirect URIs - Amazon provides exact URLs in Developer Console)*

**Save Configuration**: Restart Music Assistant if required

---

#### Step 3: Test OAuth Flow (1 minute)

**Action**: Verify end-to-end account linking

**Test in Alexa App** (mobile or web):
1. Open Alexa app → Skills & Games
2. Search for your skill (or use developer preview)
3. Click "Enable Skill"
4. Click "Link Account"
5. **Expected**: Redirected to `https://boxhillsouth.jasonhollis.com:8096/authorize`
6. Login with Music Assistant credentials
7. **Expected**: Redirected back to Alexa app
8. **Expected**: Skill shows "Account successfully linked"

**Verification Command**:
```bash
# Check OAuth server logs for authorization request
docker logs addon_xxx_music_assistant | grep -A5 "authorize"

# Expected: Log entry showing Alexa authorization request
```

---

### Configuration Summary (Scenario A)

| Component | Configuration | Value |
|-----------|--------------|-------|
| **Authorization URL** | Alexa Skill | `https://boxhillsouth.jasonhollis.com:8096/authorize` |
| **Token URL** | Alexa Skill | `https://boxhillsouth.jasonhollis.com:8096/token` |
| **Public DNS** | Nabu Casa Custom Domain | `boxhillsouth.jasonhollis.com` |
| **Internal Target** | Home Assistant | `music-assistant:8096` |
| **Proxy Layer** | Nabu Casa | `0gdzommh4w1tug2s97xnn9spylzmkkbs.ui.nabu.casa` |
| **SSL Certificate** | Nabu Casa | Auto-managed by HA Cloud |

---

### Advantages (Scenario A)

✅ **Simplest implementation** (5 minutes total)
✅ **Zero maintenance** (Nabu Casa manages everything)
✅ **Community funding** ($6.50/month supports Home Assistant development)
✅ **Automatic SSL renewal** (no certificate management)
✅ **DDoS protection** (Nabu Casa infrastructure)
✅ **Official HA integration path** (well-documented, community-supported)
✅ **No additional software** (no reverse proxy, no socat)
✅ **Reliable infrastructure** (99.9% SLA from Nabu Casa)

---

### Next Actions (Scenario A)

1. ✅ Complete Alexa Skill OAuth configuration
2. ✅ Test account linking flow
3. ✅ Document success in `SESSION_LOG.md`
4. ✅ Update `ALEXA_OAUTH_SETUP_PROGRESS.md` (mark as complete)
5. ✅ Test voice commands with Alexa
6. ✅ Consider this approach for other integrations needing OAuth

---

## Scenario B: Port 8096 Blocked by Nabu Casa

**Test Result**: `curl https://boxhillsouth.jasonhollis.com:8096/authorize` returns connection refused, timeout, or 502 Bad Gateway

**Meaning**: Nabu Casa custom domain routing limited to standard port 8123 (expected behavior)

**Two Implementation Options**:
- **Option B1**: Reverse Proxy within Home Assistant (Nabu Casa + nginx)
- **Option B2**: Fallback to Tailscale Funnel (independent approach)

### Decision Criteria: Which Option?

| Factor | Option B1 (Reverse Proxy) | Option B2 (Tailscale Funnel) |
|--------|--------------------------|------------------------------|
| **Setup Time** | 15 minutes | 15 minutes |
| **Maintenance** | Minimal (nginx config stable) | Moderate (socat process monitoring) |
| **Community Funding** | ✅ Yes (uses Nabu Casa) | ❌ No (bypasses Nabu Casa) |
| **Monthly Cost** | $0 (included in Nabu Casa) | $0 (Tailscale free tier) |
| **Reliability** | High (Nabu Casa SLA) | Moderate (Tailscale Funnel beta) |
| **Independence** | Depends on Nabu Casa | Independent from Nabu Casa |
| **Complexity** | Low (nginx add-on) | Moderate (container proxying) |
| **SSL Management** | Automatic (Nabu Casa) | Automatic (Tailscale) |
| **Custom Domain** | ✅ Yes (boxhillsouth.jasonhollis.com) | ❌ No (*.ts.net subdomain) |

**Recommendation**:
- **Prefer Option B1** if you value: Community funding, custom domain, Nabu Casa subscription utilization
- **Prefer Option B2** if you value: Independence from Nabu Casa, already-documented approach

---

## Option B1: Reverse Proxy within Home Assistant

**Approach**: Install nginx add-on to proxy `/oauth/*` paths to Music Assistant port 8096

**Architecture**:
```
Internet
  ↓
Nabu Casa Cloud (boxhillsouth.jasonhollis.com)
  ↓ HTTPS (port 443)
Home Assistant (port 8123)
  ↓ Internal routing
nginx Add-on (reverse proxy)
  ↓ HTTP (port 8096)
Music Assistant OAuth Server
```

**URL Mapping**:
- `https://boxhillsouth.jasonhollis.com/oauth/authorize` → `http://music-assistant:8096/authorize`
- `https://boxhillsouth.jasonhollis.com/oauth/token` → `http://music-assistant:8096/token`
- `https://boxhillsouth.jasonhollis.com/oauth/userinfo` → `http://music-assistant:8096/userinfo`

---

### Implementation Steps (15 Minutes)

#### Step 1: Install nginx Proxy Manager Add-on (3 minutes)

**Action**: Install nginx from Home Assistant add-on store

1. Navigate to: **Home Assistant → Settings → Add-ons → Add-on Store**
2. Search for: "nginx Proxy Manager" or "NGINX Home Assistant SSL proxy"
3. Click **Install**
4. Wait for installation to complete (~2 minutes)

**Alternative**: Use "Caddy" add-on if nginx not available
- Similar configuration, different syntax
- Automatic HTTPS handling
- Simpler reverse proxy rules

---

#### Step 2: Configure nginx Reverse Proxy (5 minutes)

**Action**: Create proxy configuration for OAuth endpoints

**nginx Configuration** (`/config/nginx/proxy_config/oauth_music_assistant.conf`):
```nginx
# Music Assistant OAuth Proxy
# Route /oauth/* to music-assistant:8096

server {
    listen 8123;
    server_name boxhillsouth.jasonhollis.com;

    # OAuth authorization endpoint
    location /oauth/authorize {
        proxy_pass http://music-assistant:8096/authorize;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # OAuth requires query parameters preserved
        proxy_pass_request_args on;
    }

    # OAuth token endpoint
    location /oauth/token {
        proxy_pass http://music-assistant:8096/token;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Token endpoint receives POST data
        proxy_pass_request_body on;
    }

    # OAuth userinfo endpoint
    location /oauth/userinfo {
        proxy_pass http://music-assistant:8096/userinfo;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Userinfo requires Authorization header
        proxy_set_header Authorization $http_authorization;
    }
}
```

**Apply Configuration**:
1. Save file in HA configuration directory
2. Restart nginx add-on: **Settings → Add-ons → nginx → Restart**
3. Check logs for errors: **Settings → Add-ons → nginx → Logs**

---

#### Step 3: Test Proxy Configuration (2 minutes)

**Verification Commands**:
```bash
# Test authorization endpoint (should return 200/401)
curl -I https://boxhillsouth.jasonhollis.com/oauth/authorize

# Test token endpoint (should return 405 for GET, accepts POST)
curl -I https://boxhillsouth.jasonhollis.com/oauth/token

# Test userinfo endpoint (should return 401 without auth)
curl -I https://boxhillsouth.jasonhollis.com/oauth/userinfo
```

**Expected Results**:
- All endpoints return HTTP responses (not connection refused)
- Authorization endpoint: 200 or 401
- Token endpoint: 405 Method Not Allowed (GET not supported)
- Userinfo endpoint: 401 Unauthorized (no auth token)

**If Tests Fail**:
- Check nginx logs: `docker logs addon_xxx_nginx`
- Verify Music Assistant reachable: `curl http://music-assistant:8096/authorize` (from HA container)
- Check nginx config syntax: `nginx -t` (in nginx container)

---

#### Step 4: Update Alexa Skill OAuth Configuration (3 minutes)

**Action**: Configure Alexa Skill with proxied URLs

**Amazon Developer Console**:
```
Authorization URI: https://boxhillsouth.jasonhollis.com/oauth/authorize
Access Token URI: https://boxhillsouth.jasonhollis.com/oauth/token

Client ID: [From Music Assistant OAuth config]
Client Secret: [From Music Assistant OAuth config]

Scopes: openid profile email
Authorization Grant Type: Auth Code Grant

Domain List:
- boxhillsouth.jasonhollis.com

Redirect URLs (provided by Amazon):
- [Copy these to Music Assistant OAuth allowed redirect URIs]
```

---

#### Step 5: Test End-to-End OAuth Flow (2 minutes)

**Action**: Complete account linking in Alexa app

1. Open Alexa app → Skills & Games
2. Find your skill → Enable Skill
3. Click "Link Account"
4. **Expected**: Redirected to `https://boxhillsouth.jasonhollis.com/oauth/authorize`
5. Login with Music Assistant credentials
6. **Expected**: Redirected back to Alexa app
7. **Expected**: "Account successfully linked"

**Verification**:
```bash
# Check nginx access logs
docker logs addon_xxx_nginx | grep oauth

# Expected: GET /oauth/authorize, POST /oauth/token entries

# Check Music Assistant OAuth logs
docker logs addon_xxx_music_assistant | grep -i oauth

# Expected: Authorization request, token exchange logs
```

---

### Configuration Summary (Option B1)

| Component | Configuration | Value |
|-----------|--------------|-------|
| **Public URL** | Alexa Skill | `https://boxhillsouth.jasonhollis.com/oauth/*` |
| **Nabu Casa Domain** | DNS CNAME | `boxhillsouth.jasonhollis.com` |
| **Reverse Proxy** | nginx Add-on | Port 8123 (HA standard port) |
| **Internal Target** | Music Assistant | `http://music-assistant:8096` |
| **SSL Termination** | Nabu Casa | Automatic certificate management |
| **Path Mapping** | nginx | `/oauth/*` → `:8096/*` |

---

### Advantages (Option B1)

✅ **Uses Nabu Casa** (community funding continues)
✅ **Custom domain** (boxhillsouth.jasonhollis.com)
✅ **Automatic SSL** (Nabu Casa handles certificates)
✅ **Standard port 8123** (Nabu Casa already proxies this)
✅ **Professional appearance** (custom domain, not *.ts.net)
✅ **Stable configuration** (nginx config rarely changes)
✅ **No external dependencies** (everything within HA ecosystem)

---

### Disadvantages (Option B1)

⚠️ **Additional add-on** (nginx requires installation and configuration)
⚠️ **Configuration complexity** (nginx proxy rules)
⚠️ **Debugging path** (requests pass through two layers: Nabu Casa → nginx → Music Assistant)
⚠️ **Maintenance burden** (nginx config updates if OAuth endpoints change)

---

### Maintenance (Option B1)

**Ongoing Tasks**:
- **None** under normal operation (nginx config stable)

**When Updates Needed**:
- Music Assistant OAuth endpoint changes → Update nginx proxy rules
- New OAuth endpoints added → Add new location blocks in nginx config

**Monitoring**:
```bash
# Check nginx is running
docker ps | grep nginx

# Check nginx logs for errors
docker logs addon_xxx_nginx --tail 100

# Check proxy performance
docker logs addon_xxx_nginx | grep oauth | tail -20
```

---

## Option B2: Fallback to Tailscale Funnel

**Approach**: Use Tailscale Funnel to expose Music Assistant OAuth independently from Nabu Casa

**Architecture**:
```
Internet
  ↓
Tailscale Funnel (a0d7b954-tailscale.ts.net)
  ↓ HTTPS (automatic SSL)
Tailscale Container (addon_a0d7b954_tailscale)
  ↓ socat/nginx proxy
Music Assistant Container (music-assistant:8096)
```

**URL Mapping**:
- `https://a0d7b954-tailscale.ts.net/oauth/authorize` → `http://music-assistant:8096/authorize`
- `https://a0d7b954-tailscale.ts.net/oauth/token` → `http://music-assistant:8096/token`

---

### Implementation Steps (15 Minutes)

**Follow Existing Documentation**:
This approach is fully documented in:
- **[Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)** - Complete implementation guide

**Quick Summary**:
1. Verify Tailscale container connectivity to Music Assistant (1 min)
2. Configure Tailscale Funnel for port 8096 (5 min)
3. Set up socat proxy in Tailscale container (5 min)
4. Test OAuth endpoints (2 min)
5. Update Alexa Skill configuration (2 min)

**Detailed Steps**: See [TAILSCALE_FUNNEL_CONFIGURATION_HA.md](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)

---

### Configuration Summary (Option B2)

| Component | Configuration | Value |
|-----------|--------------|-------|
| **Public URL** | Alexa Skill | `https://a0d7b954-tailscale.ts.net/oauth/*` |
| **Tailscale Funnel** | Auto-generated | `*.ts.net` subdomain |
| **Proxy Layer** | socat/nginx | In Tailscale container |
| **Internal Target** | Music Assistant | `http://music-assistant:8096` |
| **SSL Certificate** | Tailscale | Automatic via Funnel |
| **Independence** | Yes | No dependency on Nabu Casa |

---

### Advantages (Option B2)

✅ **Independent from Nabu Casa** (works even if Nabu Casa subscription expires)
✅ **Already documented** (complete implementation guide exists)
✅ **Zero marginal cost** (Tailscale free tier)
✅ **No custom domain required** (*.ts.net provided by Tailscale)
✅ **Automatic SSL** (Tailscale Funnel handles certificates)
✅ **Proven approach** (tested in infrastructure documentation)

---

### Disadvantages (Option B2)

⚠️ **No custom domain** (URLs are `*.ts.net`, not `boxhillsouth.jasonhollis.com`)
⚠️ **Doesn't use Nabu Casa** (community funding concern)
⚠️ **Requires proxy process** (socat or nginx in Tailscale container)
⚠️ **Maintenance burden** (monitor socat process, ensure auto-restart)
⚠️ **Tailscale Funnel beta** (feature not GA, could change)
⚠️ **Less professional appearance** (generic *.ts.net subdomain)

---

### Maintenance (Option B2)

**Ongoing Tasks**:
- Monitor socat/proxy process (ensure running)
- Check Tailscale Funnel status (ensure enabled)

**Monitoring**:
```bash
# Check socat process
docker exec addon_a0d7b954_tailscale ps aux | grep socat

# Check Tailscale Funnel status
docker exec addon_a0d7b954_tailscale tailscale funnel status

# Check proxy logs
docker logs addon_a0d7b954_tailscale | grep -i funnel
```

**Auto-Restart** (recommended):
See [Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md) section on persistence and reliability.

---

## Hybrid Approach: Both Nabu Casa and Tailscale

**Concept**: Configure both approaches for redundancy

**Use Cases**:
- **Primary**: Nabu Casa reverse proxy (custom domain, community funding)
- **Backup**: Tailscale Funnel (if Nabu Casa has outage)

**Implementation**:
1. Configure Option B1 (Nabu Casa + nginx)
2. Configure Option B2 (Tailscale Funnel)
3. Register both URLs in Alexa Skill as alternate endpoints
4. If primary fails, manually switch to backup in Alexa Developer Console

**Advantages**:
✅ Redundancy and failover capability
✅ Uses both subscriptions (Nabu Casa + Tailscale)
✅ Can A/B test performance and reliability

**Disadvantages**:
⚠️ Doubled configuration complexity
⚠️ Doubled maintenance burden
⚠️ Overkill for most use cases

---

## Summary Decision Matrix

| Scenario | Test Result | Recommended Path | Setup Time | Maintenance | Community Funding |
|----------|-------------|-----------------|------------|-------------|-------------------|
| **A** | Port 8096 works | Direct Nabu Casa | 5 min | Zero | ✅ Yes |
| **B1** | Port 8096 blocked | Nabu Casa + nginx | 15 min | Minimal | ✅ Yes |
| **B2** | Port 8096 blocked | Tailscale Funnel | 15 min | Moderate | ❌ No |
| **Hybrid** | Port 8096 blocked | Both B1 + B2 | 30 min | High | ⚠️ Partial |

**Recommendation Hierarchy**:
1. **Scenario A** (if port 8096 works) - Simplest, fastest, best outcome
2. **Option B1** (if blocked, value community) - Nabu Casa + nginx reverse proxy
3. **Option B2** (if blocked, value independence) - Tailscale Funnel

---

## Verification (All Scenarios)

After implementation, verify OAuth flow works:

### Endpoint Tests
```bash
# Authorization endpoint
curl -I https://[DOMAIN]/[PATH]/authorize

# Token endpoint
curl -I https://[DOMAIN]/[PATH]/token

# Userinfo endpoint
curl -I https://[DOMAIN]/[PATH]/userinfo
```

### Alexa Skill Account Linking Test
1. Open Alexa app → Skills & Games
2. Enable skill → Link Account
3. Complete OAuth login flow
4. Verify "Account successfully linked"

### Voice Command Test
1. Say: "Alexa, ask Music Assistant to play [song name]"
2. **Expected**: Music starts playing through Music Assistant
3. **If fails**: Check OAuth token in Music Assistant logs

---

## Next Actions

After completing chosen implementation path:

1. **Update SESSION_LOG.md**:
   ```markdown
   2025-10-25 [TIME]: Implemented OAuth exposure - [Scenario A/B1/B2]
   - Test result: [Port 8096 works/blocked]
   - Chosen path: [Direct/Reverse proxy/Tailscale]
   - Implementation time: [X minutes]
   - Status: [SUCCESS/PARTIAL/BLOCKED]
   ```

2. **Update DECISIONS.md**:
   - Record implementation decision
   - Document rationale for chosen path
   - Note any trade-offs accepted

3. **Update ALEXA_OAUTH_SETUP_PROGRESS.md**:
   - Mark OAuth exposure as complete
   - Update blocker status (resolved)
   - Record next steps (Alexa Skill setup)

4. **Test end-to-end Alexa integration**:
   - Complete Alexa Skill configuration
   - Test voice commands
   - Validate user experience

---

## See Also

- [Nabu Casa Custom Domain Test Plan](NABU_CASA_CUSTOM_DOMAIN_TEST_PLAN.md) - Test procedures and timeline
- [Nabu Casa Port Routing Architecture](../02_REFERENCE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md) - How routing works
- [Tailscale Funnel Configuration](TAILSCALE_FUNNEL_CONFIGURATION_HA.md) - Option B2 implementation
- [Tailscale OAuth Routing Interface](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md) - Routing contract (Option B2)
- [Home Assistant Container Topology](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md) - Network architecture
- [Alexa OAuth Setup Progress](ALEXA_OAUTH_SETUP_PROGRESS.md) - Overall project status
