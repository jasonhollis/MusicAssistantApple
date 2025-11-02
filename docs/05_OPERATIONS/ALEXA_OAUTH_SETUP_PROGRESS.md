# Alexa OAuth Server Setup Progress
**Purpose**: Track current status and next steps for Alexa OAuth integration
**Audience**: Operators, System Administrators
**Layer**: 05_OPERATIONS (Procedures and current state)
**Related**:
- [Alexa OAuth Endpoints Contract](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md)
- [Alexa Infrastructure Options](../02_REFERENCE/ALEXA_INFRASTRUCTURE_OPTIONS.md)
- [Alexa Authentication Strategic Analysis](../00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md)

**Last Updated**: 2025-10-25

---

## Intent

This document tracks the current status of the Alexa OAuth server implementation for Music Assistant, documenting what has been completed, what is working, current blockers, and viable paths forward.

---

## Executive Summary

**Current State**: OAuth server successfully implemented and running, but not yet publicly accessible.

**Status**: BLOCKED on public endpoint exposure - three viable paths available.

**Next Critical Step**: Choose and implement public endpoint exposure method (Nabu Casa, Tailscale Funnel, or direct routing).

---

## Completed Work

### 1. OAuth Server Implementation ✅

**Status**: COMPLETE and VERIFIED

**What Was Done**:
- Created Python aiohttp-based OAuth server
- Implemented all three required endpoints:
  - `/health` - Health check
  - `/alexa/authorize` - OAuth authorization flow
  - `/alexa/token` - Token exchange
- Deployed to Music Assistant Docker container
- Server running on port 8096

**Verification**:
```bash
# Health endpoint tested and confirmed working:
curl http://192.168.130.11:8096/health

# Response:
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

**Location**: Running inside Music Assistant Docker container at `192.168.130.11:8096`

**Process Management**: Server runs as aiohttp application managed by Docker container

---

## Current Infrastructure

### Network Topology (UPDATED 2025-10-25)

```
Internet
    ↓
[Tailscale Funnel - Public HTTPS Endpoint]
    ↓
Tailscale Container (addon_a0d7b954_tailscale)
    ├── Hostname: a0d7b954-tailscale
    ├── Public URL: https://a0d7b954-tailscale.ts.net
    ├── Network Mode: Host (shares HABoxHill network)
    ├── Funnel Capability: ✅ AVAILABLE
    └── Docker Bridge Network
            ↓
        Music Assistant Container
            ├── Container: music-assistant
            ├── Network Mode: Bridge (isolated)
            ├── OAuth Server: port 8096
            ├── Reachable via DNS: music-assistant:8096 ✅ VERIFIED
            └── Local IP: 192.168.130.11 (host network)
```

**Critical Discovery**: Tailscale and Music Assistant are **separate containers** connected via Docker bridge network. This is different from the initial assumption that Tailscale CLI would be available in Music Assistant container.

### Available Resources

**Tailscale Infrastructure** (UPDATED):
- **Container**: `addon_a0d7b954_tailscale` (Home Assistant add-on)
- **Hostname**: `a0d7b954-tailscale`
- **Public URL**: `https://a0d7b954-tailscale.ts.net`
- **Funnel Support**: ✅ Available via Tailscale CLI in container
- **Network Access**: Can reach Music Assistant via Docker DNS (`music-assistant:8096`) ✅ VERIFIED
- **CLI Access**: `docker exec addon_a0d7b954_tailscale tailscale [command]`

**Nabu Casa**:
- Home Assistant instance has active Nabu Casa subscription
- Provides nginx reverse proxy for Home Assistant
- Can potentially proxy to Music Assistant OAuth server
- **Consideration**: May be redundant if Tailscale Funnel works

