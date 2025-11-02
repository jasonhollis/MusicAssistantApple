# Tailscale Funnel Implementation for Music Assistant Alexa OAuth
**Purpose**: Step-by-step procedure to expose Music Assistant OAuth server for Alexa using Tailscale Funnel
**Audience**: System administrators implementing interim Alexa integration
**Layer**: 05_OPERATIONS (concrete procedures and runbooks)
**Status**: ⚠️ INTERIM SOLUTION - See future migration path in NABU_CASA_MUSIC_ASSISTANT_FUTURE_PLAN.md
**Related**:
- [Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md) - Why public exposure is required
- [Future Architecture Strategy](../00_ARCHITECTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md) - Permanent solution principles
- [Future Migration Plan](NABU_CASA_MUSIC_ASSISTANT_FUTURE_PLAN.md) - When and how to transition away from this

---

## Intent

This document provides a **working interim solution** for exposing Music Assistant's OAuth server to Alexa for account linking. This approach uses **Tailscale Funnel** as a temporary workaround until a permanent integrated solution is available.

**This is not the permanent solution.** See the Future Strategy and Migration Plan documents for the long-term architecture.

**Total Time**: 60 minutes from prerequisites to working Alexa integration

---

## Prerequisites Verification (All Must Pass)

Before starting, verify all prerequisites are met. **Do not proceed if any prerequisite fails.**

### 1. Tailscale Account with Funnel Access

**Check**: Visit https://login.tailscale.com/admin/settings/features

**Required**:
- Tailscale account exists
- Subscription tier: Personal Pro ($6/month) OR Team ($18/month)
- Funnel feature: Enabled

**Verification**:
```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Check Tailscale is running
tailscale status

# Expected output shows:
# homeassistant    [your-tailnet]     linux   -
```

**If prerequisite fails**:
- Create Tailscale account: https://login.tailscale.com/start
- Upgrade to Personal Pro: https://login.tailscale.com/admin/settings/billing
- Wait 5 minutes for Funnel access to activate

---

### 2. Home Assistant with Tailscale Add-on

**Check**: Home Assistant running with Tailscale installed

**Required**:
- Home Assistant OS (any platform)
- Tailscale add-on installed from HA Add-on Store
- Home Assistant joined to Tailscale network
- MagicDNS enabled

**Verification**:
```bash
# Check MagicDNS hostname
tailscale status --json | grep -E "(HostName|MagicDNSSuffix)"

# Expected output:
# "HostName": "homeassistant"
# "MagicDNSSuffix": "tail{number}.ts.net"

# Full hostname will be: homeassistant.tail{number}.ts.net
```

**If prerequisite fails**:
- Install Tailscale add-on: HA Settings → Add-ons → Add-on Store → Search "Tailscale"
- Configure Tailscale: Provide auth key from Tailscale admin console
- Enable MagicDNS: Tailscale admin console → DNS → Enable MagicDNS

---

### 3. Music Assistant Running on Port 8096

**Check**: Music Assistant accessible on default port

**Required**:
- Music Assistant add-on installed
- Running and accessible
- Port 8096 (default OAuth port)

**Verification**:
```bash
# From Home Assistant (SSH)
curl -I http://localhost:8096

# Expected: HTTP 200 OK or HTTP 401 Unauthorized (both indicate server running)

# If connection refused:
docker ps | grep music-assistant
# Should show running container
```

**If prerequisite fails**:
- Install Music Assistant: HA Settings → Add-ons → Add-on Store
- Start Music Assistant add-on
- Verify port 8096 in add-on configuration

---

### 4. Custom Domain with DNS Control

**Check**: You own a domain and can modify DNS records

**Required**:
- Custom domain registered (e.g., `yourdomain.com`)
- Access to DNS management console
- Ability to create CNAME records

**Verification**:
```bash
# Test DNS control by creating temporary test record
# (In your DNS provider, create test CNAME)

dig test.yourdomain.com CNAME

# If you can see your test record, DNS control is confirmed
# Delete test record after verification
```

