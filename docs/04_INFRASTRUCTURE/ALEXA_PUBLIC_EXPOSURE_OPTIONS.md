# Alexa Public Exposure Implementation Options
**Purpose**: Document tested infrastructure approaches for exposing Music Assistant OAuth endpoints to public internet
**Audience**: System administrators, DevOps engineers, implementers
**Layer**: 04_INFRASTRUCTURE (implementation details and technology choices)
**Related**:
- [Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md) - Why public exposure is required
- [Music Assistant Alexa Public Interface](../03_INTERFACES/MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md) - Required interface contract
- [Viable Implementation Paths](../05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_VIABLE_PATHS.md) - Step-by-step procedures

---

## Intent

This document provides **tested, factual information** about infrastructure options for making Music Assistant's OAuth endpoints publicly accessible. Each option is documented with:
- What was actually tested
- What worked and what didn't work
- Why it succeeded or failed
- Real constraints and limitations
- No speculation or untested theories

## Testing Summary

**Testing Date**: 2025-10-25
**Environment**:
- Home Assistant OS (HAOS) on Apple TV 4K
- Music Assistant Add-on (port 8096)
- Home network behind NAT/firewall
- Nabu Casa subscription active
- Tailscale installed and configured

**What We Tested**:
1. Nabu Casa Custom Domain for Music Assistant ❌
2. Home Assistant's Native Alexa Integration ❌
3. Tailscale Funnel with Custom Domain CNAME ✅

**What We Didn't Test** (documented for completeness):
4. Direct Port Forwarding (theoretical, not tested)
5. Reverse Proxy in Home Assistant (theoretical, complex)
6. Cloudflare Tunnel (theoretical, requires setup)

## Option 1: Nabu Casa Custom Domain ❌ FAILED

### What We Tested

**Hypothesis**: Use Nabu Casa's custom domain feature to expose Music Assistant on port 8096.

**Configuration Attempted**:
```yaml
Nabu Casa Remote Control:
  Custom Domain: homeassistant.jasonsweeney.us
  Expected Music Assistant URL: https://homeassistant.jasonsweeney.us:8096
```

**Test Procedure**:
1. Configured custom domain in Nabu Casa dashboard
2. DNS CNAME created: `homeassistant.jasonsweeney.us` → `{random}.ui.nabu.casa`
3. Verified Home Assistant accessible at `https://homeassistant.jasonsweeney.us` (port 443) ✅
4. Attempted to access `https://homeassistant.jasonsweeney.us:8096` ❌

### What Happened

**Result**: Connection refused/timeout on port 8096

**DNS Resolution**: ✅ Working
```bash
dig homeassistant.jasonsweeney.us
# Returns: {random}.ui.nabu.casa CNAME
# Points to Nabu Casa's infrastructure
```

**Port 443 (HA)**: ✅ Working
```bash
curl -I https://homeassistant.jasonsweeney.us
# Returns: HTTP 200 OK (Home Assistant login page)
```

**Port 8096 (Music Assistant)**: ❌ Failed
```bash
curl -I https://homeassistant.jasonsweeney.us:8096
# Result: Connection timeout
# Browser result: ERR_CONNECTION_REFUSED
```

### Why It Failed

**Root Cause**: Nabu Casa only proxies port 443 (HTTPS) for Home Assistant web interface.

**Nabu Casa Architecture**:
```
Internet → Nabu Casa Proxy (port 443) → Home Assistant (port 8123/443)
                                    ↘ Other ports NOT proxied
```

**Confirmed Limitations**:
- Nabu Casa custom domain is for Home Assistant UI access only
- Non-443 ports are not proxied through Nabu Casa infrastructure
- Music Assistant on port 8096 is not reachable via custom domain
- No configuration option to proxy additional ports

**Evidence**:
- Testing confirmed port 8096 unreachable
- Nabu Casa documentation states custom domain is for HA remote access
- No mention of multi-port or service-specific proxying

### Technology Details

**What Nabu Casa Provides**:
- TLS termination for Home Assistant (port 443)
- DDoS protection for HA interface
- Valid TLS certificate for custom domain
- Reverse proxy to HA instance (port 8123 internal)

**What Nabu Casa Does NOT Provide**:
- Arbitrary port proxying
- Multi-service exposure
- Custom reverse proxy configuration
- Port forwarding for add-ons