**Music Assistant**:
- **Container**: `music-assistant`
- **OAuth Server**: Running on port 8096
- **Network**: Docker bridge mode (isolated from host)
- **DNS Name**: `music-assistant` (Docker internal DNS)
- **Accessible from**:
  - Host: `http://localhost:8096` ✅
  - Tailscale container: `http://music-assistant:8096` ✅ VERIFIED
  - Local network: `http://192.168.130.11:8096` ✅
  - Internet: ❌ NOT YET (need Funnel or proxy)

---

## Current Blocker

### Public Endpoint Exposure Required

**Problem**: Alexa requires OAuth server accessible via public HTTPS endpoint.

**Architecture Constraint** (UPDATED): Tailscale and Music Assistant are **separate containers**:
- ✅ Tailscale container HAS Tailscale CLI (`addon_a0d7b954_tailscale`)
- ✅ Tailscale container CAN reach Music Assistant (`music-assistant:8096`)
- ⏸️ Need to configure Tailscale Funnel to forward traffic to Music Assistant

**Impact**: Cannot run `tailscale funnel` directly from Music Assistant container, but CAN configure it from Tailscale container to forward to Music Assistant.

**Why This Matters**: Amazon Alexa must be able to reach the OAuth authorization and token endpoints to complete account linking flow.

**Solution Path Now Clear**: Configure Tailscale Funnel in `addon_a0d7b954_tailscale` container to proxy traffic to `music-assistant:8096`.

---

## Three Viable Paths Forward

### Path 1: Nabu Casa Nginx Proxy (RECOMMENDED)

**Strategy**: Use existing Nabu Casa infrastructure to proxy OAuth requests to Music Assistant.

**How It Works**:
1. Configure Nabu Casa nginx to proxy `/alexa/*` paths
2. Forward requests to `http://192.168.130.11:8096`
3. Alexa connects to: `https://[nabu-casa-id].ui.nabu.casa/alexa/authorize`
4. Nginx proxies to: `http://192.168.130.11:8096/alexa/authorize`

**Advantages**:
- Uses existing paid infrastructure (no additional cost)
- Proven, stable reverse proxy
- HTTPS already configured and managed
- No additional Tailscale configuration needed
- Simple nginx configuration change

**Disadvantages**:
- Couples Music Assistant OAuth to Home Assistant infrastructure
- Requires Home Assistant nginx configuration access
- Nabu Casa URL tied to Home Assistant subscription

**Risk Level**: LOW - uses established infrastructure

**Implementation Complexity**: MEDIUM - requires nginx configuration

**Next Steps**:
1. Locate Home Assistant nginx configuration
2. Add proxy rules for `/alexa/*` paths
3. Test forwarding to Music Assistant
4. Configure Alexa skill with Nabu Casa URL

---

### Path 2: Tailscale Funnel via Tailscale Container (RECOMMENDED - UPDATED)

**Strategy**: Use `addon_a0d7b954_tailscale` container to expose Music Assistant OAuth via Funnel.

**How It Works** (UPDATED):
1. Access Tailscale container: `docker exec -it addon_a0d7b954_tailscale /bin/sh`
2. Configure Funnel to forward to Music Assistant: `tailscale serve https / http://music-assistant:8096`
3. Enable Funnel: `tailscale funnel on 443`
4. Alexa connects to: `https://a0d7b954-tailscale.ts.net/alexa/authorize`
5. Tailscale Funnel forwards to: `http://music-assistant:8096/alexa/authorize`

**Advantages** (UPDATED):
- ✅ **Tailscale CLI confirmed available** in `addon_a0d7b954_tailscale` container
- ✅ **Container connectivity verified** - Tailscale can reach Music Assistant via Docker DNS
- ✅ Public URL confirmed: `https://a0d7b954-tailscale.ts.net`
- ✅ Decouples from Home Assistant/Nabu Casa infrastructure
- ✅ Independent of Nabu Casa subscription
- ✅ Tailscale Funnel handles HTTPS automatically
- ✅ More portable if Music Assistant moves
- ✅ No nginx configuration required

**Disadvantages**:
- Depends on Tailscale service availability (99.9% SLA)
- Requires running commands in Tailscale container
- May need persistence configuration (Funnel settings survive restart)

