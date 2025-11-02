# Nabu Casa Port 8096 Test - Ready to Execute
**Created**: 2025-10-25 18:44
**Status**: WAITING FOR HA BOOT (expected ready 18:50)
**Purpose**: Executive summary for immediate action when Home Assistant is online

---

## Current Situation

✅ **Custom domain configured**: `boxhillsouth.jasonhollis.com`
✅ **DNS propagated**: CNAME → `0gdzommh4w1tug2s97xnn9spylzmkkbs.ui.nabu.casa`
⏳ **Home Assistant**: REBOOTING (SSL certificate generation in progress)
❓ **Critical unknown**: Can Nabu Casa route to port 8096 (Music Assistant OAuth)?

**Expected ready time**: ~18:50 (5-7 minutes from 18:44)

---

## What Happens Next (3-Minute Overview)

### When HA is Ready (~18:50)

**Run 2 quick tests** (2 minutes total):

```bash
# Test 1: Verify custom domain works (baseline)
curl -I https://boxhillsouth.jasonhollis.com/

# Expected: 200 OK or 401 Unauthorized
# If timeout: Wait 2 more minutes, HA still booting

# Test 2: Test port 8096 routing (CRITICAL TEST)
curl -I https://boxhillsouth.jasonhollis.com:8096/authorize

# If 200/401: PORT WORKS! → Go to Path A (5 min to success)
# If connection refused/timeout: PORT BLOCKED → Go to Path B (15 min to success)
```

---

## Path A: Port 8096 Works (5 Minutes to Success)

**If Test 2 succeeds** (200 or 401 response):

1. Update Alexa Skill with these URLs (3 min):
   - Authorization: `https://boxhillsouth.jasonhollis.com:8096/authorize`
   - Token: `https://boxhillsouth.jasonhollis.com:8096/token`

2. Test OAuth flow (2 min):
   - Open Alexa app → Enable skill → Link account
   - Expected: Redirected to Music Assistant login
   - Expected: Account linked successfully

**Result**: ✅ Nabu Casa works perfectly, zero additional config needed!

---

## Path B: Port 8096 Blocked (15 Minutes to Success)

**If Test 2 fails** (connection refused, timeout, 502):

**Choose between two options**:

### Option B1: Reverse Proxy (RECOMMENDED if you value community funding)

**Why**: Uses Nabu Casa (community funding), custom domain, minimal maintenance

**What**: Install nginx add-on to proxy `/oauth/*` to `music-assistant:8096`

**Steps**:
1. Install nginx add-on from HA store (3 min)
2. Configure proxy rules (5 min) - exact config provided in docs
3. Update Alexa Skill URLs to use `/oauth/` paths (3 min)
4. Test OAuth flow (4 min)

**URLs**:
- Authorization: `https://boxhillsouth.jasonhollis.com/oauth/authorize`
- Token: `https://boxhillsouth.jasonhollis.com/oauth/token`

**Pros**: Custom domain, uses Nabu Casa, minimal maintenance
**Cons**: Nginx add-on required (one-time setup)

---

### Option B2: Tailscale Funnel (Alternative)

**Why**: Independent from Nabu Casa, already documented

**What**: Use Tailscale Funnel to expose OAuth directly

**Steps**: Follow existing docs/05_OPERATIONS/TAILSCALE_FUNNEL_CONFIGURATION_HA.md

**URLs**:
- Authorization: `https://a0d7b954-tailscale.ts.net/oauth/authorize`
- Token: `https://a0d7b954-tailscale.ts.net/oauth/token`

**Pros**: Independent, proven working, simple
**Cons**: No custom domain (*.ts.net), doesn't use Nabu Casa subscription

---

## Complete Documentation (Read While Waiting)

### Test Procedures
**Location**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/docs/05_OPERATIONS/NABU_CASA_CUSTOM_DOMAIN_TEST_PLAN.md`

**Contains**:
- Exact test commands with expected outputs
- Timeline (when to run each test)
- Troubleshooting for test failures
- Verification procedures

---

### Decision Tree
**Location**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/docs/05_OPERATIONS/NABU_CASA_VS_TAILSCALE_DECISION_TREE.md`

**Contains**:
- Scenario A implementation (port 8096 works)
- Scenario B1 implementation (reverse proxy)
- Scenario B2 implementation (Tailscale Funnel)
- Complete nginx configuration
- Verification steps for each path
- Maintenance requirements

---

### Port Routing Reference
**Location**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/docs/02_REFERENCE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md`

**Contains**:
- How Nabu Casa routing works (architecture)
- Why port 8096 might be blocked
- Known workarounds and alternatives
- Performance and security considerations
- Troubleshooting reference

---

## Quick Command Reference

### Check HA Boot Status
```bash
# Test if HA is responding
curl -I https://boxhillsouth.jasonhollis.com/

