# Alexa Infrastructure Options Reference
**Purpose**: Quick reference for public endpoint exposure options
**Audience**: System Administrators, DevOps, Decision Makers
**Layer**: 02_REFERENCE (Quick lookup and comparison)
**Related**:
- [Alexa OAuth Setup Progress](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md)
- [Alexa OAuth Endpoints Contract](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md)

**Last Updated**: 2025-10-25

---

## Intent

Quick reference for choosing how to expose Music Assistant OAuth server to Amazon Alexa. Compares three viable infrastructure approaches with clear trade-offs to enable fast decision-making.

---

## Current Infrastructure Context

**Music Assistant**: Docker container at `192.168.130.11:8096` (local network only)

**Available Resources**:
- Nabu Casa subscription (Home Assistant cloud service)
- Tailscale network (router + separate HA docker container)
- Standard home network (192.168.130.0/24)

**Constraint**: Tailscale CLI not available in Music Assistant docker container (Home Assistant add-on limitation)

**Requirement**: Alexa needs public HTTPS endpoint for OAuth authorization and token exchange

---

## Option Comparison Table

| Criterion | Nabu Casa Proxy | Tailscale Funnel | Direct Routing |
|-----------|----------------|------------------|----------------|
| **Public HTTPS** | ✅ Yes | ✅ Yes (if available) | ❌ No |
| **Uses Existing Infrastructure** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Additional Cost** | ✅ None (already paid) | ✅ None | ✅ None |
| **Setup Complexity** | 🟡 Medium (nginx config) | 🟡 Medium (funnel config) | 🔴 High (routing + NAT) |
| **Dependency on HA** | 🔴 High | 🟡 Medium | ✅ None |
| **Dependency on Subscription** | 🔴 Nabu Casa | 🔴 Tailscale | ✅ None |
| **Portability** | 🔴 Low (tied to HA) | 🟡 Medium | ✅ High |
| **Security** | ✅ Nginx layer | ✅ Tailscale layer | 🔴 Direct exposure |
| **Alexa Compatibility** | ✅ Guaranteed | ✅ Guaranteed | ❌ Unlikely |
| **Implementation Risk** | ✅ Low | 🟡 Medium | 🔴 High |
| **Maintenance Burden** | ✅ Low | ✅ Low | 🔴 High |
| **Recommended** | ✅ **YES** | 🟡 Backup | ❌ Avoid |

**Legend**: ✅ Good | 🟡 Acceptable | 🔴 Poor

---

## Option 1: Nabu Casa Nginx Proxy (RECOMMENDED)

### Summary
Use Home Assistant's existing Nabu Casa cloud connection to proxy OAuth requests to Music Assistant.

### How It Works
```
Internet
    ↓
[Nabu Casa Cloud] (handles TLS, provides public domain)
    ↓
[Home Assistant nginx] (proxies /alexa/* paths)
    ↓
Music Assistant Docker (192.168.130.11:8096)
```

### URLs
**Public OAuth Endpoints**:
- `https://[nabu-casa-id].ui.nabu.casa/alexa/authorize`
- `https://[nabu-casa-id].ui.nabu.casa/alexa/token`
- `https://[nabu-casa-id].ui.nabu.casa/alexa/health`

**Internal Music Assistant**:
- `http://192.168.130.11:8096/alexa/*`

### Advantages
- **Proven Infrastructure**: Uses existing paid cloud service
- **HTTPS Included**: Nabu Casa handles TLS certificates automatically
- **Low Risk**: Established reverse proxy pattern
- **Fast Setup**: Single nginx configuration file change
- **No Additional Cost**: Already paying for Nabu Casa
- **Security Layer**: Nginx provides request filtering and rate limiting
- **Managed Service**: Nabu Casa handles uptime, updates, security patches

### Disadvantages
- **Coupling to Home Assistant**: OAuth depends on HA infrastructure
- **Subscription Dependency**: If Nabu Casa subscription lapses, OAuth breaks
- **Single Point of Failure**: HA outage breaks OAuth
- **URL Tied to HA**: Cannot move OAuth without changing Alexa skill config
- **Shared Resource**: Nginx configuration affects all HA services

### Technical Requirements
- Access to Home Assistant nginx configuration
- Ability to reload/restart nginx
- Understanding of nginx proxy configuration syntax

### Implementation Complexity
**Effort**: 30-60 minutes (including testing)