**Risk Level**: LOW - infrastructure verified, clear implementation path

**Implementation Complexity**: LOW - simple Tailscale commands, well-documented

**Recommended**: ✅ YES - This is now the **PRIMARY RECOMMENDED PATH** given verified infrastructure

**Implementation Guide**: See [TAILSCALE_FUNNEL_CONFIGURATION_HA](TAILSCALE_FUNNEL_CONFIGURATION_HA.md) for detailed procedures

**Next Steps**:
1. ✅ VERIFIED: Tailscale container exists and is accessible
2. ✅ VERIFIED: Music Assistant reachable from Tailscale container
3. ⏸️ TODO: Configure Funnel forwarding (detailed guide available)
4. ⏸️ TODO: Test public endpoint from internet
5. ⏸️ TODO: Configure Alexa skill with Tailscale URL

---

### Path 3: Direct Tailscale Routing (Router-Based)

**Strategy**: Use router's Tailscale connection to expose Music Assistant without Funnel.

**How It Works**:
1. Configure router (192.168.130.1) to route Tailscale traffic to Music Assistant
2. Use standard Tailscale sharing to make endpoint accessible
3. Alexa connects via Tailscale network (if supported)
4. Router forwards to: `http://192.168.130.11:8096`

**Advantages**:
- Uses existing router Tailscale connection
- No dependency on Home Assistant
- No dependency on Nabu Casa
- Direct network routing

**Disadvantages**:
- Requires Amazon Alexa to reach private Tailscale network (likely NOT supported)
- More complex routing configuration
- Potential NAT traversal issues
- May not provide public HTTPS endpoint Amazon requires

**Risk Level**: HIGH - Amazon likely requires public HTTPS, not private VPN access

**Implementation Complexity**: HIGH - complex routing, may not work

**Recommendation**: AVOID unless other options fail

---

## Recommended Path: Tailscale Funnel (UPDATED 2025-10-25)

### Why This Path? (Changed from Nabu Casa)

**Original Recommendation**: Nabu Casa nginx proxy
**Updated Recommendation**: Tailscale Funnel via `addon_a0d7b954_tailscale` container

**Reasons for Change**:
1. ✅ **Infrastructure Verified**: Tailscale container confirmed with CLI access
2. ✅ **Connectivity Verified**: Tailscale container can reach Music Assistant via Docker DNS
3. ✅ **Simpler Implementation**: No nginx configuration required
4. ✅ **Better Separation of Concerns**: Decouples OAuth from Home Assistant
5. ✅ **More Portable**: If Music Assistant moves, OAuth endpoint moves with it
6. ✅ **Clear Documentation**: Detailed implementation guide created ([TAILSCALE_FUNNEL_CONFIGURATION_HA](TAILSCALE_FUNNEL_CONFIGURATION_HA.md))
7. ✅ **No Additional Services**: Uses existing Tailscale infrastructure

**Comparison**:
| Factor | Tailscale Funnel | Nabu Casa Nginx |
|--------|------------------|-----------------|
| Infrastructure verified | ✅ Yes | ⏸️ Unknown |
| Implementation complexity | ✅ Simple (3 commands) | ⚠️ Medium (nginx config) |
| Dependency on HA | ✅ Independent | ❌ Tightly coupled |
| Documentation | ✅ Complete guide | ⚠️ Requires investigation |
| Risk of breaking HA | ✅ Zero risk | ⚠️ Could break HA UI |
| Portability | ✅ High | ❌ Tied to HA |

### Implementation Steps (UPDATED - Tailscale Funnel)

**For complete detailed procedures, see**: [TAILSCALE_FUNNEL_CONFIGURATION_HA.md](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)

**Quick Summary**:

#### Step 1: Access Tailscale Container

```bash
# SSH to HABoxHill host
docker exec -it addon_a0d7b954_tailscale /bin/sh
```

#### Step 2: Configure Tailscale Serve

