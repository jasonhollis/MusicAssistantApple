# Nabu Casa + Music Assistant Future Migration Plan
**Purpose**: When and how to transition from Tailscale Funnel interim solution to permanent architecture
**Audience**: System administrators, users operating the interim solution
**Layer**: 05_OPERATIONS (concrete procedures and decision trees)
**Related**:
- [Future Architecture Strategy](../00_ARCHITECTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md) - Why we're migrating
- [Future Implementation Work](../04_INFRASTRUCTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_WORK.md) - What needs to be built
- [Current Interim Solution](TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md) - What we're migrating from

---

## Intent

This document provides **operational guidance** for monitoring triggers and executing migration from the current Tailscale Funnel interim solution to a permanent integrated architecture.

**Key Concepts**:
- **Interim Solution**: Tailscale Funnel (current, working, but temporary)
- **Future Solution**: One of three paths (HA Integration, Nabu Casa Proxy, MA Cloud)
- **Trigger**: Event that signals readiness to migrate
- **Migration**: Transition from interim to permanent solution
- **Rollback**: Return to interim solution if migration fails

**Status**: Current users on Tailscale Funnel should **monitor these triggers** and **execute migration when triggered**.

---

## Current Interim Solution (What We Have Today)

**Technology**: Tailscale Funnel exposing Music Assistant OAuth on port 8096

**Architecture**:
```
Internet → Custom Domain CNAME
         → Tailscale MagicDNS (*.ts.net)
         → Tailscale Funnel (HTTPS)
         → Home Assistant
         → Music Assistant (port 8096)
```

**Status**: ✅ **WORKING** - Functional interim solution