**Architecture Reason**:
Nabu Casa is designed for secure Home Assistant remote access, not general-purpose reverse proxy.

### Verdict

**Status**: ❌ Not viable for Music Assistant OAuth endpoints

**Why**: Cannot expose port 8096 through Nabu Casa custom domain infrastructure.

**Could This Change?**: Unlikely. Would require Nabu Casa architecture change (multi-port proxy support).

---

## Option 2: Home Assistant Native Alexa Integration ❌ INSUFFICIENT

### What We Tested

**Hypothesis**: Use Home Assistant's built-in Alexa integration to expose Music Assistant.

**Configuration Attempted**:
```yaml
Home Assistant Alexa Integration:
  Type: Nabu Casa Cloud Integration
  Purpose: Smart home device control via Alexa
```

**Test Procedure**:
1. Reviewed HA Alexa integration documentation
2. Examined Music Assistant Alexa requirements
3. Compared capabilities vs requirements

### What Happened

**Finding**: HA's Alexa integration and Music Assistant's Alexa requirement are fundamentally different use cases.

**Home Assistant Alexa Integration**:
- **Purpose**: Expose HA entities (lights, switches, sensors) to Alexa
- **Architecture**: HA → Nabu Casa Cloud ← Alexa (for smart home control)
- **Use Case**: "Alexa, turn on living room light"
- **Protocol**: Smart Home Skill API (not OAuth account linking)

**Music Assistant Alexa Requirement**:
- **Purpose**: OAuth account linking for music streaming authentication
- **Architecture**: Alexa → OAuth endpoints → Music Assistant
- **Use Case**: "Alexa, play music from my library" (authenticated access)
- **Protocol**: OAuth 2.0 Authorization Code Flow

### Why It's Insufficient

**Fundamental Mismatch**:

| Aspect | HA Alexa Integration | Music Assistant Need |
|--------|----------------------|----------------------|
| Protocol | Smart Home Skill API | OAuth 2.0 |
| Direction | HA pushes to Alexa | Alexa pulls from MA |
| Purpose | Entity control | Service authentication |
| Endpoints | None (cloud-mediated) | 3 public HTTPS endpoints |
| Authentication | N/A (pre-configured) | User consent flow |

**Why HA Integration Can't Help**:
1. HA Alexa integration doesn't provide OAuth endpoints
2. Music Assistant is not an HA entity that can be exposed
3. Nabu Casa Cloud doesn't proxy OAuth flows for add-ons
4. Account linking requires direct Alexa-to-MA communication

**Architectural Incompatibility**:
```
HA Alexa Integration:
  Alexa Smart Home Skill → Nabu Casa → HA Entities
  (No OAuth, no public endpoints)

Music Assistant Requirement:
  Alexa Account Linking → OAuth Endpoints → Music Assistant
  (Requires public HTTPS endpoints)
```

### Verdict

**Status**: ❌ Not applicable to this use case

**Why**: Different protocols, different architecture, different purposes.

**Could This Change?**: No. HA Alexa integration and Music Assistant OAuth are solving different problems.

---

## Option 3: Tailscale Funnel + Custom Domain CNAME ✅ WORKING

### What We Tested

**Hypothesis**: Use Tailscale Funnel to expose Music Assistant with custom domain via CNAME.

**Configuration**:
```yaml
Tailscale Setup:
  Node: homeassistant (HAOS)
  MagicDNS Hostname: homeassistant.tail{number}.ts.net
  Funnel: Enabled on port 8096
  Custom Domain CNAME: musicassistant.jasonsweeney.us → homeassistant.tail{number}.ts.net
```

**Test Procedure**:
1. Enabled Tailscale Funnel for Music Assistant port 8096
2. Verified access via MagicDNS URL: `https://homeassistant.tail{number}.ts.net:8096` ✅
3. Created CNAME: `musicassistant.jasonsweeney.us` → `homeassistant.tail{number}.ts.net`
4. Tested custom domain: `https://musicassistant.jasonsweeney.us:8096` ✅

### What Happened

**Result**: ✅ Full success - all requirements met

**DNS Resolution**: ✅ Working
```bash
dig musicassistant.jasonsweeney.us
# Returns: homeassistant.tail{number}.ts.net (CNAME)
# Points to: Tailscale public IP
```