**If prerequisite fails**:
- Register domain: Namecheap, Cloudflare, AWS Route 53, etc. (~$10-15/year)
- Locate DNS management: Usually in domain registrar's control panel
- Alternative: Use free subdomain service (DuckDNS, afraid.org) - not recommended for production

---

### 5. External Network Access for Testing

**Check**: Ability to test from outside home network

**Required** (at least one):
- Mobile phone with cellular data (hotspot capability)
- VPS or cloud instance for testing
- Friend/family on different network

**Verification**:
```bash
# Disconnect from home WiFi
# Connect to mobile hotspot
# Test external access:
curl -I https://google.com

# Expected: Connection succeeds (validates external network access)
```

**If prerequisite fails**:
- Enable mobile hotspot on phone
- Alternative: Use online testing tool (reqbin.com)

---

## Phase 1: Enable Tailscale Funnel on Port 8096 (5 minutes)

**Goal**: Expose Music Assistant OAuth server to public internet via Tailscale Funnel

### Step 1.1: SSH to Home Assistant

```bash
# From your local machine
ssh root@homeassistant.local

# Alternative: Use Home Assistant Terminal add-on (if SSH not enabled)
```

**Expected**: Shell prompt showing `homeassistant:~#`

---

### Step 1.2: Verify Tailscale Status

```bash
# Check Tailscale is connected and running
tailscale status

# Expected output shows:
# homeassistant    [tailnet-name]     linux   -
# (plus other devices on your tailnet)
```

**If Tailscale not running**:
```bash
# Restart Tailscale add-on in Home Assistant UI
# Or restart via CLI:
ha addons restart 4qbl3bsd_tailscale
```

---

### Step 1.3: Get MagicDNS Hostname

```bash
# Retrieve your Tailscale MagicDNS hostname
tailscale status --json | grep "MagicDNSSuffix"

# Expected output:
# "MagicDNSSuffix": "tail{number}.ts.net"

# Your full hostname is: homeassistant.tail{number}.ts.net
# WRITE THIS DOWN - you'll need it for DNS configuration
```

---

### Step 1.4: Enable Funnel for Port 8096

```bash
# Enable Tailscale Funnel on Music Assistant OAuth port
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

**What this does**:
- Exposes local port 8096 to public internet
- Provides HTTPS with valid Let's Encrypt certificate
- No firewall or router configuration needed
- Automatic certificate renewal by Tailscale

---

### Step 1.5: Verify Funnel Configuration

```bash
# Check Funnel status
tailscale funnel status

# Expected output:
# https://homeassistant.tail{number}.ts.net:8096 (Funnel on)
#     |-- / proxy http://127.0.0.1:8096
```

**If Funnel shows as off**:
- Run `tailscale funnel 8096` again
- Check subscription includes Funnel feature
- Verify no other service is using port 8096

---

### Step 1.6: Test Internal Access

```bash
# Test Music Assistant responds via Funnel (from HA itself)
curl -I https://homeassistant.tail{number}.ts.net:8096

# Expected: HTTP/2 200 OK (or 401 Unauthorized - both indicate working)

# If connection refused or timeout:
# - Check Music Assistant is running
# - Check port 8096 is correct
# - Restart Music Assistant add-on
```

---

### Rollback Procedure (Phase 1)

If Phase 1 fails or needs to be reversed:

```bash
# Disable Funnel
tailscale funnel off