**Limitations**:
- External dependency on Tailscale (commercial service)
- Subscription cost ($6-18/month)
- Not integrated with Nabu Casa (doesn't support HA community)
- Separate from HA ecosystem (different auth, monitoring, maintenance)

**When to migrate**: When one of the migration triggers occurs (see below).

---

## Migration Triggers (When to Transition)

### Trigger 1: Path 2 (Nabu Casa Proxy) Becomes Available ✅ RECOMMENDED

**Event**: Nabu Casa releases custom service routing feature

**Indicators**:
- Nabu Casa blog post announces custom service routing
- Home Assistant release notes mention Nabu Casa custom services
- Nabu Casa integration in HA shows custom service configuration UI
- Community confirms feature works with Music Assistant OAuth

**Verification**:
```bash
# Check HA version includes Nabu Casa custom service feature
ha core info | grep version
# Expected: Version with feature (TBD when released)

# Check Nabu Casa integration config
# Navigate to HA UI: Settings → Nabu Casa → Custom Services
# If UI exists, feature is available
```

**Timeline**: Unknown - Monitor Nabu Casa roadmap and HA release notes

**Action**: Execute Migration Path 2 (see section below)

**Priority**: ⭐⭐⭐ HIGH - This is the recommended migration path (lowest effort, best sustainability)

---

### Trigger 2: Path 1 (HA Integration) Becomes Available

**Event**: Music Assistant released as official Home Assistant integration

**Indicators**:
- Music Assistant GitHub announces HA integration release
- Music Assistant available in HA integration store (not just add-on store)
- Documentation shows OAuth via HA OAuth server
- Community reports successful Alexa linking via HA OAuth

**Verification**:
```bash
# Check if MA available as HA integration
# Navigate to HA UI: Settings → Devices & Services → Add Integration
# Search for "Music Assistant"
# If found in integration store (not add-on), feature is available
```

**Timeline**: Unknown - Monitor Music Assistant project roadmap

**Action**: Execute Migration Path 1 (see section below)

**Priority**: ⭐⭐ MEDIUM - Deeper integration, but requires MA architectural changes

---

### Trigger 3: Path 3 (MA Cloud Service) Becomes Available

**Event**: Music Assistant launches official cloud service with Alexa skill

**Indicators**:
- Music Assistant announces cloud service (blog, GitHub release)
- Official Music Assistant Alexa skill published in Alexa Skills Store
- Documentation shows cloud account linking procedure
- Community confirms working Alexa integration via MA Cloud

**Verification**:
```bash
# Check Alexa Skills Store
# Amazon Alexa app: Skills & Games → Search "Music Assistant"
# Look for official Music Assistant skill (not third-party)
```

**Timeline**: Unknown - Monitor Music Assistant project announcements

**Action**: Execute Migration Path 3 (see section below)

**Priority**: ⭐ LOW - Only if standalone MA use case (not HA-integrated users)

---

### Trigger 4: Tailscale Becomes Unsustainable (URGENT)

**Event**: Tailscale Funnel feature deprecated, pricing increases significantly, or extended outage

**Indicators**:
- Tailscale announces Funnel deprecation
- Tailscale pricing increases beyond acceptable threshold (e.g., >$20/month)
- Tailscale has multi-day outage affecting Funnel
- Tailscale changes terms of service (unfavorable for home use)

**Verification**:
```bash
# Check Tailscale status page
curl -I https://status.tailscale.com

# Check Tailscale pricing page
# Visit: https://tailscale.com/pricing

# Check Funnel still available
ssh root@homeassistant.local
tailscale funnel status
# If "funnel: not available" → Feature deprecated
```

**Timeline**: Monitor Tailscale communications and status

**Action**:
- **If permanent solution available**: Execute migration immediately
- **If no permanent solution**: Switch to alternative interim solution (see Contingency Plans)

**Priority**: 🔴 URGENT - Mitigate service interruption

---

### Trigger 5: User Requirements Change

**Event**: New requirements that Tailscale cannot satisfy

**Examples**:
- Need for unified authentication (single sign-on with HA)
- Compliance requirements (GDPR, SOC 2, data residency)
- Corporate deployment (no external dependencies allowed)
- Cost constraints (cannot afford Tailscale subscription)

**Verification**: User-specific - document requirements and evaluate solutions

**Action**: Evaluate which migration path satisfies new requirements

**Priority**: ⭐⭐ MEDIUM - User-driven, not urgent unless blocking

---

## Migration Decision Tree

**Use this decision tree when a trigger occurs**:

```
[Trigger Occurs]
    ↓
Is Path 2 (Nabu Casa Proxy) available?
    ├── YES → Migrate to Path 2 (RECOMMENDED)
    │         └── Follow "Migration Path 2 Procedure" below
    │
    └── NO → Is Path 1 (HA Integration) available?
              ├── YES → Migrate to Path 1
              │         └── Follow "Migration Path 1 Procedure" below
              │
              └── NO → Is Path 3 (MA Cloud) available?
                        ├── YES → Evaluate if standalone use case
                        │         ├── YES → Migrate to Path 3
                        │         │         └── Follow "Migration Path 3 Procedure"
                        │         └── NO → Stay on Tailscale (re-evaluate triggers)
                        │
                        └── NO → Is Tailscale still viable?
                                  ├── YES → Stay on Tailscale (monitor triggers)
                                  └── NO → Execute Contingency Plan (see below)
```

---

## Migration Path 1 Procedure: HA Integration

**Prerequisites**:
- Music Assistant HA integration available in integration store
- Home Assistant supports OAuth scope delegation
- Nabu Casa subscription active

**Estimated Downtime**: 30-60 minutes (Alexa account linking unavailable)

---

### Phase 1: Backup Current Configuration (5 minutes)

```bash
# Backup Music Assistant configuration
ssh root@homeassistant.local
cp -r /config/music_assistant /backup/music_assistant_pre_migration_$(date +%Y%m%d)

# Backup Alexa Skill OAuth configuration
# Screenshot Alexa Developer Console OAuth settings
# Record:
# - Client ID
# - Client Secret
# - Redirect URIs
```

---

### Phase 2: Install Music Assistant Integration (15 minutes)

1. **Navigate to HA Integrations**:
   - Settings → Devices & Services → Add Integration
   - Search: "Music Assistant"
   - Select Music Assistant integration (not add-on)

2. **Configure Integration**:
   - Follow HA integration setup flow
   - Import existing Music Assistant configuration (if supported)
   - Configure OAuth scopes: `music_assistant.read`, `music_assistant.control`

3. **Verify Integration**:
   ```bash
   # Check integration loaded
   ha core info | grep music_assistant
   # Expected: Music Assistant integration active
   ```

---

### Phase 3: Update Alexa Skill OAuth Configuration (10 minutes)

1. **Open Alexa Developer Console**: https://developer.amazon.com/alexa/console/ask
2. **Select Music Assistant Skill**
3. **Update Account Linking**:
   - Authorization URI: `https://[uuid].ui.nabu.casa/auth/authorize`
   - Access Token URI: `https://[uuid].ui.nabu.casa/auth/token`
   - Scopes: `music_assistant.read music_assistant.control`
   - Keep same Client ID and Client Secret (or regenerate if prompted)
4. **Save Configuration**

---

### Phase 4: Test OAuth Flow (10 minutes)

```bash
# Test HA OAuth endpoints via Nabu Casa
curl -I https://[uuid].ui.nabu.casa/auth/authorize

# Expected: HTTP 200 or 302 (redirect to login)

# Test in Alexa Developer Console
# Navigate to Test tab
# Click "Link Account"
# Expected: Redirects to HA login (not Music Assistant login)
# Login with HA credentials
# Expected: Account linked successfully
```

---

### Phase 5: Disable Tailscale Funnel (5 minutes)

```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Disable Tailscale Funnel
tailscale funnel off

# Verify disabled
tailscale funnel status
# Expected: No funnels configured
```

---

### Phase 6: Update DNS (Optional - 5 minutes)

**If using custom domain with Tailscale**:

1. Delete CNAME pointing to Tailscale MagicDNS
2. DNS now resolves directly to Nabu Casa (via HA)
3. Wait 5-15 minutes for DNS propagation

**Alternatively**: Keep CNAME for other uses (non-OAuth access)

---

### Phase 7: End-to-End Verification (10 minutes)

1. **Test Alexa App Account Linking**:
   - Open Alexa app
   - Disable Music Assistant skill
   - Re-enable Music Assistant skill
   - Complete account linking
   - Expected: Links using HA credentials (via Nabu Casa)

2. **Test Voice Commands**:
   ```
   "Alexa, play my music from Music Assistant"
   ```
   - Expected: Music plays successfully

3. **Verify from External Network**:
   - Disconnect from home WiFi
   - Connect to mobile hotspot
   - Retry account linking
   - Expected: Works from external network

---

### Rollback Procedure (Path 1)

**If migration fails**:

1. **Re-enable Tailscale Funnel**:
   ```bash
   ssh root@homeassistant.local
   tailscale funnel 8096
   ```

2. **Revert Alexa Skill OAuth URLs**:
   - Authorization URI: `https://musicassistant.yourdomain.com:8096/authorize`
   - Token URI: `https://musicassistant.yourdomain.com:8096/token`

3. **Test Original Configuration**:
   - Re-link Alexa account
   - Verify voice commands work

4. **Uninstall HA Integration** (if desired):
   - Settings → Devices & Services → Music Assistant → Remove

**State after rollback**: Back on Tailscale Funnel interim solution

---

## Migration Path 2 Procedure: Nabu Casa Proxy

**Prerequisites**:
- Nabu Casa custom service routing feature available
- Home Assistant version supports feature
- Nabu Casa subscription active

**Estimated Downtime**: 15-30 minutes (Alexa account linking unavailable)

---

### Phase 1: Backup Current Configuration (5 minutes)

```bash
# Same as Path 1, Phase 1
# Backup Music Assistant config and Alexa OAuth settings
```

---

### Phase 2: Configure Nabu Casa Custom Service Routing (10 minutes)

1. **Navigate to Nabu Casa Settings**:
   - HA UI: Settings → Nabu Casa → Custom Services (or similar)

2. **Add Music Assistant Service Route**:
   - Path: `/music-assistant`
   - Target: `http://music-assistant.local:8096` (or container IP)
   - Strip path: Yes (maps `/music-assistant/authorize` → `/authorize`)

3. **Save Configuration**

4. **Verify Route Active**:
   ```bash
   # Test from external network (mobile hotspot)
   curl -I https://[uuid].ui.nabu.casa/music-assistant/authorize

   # Expected: HTTP 200 or 401 (OAuth endpoint responds)
   ```

---

### Phase 3: Update Music Assistant to Trust Proxy Headers (5 minutes)

**If Music Assistant doesn't already trust proxy headers**:

1. **Edit Music Assistant Configuration**:
   ```yaml
   # music_assistant config (location varies by version)
   oauth:
     trust_proxy_headers: true
   ```

2. **Restart Music Assistant**:
   ```bash
   ha addons restart [music-assistant-addon-id]
   ```

3. **Verify Configuration**:
   ```bash
   # Check MA logs for proxy header usage
   ha addons logs [music-assistant-addon-id] | grep -i proxy
   ```

---

### Phase 4: Update Alexa Skill OAuth Configuration (10 minutes)

1. **Open Alexa Developer Console**: https://developer.amazon.com/alexa/console/ask
2. **Select Music Assistant Skill**
3. **Update Account Linking**:
   - Authorization URI: `https://[uuid].ui.nabu.casa/music-assistant/authorize`
   - Token URI: `https://[uuid].ui.nabu.casa/music-assistant/token`
   - Keep same Client ID and Client Secret
4. **Save Configuration**

---

### Phase 5: Test OAuth Flow (10 minutes)

```bash
# Test Nabu Casa proxy to Music Assistant
curl -I https://[uuid].ui.nabu.casa/music-assistant/authorize

# Expected: HTTP 200 or 401

# Test in Alexa Developer Console
# Navigate to Test tab → Link Account
# Expected: Redirects to Music Assistant login (via Nabu Casa proxy)
# Login with MA credentials
# Expected: Account linked successfully
```

---

### Phase 6: Disable Tailscale Funnel (5 minutes)

```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Disable Tailscale Funnel
tailscale funnel off

# Verify disabled
tailscale funnel status
# Expected: No funnels configured
```

---

### Phase 7: Update DNS (Optional - 5 minutes)

**Option A: Keep custom domain CNAME** (points to Tailscale, but Funnel off):
- Custom domain no longer works for OAuth (expected)
- Alexa now uses Nabu Casa domain: `[uuid].ui.nabu.casa`

**Option B: Update CNAME to Nabu Casa**:
- Some DNS providers allow CNAME to Nabu Casa domain
- Check if `[uuid].ui.nabu.casa` is stable (may change)
- Recommended: Use Nabu Casa domain directly (no CNAME)

---

### Phase 8: End-to-End Verification (10 minutes)

```bash
# Same as Path 1, Phase 7
# Test Alexa app account linking
# Test voice commands
# Test from external network
```

---

### Rollback Procedure (Path 2)

**If migration fails**:

1. **Re-enable Tailscale Funnel**:
   ```bash
   ssh root@homeassistant.local
   tailscale funnel 8096
   ```

2. **Revert Alexa Skill OAuth URLs**:
   - Authorization URI: `https://musicassistant.yourdomain.com:8096/authorize`
   - Token URI: `https://musicassistant.yourdomain.com:8096/token`

3. **Revert Music Assistant Proxy Settings** (if changed):
   ```yaml
   oauth:
     trust_proxy_headers: false
   ```
   - Restart Music Assistant

4. **Remove Nabu Casa Custom Service** (optional):
   - Delete `/music-assistant` route in Nabu Casa settings

**State after rollback**: Back on Tailscale Funnel interim solution

---

## Migration Path 3 Procedure: MA Cloud Service

**Prerequisites**:
- Music Assistant Cloud service operational
- Official Music Assistant Alexa skill published
- MA Cloud account created

**Estimated Downtime**: 30-45 minutes (local MA reconfiguration + Alexa re-linking)

---

### Phase 1: Create MA Cloud Account (5 minutes)

1. **Visit Music Assistant Cloud** (URL TBD when service launches)
2. **Create Account**:
   - Email, password
   - Verify email
3. **Note Account Credentials**: Save for local MA linking

---

### Phase 2: Link Local MA to MA Cloud (15 minutes)

1. **Open Local Music Assistant UI**: `http://homeassistant.local:8096`
2. **Navigate to Cloud Settings** (location TBD)
3. **Link to MA Cloud**:
   - Enter MA Cloud credentials
   - Authorize local instance
   - Expected: WebSocket connection established
4. **Verify Connection**:
   ```bash
   # Check MA logs for cloud connection
   ha addons logs [music-assistant-addon-id] | grep -i cloud
   # Expected: "Connected to MA Cloud" or similar
   ```

---

### Phase 3: Enable Official Music Assistant Alexa Skill (10 minutes)

1. **Open Alexa App**
2. **Search for Music Assistant Skill** (official skill)
3. **Enable Skill**
4. **Link Account**:
   - Redirects to MA Cloud OAuth
   - Login with MA Cloud credentials (not local MA)
   - Authorize Alexa
   - Expected: Account linked successfully

---

### Phase 4: Test Voice Commands (5 minutes)

```
"Alexa, play my music from Music Assistant"
```

- Expected: Alexa → MA Cloud → Local MA → Music plays

---

### Phase 5: Disable Tailscale Funnel (5 minutes)

```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Disable Tailscale Funnel
tailscale funnel off

# Verify disabled
tailscale funnel status
# Expected: No funnels configured
```

---

### Phase 6: End-to-End Verification (10 minutes)

1. **Test from external network** (mobile hotspot)
2. **Verify local MA receives commands from Alexa**
3. **Check MA Cloud dashboard** (if available) for connection status

---

### Rollback Procedure (Path 3)

**If migration fails**:

1. **Disconnect Local MA from MA Cloud**:
   - MA UI → Cloud Settings → Disconnect
   - Or delete MA Cloud account

2. **Re-enable Tailscale Funnel**:
   ```bash
   ssh root@homeassistant.local
   tailscale funnel 8096
   ```

3. **Revert to Original Alexa Skill** (if using custom skill):
   - Disable official MA skill
   - Re-enable custom/community skill
   - Re-link with original OAuth URLs

**State after rollback**: Back on Tailscale Funnel interim solution

---

## Contingency Plans (If All Paths Unavailable)

### Scenario: Tailscale Becomes Unavailable Before Permanent Solution Ready

**Options**:

---

#### Option A: Switch to Cloudflare Tunnel (Interim Alternative)

**Prerequisites**:
- Domain on Cloudflare
- `cloudflared` available for Home Assistant OS

**Steps**:
1. Install Cloudflare Tunnel (if add-on available)
2. Configure tunnel to route custom domain to MA port 8096
3. Update Alexa Skill OAuth URLs to Cloudflare domain
4. Test OAuth flow
5. Disable Tailscale subscription

**Pros**: Free, similar to Tailscale (no firewall changes)

**Cons**: Different commercial dependency (Cloudflare), not community-funded

---

#### Option B: Direct Port Forwarding (High Risk - Not Recommended)

**Prerequisites**:
- No CGNAT (carrier-grade NAT)
- Router access for port forwarding
- Ability to manage TLS certificates

**Steps**:
1. Verify public IP: `curl ifconfig.me`
2. Configure router port forwarding: External 443 → Internal 8096
3. Obtain TLS certificate (Let's Encrypt HTTP-01 or DNS-01)
4. Install certificate in Music Assistant (or reverse proxy)
5. Update Alexa Skill OAuth URLs to public IP or DynDNS domain
6. Implement security hardening (firewall rules, rate limiting)

**Pros**: No external dependencies, no subscription cost

**Cons**: Security risk, certificate management complexity, ISP may block ports

**Recommendation**: Only use if other options infeasible and you have security expertise

---

#### Option C: Wait for Permanent Solution (Delay Alexa Integration)

**Prerequisites**: None

**Steps**:
1. Disable Alexa Skill integration
2. Continue using Music Assistant locally (without Alexa)
3. Monitor triggers for permanent solution
4. Re-enable when solution available

**Pros**: No interim workaround needed, no security risk

**Cons**: Lose Alexa voice control functionality

---

## Monitoring and Alerting

**What to monitor while on interim Tailscale solution**:

### Weekly Checks

```bash
# Verify Tailscale Funnel still running
ssh root@homeassistant.local
tailscale funnel status

# Expected: Funnel on for port 8096
# If Funnel off, re-enable: tailscale funnel 8096
```

### Monthly Checks

1. **Tailscale Subscription Status**:
   - Visit: https://login.tailscale.com/admin/settings/billing
   - Verify subscription active
   - Check payment method valid

2. **Tailscale Pricing**:
   - Check: https://tailscale.com/pricing
   - Note any price increases
   - If >$20/month, evaluate migration urgency

3. **Migration Trigger Status**:
   - Check Nabu Casa roadmap: https://www.nabucasa.com/roadmap (if exists)
   - Check Music Assistant GitHub releases: https://github.com/music-assistant/hass-music-assistant/releases
   - Check Tailscale status: https://status.tailscale.com

### Automated Monitoring (Optional)

**Set up alerts**:

```yaml
# Home Assistant automation (example)
automation:
  - alias: "Alert: Tailscale Funnel Down"
    trigger:
      platform: time_pattern
      hours: "/1"  # Every hour
    condition:
      # Check if Funnel endpoint unreachable (requires custom sensor)
      - condition: state
        entity_id: sensor.tailscale_funnel_status
        state: 'down'
    action:
      - service: notify.mobile_app
        data:
          message: "Tailscale Funnel is down - Alexa OAuth unavailable"
```

---

## Communication Plan

**When migrating**:

### Before Migration

1. **Announce Migration Plan** (GitHub issue, forum post):
   - Timeline (when migration will occur)
   - Expected downtime (15-60 minutes)
   - User action required (if any)

2. **Prepare Documentation**:
   - Migration guide (this document)
   - Troubleshooting guide (common issues)
   - Rollback procedure

### During Migration

1. **Update Status** (progress updates):
   - "Migration Phase 1 complete"
   - "Migration Phase 2 in progress"
   - "Testing in progress"

2. **Monitor for Issues**:
   - Check community reports (Discord, forum)
   - Respond to troubleshooting questions

### After Migration

1. **Announce Completion**:
   - Migration successful
   - Verify users can re-link accounts
   - Document any issues encountered

2. **Gather Feedback**:
   - Survey users on migration experience
   - Document lessons learned
   - Update migration procedure based on feedback

---

## Success Criteria for Migration

**Migration is successful when**:

- ✅ Alexa account linking works via new solution (Nabu Casa or MA Cloud)
- ✅ Voice commands trigger Music Assistant playback
- ✅ Account linking persists across HA restarts
- ✅ Works from external network (not just local)
- ✅ Tailscale Funnel disabled (no longer needed)
- ✅ No increase in operational complexity (or reduced complexity)
- ✅ Ongoing costs acceptable (preferably Nabu Casa subscription only)

---

## Post-Migration Cleanup

**After successful migration**:

1. **Cancel Tailscale Subscription** (if no other use):
   - Visit: https://login.tailscale.com/admin/settings/billing
   - Cancel subscription (if Tailscale only used for Funnel)

2. **Delete DNS CNAME** (if no longer used):
   - Remove CNAME pointing to Tailscale MagicDNS
   - Wait for DNS propagation (5-15 minutes)

3. **Update Documentation**:
   - Mark Tailscale procedure as DEPRECATED
   - Update quickstart guides to reference new solution
   - Archive interim solution documentation

4. **Remove Tailscale Add-on** (optional):
   - If Tailscale only used for Funnel (not VPN)
   - HA Settings → Add-ons → Tailscale → Uninstall

---

## FAQs

### Q: Can I migrate before trigger occurs?

**A**: Yes, if you want to test new solution early. Follow migration procedure, but be prepared for potential bugs/issues in early releases.

---

### Q: Can I use multiple solutions simultaneously?

**A**: Not recommended. Running both Tailscale and Nabu Casa proxy simultaneously can cause OAuth confusion (multiple redirect URIs). Choose one solution.

---

### Q: What if migration fails mid-process?

**A**: Execute rollback procedure for the attempted path. Return to Tailscale Funnel interim solution. Document failure reason, report to community.

---

### Q: Will I lose Music Assistant data during migration?

**A**: No. Music Assistant library, playlists, and configuration are preserved. Only OAuth configuration changes. However, **always backup before migration** (Phase 1 of each procedure).

---

### Q: How long should I stay on interim solution?

**A**: Until one of the migration triggers occurs. Monitor triggers monthly. Interim solution is stable and functional - no urgency to migrate unless triggered.

---

## See Also

- **[Future Architecture Strategy](../00_ARCHITECTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md)** - Why we're migrating (principles)
- **[Future Implementation Work](../04_INFRASTRUCTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_WORK.md)** - What needs to be built (technical details)
- **[Current Interim Solution](TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md)** - How to implement Tailscale Funnel (if not yet migrated)
- **[Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md)** - Why public OAuth exposure is required

---

## Document Maintenance

**Review Frequency**: Quarterly or when triggers change status

**Update When**:
- Nabu Casa announces custom service routing roadmap
- Music Assistant announces HA integration plans
- Music Assistant announces cloud service plans
- Tailscale changes Funnel availability or pricing
- Community feedback identifies migration issues

**Maintainer**: Operations team, community contributors
