# Music Assistant Alexa Integration - Viable Implementation Paths
**Purpose**: Step-by-step operational procedures for implementing tested, viable approaches to expose Music Assistant OAuth to Alexa
**Audience**: System administrators implementing the solution
**Layer**: 05_OPERATIONS (concrete procedures and runbooks)
**Related**:
- [Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md) - Why this is needed
- [Music Assistant Alexa Public Interface](../03_INTERFACES/MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md) - Interface requirements
- [Public Exposure Options](../04_INFRASTRUCTURE/ALEXA_PUBLIC_EXPOSURE_OPTIONS.md) - Technology options comparison

---

## Intent

This document provides **concrete, step-by-step procedures** for implementing the viable path: **Tailscale Funnel with Custom Domain CNAME**. This is the only approach that has been tested and verified working as of 2025-10-25.

Other theoretical approaches are documented for reference but have not been tested and may require additional research and troubleshooting.

---

## Path 1: Tailscale Funnel + Custom Domain CNAME ✅ TESTED WORKING

**Status**: ✅ Verified working on 2025-10-25
**Difficulty**: Low
**Time**: 30-60 minutes
**Cost**: $6/month (individual) or $18/month (team) Tailscale subscription
**Prerequisites**: Tailscale account with Funnel access, custom domain control

### Overview

**What This Does**:
- Exposes Music Assistant port 8096 to public internet via Tailscale Funnel
- Provides valid HTTPS with Let's Encrypt certificate
- Uses custom domain via CNAME to Tailscale's MagicDNS hostname
- No firewall/router configuration required
- No port forwarding required

**Architecture**:
```
Internet → musicassistant.yourdomain.com (CNAME) →
         homeassistant.tail{number}.ts.net (MagicDNS) →
         Tailscale Funnel (HTTPS) →
         Home Assistant (Tailscale node) →
         Music Assistant (port 8096)
```