# Verify disabled
tailscale funnel status
# Expected: No funnels configured
```

**State after rollback**: Music Assistant still accessible locally, not publicly exposed.

---

## Phase 2: Create DNS CNAME for Custom Domain (2 minutes)

**Goal**: Map custom domain to Tailscale MagicDNS hostname for branded OAuth URLs

### Step 2.1: Choose Custom Subdomain

**Recommended format**: `musicassistant.yourdomain.com`

**Alternatives**:
- `ma.yourdomain.com` (shorter)
- `alexa.yourdomain.com` (purpose-specific)

**Write down your choice**: `_____________________.yourdomain.com`

---

### Step 2.2: Create CNAME Record in DNS Provider

**Values needed**:
- **Record Type**: CNAME
- **Name/Host**: `musicassistant` (subdomain part only)
- **Target/Value**: `homeassistant.tail{number}.ts.net` (from Phase 1, Step 1.3)
- **TTL**: 300 seconds (5 minutes)
- **Proxy**: DISABLED (DNS only, no CDN/proxy)

**Cloudflare Example**:
1. Log in to Cloudflare dashboard
2. Select your domain
3. Go to DNS → Records
4. Click "Add record"
5. Configure:
   - Type: CNAME
   - Name: `musicassistant`
   - Target: `homeassistant.tail{number}.ts.net`
   - Proxy status: DNS only (gray cloud icon)
   - TTL: Auto
6. Click "Save"

**AWS Route 53 Example**:
1. Log in to AWS Console
2. Navigate to Route 53 → Hosted Zones
3. Select your domain
4. Click "Create record"
5. Configure:
   - Record name: `musicassistant`
   - Record type: CNAME
   - Value: `homeassistant.tail{number}.ts.net`
   - TTL: 300
6. Click "Create records"

**Generic DNS Provider**:
- Find "DNS Management" or "DNS Records" section
- Add new record
- Fill in values from above
- Save changes

---

### Step 2.3: Verify DNS Propagation

```bash
# Wait 1-5 minutes for DNS propagation
# Then check CNAME resolution:

dig musicassistant.yourdomain.com CNAME

# Expected output:
# ;; ANSWER SECTION:
# musicassistant.yourdomain.com. 300 IN CNAME homeassistant.tail{number}.ts.net.

# Alternative verification (if dig not available):
nslookup musicassistant.yourdomain.com

# Expected output:
# musicassistant.yourdomain.com canonical name = homeassistant.tail{number}.ts.net
```

**If DNS doesn't resolve after 5 minutes**:
- Check CNAME record was saved in DNS provider
- Verify no typos in hostname
- Check domain is active and not expired
- Try flushing local DNS cache: `sudo dscacheutil -flushcache` (macOS)
- Wait up to 15 minutes for worldwide propagation

---

### Rollback Procedure (Phase 2)

If Phase 2 fails or needs to be reversed:

1. Delete CNAME record from DNS provider
2. Wait 5-15 minutes for deletion to propagate
3. Verify deletion: `dig musicassistant.yourdomain.com CNAME` (should return NXDOMAIN)

**State after rollback**: Funnel still active, but only accessible via `homeassistant.tail{number}.ts.net`, not custom domain.

---

## Phase 3: Configure Music Assistant OAuth Endpoints (3 minutes)

**Goal**: Ensure Music Assistant OAuth server is configured and accessible

### Step 3.1: Verify OAuth Endpoints Exist

```bash
# Test OAuth authorization endpoint
curl -I https://musicassistant.yourdomain.com:8096/authorize

# Expected: HTTP 200 or 401 (server responds)

# Test OAuth token endpoint
curl -I https://musicassistant.yourdomain.com:8096/token

# Expected: HTTP 200, 401, or 405 (server responds, may reject GET)
```

**If endpoints return 404**:
- Music Assistant may not have OAuth configured
- Check Music Assistant version supports OAuth
- Verify Music Assistant configuration includes OAuth provider

---

### Step 3.2: Access Music Assistant Settings

1. Open browser to `https://musicassistant.yourdomain.com:8096`
2. Log in to Music Assistant
3. Navigate to Settings (exact location varies by version)

---

### Step 3.3: Verify OAuth Configuration

**Look for**:
- OAuth provider settings
- Client ID and Client Secret configuration
- Redirect URI configuration
- Authorization/Token endpoint configuration

**Typical location**:
- Settings → Providers → OAuth
- Settings → Security → OAuth
- Settings → Integrations → OAuth

**Note**: OAuth configuration varies significantly by Music Assistant version. Consult Music Assistant documentation for your specific version.

---

### Step 3.4: Test OAuth Flow (Without Alexa)

```bash
# Test complete OAuth authorization flow
curl -L "https://musicassistant.yourdomain.com:8096/authorize?response_type=code&client_id=test&redirect_uri=http://localhost"

# Expected: HTML login page or OAuth error (not connection error)
# If connection refused: OAuth server not running
# If 404: OAuth endpoints not configured
```

---