# If timeout: Not ready yet, wait 2 minutes
# If 200/401: Ready for testing!
```

---

### Run Critical Test
```bash
# The test that determines everything
curl -I https://boxhillsouth.jasonhollis.com:8096/authorize

# Success indicators:
# - HTTP/2 200 OK
# - HTTP/2 401 Unauthorized
# - Response headers visible

# Failure indicators:
# - curl: (7) Failed to connect
# - curl: (28) Connection timed out
# - HTTP/2 502 Bad Gateway
```

---

### Test Internal OAuth Server (If External Test Fails)
```bash
# SSH to HA host, then:
docker exec -it homeassistant curl -I http://music-assistant:8096/authorize

# If this works but external test fails:
# → OAuth server is running
# → Nabu Casa blocking port 8096
# → Proceed to Path B (reverse proxy or Tailscale)

# If this fails:
# → OAuth server not running
# → Check Music Assistant configuration
# → Restart Music Assistant container
```

---

## Expected Timelines

| Scenario | Total Time | Breakdown |
|----------|-----------|-----------|
| **HA Boot** | 5-7 min | Waiting time (18:44 → 18:50) |
| **Run Tests** | 2 min | Test 1 + Test 2 + diagnosis |
| **Path A** | +5 min | Update Alexa Skill, test flow |
| **Path B1** | +15 min | Install nginx, configure, test |
| **Path B2** | +15 min | Configure Tailscale Funnel |
| | | |
| **Best case** | 12-14 min | Port 8096 works (Path A) |
| **Likely case** | 22-24 min | Port blocked, reverse proxy (Path B1) |
| **Alternative** | 22-24 min | Port blocked, Tailscale (Path B2) |

**Current time**: 18:44
**Expected completion**: 18:57 (best case) or 19:08 (likely case)

---

## Success Criteria

After implementation (any path), verify:

1. ✅ OAuth endpoints accessible via HTTPS
2. ✅ Alexa Skill can complete account linking
3. ✅ Music Assistant OAuth server receives authorization requests
4. ✅ Token exchange succeeds
5. ✅ Alexa app shows "Account linked"
6. ✅ Voice commands work: "Alexa, ask Music Assistant to play [song]"

---

## What to Do RIGHT NOW

1. ☕ **Wait for HA boot** (expected ready 18:50)
   - Optional: Read full documentation while waiting
   - Recommended: Have terminal ready with curl commands

2. ⏰ **At 18:50**: Run Test 1 (baseline check)
   ```bash
   curl -I https://boxhillsouth.jasonhollis.com/
   ```

3. 🎯 **If Test 1 succeeds**: Run Test 2 (critical test)
   ```bash
   curl -I https://boxhillsouth.jasonhollis.com:8096/authorize
   ```

4. 🚀 **Follow the path** based on Test 2 result:
   - **200/401** → Path A (5 min to success)
   - **Connection refused/timeout** → Path B1 or B2 (15 min to success)

---

## Questions Answered by This Test

❓ **Does Nabu Casa support non-standard ports?**
→ Test 2 answers definitively

❓ **Do I need additional configuration?**
→ Path A: No | Path B: Yes (reverse proxy or Tailscale)

❓ **Can I use custom domain for OAuth?**
→ Path A & B1: Yes | Path B2: No (*.ts.net subdomain)

❓ **How long until working OAuth?**
→ Path A: 5 min | Path B: 15 min

❓ **Does this support community funding?**
→ Path A & B1: Yes (uses Nabu Casa) | Path B2: No

---

## After Success

**Document the result**:
```bash
# Add to SESSION_LOG.md
echo "2025-10-25 18:XX: Nabu Casa test complete - [Result]" >> SESSION_LOG.md

# Add to DECISIONS.md (if needed)
# Document which path was chosen and why
```

**Update progress tracker**:
- Mark OAuth exposure as COMPLETE in docs/05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md
- Update blocker status (resolved)
- Record implementation approach

**Next steps**:
- Complete Alexa Skill configuration
- Test voice commands
- Celebrate working OAuth! 🎉

---

## Links to Full Documentation

- **Test Plan**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/docs/05_OPERATIONS/NABU_CASA_CUSTOM_DOMAIN_TEST_PLAN.md`
- **Decision Tree**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/docs/05_OPERATIONS/NABU_CASA_VS_TAILSCALE_DECISION_TREE.md`
- **Port Routing Reference**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/docs/02_REFERENCE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md`

---

**YOU ARE HERE**: ⏳ Waiting for HA boot (ready ~18:50)
**NEXT ACTION**: Run Test 1 at 18:50, then Test 2
**EXPECTED OUTCOME**: Working OAuth in 12-24 minutes (depending on test result)