**Result**:
- OAuth endpoints accessible: `https://musicassistant.yourdomain.com:8096/authorize`
- Valid HTTPS certificate (Let's Encrypt wildcard via Tailscale)
- Stable hostname (doesn't change with IP changes)

---

### Prerequisites

**1. Tailscale Account with Funnel**:
- Tailscale account created (free trial available)
- Subscription with Funnel feature:
  - **Personal Pro**: $6/month (individual use)
  - **Team**: $18/month (team/family use)
- Verify Funnel access: https://login.tailscale.com/admin/settings/features

**2. Home Assistant with Tailscale**:
- Home Assistant OS running (tested on Apple TV 4K)
- Tailscale add-on installed and configured
- Home Assistant joined to Tailscale network
- Verify: Check Tailscale admin console for `homeassistant` node

**3. Music Assistant Add-on**:
- Music Assistant installed as HA add-on
- Running on port 8096 (default)
- Accessible from HA network: `http://homeassistant.local:8096`

**4. Custom Domain Control**:
- Own a domain (e.g., `yourdomain.com`)
- Access to DNS management (to create CNAME record)
- DNS provider supports CNAME records

**5. Verification Tools**:
- SSH access to Home Assistant (for testing)
- External network access (mobile hotspot or VPS for testing)
- DNS tools (dig, nslookup, or online DNS checker)

---

### Step 1: Enable Tailscale Funnel for Music Assistant

**Purpose**: Configure Tailscale to expose Music Assistant port 8096 to public internet.

**1.1: SSH into Home Assistant**:
```bash
# From your local machine
ssh root@homeassistant.local
# Or use HA Terminal add-on
```

**1.2: Verify Tailscale is Running**:
```bash
# Check Tailscale status
tailscale status

# Expected output:
# homeassistant    [your-tailnet]     linux   -
# ... other devices ...

# Verify IP and hostname
tailscale status --json | grep -E "(HostName|MagicDNSSuffix)"

# Expected output shows:
# "HostName": "homeassistant"
# "MagicDNSSuffix": "tail{number}.ts.net"
```

**1.3: Enable Funnel for Port 8096**:
```bash
# Enable Funnel for Music Assistant
tailscale funnel 8096

# Expected output:
# Available within your tailnet:
#
#   https://homeassistant.tail{number}.ts.net:8096/
#
# Available on the internet:
#
#   https://homeassistant.tail{number}.ts.net:8096/
#
# Funnel started and running in the background.
```

**1.4: Verify Funnel Status**:
```bash
# Check Funnel configuration
tailscale funnel status

# Expected output:
# https://homeassistant.tail{number}.ts.net:8096 (Funnel on)
#     |-- / proxy http://127.0.0.1:8096
```

**1.5: Test Funnel Access**:
```bash
# From Home Assistant itself
curl -I https://homeassistant.tail{number}.ts.net:8096

# Expected: HTTP 200 OK (Music Assistant responds)
```

**Verification**:
- ✅ Tailscale Funnel enabled and running
- ✅ MagicDNS hostname known: `homeassistant.tail{number}.ts.net`
- ✅ Port 8096 accessible via HTTPS
- ✅ Valid certificate (Let's Encrypt via Tailscale)

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| `funnel: not available` | Subscription doesn't include Funnel | Upgrade to Personal Pro or Team plan |
| `bind: address already in use` | Port 8096 conflict | Check if another service uses port 8096 |
| `certificate error` | Tailscale hasn't provisioned cert | Wait 1-2 minutes, retry |
| `connection refused` | Music Assistant not running | Verify Music Assistant add-on is started |

---

### Step 2: Test External Access via MagicDNS

**Purpose**: Verify public internet accessibility via Tailscale's MagicDNS hostname before adding custom domain.

**2.1: Test from External Network**:

**Option A: Use Mobile Hotspot**:
```bash
# Disconnect from home WiFi
# Connect to mobile hotspot (ensures external network)
curl -I https://homeassistant.tail{number}.ts.net:8096

# Expected: HTTP 200 OK
```

**Option B: Use Online Testing Tool**:
- Visit: https://reqbin.com/ (HTTP request tester)
- Enter URL: `https://homeassistant.tail{number}.ts.net:8096`
- Method: GET
- Click "Send"
- Expected: Status 200 OK

**2.2: Test in Web Browser**:
```
URL: https://homeassistant.tail{number}.ts.net:8096
Expected: Music Assistant web interface loads
Certificate: Valid (Let's Encrypt, no browser warnings)
```

**2.3: Verify Certificate Details**:
```bash
# Check certificate
openssl s_client -connect homeassistant.tail{number}.ts.net:8096 \
  -servername homeassistant.tail{number}.ts.net

# Expected output includes:
# subject=CN=*.tail{number}.ts.net
# issuer=C = US, O = Let's Encrypt, CN = R3
# Verify return code: 0 (ok)
```

**Verification**:
- ✅ External access works (not just local network)
- ✅ HTTPS certificate valid (no browser warnings)
- ✅ Music Assistant web interface loads
- ✅ No firewall/router configuration needed

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Funnel not running | Run `tailscale funnel 8096` again |
| Certificate invalid | Using IP instead of hostname | Use MagicDNS hostname, not IP |
| 404 Not Found | Funnel routing incorrect | Check `tailscale funnel status` |
| Music Assistant doesn't load | Service not running | Restart Music Assistant add-on |

---

### Step 3: Create DNS CNAME Record

**Purpose**: Map custom domain to Tailscale MagicDNS hostname for branded URLs.

**3.1: Determine Your Tailscale MagicDNS Hostname**:
```bash
# On Home Assistant
tailscale status --json | grep "MagicDNSName"

# Or from Funnel output (Step 1.3)
# Example: homeassistant.tail12345.ts.net
```

**3.2: Choose Your Custom Subdomain**:
```
Examples:
- musicassistant.yourdomain.com
- ma.yourdomain.com
- alexa.yourdomain.com

Recommendation: musicassistant.yourdomain.com (clear, descriptive)
```

**3.3: Create CNAME Record in DNS Provider**:

**Example: Cloudflare**:
1. Log in to Cloudflare dashboard
2. Select your domain
3. Go to DNS → Records
4. Click "Add record"
5. Configure:
   - **Type**: CNAME
   - **Name**: `musicassistant` (subdomain part only)
   - **Target**: `homeassistant.tail{number}.ts.net`
   - **Proxy status**: DNS only (gray cloud, NOT proxied)
   - **TTL**: Auto or 300 seconds
6. Click "Save"

**Example: AWS Route 53**:
1. Log in to AWS Console
2. Navigate to Route 53 → Hosted Zones
3. Select your domain
4. Click "Create record"
5. Configure:
   - **Record name**: `musicassistant`
   - **Record type**: CNAME
   - **Value**: `homeassistant.tail{number}.ts.net`
   - **TTL**: 300
   - **Routing policy**: Simple routing
6. Click "Create records"

**Example: Generic DNS Provider**:
```
Record Type: CNAME
Host/Name: musicassistant (or full: musicassistant.yourdomain.com)
Points To/Target: homeassistant.tail{number}.ts.net
TTL: 300 (5 minutes)
```

**3.4: Verify DNS Propagation**:
```bash
# Wait 1-5 minutes for DNS propagation
# Check CNAME resolution
dig musicassistant.yourdomain.com CNAME

# Expected output:
# ;; ANSWER SECTION:
# musicassistant.yourdomain.com. 300 IN CNAME homeassistant.tail{number}.ts.net.

# Or use nslookup
nslookup musicassistant.yourdomain.com

# Expected output:
# musicassistant.yourdomain.com canonical name = homeassistant.tail{number}.ts.net.
```

**Verification**:
- ✅ CNAME record created in DNS
- ✅ DNS resolves custom domain to Tailscale MagicDNS
- ✅ No proxy/CDN enabled (DNS only)
- ✅ TTL set appropriately (300-600 seconds)

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| DNS not resolving | Propagation delay | Wait 5-15 minutes, retry |
| Wrong IP returned | A record instead of CNAME | Delete A record, use CNAME only |
| NXDOMAIN error | Typo in record | Verify record name spelling |
| Cloudflare proxy enabled | Orange cloud active | Set to DNS only (gray cloud) |

---

### Step 4: Test Custom Domain Access

**Purpose**: Verify Music Assistant is accessible via custom domain with valid HTTPS.

**4.1: Test DNS Resolution**:
```bash
# Verify full resolution chain
dig musicassistant.yourdomain.com

# Expected output shows:
# musicassistant.yourdomain.com → homeassistant.tail{number}.ts.net → [IP]
```

**4.2: Test HTTPS Access**:
```bash
# From external network (mobile hotspot)
curl -I https://musicassistant.yourdomain.com:8096

# Expected: HTTP 200 OK
```

**4.3: Test Certificate Validation**:
```bash
# Check certificate accepted for custom domain
openssl s_client -connect musicassistant.yourdomain.com:8096 \
  -servername musicassistant.yourdomain.com

# Verify:
# - No certificate errors
# - Verify return code: 0 (ok)
# - Certificate subject: *.tail{number}.ts.net (wildcard)
```

**Why Wildcard Cert Works**:
- Browser resolves CNAME: `musicassistant.yourdomain.com` → `homeassistant.tail{number}.ts.net`
- TLS connection uses final hostname: `homeassistant.tail{number}.ts.net`
- Certificate `*.tail{number}.ts.net` matches `homeassistant.tail{number}.ts.net`
- Certificate validation succeeds

**4.4: Test in Web Browser**:
```
URL: https://musicassistant.yourdomain.com:8096
Expected:
- Music Assistant interface loads
- Green padlock (valid HTTPS)
- No certificate warnings
- Certificate details show Let's Encrypt
```

**4.5: Test OAuth Endpoints**:
```bash
# Test authorize endpoint (should show Music Assistant login or error)
curl https://musicassistant.yourdomain.com:8096/authorize?response_type=code&client_id=test

# Test token endpoint (should return OAuth error, not connection error)
curl -X POST https://musicassistant.yourdomain.com:8096/token \
  -d "grant_type=authorization_code&code=test"
```

**Verification**:
- ✅ Custom domain accessible via HTTPS
- ✅ Valid certificate (no browser warnings)
- ✅ Music Assistant web interface loads
- ✅ OAuth endpoints reachable

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| Certificate error in browser | CNAME not resolving correctly | Verify DNS CNAME with `dig` |
| Connection timeout | DNS cached wrong IP | Clear DNS cache, wait for propagation |
| 404 error | Wrong port in URL | Ensure `:8096` in URL |
| Music Assistant 404 | OAuth endpoints not configured | Check Music Assistant OAuth settings |

---

### Step 5: Configure Alexa Skill Account Linking

**Purpose**: Register OAuth endpoints in Alexa Developer Console for Music Assistant skill.

**5.1: Log in to Alexa Developer Console**:
```
URL: https://developer.amazon.com/alexa/console/ask
Login: Use your Amazon Developer account
```

**5.2: Create or Select Music Assistant Skill**:
- If creating new: Click "Create Skill"
- If existing: Select Music Assistant skill from list

**5.3: Configure Account Linking**:
1. Navigate to "Account Linking" section in skill settings
2. Enable "Do you allow users to create an account or link to an existing account with you?"
3. Configure Authorization URI:
   ```
   https://musicassistant.yourdomain.com:8096/authorize
   ```
4. Configure Access Token URI:
   ```
   https://musicassistant.yourdomain.com:8096/token
   ```
5. Configure Client ID:
   - Generate or use existing Music Assistant OAuth client ID
   - Note this value (needed in Music Assistant config)
6. Configure Client Secret:
   - Generate or use existing Music Assistant OAuth client secret
   - Note this value (needed in Music Assistant config)
7. Configure Scopes (if required by Music Assistant):
   - Example: `music:read`, `music:control`
   - Check Music Assistant documentation for required scopes
8. Configure Redirect URLs (provided by Amazon):
   - Amazon provides redirect URLs for each region
   - Copy these URLs (needed for Music Assistant OAuth config)
9. Click "Save"

**5.4: Test Account Linking**:
1. In Alexa Developer Console, click "Test" tab
2. Enable testing for this skill
3. Click "Account Linking" → "Link Account"
4. Expected: Redirects to `https://musicassistant.yourdomain.com:8096/authorize`
5. Expected: Shows Music Assistant login page
6. Enter Music Assistant credentials
7. Expected: Redirects back to Alexa with success message

**Verification**:
- ✅ Authorization URI accessible from Alexa
- ✅ Token URI accessible from Alexa servers
- ✅ Account linking flow completes successfully
- ✅ Access token received by Alexa

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| Invalid redirect URI | Redirect URI not registered in MA | Add Alexa redirect URIs to MA config |
| Invalid client credentials | client_id/secret mismatch | Verify credentials match in Alexa and MA |
| OAuth error: unauthorized_client | Client not registered | Register Alexa skill as OAuth client in MA |
| Connection timeout | OAuth endpoints not accessible | Verify Step 4 (custom domain access) |

---

### Step 6: Configure Music Assistant OAuth Provider

**Purpose**: Configure Music Assistant to accept OAuth requests from Alexa skill.

**6.1: Access Music Assistant Settings**:
```
URL: https://musicassistant.yourdomain.com:8096
Navigate to: Settings → Providers → OAuth (or similar)
```

**Note**: OAuth provider configuration varies by Music Assistant version. Consult Music Assistant documentation for exact settings location.

**6.2: Register Alexa Skill as OAuth Client**:

**Typical Configuration**:
```yaml
OAuth Client:
  client_id: [value from Alexa Developer Console Step 5.3.5]
  client_secret: [value from Alexa Developer Console Step 5.3.6]
  redirect_uris:
    - [redirect URL 1 from Alexa - North America]
    - [redirect URL 2 from Alexa - Europe]
    - [redirect URL 3 from Alexa - Far East]
  allowed_scopes:
    - music:read
    - music:control
```

**6.3: Verify OAuth Endpoint Configuration**:
```
Authorization Endpoint: /authorize (default)
Token Endpoint: /token (default)
Callback Endpoint: /callback (optional)
```

**6.4: Save Configuration**:
- Click "Save" or "Apply"
- Restart Music Assistant if required

**Verification**:
- ✅ Alexa skill registered as OAuth client
- ✅ Redirect URIs configured correctly
- ✅ Client credentials match Alexa skill settings
- ✅ OAuth endpoints enabled and accessible

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| OAuth provider not available | MA version doesn't support OAuth | Upgrade Music Assistant or use alternative auth |
| Redirect URI rejected | URI not in allowed list | Add all Alexa redirect URIs to MA config |
| Client secret exposed | Stored in plain text | Ensure MA encrypts secrets (check MA docs) |

---

### Step 7: Test End-to-End Alexa Account Linking

**Purpose**: Verify complete OAuth flow from Alexa app to Music Assistant and back.

**7.1: Open Alexa App**:
- Launch Amazon Alexa app on mobile device
- Log in with Amazon account

**7.2: Enable Music Assistant Skill**:
1. Tap "More" → "Skills & Games"
2. Search for "Music Assistant" skill
3. Tap skill to open details
4. Tap "Enable to Use"

**7.3: Complete Account Linking**:
1. Alexa app prompts "Link your Music Assistant account"
2. Tap "Link Account"
3. Expected: Browser/webview opens to `https://musicassistant.yourdomain.com:8096/authorize`
4. Enter Music Assistant username and password
5. Review permissions requested
6. Tap "Authorize" or "Allow"
7. Expected: Redirects back to Alexa app with success message
8. Expected: Alexa app shows "Account successfully linked"

**7.4: Test Alexa Voice Commands**:
```
"Alexa, play my music from Music Assistant"
"Alexa, play [artist name] from Music Assistant"
"Alexa, play [playlist name] from Music Assistant"
```

**Expected**: Alexa plays music from Music Assistant library.

**Verification**:
- ✅ Account linking completes in Alexa app
- ✅ Alexa receives access token from Music Assistant
- ✅ Alexa can invoke Music Assistant music playback
- ✅ Voice commands work as expected

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| "Link Account" does nothing | OAuth URIs incorrect in skill | Verify Step 5 (Alexa skill config) |
| Login page doesn't load | DNS/Funnel issue | Verify Step 4 (custom domain access) |
| "Invalid redirect URI" error | Redirect URI not in MA config | Verify Step 6 (MA OAuth config) |
| "Invalid credentials" error | Wrong MA username/password | Use correct MA credentials |
| Linking succeeds but music doesn't play | Token not valid for music API | Check MA OAuth scopes and permissions |

---

### Step 8: Operational Maintenance

**Purpose**: Ensure continued operation and handle certificate renewals, DNS updates, etc.

**8.1: Monitor Tailscale Funnel Status**:

**Frequency**: Weekly or when issues occur

```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Check Funnel status
tailscale funnel status

# Expected:
# https://homeassistant.tail{number}.ts.net:8096 (Funnel on)

# If Funnel stopped, restart:
tailscale funnel 8096
```

**8.2: Monitor Certificate Validity**:

**Frequency**: Monthly

```bash
# Check certificate expiration
echo | openssl s_client -connect musicassistant.yourdomain.com:8096 2>/dev/null | \
  openssl x509 -noout -dates

# Expected: notAfter date at least 30 days in future

# Tailscale handles renewal automatically (Let's Encrypt)
```

**8.3: Monitor DNS Resolution**:

**Frequency**: After any DNS changes

```bash
dig musicassistant.yourdomain.com CNAME

# Verify: CNAME points to correct Tailscale MagicDNS hostname
```

**8.4: Test Account Linking Periodically**:

**Frequency**: Monthly or after HA/MA updates

1. Open Alexa app
2. Navigate to Skills → Music Assistant
3. Tap "Disable Skill"
4. Tap "Enable Skill"
5. Complete account linking again
6. Verify music playback works

**8.5: Update Alexa Skill if OAuth Endpoints Change**:

If you change custom domain or Tailscale hostname:
1. Update DNS CNAME to new hostname
2. Update Alexa Developer Console OAuth URIs
3. Test account linking again

**8.6: Monitor Tailscale Subscription**:

**Frequency**: Before subscription renewal date

- Verify Tailscale subscription is active
- Check payment method is valid
- Funnel requires active subscription (Personal Pro or Team)

**8.7: Backup Configuration**:

**What to backup**:
```yaml
Tailscale Configuration:
  - MagicDNS hostname: homeassistant.tail{number}.ts.net
  - Funnel port: 8096

DNS Configuration:
  - CNAME record: musicassistant.yourdomain.com → homeassistant.tail{number}.ts.net

Alexa Skill Configuration:
  - Authorization URI
  - Token URI
  - Client ID
  - Client Secret (encrypted storage)

Music Assistant OAuth Configuration:
  - Registered clients
  - Redirect URIs
  - Scopes
```

**8.8: Handle Failures**:

**If Music Assistant doesn't respond**:
1. Check Music Assistant add-on is running in HA
2. Check Tailscale service is running: `tailscale status`
3. Check Funnel is enabled: `tailscale funnel status`
4. Restart Music Assistant add-on if needed
5. Re-enable Funnel if needed: `tailscale funnel 8096`

**If Certificate invalid**:
1. Verify Tailscale subscription is active
2. Verify MagicDNS is enabled in Tailscale admin console
3. Wait for Tailscale to renew certificate (automatic)
4. Contact Tailscale support if persistent

**If DNS doesn't resolve**:
1. Check DNS provider for CNAME record
2. Verify CNAME points to correct hostname
3. Check domain registration is active
4. Clear local DNS cache: `sudo dscacheutil -flushcache` (macOS)

**If Alexa can't link account**:
1. Verify OAuth endpoints accessible (Step 4 tests)
2. Verify Alexa skill OAuth configuration (Step 5)
3. Verify Music Assistant OAuth configuration (Step 6)
4. Check Music Assistant logs for OAuth errors
5. Test OAuth flow manually with curl

---

## Path 2: Cloudflare Tunnel ⚠️ THEORETICAL (Not Tested)

**Status**: ⚠️ Not tested, theoretical only
**Difficulty**: Moderate
**Time**: 1-2 hours
**Cost**: Free (Cloudflare free tier supports Tunnels)
**Prerequisites**: Domain on Cloudflare, `cloudflared` installation

### High-Level Steps (Untested)

**1. Install Cloudflared**:
- Option A: Find Home Assistant add-on for Cloudflared
- Option B: Run `cloudflared` on separate Linux system (Raspberry Pi, etc.)

**2. Create Cloudflare Tunnel**:
```bash
cloudflared tunnel create ha-tunnel
cloudflared tunnel route dns ha-tunnel musicassistant.yourdomain.com
```

**3. Configure Tunnel**:
```yaml
# config.yml
tunnel: <tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: musicassistant.yourdomain.com
    service: http://homeassistant-ip:8096
  - service: http_status:404
```

**4. Run Tunnel**:
```bash
cloudflared tunnel run ha-tunnel
```

**5. Configure Alexa Skill**:
- Authorization URI: `https://musicassistant.yourdomain.com/authorize` (port 443, no :8096)
- Token URI: `https://musicassistant.yourdomain.com/token`

**6. Test Account Linking**:
- Complete same testing as Path 1

**Unknowns**:
- Cloudflare proxy header compatibility with OAuth
- `cloudflared` add-on availability/quality for Home Assistant
- SSL/TLS mode configuration (Full vs Full Strict)
- Performance (Cloudflare proxy latency)

**Research Required**:
- Test OAuth flow through Cloudflare proxy
- Verify header preservation (critical for OAuth)
- Test certificate validation
- Document `cloudflared` installation on HAOS

---

## Path 3: Direct Port Forwarding ⚠️ THEORETICAL (Not Tested, Security Risk)

**Status**: ⚠️ Not tested, security concerns
**Difficulty**: Moderate to High
**Time**: 2-4 hours
**Cost**: Free (may need DynDNS ~$5/year)
**Prerequisites**: Static public IP or DynDNS, router access, certificate management

### High-Level Steps (Untested)

**1. Check for CGNAT**:
```bash
# From home network
curl ifconfig.me
# Compare to router WAN IP (should match if no CGNAT)
```

**2. Configure Port Forwarding**:
- Router: Forward external port 443 (or 8096) → internal port 8096 (HA IP)

**3. Setup DynDNS** (if dynamic IP):
- Register with DynDNS service (DuckDNS, No-IP, etc.)
- Configure router or script to update DNS on IP change

**4. Obtain TLS Certificate**:
- Option A: Let's Encrypt HTTP-01 challenge (requires port 80 forwarded)
- Option B: Let's Encrypt DNS-01 challenge (requires DNS provider API)
- Option C: Use reverse proxy (Nginx, Caddy) to handle certificates

**5. Configure Music Assistant** (or reverse proxy):
- Install certificate in Music Assistant (or proxy)
- Configure OAuth endpoints with TLS

**6. Configure Alexa Skill**:
- Authorization URI: `https://musicassistant.yourdomain.com:8096/authorize` (or `:443` if proxy)
- Token URI: `https://musicassistant.yourdomain.com:8096/token`

**7. Test Account Linking**:
- Complete same testing as Path 1

**Security Concerns**:
- ⚠️ Direct exposure of home network to internet
- ⚠️ Attack surface includes all of Music Assistant
- ⚠️ No DDoS protection
- ⚠️ Must implement rate limiting manually
- ⚠️ Certificate management complexity

**Unknowns**:
- Whether Music Assistant supports ACME/Let's Encrypt
- ISP port blocking (port 443/8096)
- Certificate renewal automation
- Dynamic IP handling (DNS propagation delays)

**Research Required**:
- Test Music Assistant certificate installation
- Test ACME challenge (HTTP-01 or DNS-01)
- Verify ISP doesn't block ports
- Document certificate renewal process
- Implement security hardening (firewall rules, rate limiting)

**Recommendation**: Only pursue if you have networking/security expertise and accept the risks.

---

## Decision Matrix: When to Use Each Path

| Criteria | Tailscale Funnel ✅ | Cloudflare Tunnel ⚠️ | Direct Port Forward ⚠️ |
|----------|---------------------|----------------------|------------------------|
| **Tested and working** | ✅ Yes | ❌ No | ❌ No |
| **Security** | ✅ High (no direct exposure) | ✅ High (no direct exposure) | ❌ Low (direct exposure) |
| **Setup complexity** | ✅ Low | ⚠️ Moderate | ❌ High |
| **Recurring cost** | ⚠️ $6-18/month | ✅ Free | ✅ Free (+DynDNS) |
| **Firewall changes** | ✅ None | ✅ None | ❌ Required |
| **Certificate management** | ✅ Automatic | ✅ Automatic | ❌ Manual |
| **DDoS protection** | ✅ Yes (Tailscale) | ✅ Yes (Cloudflare) | ❌ No |
| **ISP dependencies** | ✅ None | ✅ None | ❌ High (CGNAT, blocking) |
| **Recommended for** | Everyone | Advanced users | Security experts only |

**Recommendation**: Use **Path 1: Tailscale Funnel** unless you have specific requirements or constraints that make it unsuitable.

---

## Success Criteria

Regardless of path chosen, verify these before considering implementation complete:

**✅ Public Accessibility**:
```bash
curl -I https://musicassistant.yourdomain.com:8096
# Expected: HTTP 200 OK from external network
```

**✅ Valid HTTPS**:
```bash
openssl s_client -connect musicassistant.yourdomain.com:8096
# Expected: Verify return code: 0 (ok)
# Expected: Certificate from trusted CA
```

**✅ DNS Resolution**:
```bash
dig musicassistant.yourdomain.com
# Expected: Resolves to correct IP/CNAME
```

**✅ OAuth Endpoints**:
```bash
curl https://musicassistant.yourdomain.com:8096/authorize?response_type=code&client_id=test
# Expected: OAuth response (not connection error)
```

**✅ Alexa Account Linking**:
- Complete account linking in Alexa app
- No errors during OAuth flow
- Music playback works via Alexa voice commands

**✅ Operational Stability**:
- Service survives Home Assistant restarts
- Service survives Music Assistant updates
- Certificate renewals happen automatically
- No manual intervention needed for normal operation

---

## See Also

- **[Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md)** - Why this integration is complex
- **[Music Assistant Alexa Public Interface](../03_INTERFACES/MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md)** - OAuth interface requirements
- **[Public Exposure Options](../04_INFRASTRUCTURE/ALEXA_PUBLIC_EXPOSURE_OPTIONS.md)** - Detailed comparison of all options
- **[OAuth 2.0 Reference](../02_REFERENCE/OAUTH2_FLOW.md)** - OAuth protocol details