### Rollback Procedure (Phase 3)

If Phase 3 fails, no rollback needed. Music Assistant configuration changes can be reverted:

1. Disable OAuth provider in Music Assistant settings (if enabled)
2. Music Assistant continues functioning normally without OAuth

**State after rollback**: Funnel and DNS active, but OAuth not functional.

---

## Phase 4: Create Alexa Skill with Account Linking (30 minutes)

**Goal**: Configure Alexa Developer Console to use Music Assistant OAuth for account linking

### Step 4.1: Log in to Alexa Developer Console

1. Navigate to: https://developer.amazon.com/alexa/console/ask
2. Log in with Amazon Developer account
3. Accept terms of service (if first time)

**If no Amazon Developer account**:
- Create account: https://developer.amazon.com/
- Enable developer account (free)
- May require verification (email/phone)

---

### Step 4.2: Create New Alexa Skill

1. Click "Create Skill"
2. Configure skill basics:
   - **Skill name**: Music Assistant
   - **Default language**: English (US) (or your locale)
   - **Choose a model**: Smart Home
   - **Choose a method**: Provision your own
3. Click "Create skill"
4. Wait for skill creation (30-60 seconds)

**Alternative**: If Music Assistant has official Alexa skill template, import that instead.

---

### Step 4.3: Configure Skill Settings

1. In skill editor, navigate to "Skill Information"
2. Fill in required fields:
   - **Skill name**: Music Assistant
   - **Description**: Control Music Assistant via Alexa voice commands
   - **Category**: Music & Audio
   - **Testing Instructions**: (for certification - not needed for testing)

---

### Step 4.4: Configure Account Linking

This is the critical section for OAuth integration.

1. Navigate to "Account Linking" in skill settings
2. Enable: "Do you allow users to create an account or link to an existing account with you?"
3. Configure OAuth settings:

**Authorization URI**:
```
https://musicassistant.yourdomain.com:8096/authorize
```

**Access Token URI**:
```
https://musicassistant.yourdomain.com:8096/token
```

**Client ID**:
- Generate a random UUID: `uuidgen` (macOS/Linux)
- Or use existing Music Assistant OAuth client ID
- Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- **WRITE THIS DOWN** - needed for Music Assistant config

**Client Secret**:
- Generate secure random: `openssl rand -hex 32`
- Or use existing Music Assistant OAuth client secret
- Example: `a1b2c3d4e5f6789012345678901234567890abcdef123456789012345678901234`
- **WRITE THIS DOWN** - needed for Music Assistant config
- **KEEP SECURE** - treat like a password

**Client Authentication Scheme**:
- Select: "HTTP Basic (Recommended)"

**Scopes** (if required by Music Assistant):
- Add scope: `music:read`
- Add scope: `music:control`
- Check Music Assistant documentation for required scopes

**Domain List** (optional):
- Add domain: `yourdomain.com`

**Redirect URLs** (provided by Amazon):
- Amazon automatically generates redirect URLs for each region
- Copy these URLs (needed for Music Assistant OAuth configuration)
- Typical format:
  - `https://pitangui.amazon.com/api/skill/link/[SKILL_ID]` (North America)
  - `https://layla.amazon.com/api/skill/link/[SKILL_ID]` (Europe)
  - `https://alexa.amazon.co.jp/api/skill/link/[SKILL_ID]` (Far East)

4. Click "Save"

---

### Step 4.5: Enable Skill for Testing

1. Navigate to "Test" tab in Alexa Developer Console
2. Enable testing: Select "Development"
3. Status should show: "In Development - This skill can be tested on your account"

---

### Step 4.6: Configure Music Assistant OAuth Client

**Important**: Music Assistant must be configured with the same credentials as Alexa skill.

1. Open Music Assistant UI: `https://musicassistant.yourdomain.com:8096`
2. Navigate to OAuth settings (location varies by version)
3. Add new OAuth client (or update existing):
   - **Client ID**: [value from Step 4.4]
   - **Client Secret**: [value from Step 4.4]
   - **Redirect URIs**: [all Amazon redirect URLs from Step 4.4]
   - **Allowed Scopes**: `music:read`, `music:control` (or as required)