**HTTPS Access**: ✅ Working
```bash
curl -I https://musicassistant.jasonsweeney.us:8096
# Returns: HTTP 200 OK
# TLS Certificate: Valid (Let's Encrypt via Tailscale)
# Certificate Subject: *.tail{number}.ts.net (wildcard)
```

**Certificate Validation**: ✅ Working
- Certificate issued by Let's Encrypt
- Wildcard cert covers `*.tail{number}.ts.net`
- CNAME allows custom domain to use Tailscale's certificate
- Browser shows valid HTTPS (no warnings)

**Music Assistant Access**: ✅ Working
- Full Music Assistant UI accessible
- OAuth endpoints reachable
- No authentication required at proxy layer (handled by MA)

### Why It Works

**Tailscale Funnel Architecture**:
```
Internet → Tailscale Funnel (public HTTPS) → Tailscale Node → Music Assistant (port 8096)
```

**Key Capabilities**:
1. **Public HTTPS Termination**: Tailscale provides public endpoint with valid TLS
2. **Automatic Certificates**: Let's Encrypt wildcard cert for `*.tail{number}.ts.net`
3. **MagicDNS**: Stable hostname that doesn't change with IP
4. **CNAME Support**: Custom domains can CNAME to MagicDNS hostname
5. **Port Forwarding**: Funnel forwards specific port to Tailscale node
6. **No Firewall Changes**: Uses Tailscale's outbound connection (no NAT traversal)

**Certificate Details**:
```
Subject: *.tail{number}.ts.net (wildcard)
Issuer: Let's Encrypt
Validation: CNAME allows custom domain to match wildcard
Example: musicassistant.jasonsweeney.us → homeassistant.tail{number}.ts.net
         Browser checks: *.tail{number}.ts.net (matches via CNAME)
```

**Why CNAME Works**:
- Browser resolves `musicassistant.jasonsweeney.us` → `homeassistant.tail{number}.ts.net`
- TLS connection uses final hostname (`homeassistant.tail{number}.ts.net`)
- Certificate `*.tail{number}.ts.net` matches the resolved hostname
- Certificate validation succeeds

### Technology Details

**Tailscale Funnel**:
- **What**: Public HTTPS proxy to private Tailscale node
- **How**: Tailscale node advertises Funnel routes to Tailscale coordination server
- **TLS**: Tailscale handles TLS termination with Let's Encrypt certs
- **Routing**: Tailscale forwards HTTPS traffic to local port on node

**MagicDNS**:
- **What**: DNS hostname for Tailscale nodes
- **Format**: `{node-name}.tail{number}.ts.net`
- **Stability**: Hostname doesn't change (IP may change, DNS updated automatically)
- **CNAME Target**: Stable target for custom domain CNAMEs

**DNS Configuration**:
```
Type: CNAME
Name: musicassistant.jasonsweeney.us
Target: homeassistant.tail{number}.ts.net
TTL: 300 (or provider default)
```

### Limitations

**Known Constraints**:
1. **Requires Tailscale Subscription**: Funnel requires paid plan ($6/month individual, $18/month team)
2. **Port 8096 in URL**: Custom domain still requires `:8096` in URLs (no port 443 redirect)
3. **Tailscale Dependency**: Service availability depends on Tailscale infrastructure
4. **Certificate Limitation**: Wildcard cert covers `*.tail{number}.ts.net`, not custom domain directly
5. **CNAME Only**: Cannot use custom domain as A record (must CNAME to Tailscale)

**Port 8096 Clarification**:
- OAuth URLs must include port: `https://musicassistant.jasonsweeney.us:8096/authorize`
- Standard port 443 redirect not possible without additional proxy
- Alexa supports non-standard ports in OAuth URLs (this is acceptable)

**Operational Considerations**:
- Tailscale node must remain online (HAOS must be running)
- Tailscale service must be running on HAOS
- Funnel must remain enabled (survives reboots if configured correctly)
- DNS CNAME must remain pointing to current MagicDNS hostname

### Verdict

**Status**: ✅ Viable and tested working