**Skills Required**:
- Basic nginx configuration knowledge
- SSH access to Home Assistant box
- Understanding of reverse proxy concepts

**Configuration**:
```nginx
# Add to nginx server block
location /alexa/ {
    proxy_pass http://192.168.130.11:8096/alexa/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Cookie $http_cookie;
    proxy_redirect off;
}
```

### When to Choose This
- **You have active Nabu Casa subscription** ✅
- **Home Assistant is stable and reliable** ✅
- **You prefer proven, managed infrastructure** ✅
- **You want fastest path to working OAuth** ✅
- **You don't plan to move Music Assistant away from HA ecosystem** ✅

### When to Avoid This
- **No Nabu Casa subscription** (requires paid subscription)
- **Home Assistant frequently offline** (OAuth unavailable when HA down)
- **Planning to move Music Assistant to different host** (URL will change)
- **Prefer infrastructure independence** (use Tailscale instead)

---

## Option 2: Tailscale Funnel (BACKUP OPTION)

### Summary
Use Home Assistant's Tailscale docker container to expose Music Assistant via Tailscale Funnel.

### How It Works
```
Internet
    ↓
[Tailscale Funnel] (public HTTPS endpoint)
    ↓
[HA Tailscale Container] (routes traffic)
    ↓
Music Assistant Docker (192.168.130.11:8096)
```

### URLs
**Public OAuth Endpoints**:
- `https://[tailscale-hostname].ts.net/alexa/authorize`
- `https://[tailscale-hostname].ts.net/alexa/token`
- `https://[tailscale-hostname].ts.net/alexa/health`

**Internal Music Assistant**:
- `http://192.168.130.11:8096/alexa/*`

### Advantages
- **Infrastructure Independence**: Not tied to Home Assistant availability
- **Subscription Flexibility**: Different from Nabu Casa subscription
- **Tailscale-Managed HTTPS**: Automatic certificate handling
- **Portability**: Can move to different Tailscale node easily
- **Direct Tailscale Access**: Can also access via private Tailscale network
- **Built-in Security**: Tailscale ACLs provide additional security layer

### Disadvantages
- **Funnel Availability Unknown**: Must verify HA Tailscale container supports Funnel
- **Configuration Complexity**: Tailscale Funnel configuration more complex than nginx
- **Tailscale Dependency**: Depends on Tailscale service availability
- **Less Familiar**: Team may have less experience with Tailscale Funnel vs nginx
- **Debugging Harder**: Fewer standard tools for troubleshooting Tailscale routing

### Technical Requirements
- Home Assistant Tailscale container must support Funnel feature
- Access to Tailscale container configuration
- Understanding of Tailscale routing and Funnel concepts
- Tailscale admin access for ACL configuration

### Implementation Complexity
**Effort**: 1-2 hours (including verification and testing)

**Skills Required**:
- Tailscale Funnel configuration knowledge
- Docker container management
- Network routing understanding
- Tailscale ACL configuration

**Configuration** (example):
```bash
# Inside HA Tailscale container
tailscale funnel --https=443 --set-path=/alexa http://192.168.130.11:8096/alexa
```

### When to Choose This
- **Nabu Casa unavailable or unreliable** (subscription lapsed, service issues)
- **Prefer Tailscale ecosystem** (already using Tailscale extensively)
- **Want infrastructure independence from HA** (OAuth survives HA downtime)
- **Tailscale Funnel verified available** (confirmed in HA container)
- **Need private Tailscale access + public access** (dual access modes)