4. Save configuration
5. Restart Music Assistant (if required)

**Example YAML configuration** (if Music Assistant uses config files):
```yaml
oauth:
  clients:
    - client_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
      client_secret: "a1b2c3d4e5f6789012345678901234567890abcdef123456789012345678901234"
      redirect_uris:
        - "https://pitangui.amazon.com/api/skill/link/[SKILL_ID]"
        - "https://layla.amazon.com/api/skill/link/[SKILL_ID]"
        - "https://alexa.amazon.co.jp/api/skill/link/[SKILL_ID]"
      allowed_scopes:
        - "music:read"
        - "music:control"
```

---

### Rollback Procedure (Phase 4)

If Phase 4 fails or needs to be reversed:

1. In Alexa Developer Console, disable account linking
2. Delete OAuth client from Music Assistant configuration
3. Optionally: Delete Alexa skill (if no longer needed)

**State after rollback**: Skill exists but account linking disabled. Can be re-enabled later.

---

## Phase 5: End-to-End Testing (15 minutes)

**Goal**: Verify complete OAuth flow from Alexa app to Music Assistant and back

### Step 5.1: Test in Alexa Developer Console

1. In Alexa Developer Console, navigate to Test tab
2. Click "Account Linking"
3. Click "Link Account"
4. Expected: Browser opens to `https://musicassistant.yourdomain.com:8096/authorize`
5. Enter Music Assistant credentials
6. Click "Authorize" or "Allow"
7. Expected: Redirects back to Alexa with success message

**If account linking fails**:
- Check browser console for errors (F12)
- Verify OAuth endpoints accessible: `curl -I https://musicassistant.yourdomain.com:8096/authorize`
- Check Music Assistant logs for OAuth errors
- Verify client_id and client_secret match between Alexa and MA

---

### Step 5.2: Test in Alexa Mobile App

1. Open Amazon Alexa app on mobile device
2. Navigate to: More → Skills & Games
3. Search for: "Music Assistant"
4. Select your skill (should show "Dev" badge)
5. Tap "Enable to Use"
6. Expected: Prompt to link account appears
7. Tap "Link Account"
8. Expected: Webview opens to `https://musicassistant.yourdomain.com:8096/authorize`
9. Enter Music Assistant username and password
10. Tap "Authorize"
11. Expected: Returns to Alexa app with "Account successfully linked" message

**If mobile linking fails**:
- Ensure mobile device on WiFi or cellular (not connected via VPN)
- Check custom domain resolves externally: `dig musicassistant.yourdomain.com` (from mobile hotspot)
- Verify certificate valid: Visit `https://musicassistant.yourdomain.com:8096` in mobile browser (should show green padlock)

---

### Step 5.3: Test Voice Commands

**Prerequisites**: Alexa device available (Echo, Echo Dot, etc.)

**Test commands**:
```
"Alexa, ask Music Assistant to play [song name]"
"Alexa, play my music from Music Assistant"
"Alexa, play [artist name] from Music Assistant"
"Alexa, play [playlist name] from Music Assistant"
```

**Expected**: Alexa plays music from Music Assistant library.

**If voice commands fail**:
- Verify account linking succeeded (check Alexa app)
- Check Music Assistant logs for playback requests
- Verify Music Assistant can play music directly (not just via Alexa)
- Check Alexa device is online and responds to other commands

---

### Step 5.4: Test Token Refresh (Optional)

**Purpose**: Verify OAuth token refresh works (prevents re-authentication)

1. Wait 24-48 hours after initial linking
2. Try voice command again
3. Expected: Music plays without re-linking account

**If token refresh fails**:
- User may need to re-link account periodically
- Check Music Assistant logs for token refresh errors
- Verify Music Assistant OAuth server implements refresh token flow

---

### Step 5.5: Verify from External Network

**Purpose**: Confirm OAuth works from internet, not just local network

1. Disconnect from home WiFi
2. Connect to mobile hotspot (cellular data)
3. Open Alexa app
4. Disable and re-enable Music Assistant skill
5. Complete account linking again
6. Expected: Linking succeeds from external network