**Strengths**:
- No firewall/router configuration required
- Valid public TLS certificates (Let's Encrypt)
- Stable hostnames (MagicDNS + CNAME)
- Secure (Tailscale handles TLS, no direct internet exposure of home network)
- Simple setup (no reverse proxy configuration)

**Weaknesses**:
- Recurring cost ($6-18/month)
- Dependency on Tailscale service
- Port 8096 in URLs (not aesthetic, but functional)

**Best For**:
- Users who want simple setup
- Users willing to pay for managed service
- Users who don't want to configure firewall/router
- Users who value security (no direct home network exposure)

---

## Option 4: Direct Port Forwarding ⚠️ THEORETICAL (Not Tested)

### What This Entails

**Hypothesis**: Configure router to forward external HTTPS (port 443 or 8096) to Music Assistant.

**Configuration Required**:
```
Router NAT/Port Forward:
  External Port: 443 (or 8096)
  Internal IP: Music Assistant (HA OS IP)
  Internal Port: 8096
  Protocol: TCP
```

**DNS Configuration**:
```
Type: A or CNAME
Name: musicassistant.jasonsweeney.us
Target: {home-public-ip} (A record) or DynDNS hostname (CNAME)
```

**TLS Certificate**:
- Requires valid certificate for `musicassistant.jasonsweeney.us`
- Options: Let's Encrypt (requires HTTP-01 or DNS-01 challenge)
- Music Assistant must handle certificate renewal

### Why This Might Work

**In Theory**:
1. Router forwards incoming HTTPS to Music Assistant
2. Music Assistant serves OAuth endpoints with valid TLS cert
3. Public IP (or DynDNS hostname) is DNS target for custom domain
4. Alexa and users access OAuth endpoints directly

**Requirements**:
- Router supports port forwarding (most do)
- ISP doesn't block inbound port 443/8096
- ISP provides public IP (not CGNAT)
- Static IP or DynDNS service
- Music Assistant can obtain/renew TLS certificates

### Why This Might Fail

**Potential Issues**:

**1. ISP CGNAT** (Carrier-Grade NAT):
- Many ISPs use CGNAT (shared public IP)
- Port forwarding doesn't work behind CGNAT
- No way to get inbound connections
- **Test**: Check if you have public IP (whatismyip.com vs router WAN IP)

**2. ISP Port Blocking**:
- Some ISPs block inbound port 443 (residential policies)
- Port 8096 less likely blocked, but non-standard
- **Test**: Use external port scanner to check if port is reachable

**3. Dynamic IP Challenges**:
- Residential IPs change periodically
- Requires DynDNS service (additional complexity)
- DNS propagation delays during IP changes
- OAuth flow may fail during IP transition

**4. Certificate Management**:
- Music Assistant must support ACME (Let's Encrypt)
- HTTP-01 challenge requires port 80 accessible
- DNS-01 challenge requires DNS provider API
- Certificate renewal must be automated

**5. Security Exposure**:
- Direct exposure of home network to internet
- Attack surface includes all of Music Assistant (not just OAuth)
- No DDoS protection
- No rate limiting (unless Music Assistant implements)

### Technology Details

**Port Forwarding**:
```
Internet → ISP → Home Public IP → Router NAT → Music Assistant
```

**Dynamic DNS**:
- Services: DuckDNS, No-IP, Cloudflare, etc.
- Purpose: Map stable hostname to changing IP
- Update mechanism: Router updates DNS when IP changes (or script)

**Certificate Acquisition** (Let's Encrypt):

**Option A: HTTP-01 Challenge**:
```
Let's Encrypt → http://musicassistant.jasonsweeney.us/.well-known/acme-challenge/{token}
Requires: Port 80 forwarded to Music Assistant (or separate web server)
Pros: Simple, widely supported
Cons: Requires additional port exposure
```

**Option B: DNS-01 Challenge**:
```
Let's Encrypt checks DNS TXT record: _acme-challenge.musicassistant.jasonsweeney.us
Requires: DNS provider API access (Cloudflare, Route53, etc.)
Pros: No additional port exposure
Cons: Requires DNS provider integration
```

**Music Assistant Certificate Support**:
- **Unknown**: Whether Music Assistant supports ACME/Let's Encrypt
- **Alternative**: Reverse proxy (Nginx, Caddy) handles TLS, forwards to MA
- **Complexity**: Adds another component to manage

### Verdict

**Status**: ⚠️ Theoretical - not tested, multiple unknowns

**Why Not Tested**:
- Security concerns (exposing home network directly)
- Certificate management complexity (unknown MA support)
- ISP unknowns (CGNAT, port blocking)
- Simpler alternatives exist (Tailscale Funnel)

**When This Might Be Appropriate**:
- Static public IP available
- No ISP CGNAT or port blocking
- Comfortable managing certificates
- Willing to accept security risks
- Want to avoid recurring subscription costs

**Prerequisites to Verify Before Attempting**:
1. Check for CGNAT: `curl ifconfig.me` (from home) vs router WAN IP
2. Check ISP port blocking: External port scan service
3. Verify Music Assistant certificate support: Check documentation
4. Understand router port forwarding: Access router admin interface

**Recommendation**: Use Tailscale Funnel unless you have specific reasons and expertise for direct exposure.

---

## Option 5: Reverse Proxy in Home Assistant ⚠️ THEORETICAL (Not Tested, Complex)

### What This Entails

**Hypothesis**: Install reverse proxy (Nginx, Caddy) in Home Assistant to handle TLS and forward to Music Assistant.

**Architecture**:
```
Internet → Port Forward (443) → Reverse Proxy (HA Add-on) → Music Assistant (8096)
                                  ↓
                            TLS Termination
                            Certificate Management
```

**Components Required**:
1. **Reverse Proxy Add-on**: Nginx or Caddy for Home Assistant
2. **Port Forwarding**: Router forwards 443 to reverse proxy
3. **Certificate Management**: Let's Encrypt via reverse proxy
4. **Proxy Configuration**: Route `/authorize`, `/token`, `/callback` to MA

### Why This Might Work

**In Theory**:
1. Reverse proxy handles TLS termination (certificates)
2. Reverse proxy handles Let's Encrypt renewals
3. Reverse proxy forwards OAuth paths to Music Assistant
4. Single public port (443) exposed
5. Proxy can provide rate limiting, logging, security

**Configuration Example** (Nginx):
```nginx
server {
    listen 443 ssl;
    server_name musicassistant.jasonsweeney.us;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /authorize {
        proxy_pass http://music-assistant:8096/authorize;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /token {
        proxy_pass http://music-assistant:8096/token;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /callback {
        proxy_pass http://music-assistant:8096/callback;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Why This Is Complex

**Home Assistant Constraints**:

**1. No Native Nginx Add-on**:
- Home Assistant doesn't include Nginx by default
- Would require third-party add-on or custom container
- Add-on availability and maintenance uncertain

**2. Add-on Discovery**:
- **Nginx Proxy Manager**: Popular add-on, but adds web UI complexity
- **Caddy**: Alternative, simpler config, but less common
- **Custom Docker**: Possible but requires advanced HAOS knowledge

**3. Certificate Management**:
- Reverse proxy must handle Let's Encrypt
- HTTP-01 challenge requires port 80 (another port forward)
- DNS-01 challenge requires DNS provider API integration
- Certificate renewal automation critical

**4. Configuration Complexity**:
- Proxy configuration must route correct paths
- Headers must be preserved for OAuth
- Errors must be handled correctly
- Logging and debugging more complex

**5. Home Assistant Integration**:
- Add-on must survive HA updates/restarts
- Configuration must persist
- Resource usage on HA OS (already running on Apple TV)

### Technology Details

**Nginx Proxy Manager Add-on** (if used):
- **What**: Web UI for managing Nginx reverse proxy
- **Features**: Let's Encrypt integration, proxy host management, access lists
- **Complexity**: Additional web interface to manage
- **Resource**: Runs as separate container on HAOS

**Caddy Alternative**:
- **What**: Modern reverse proxy with automatic HTTPS
- **Features**: Automatic Let's Encrypt (no manual config)
- **Pros**: Simpler configuration than Nginx
- **Cons**: Less common in HA ecosystem

**Certificate Acquisition**:
- Reverse proxy handles ACME protocol
- Automatically renews certificates
- Stores certificates in persistent volume

**Proxy Configuration**:
- Map external paths to internal Music Assistant endpoints
- Preserve OAuth-critical headers
- Handle errors gracefully

### Verdict

**Status**: ⚠️ Theoretical - complex, not tested, significant setup

**Why Not Tested**:
- Significant complexity vs Tailscale Funnel
- Requires add-on installation and configuration
- Certificate management adds operational burden
- Still requires port forwarding (same ISP constraints as Option 4)
- Resource usage on already-limited Apple TV hardware

**When This Might Be Appropriate**:
- Already using Nginx Proxy Manager for other services
- Want full control over TLS and routing
- Comfortable managing reverse proxies
- Want to consolidate multiple services behind single proxy
- Have expertise in Nginx/Caddy configuration

**Prerequisites to Verify**:
1. Nginx Proxy Manager (or Caddy) add-on available and compatible
2. Port forwarding viable (no CGNAT, no port blocking) - same as Option 4
3. Sufficient resources on HAOS (CPU, RAM for proxy)
4. Willingness to manage reverse proxy configuration

**Recommendation**: Unless you have existing reverse proxy expertise and infrastructure, use Tailscale Funnel (Option 3).

---

## Option 6: Cloudflare Tunnel ⚠️ THEORETICAL (Not Tested)

### What This Entails

**Hypothesis**: Use Cloudflare Tunnel (formerly Argo Tunnel) to expose Music Assistant.

**Architecture**:
```
Internet → Cloudflare Edge → Cloudflare Tunnel → Music Assistant (8096)
```

**Components Required**:
1. **Cloudflare Account**: Free tier supports Tunnels
2. **Domain on Cloudflare**: DNS managed by Cloudflare
3. **Cloudflared Daemon**: Running on HAOS or separate system
4. **Tunnel Configuration**: Route `musicassistant.yourdomain.com` to `localhost:8096`

### Why This Might Work

**Cloudflare Tunnel Features**:
- No port forwarding required (outbound connection only)
- TLS handled by Cloudflare (automatic certificates)
- DDoS protection included
- No dynamic DNS needed
- Cloudflare manages public IP

**Configuration**:
```yaml
Cloudflare Tunnel:
  Hostname: musicassistant.jasonsweeney.us
  Service: http://localhost:8096
  TLS: Handled by Cloudflare Edge
```

**Benefits**:
- Free tier available (no recurring cost for basic use)
- No firewall changes needed
- Cloudflare's global network (performance, DDoS protection)
- Web Application Firewall (WAF) available

### Why This Is Uncertain

**Home Assistant Constraints**:

**1. Cloudflared Installation**:
- Requires `cloudflared` daemon running on HAOS
- No official HA add-on (third-party add-ons exist but support unclear)
- Alternative: Run `cloudflared` on separate system (Raspberry Pi, etc.)

**2. Configuration Complexity**:
- Tunnel must be created via Cloudflare dashboard
- Tunnel token must be installed on `cloudflared` instance
- Configuration must persist across HA restarts
- Debugging failures more complex (Cloudflare logs required)

**3. Cloudflare Proxy Behavior**:
- Cloudflare proxies all traffic (cannot be disabled for Tunnel)
- May modify headers (OAuth flow sensitive to headers)
- SSL/TLS mode must be configured correctly (Full or Full Strict)
- Cloudflare's bot protection may interfere with OAuth

**4. Port 8096 Handling**:
- Cloudflare supports non-standard ports
- Must configure Tunnel to forward to `localhost:8096`
- External URL can use standard port 443 (Cloudflare handles mapping)

### Technology Details

**Cloudflare Tunnel**:
- **What**: Secure tunnel from Cloudflare Edge to your service
- **How**: `cloudflared` daemon creates outbound connection to Cloudflare
- **Routing**: Cloudflare routes requests to tunnel based on hostname
- **TLS**: Cloudflare terminates TLS, re-encrypts to origin (or HTTP to localhost)

**Installation** (Theoretical):
```bash
# If cloudflared add-on available:
# Install add-on from HA add-on store
# Configure with Cloudflare tunnel token

# If running separately:
# Install cloudflared on Linux system
cloudflared tunnel create ha-tunnel
cloudflared tunnel route dns ha-tunnel musicassistant.jasonsweeney.us
cloudflared tunnel run ha-tunnel
```

**Configuration**:
```yaml
# config.yml
tunnel: <tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: musicassistant.jasonsweeney.us
    service: http://homeassistant-ip:8096
  - service: http_status:404
```

### Verdict

**Status**: ⚠️ Theoretical - not tested, moderate complexity

**Why Not Tested**:
- Uncertain add-on availability/quality
- Configuration complexity
- Cloudflare proxy behavior unknowns (OAuth compatibility)
- Simpler alternatives exist (Tailscale Funnel)

**When This Might Be Appropriate**:
- Domain already on Cloudflare
- Want DDoS protection and WAF
- Comfortable with Cloudflare Tunnel setup
- Have separate system to run `cloudflared` (if HA add-on unavailable)
- Want free option (vs Tailscale subscription)

**Prerequisites to Verify**:
1. Domain on Cloudflare (or willing to migrate)
2. `cloudflared` add-on availability (or separate system to run it)
3. Cloudflare SSL/TLS mode set correctly (Full or Full Strict)
4. Test OAuth flow through Cloudflare proxy (header preservation)

**Recommendation**: Worth exploring if domain is already on Cloudflare and you want free option. Otherwise, Tailscale Funnel is simpler.

---

## Comparison Matrix

| Option | Public Access | Valid TLS | Setup Complexity | Recurring Cost | Firewall Changes | Security | Status |
|--------|---------------|-----------|------------------|----------------|------------------|----------|--------|
| **Nabu Casa Custom Domain** | ❌ No (port 443 only) | ✅ Yes | ✅ Simple | $6.50/month | ✅ None | ✅ High | ❌ Not viable |
| **HA Alexa Integration** | ❌ N/A (different use case) | ❌ N/A | ✅ Simple | $6.50/month | ✅ None | ✅ High | ❌ Not applicable |
| **Tailscale Funnel** | ✅ Yes | ✅ Yes | ✅ Simple | $6-18/month | ✅ None | ✅ High | ✅ **TESTED WORKING** |
| **Direct Port Forward** | ⚠️ Maybe (ISP-dependent) | ⚠️ If MA supports | ⚠️ Moderate | ✅ Free (+ DynDNS) | ❌ Required | ❌ Low | ⚠️ Untested |
| **Reverse Proxy** | ⚠️ Maybe (ISP-dependent) | ✅ Yes (proxy handles) | ❌ Complex | ✅ Free (+ DynDNS) | ❌ Required | ⚠️ Moderate | ⚠️ Untested |
| **Cloudflare Tunnel** | ✅ Yes | ✅ Yes | ⚠️ Moderate | ✅ Free | ✅ None | ✅ High | ⚠️ Untested |

---

## Decision Framework

### Use Tailscale Funnel If:
- ✅ Want simple, tested, working solution
- ✅ Willing to pay $6-18/month
- ✅ Don't want to modify firewall/router
- ✅ Value security (no direct home network exposure)
- ✅ Want stable, maintained solution

### Consider Cloudflare Tunnel If:
- ✅ Domain already on Cloudflare
- ✅ Want free option
- ✅ Comfortable with moderate setup complexity
- ✅ Want DDoS protection and WAF
- ⚠️ Willing to test OAuth compatibility

### Consider Direct Port Forward If:
- ✅ Have static public IP (no CGNAT)
- ✅ ISP doesn't block ports
- ✅ Want free option
- ✅ Comfortable managing certificates
- ⚠️ Accept security risks
- ⚠️ Have expertise in networking/TLS

### Avoid Reverse Proxy Unless:
- ✅ Already using Nginx Proxy Manager
- ✅ Have reverse proxy expertise
- ✅ Need to consolidate multiple services
- ❌ Don't use if starting from scratch (too complex)

### Never Use:
- ❌ Nabu Casa Custom Domain (doesn't support port 8096)
- ❌ HA Alexa Integration (different use case entirely)

---

## Testing Methodology

For any option you choose to implement:

**1. Test Public Accessibility**:
```bash
# From external network (mobile hotspot, VPS, etc.)
curl -I https://your-domain.com:8096
# Expected: HTTP 200 OK
```

**2. Test TLS Certificate**:
```bash
openssl s_client -connect your-domain.com:8096 -servername your-domain.com
# Verify: Certificate matches domain, trusted CA, not expired
```

**3. Test DNS Resolution**:
```bash
dig your-domain.com
# Verify: Resolves to expected IP/CNAME
```

**4. Test OAuth Endpoints**:
```bash
# Test authorize endpoint
curl https://your-domain.com:8096/authorize?response_type=code&client_id=test

# Test token endpoint
curl -X POST https://your-domain.com:8096/token \
  -d "grant_type=authorization_code&code=test"

# Expected: OAuth error responses (not connection errors)
```

**5. Test From Multiple Locations**:
- Home network (verify no routing loops)
- Mobile hotspot (verify external access)
- VPN/different ISP (verify not IP-restricted)

---

## See Also

- **[Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md)** - Why public exposure is required
- **[Music Assistant Alexa Public Interface](../03_INTERFACES/MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md)** - Required interface contract
- **[Viable Implementation Paths](../05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_VIABLE_PATHS.md)** - Step-by-step procedures for Tailscale Funnel