### When to Avoid This
- **Tailscale Funnel not available in HA container** (check first!)
- **No Tailscale experience on team** (nginx simpler and more familiar)
- **Nabu Casa works well** (don't add complexity unnecessarily)
- **Time-constrained** (Nabu Casa faster to implement)

### Verification Required
**Before choosing this option, verify**:
```bash
# SSH to Home Assistant box
# Check if Tailscale container has funnel capability
docker exec [tailscale-container] tailscale funnel --help

# Expected: Command help text (funnel supported)
# If error: Funnel not available, choose different option
```

---

## Option 3: Direct Tailscale Routing (NOT RECOMMENDED)

### Summary
Use router's Tailscale connection to route traffic to Music Assistant without Funnel.

### How It Works
```
Internet ❌ (Alexa likely cannot reach)
    ↓
[Tailscale Private Network] (VPN only, not public)
    ↓
[Router at 192.168.130.1] (Tailscale node)
    ↓
Music Assistant Docker (192.168.130.11:8096)
```

### URLs
**Private Tailscale Access Only**:
- `http://[tailscale-ip]:8096/alexa/*` (not public HTTPS!)

**Problem**: Amazon Alexa requires public HTTPS endpoint, not private VPN access.

### Why This Won't Work

**Critical Flaw**: Amazon Alexa OAuth account linking requires:
1. Public HTTPS endpoint (TLS certificate verification)
2. Accessible from Amazon's servers (not behind VPN)
3. Standard port 443 (HTTPS)

**What Direct Routing Provides**:
1. ❌ Private VPN access only (Tailscale network members only)
2. ❌ No automatic HTTPS/TLS
3. ❌ Non-standard port (8096)
4. ❌ Requires Amazon servers to join Tailscale network (impossible)

### Technical Reality

**Even if configured correctly**:
- OAuth endpoints only accessible to Tailscale network members
- Amazon Alexa backend cannot join your private Tailscale network
- No public HTTPS endpoint for Amazon to reach
- Account linking will fail with unreachable endpoint error

### When to Choose This
**NEVER** - Does not meet Amazon Alexa requirements

### When It Might Be Useful
- **Personal testing** from Tailscale-connected devices
- **Development** before public deployment
- **Internal tools** that don't require public access

**For Alexa OAuth**: Must use Option 1 (Nabu Casa) or Option 2 (Tailscale Funnel)

---

## Decision Matrix

### Choose Based on Your Priorities

**Priority: Fastest Implementation**
→ **Option 1: Nabu Casa** (30-60 minutes, familiar nginx)

**Priority: Infrastructure Independence**
→ **Option 2: Tailscale Funnel** (if available and verified)

**Priority: Lowest Maintenance**
→ **Option 1: Nabu Casa** (managed service, automatic updates)

**Priority: Portability**
→ **Option 2: Tailscale Funnel** (easier to move between hosts)

**Priority: Cost**
→ **Tie** (both use existing paid subscriptions)

**Priority: Security**
→ **Tie** (both provide HTTPS + security layer)

**Priority: Reliability**
→ **Option 1: Nabu Casa** (proven, established service)

---

## Implementation Effort Comparison

| Task | Nabu Casa | Tailscale Funnel |
|------|-----------|------------------|
| Verify prerequisites | 5 min (check nginx access) | 15 min (verify Funnel support) |
| Configuration | 15 min (edit nginx) | 30 min (configure Funnel) |
| Testing local access | 5 min | 10 min |
| Testing public access | 10 min | 15 min |
| Troubleshooting buffer | 15 min | 30 min |
| Documentation | 10 min | 15 min |
| **Total Estimated Time** | **60 min** | **115 min** |

---

## Failure Scenarios and Recovery

### Nabu Casa Proxy Failures

**Scenario 1: Nginx misconfiguration breaks Home Assistant**
- **Symptom**: HA UI stops responding after nginx change
- **Recovery**: Rollback nginx config, reload nginx (5 min)
- **Prevention**: Test nginx syntax before reload (`nginx -t`)

**Scenario 2: Nabu Casa subscription lapses**
- **Symptom**: OAuth endpoints return 502/503 errors
- **Recovery**: Renew subscription or switch to Tailscale Funnel
- **Prevention**: Set calendar reminder before subscription expiry

**Scenario 3: Home Assistant offline**
- **Symptom**: All OAuth requests fail
- **Recovery**: Restart Home Assistant
- **Prevention**: Ensure HA system stability before deploying OAuth

### Tailscale Funnel Failures

**Scenario 1: Funnel not available in HA container**
- **Symptom**: `tailscale funnel` command not found
- **Recovery**: Switch to Nabu Casa option instead
- **Prevention**: Verify Funnel support before starting implementation

**Scenario 2: Tailscale service outage**
- **Symptom**: Public endpoint unreachable
- **Recovery**: Wait for Tailscale service restoration
- **Prevention**: Monitor Tailscale status page

**Scenario 3: Routing misconfiguration**
- **Symptom**: Funnel works but routes to wrong service
- **Recovery**: Fix Funnel path configuration
- **Prevention**: Test with curl before configuring Alexa skill

---

## Cost Analysis

### Initial Setup Cost
| Option | Time Cost | Monetary Cost |
|--------|-----------|---------------|
| Nabu Casa | 1 hour (engineer time) | $0 (existing subscription) |
| Tailscale Funnel | 2 hours (engineer time) | $0 (existing subscription) |
| Direct Routing | N/A | N/A (won't work) |

### Ongoing Maintenance Cost
| Option | Monthly Time | Monthly Subscription |
|--------|--------------|---------------------|
| Nabu Casa | ~15 min (monitoring) | $6.50 (existing HA subscription) |
| Tailscale Funnel | ~15 min (monitoring) | $0 (free tier) or $6 (personal) |

**Note**: Both options use existing subscriptions, no additional cost for OAuth specifically.

---

## Migration Considerations

### Future Platform Changes

**If moving Music Assistant to different host**:

**Nabu Casa Path**:
1. Update nginx proxy target IP
2. Reload nginx
3. No Alexa skill changes needed (URL same)

**Tailscale Funnel Path**:
1. Move Funnel to new Tailscale node
2. Update Funnel routing
3. Possibly update Alexa skill if hostname changes

**Winner**: Nabu Casa (URL stable, only internal routing changes)

### If Switching Between Options

**Nabu Casa → Tailscale Funnel**:
1. Set up Tailscale Funnel
2. Update Alexa skill OAuth URLs
3. Test new endpoints
4. Remove nginx proxy configuration
5. Users must re-link accounts (URL changed)

**Tailscale Funnel → Nabu Casa**:
1. Set up nginx proxy
2. Update Alexa skill OAuth URLs
3. Test new endpoints
4. Remove Tailscale Funnel
5. Users must re-link accounts (URL changed)

**Impact**: URL change requires Alexa skill reconfiguration + user re-linking.

---

## Quick Decision Guide

### Answer These Questions

**1. Do you have active Nabu Casa subscription?**
- Yes → Consider Nabu Casa (Option 1)
- No → Must use Tailscale Funnel (Option 2)

**2. Is Home Assistant stable and reliable?**
- Yes → Nabu Casa safe choice
- No → Prefer Tailscale Funnel (independent of HA)

**3. Do you need this working today?**
- Yes → Nabu Casa (faster setup)
- No → Either option acceptable

**4. Do you have nginx configuration experience?**
- Yes → Nabu Casa easier
- No → Tailscale Funnel may be simpler (less config)

**5. Is infrastructure independence important?**
- Yes → Tailscale Funnel better
- No → Nabu Casa fine

### Recommended Decision Tree

```
START
  │
  ├─ Have Nabu Casa? ──NO──→ Use Tailscale Funnel (Option 2)
  │                          [Verify Funnel support first!]
  YES
  │
  ├─ Need it working in <2 hours? ──YES──→ Use Nabu Casa (Option 1)
  │                                        [Fastest path]
  NO
  │
  ├─ HA frequently offline? ──YES──→ Use Tailscale Funnel (Option 2)
  │                                   [Infrastructure independence]
  NO
  │
  └─ Use Nabu Casa (Option 1)
     [Recommended default: proven, fast, reliable]
```

---

## Testing Checklist

### Before Choosing Option

**For Nabu Casa**:
- [ ] Verify Nabu Casa subscription active
- [ ] Confirm nginx configuration access
- [ ] Test nginx reload works
- [ ] Backup current nginx configuration

**For Tailscale Funnel**:
- [ ] Verify Tailscale container has Funnel support
- [ ] Confirm Tailscale admin access
- [ ] Test Tailscale container can reach Music Assistant
- [ ] Review Tailscale ACL configuration

### After Implementation

**All Options**:
- [ ] Health endpoint accessible from internet
- [ ] Authorization endpoint redirects correctly
- [ ] Token endpoint accepts POST requests
- [ ] HTTPS certificate valid (no warnings)
- [ ] Response times acceptable (<1 second)
- [ ] Error responses return proper JSON

---

## See Also

- **[Alexa OAuth Setup Progress](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md)** - Current implementation status
- **[Alexa OAuth Endpoints Contract](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md)** - API specifications
- **[Nabu Casa Documentation](https://www.nabucasa.com/config/)** - Official Nabu Casa docs
- **[Tailscale Funnel Documentation](https://tailscale.com/kb/1223/tailscale-funnel/)** - Official Funnel docs