```bash
# Inside Tailscale container
tailscale serve https / http://music-assistant:8096
```

**What this does**: Maps public HTTPS root to Music Assistant OAuth server via Docker DNS.

#### Step 3: Enable Tailscale Funnel

```bash
# Inside Tailscale container
tailscale funnel on 443
```

**Result**: Public endpoint `https://a0d7b954-tailscale.ts.net` now forwards to Music Assistant OAuth server.

#### Step 4: Verify Configuration

```bash
# Check Funnel status
tailscale funnel status

# Expected output:
# Funnel on:
#   https://a0d7b954-tailscale.ts.net/
#     ↳ http://music-assistant:8096

# Exit container
exit
```

#### Step 5: Test Public Endpoint

```bash
# From external network (NOT on Tailscale or home network)
curl https://a0d7b954-tailscale.ts.net/health

# Expected response:
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": ["/alexa/authorize", "/alexa/token", "/health"]
}
```

#### Step 6: Configure Alexa Skill

**Account Linking Settings**:
- Authorization URI: `https://a0d7b954-tailscale.ts.net/alexa/authorize`
- Access Token URI: `https://a0d7b954-tailscale.ts.net/alexa/token`
- Client ID: (from Music Assistant OAuth config)
- Client Secret: (from Music Assistant OAuth config)
- Authentication Scheme: HTTP Basic
- Scopes: (as required by Music Assistant)

**Note**: No `/alexa/` prefix in URL - Funnel forwards entire path unchanged.

---

## Verification Procedures

### Verify OAuth Server Running

```bash
# From local network
curl http://192.168.130.11:8096/health

# Expected response code: 200
# Expected JSON: {"status":"ok", ...}
```

### Verify Public Endpoint (After Proxy Setup)

```bash
# From external network (use phone hotspot or VPN elsewhere)
curl https://[your-nabu-casa-id].ui.nabu.casa/alexa/health

# Expected response code: 200
# Expected JSON: {"status":"ok", ...}
```

### Verify Authorization Flow

```bash
# Test authorization endpoint
curl -v "https://[your-nabu-casa-id].ui.nabu.casa/alexa/authorize?client_id=TEST&redirect_uri=https://example.com&state=test123"

# Expected: HTTP redirect or authorization page
```

### Verify Token Exchange

```bash
# Test token endpoint (requires valid auth code)
curl -X POST https://[your-nabu-casa-id].ui.nabu.casa/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=TEST&client_id=TEST&client_secret=TEST&redirect_uri=https://example.com"

# Expected: JSON token response or error
```

---

## Rollback Procedures

### If Nginx Proxy Breaks Home Assistant

**Symptoms**: Home Assistant UI stops responding after nginx configuration change.

**Immediate Rollback**:
```bash
# 1. Remove added configuration
# Edit nginx config file, delete /alexa/ location block

# 2. Reload nginx
nginx -s reload

# 3. Verify Home Assistant UI accessible
curl https://[your-nabu-casa-id].ui.nabu.casa
```

### If OAuth Server Stops Responding

**Symptoms**: Health endpoint returns errors after public exposure.

**Diagnosis**:
```bash
# Check OAuth server still running
curl http://192.168.130.11:8096/health

# Check Music Assistant container logs
docker logs [music-assistant-container-id] --tail 100

# Check for port conflicts
netstat -tuln | grep 8096
```

**Recovery**:
```bash
# Restart Music Assistant container
docker restart [music-assistant-container-id]

# Wait 30 seconds, verify health
curl http://192.168.130.11:8096/health
```

---

## Known Issues and Workarounds

### Issue: Nginx Configuration Location Unknown

**Problem**: Cannot locate nginx configuration files on Home Assistant box.

**Workaround**:
1. Check Home Assistant documentation for nginx customization
2. Consider using Home Assistant's built-in nginx proxy add-on
3. Fallback to Path 2 (Tailscale Funnel) instead

### Issue: Nabu Casa Doesn't Support Custom Paths