**If external linking fails**:
- Funnel may have stopped: Check `tailscale funnel status`
- DNS may not be propagated: Check `dig musicassistant.yourdomain.com` from external network
- Certificate may be invalid: Check browser shows green padlock

---

### Rollback Procedure (Phase 5)

If Phase 5 testing identifies issues, no rollback needed. Troubleshoot specific failure:

- **OAuth flow fails**: Check Phase 3 (Music Assistant OAuth config)
- **Account linking fails**: Check Phase 4 (Alexa skill config)
- **Voice commands fail**: Check Music Assistant skill implementation (not OAuth issue)

---

## Verification Checklist

After completing all phases, verify these criteria:

**✅ Tailscale Funnel Status**:
```bash
tailscale funnel status
# Expected: Funnel on for port 8096
```

**✅ DNS Resolution**:
```bash
dig musicassistant.yourdomain.com CNAME
# Expected: CNAME points to homeassistant.tail{number}.ts.net
```

**✅ External HTTPS Access**:
```bash
# From mobile hotspot or external network
curl -I https://musicassistant.yourdomain.com:8096
# Expected: HTTP 200 OK (or 401 if auth required)
```

**✅ Certificate Validity**:
```bash
openssl s_client -connect musicassistant.yourdomain.com:8096 -servername musicassistant.yourdomain.com </dev/null 2>/dev/null | openssl x509 -noout -dates
# Expected: notAfter date in future (Let's Encrypt, 90 days)
```

**✅ OAuth Endpoints**:
```bash
curl -I https://musicassistant.yourdomain.com:8096/authorize
curl -I https://musicassistant.yourdomain.com:8096/token
# Expected: Both return HTTP 200, 401, or 405 (not 404 or connection error)
```

**✅ Alexa Account Linking**:
- Open Alexa app
- Music Assistant skill shows "Account linked"
- Voice commands trigger Music Assistant playback

**✅ External Network Test**:
- Account linking works from mobile hotspot
- OAuth flow completes from non-home network

---

## Ongoing Maintenance

### Weekly Checks

```bash
# Verify Funnel still running
ssh root@homeassistant.local
tailscale funnel status

# Expected: Funnel on for port 8096
# If Funnel stopped, restart:
tailscale funnel 8096
```

### Monthly Checks

```bash
# Verify certificate validity
openssl s_client -connect musicassistant.yourdomain.com:8096 </dev/null 2>/dev/null | openssl x509 -noout -dates

# Expected: notAfter date at least 30 days in future
# Tailscale handles renewal automatically
```

### After Home Assistant Updates

```bash
# Verify Funnel persists through HA restart
# After HA update:
tailscale funnel status

# If Funnel disabled, re-enable:
tailscale funnel 8096
```

### After Music Assistant Updates

```bash
# Verify OAuth configuration persists
curl -I https://musicassistant.yourdomain.com:8096/authorize

# Expected: HTTP 200 or 401
# If 404, reconfigure OAuth in Music Assistant
```

---

## Troubleshooting Guide

### Issue: Funnel won't enable

**Error**: `funnel: not available`

**Cause**: Subscription doesn't include Funnel feature

**Solution**:
1. Check subscription tier: https://login.tailscale.com/admin/settings/billing
2. Upgrade to Personal Pro ($6/month) or Team ($18/month)
3. Wait 5 minutes for feature activation
4. Retry: `tailscale funnel 8096`

---

### Issue: Certificate errors in browser

**Error**: "Your connection is not private" or "NET::ERR_CERT_AUTHORITY_INVALID"

**Cause**: Using IP address instead of hostname, or DNS not resolving correctly

**Solution**:
1. Verify DNS resolution: `dig musicassistant.yourdomain.com`
2. Ensure CNAME points to `homeassistant.tail{number}.ts.net`
3. Clear browser cache and DNS cache
4. Use hostname, not IP address
5. Wait 15 minutes for DNS propagation

---

### Issue: Connection timeout from external network

**Error**: `curl: (28) Connection timed out`

**Cause**: Funnel not running or DNS not propagated