**Problem**: Nabu Casa may not allow proxy configuration to external services.

**Workaround**:
1. Switch to Path 2 (Tailscale Funnel)
2. Use Home Assistant automation to forward requests
3. Run small nginx container alongside Music Assistant

### Issue: SSL Certificate Mismatch

**Problem**: Alexa rejects certificate when proxying through Nabu Casa.

**Workaround**:
1. Ensure nginx proxy_set_header includes all required headers
2. Verify `X-Forwarded-Proto` is set to `https`
3. Check Alexa developer console for specific SSL errors

---

## Next Actions (UPDATED 2025-10-25)

### Immediate (Next 1-2 Hours)

- [x] ✅ **DECISION MADE**: Tailscale Funnel (infrastructure verified)
- [x] ✅ **VERIFIED**: Tailscale container accessible and has CLI
- [x] ✅ **VERIFIED**: Music Assistant reachable from Tailscale container
- [x] ✅ **DOCUMENTED**: Created comprehensive implementation guide
- [ ] ⏸️ **NEXT**: Configure Tailscale Funnel forwarding (see [TAILSCALE_FUNNEL_CONFIGURATION_HA](TAILSCALE_FUNNEL_CONFIGURATION_HA.md))
- [ ] ⏸️ **NEXT**: Run `tailscale serve https / http://music-assistant:8096`
- [ ] ⏸️ **NEXT**: Run `tailscale funnel on 443`

### Short Term (Next 24 Hours)

- [ ] Verify Funnel status with `tailscale funnel status`
- [ ] Test public endpoint from external network
- [ ] Verify all three OAuth endpoints accessible (health, authorize, token)
- [ ] Document actual public URL: `https://a0d7b954-tailscale.ts.net`
- [ ] Configure persistence (auto-restart Funnel after container restart)
- [ ] Set up monitoring for Funnel health

### Medium Term (Next Week)

- [ ] Create Alexa Skill in Amazon Developer Console
- [ ] Configure account linking with OAuth endpoints
- [ ] Test account linking flow end-to-end
- [ ] Document any issues encountered
- [ ] Update this document with final configuration

---

## Success Criteria

**Milestone 1: Public Endpoint Working**
- [ ] Health endpoint accessible via HTTPS from internet
- [ ] Response matches local health check
- [ ] No SSL certificate errors

**Milestone 2: Authorization Flow Working**
- [ ] `/alexa/authorize` endpoint accessible
- [ ] Returns authorization page or redirect
- [ ] Handles client_id, redirect_uri, state parameters correctly

**Milestone 3: Token Exchange Working**
- [ ] `/alexa/token` endpoint accessible
- [ ] Accepts POST requests with authorization code
- [ ] Returns valid OAuth token response

**Milestone 4: Alexa Integration Complete**
- [ ] Alexa Skill created
- [ ] Account linking configured
- [ ] User can link Music Assistant account
- [ ] Alexa can control Music Assistant playback

---

## See Also

**NEW Documentation (2025-10-25)**:
- **[TAILSCALE_FUNNEL_CONFIGURATION_HA](TAILSCALE_FUNNEL_CONFIGURATION_HA.md)** - Complete Funnel setup guide (RECOMMENDED)
- **[HABoxHill Network Topology](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md)** - Container architecture details
- **[Tailscale OAuth Routing Contract](../03_INTERFACES/TAILSCALE_OAUTH_ROUTING.md)** - Network path and routing specifications
- **[Home Assistant Container Topology](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md)** - Container reference guide

**Existing Documentation**:
- **[Alexa OAuth Endpoints Contract](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md)** - API specifications
- **[Alexa Infrastructure Options](../02_REFERENCE/ALEXA_INFRASTRUCTURE_OPTIONS.md)** - Detailed option comparison
- **[Alexa Authentication Strategic Analysis](../00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md)** - Architectural principles
- **[Alexa Auth Troubleshooting](ALEXA_AUTH_TROUBLESHOOTING.md)** - Troubleshooting procedures