**Solution**:
```bash
# Check Funnel status
ssh root@homeassistant.local
tailscale funnel status

# If Funnel off, re-enable:
tailscale funnel 8096

# Check DNS from external network:
# (Use mobile hotspot)
dig musicassistant.yourdomain.com
```

---

### Issue: OAuth endpoints return 404

**Error**: `HTTP 404 Not Found` on `/authorize` or `/token`

**Cause**: Music Assistant OAuth not configured or not running

**Solution**:
1. Verify Music Assistant is running: `curl -I http://localhost:8096`
2. Check Music Assistant OAuth configuration
3. Verify OAuth provider enabled in Music Assistant settings
4. Check Music Assistant logs for errors
5. Restart Music Assistant add-on

---

### Issue: Alexa account linking fails

**Error**: "Unable to link account" or "Invalid redirect_uri"

**Cause**: Redirect URIs not registered in Music Assistant

**Solution**:
1. Copy all Amazon redirect URLs from Alexa Developer Console
2. Add redirect URLs to Music Assistant OAuth client configuration
3. Ensure client_id and client_secret match between Alexa and MA
4. Restart Music Assistant
5. Retry account linking

---

### Issue: Voice commands don't work after linking

**Error**: "Music Assistant is not responding" or "I couldn't find [song]"

**Cause**: Token not being sent or Music Assistant skill not implemented

**Solution**:
1. Verify account linking succeeded: Check Alexa app
2. Check Music Assistant logs for playback requests
3. Verify Music Assistant skill implementation (separate from OAuth)
4. Test Music Assistant playback directly (not via Alexa)
5. Re-link account in Alexa app

---

## Security Considerations

**This interim solution has security implications**:

1. **Public OAuth Exposure**: Music Assistant OAuth server is publicly accessible
   - Mitigated by: OAuth protocol security (client_secret)
   - Risk: Potential for brute-force attacks on OAuth endpoints
   - Recommendation: Monitor Music Assistant logs for failed auth attempts

2. **Tailscale Dependency**: Relies on third-party service for public access
   - Mitigated by: Tailscale's security track record
   - Risk: Tailscale service outage breaks OAuth
   - Recommendation: Monitor Tailscale status page

3. **Certificate Management**: Relies on Tailscale for Let's Encrypt certificates
   - Mitigated by: Automatic renewal by Tailscale
   - Risk: Certificate expiration if Tailscale issue
   - Recommendation: Monitor certificate expiration dates

4. **Client Secret in Configuration**: OAuth client secret stored in Music Assistant config
   - Risk: Potential exposure if Music Assistant compromised
   - Recommendation: Ensure Music Assistant config files have restricted permissions (0600)

**For production use**: Transition to integrated Nabu Casa solution (see Future Migration Plan).

---

## Success Criteria

This implementation is successful when:

- ✅ Tailscale Funnel exposes port 8096 publicly with valid HTTPS
- ✅ Custom domain resolves to Tailscale MagicDNS hostname
- ✅ OAuth endpoints accessible from external network
- ✅ Alexa account linking completes successfully in Alexa app
- ✅ Voice commands trigger Music Assistant playback
- ✅ Account linking persists across HA/MA restarts
- ✅ OAuth flow works from any network (home/cellular/external)

---

## Migration Path to Permanent Solution

**This is an interim solution.** When ready to migrate to permanent integrated solution:

1. Read: [Future Architecture Strategy](../00_ARCHITECTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md)
2. Read: [Future Migration Plan](NABU_CASA_MUSIC_ASSISTANT_FUTURE_PLAN.md)
3. Monitor triggers for migration (see Migration Plan)
4. Follow migration procedure when triggered
5. Disable Tailscale Funnel after migration: `tailscale funnel off`

**Do not consider this a permanent architecture.** This is a working solution until better integration is available.

---

## See Also

- **[Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md)** - Why public exposure is required
- **[Future Architecture Strategy](../00_ARCHITECTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md)** - Long-term architecture principles
- **[Future Migration Plan](NABU_CASA_MUSIC_ASSISTANT_FUTURE_PLAN.md)** - When and how to transition
- **[Music Assistant Alexa Public Interface](../03_INTERFACES/MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md)** - OAuth interface requirements
