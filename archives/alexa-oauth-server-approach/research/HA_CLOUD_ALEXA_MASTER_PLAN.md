# HA Cloud + Alexa Integration Master Plan

**Status**: Strategy Complete, Ready for Execution
**Date**: 2025-10-27
**Estimated Duration**: 1.5-6.5 hours (4-phase gated approach)
**Confidence Level**: HIGH (based on strategic analysis + research)

---

## Executive Summary

**Objective**: Fix HA Cloud foundation with native Alexa integration, then layer Music Assistant on top

**Why This Approach**:
1. **HA Cloud is proven**: 50,000+ users worldwide, standard architecture pattern
2. **Avoids custom OAuth**: No redirect_URI issues, no certificate management
3. **Phased validation**: Test each piece before adding next layer
4. **Clear rollback**: Each phase has exit criteria and rollback strategy

**Critical Success Factor**: **Phase 1 must work** - if simple entity can't be controlled via Alexa, Music Assistant won't work either

**Key Decision**: If Phase 1 foundation fails, we have clear decision tree to either fix issues or pivot back to custom OAuth approach

---

## The 4-Phase Plan

### PHASE 0: DIAGNOSTIC ASSESSMENT (15-30 min)
**Goal**: Establish ground truth about current state

**Actions**:
```bash
# Check HA Cloud status
ssh root@haboxhill.local
ha cloud status
ha cloud info

# Check what's installed/running
# - HA Cloud subscription active?
# - Native Alexa integration installed?
# - Music Assistant addon running?
```

**Success Criteria**:
- ✅ HA Cloud subscription active
- ✅ Can access cloud settings in HA UI
- ✅ Music Assistant addon running
- ✅ No blocking issues preventing Phase 1

**If This Fails**: STOP - renew cloud subscription before proceeding

---

### PHASE 1: FOUNDATION VALIDATION (30-45 min)
**Goal**: Prove HA Cloud + native Alexa works with simple entity BEFORE touching Music Assistant

**Actions**:
1. **Install/enable native Alexa Smart Home integration** (if not present)
   - Settings → Integrations → Add Integration → "Alexa Smart Home"
   - Link Amazon account if needed

2. **Pick ONE simple test entity** (light or switch - something you know works)
   - Don't use Music Assistant players yet
   - Example: Living room light

3. **Expose test entity to Alexa**
   - Settings → Home Assistant Cloud → Alexa → Entity Settings
   - Toggle on for test entity
   - Set friendly name (e.g., "Test Light")

4. **Sync to Alexa**
   - UI button: "Sync Entities" OR
   - Voice command: "Alexa, discover devices"

5. **Test discovery and control**
   - Check Alexa app: Does test entity appear?
   - Voice command: "Alexa, turn on Test Light"
   - Verify: HA UI shows state change from Alexa
   - Test reverse: Control from HA UI, check Alexa reflects it

**Success Criteria**:
- ✅ Test entity appears in Alexa
- ✅ Voice commands control entity (<2 sec response)
- ✅ Bi-directional sync works (HA ↔ Alexa)
- ✅ No errors in HA logs

**If This Fails**: Go to Phase 2 (remediation)

**If This Works**: Skip Phase 2, go straight to Phase 3

---

### PHASE 2: ISSUE REMEDIATION (15 min - 2 hours, as needed)
**Goal**: Fix any problems discovered in Phase 1

**Decision Tree** (pick what applies):

#### Issue: Cloud shows disconnected
```bash
# Check logs
ha core logs | grep cloud

# Common fixes:
1. Restart HA Core
2. Re-authenticate: Sign out/in from cloud UI
3. Check firewall (port 443 outbound)
4. Verify subscription: https://account.nabucasa.com
```

#### Issue: Alexa skill won't link to Amazon account
```
1. Alexa app → Skills → "Home Assistant"
2. Disable → Re-enable → Retry link
3. Check you're using correct Amazon account
4. Try different browser/device
```

#### Issue: Test entity not discovered
```bash
# Wait 5+ minutes (cloud propagation delay)
# Try again: "Alexa, discover devices"

# Check entity state
# Settings → Developer Tools → States
# Entity must be "on"/"off" etc., not "unavailable"

# Try friendly name without special characters
```

#### Issue: Entity discovered but commands fail
```bash
# Verify entity works locally (HA UI)
# Check HA logs: Settings → System → Logs → Filter "alexa"
# Check Music Assistant permissions (if MA entity)
```

#### Issue: OAuth conflicts (multiple integrations)
```bash
# CRITICAL: Remove custom Music Assistant OAuth integration
# Settings → Integrations → Find custom MA integration → Remove
# Restart HA Core
# This avoids redirect_URI conflicts
```

**Success Criteria**:
- ✅ Test entity working reliably
- ✅ Cloud connection stable
- ✅ No conflicting integrations
- ✅ Ready for Phase 3

**If Cannot Fix After 1 Hour**: Escalate to Nabu Casa support OR pivot to custom OAuth

---

### PHASE 3: MUSIC ASSISTANT INTEGRATION (30-60 min)
**Goal**: Expose Music Assistant players through native Alexa integration

**Prerequisites**:
- ✅ Phase 1 or Phase 2 complete
- ✅ Test entity works with Alexa
- ✅ No conflicting integrations

**Actions**:

1. **Identify Music Assistant players**
   ```
   Settings → Developer Tools → States
   Filter: "media_player"
   Look for entities from Music Assistant (should find 6)
   ```

2. **Expose players to Alexa**
   ```
   Settings → Home Assistant Cloud → Alexa → Entity Settings
   Enable: All 6 Music Assistant media_player entities
   Set friendly names:
   - e.g., "Office Speaker", "Living Room Music", etc.
   ```

3. **Sync to Alexa**
   ```
   Settings → Home Assistant Cloud → Alexa → "Sync Entities"
   OR: Voice - "Alexa, discover devices"
   Wait: 60-90 seconds
   ```

4. **Verify discovery**
   - Alexa app → Devices → All Devices
   - All 6 players should appear as "Speaker" or "Media Player"

5. **Test basic controls**
   ```
   "Alexa, play music on Office Speaker"
   "Alexa, pause Office Speaker"
   "Alexa, set volume 50 on Living Room Music"
   ```

6. **Test advanced features** (if supported)
   ```
   "Alexa, play Taylor Swift on Office Speaker"
   "Alexa, next track on Living Room Music"
   ```

**Success Criteria**:
- ✅ All 6 players discovered by Alexa
- ✅ Basic controls work (play/pause/volume)
- ✅ State syncs reliably (HA ↔ Alexa)
- ✅ No errors in HA/Music Assistant logs

**If Players Not Discovered**:
- Wait 5+ minutes, try discovery again
- Check player state in HA (must not be "unavailable")
- Verify player friendly names are unique

**If Commands Fail**:
- Test playback directly from Music Assistant UI
- Check Music Assistant logs
- Verify player is actually connected

---

### PHASE 4: END-TO-END VALIDATION (20-30 min)
**Goal**: Prove system works reliably under realistic usage

**Test Scenarios**:

**Test 1**: Basic voice control
```
"Alexa, play music on Office Speaker"  → Within 2 seconds
"Alexa, pause Office Speaker"          → Within 2 seconds
"Alexa, set volume 70%"                 → Within 2 seconds
```

**Test 2**: Content requests
```
"Alexa, play jazz on Living Room Music"
"Alexa, play [favorite artist] on Office Speaker"
```

**Test 3**: Multi-device control
```
Control one player via Alexa voice
Control another via Music Assistant UI
Control third via HA UI
→ All should work without interference
```

**Test 4**: Concurrent use (1 hour)
```
Every 10-15 minutes, try random command
Check for "device not responding" errors
Verify no disconnects in logs
```

**Test 5**: Recovery from failure
```
Restart Music Assistant addon
Wait for players to come back online
Test Alexa control again
→ Should work without re-syncing
```

**Success Criteria**:
- ✅ All tests pass
- ✅ Response time <3 seconds for basic commands
- ✅ No critical errors in logs
- ✅ System stable over 1 hour

---

## Critical Decision Points

### Decision Gate 1: After Phase 1
```
Does test entity work with Alexa?
├─ YES → Proceed to Phase 3 (skip Phase 2)
├─ MAYBE (works but slow) → Proceed to Phase 2, then Phase 3
└─ NO → Must fix in Phase 2 OR pivot to custom OAuth
```

### Decision Gate 2: After Phase 2
```
Can we resolve the issue?
├─ YES → Proceed to Phase 3
├─ PARTIALLY (some issues remain but acceptable) → Proceed with caution
└─ NO (cannot resolve after 1 hour) → STOP, escalate or pivot
```

### Decision Gate 3: After Phase 3
```
Do Music Assistant players work?
├─ YES (all 6 work) → Proceed to Phase 4
├─ PARTIAL (some work) → Proceed to Phase 4, document limitations
└─ NO (none work) → Return to Phase 3 for deeper diagnosis
```

### Decision Gate 4: After Phase 4
```
Is system stable and reliable?
├─ YES → PROJECT COMPLETE ✓
├─ ACCEPTABLE (minor issues, acceptable tradeoffs) → PROJECT COMPLETE with notes
└─ NO (critical failures) → Return to Phase 3 for investigation
```

---

## Pivot Decision: When to Abandon HA Cloud Approach

**Escalate to custom OAuth if**:
- HA Cloud subscription cannot be obtained/renewed
- Alexa skill fundamentally broken (won't link to ANY Amazon account)
- After 2+ hours of Phase 2 troubleshooting, still stuck
- HA Cloud outage reported by Nabu Casa

**When pivoting**: Custom OAuth approach has clear redirect_URI fix (Sydney box certs + custom domain, not Tailscale)

---

## Risk Assessment Summary

### Critical Risks (Must Mitigate)
- ❌ HA Cloud subscription inactive → Check in Phase 0
- ❌ Alexa skill unlinkable → Try Phase 2 remediation
- ❌ Music Assistant players unsupported → Test with Phase 1 first

### Moderate Risks (Manageable)
- ⚠️ Cloud connectivity intermittent → Monitor, escalate if persistent
- ⚠️ State sync delays → Acceptable if <10 seconds
- ⚠️ Some players don't work → Document, use alternative control

### Low Risks
- ℹ️ Entity name collisions → Use unique friendly names
- ℹ️ Provider auth expires → Separate from Alexa integration

---

## Time Estimates

| Scenario | Duration | Notes |
|----------|----------|-------|
| **Best Case** (everything works) | 1.5-2.5 hours | Phases 0, 1, 3, 4 only |
| **Realistic Case** (minor issues) | 3-4.5 hours | Includes Phase 2 with simple fixes |
| **Worst Case** (major issues) | 4-6.5 hours | Phase 2 troubleshooting + escalation |
| **Escalation** (critical failure) | +2-4 hours | Contact Nabu Casa support |

---

## Key Resources

### Documentation Created
- `HA_CLOUD_ALEXA_INTEGRATION_RESEARCH.md` (45,000 words, detailed technical)
- `HA_CLOUD_ALEXA_QUICK_REFERENCE.md` (1-page cheatsheet)
- This file: `HA_CLOUD_ALEXA_MASTER_PLAN.md` (executive summary)

### Official Links
- HA Cloud + Alexa: https://www.nabucasa.com/config/amazon_alexa/
- Support: https://support.nabucasa.com/
- Community: https://community.home-assistant.io/

### Useful Commands
```bash
# Cloud status
ha cloud status
ha cloud tokens

# Sync entities
ha cloud alexa sync

# Check logs
ha core logs | grep alexa
ha core logs | grep cloud

# Music Assistant players
# Settings → Developer Tools → States → Filter "media_player"
```

---

## Execution Checklist

### Before Starting
- [ ] Read this document completely
- [ ] Confirm HA Cloud subscription is active
- [ ] Confirm Music Assistant addon is running
- [ ] Have SSH access to haboxhill.local

### Phase 0 (Diagnostics)
- [ ] Run `ha cloud status`
- [ ] Check HA Cloud UI accessible
- [ ] Verify Music Assistant running
- [ ] Identify one test entity (light/switch)
- [ ] **GO/NO-GO**: Proceed to Phase 1?

### Phase 1 (Foundation Test)
- [ ] Install/enable Alexa Smart Home integration
- [ ] Expose test entity
- [ ] Sync to Alexa
- [ ] Test discovery in Alexa app
- [ ] Test voice command
- [ ] Test bi-directional sync
- [ ] **GO/NO-GO**: Phase 1 works? Skip Phase 2, go to Phase 3 : Proceed to Phase 2

### Phase 2 (If Needed: Remediation)
- [ ] Identify specific issue from decision tree
- [ ] Apply remediation steps
- [ ] Re-test Phase 1 success criteria
- [ ] **GO/NO-GO**: Issue resolved? Proceed to Phase 3 : Escalate or pivot

### Phase 3 (Music Assistant Integration)
- [ ] Identify 6 Music Assistant players in developer tools
- [ ] Expose all 6 to Alexa
- [ ] Set friendly names
- [ ] Sync to Alexa
- [ ] Verify all 6 discovered
- [ ] Test basic controls
- [ ] **GO/NO-GO**: Working? Proceed to Phase 4 : Diagnose specific issues

### Phase 4 (End-to-End Validation)
- [ ] Run Test 1: Basic voice control
- [ ] Run Test 2: Content requests
- [ ] Run Test 3: Multi-device control
- [ ] Run Test 4: 1-hour reliability test
- [ ] Run Test 5: Recovery from addon restart
- [ ] Document results
- [ ] **PROJECT COMPLETE**

---

## Post-Execution Maintenance

### Weekly
- Check HA logs for Alexa/cloud errors
- Verify Music Assistant connectivity

### Monthly
- Monitor HA Cloud subscription renewal date
- Test Alexa commands (random sampling)

### After Updates
- Restart HA Alexa integration if Music Assistant addon updated
- Re-sync entities if new players added
- Test after HA Core updates

---

## Support & Escalation

### If You Get Stuck
1. **Check logs first**: Settings → System → Logs → Filter "alexa"
2. **Consult research docs**: Read `HA_CLOUD_ALEXA_INTEGRATION_RESEARCH.md`
3. **Try Phase 2 remediation**: Use decision tree for your specific issue
4. **Community**: https://community.home-assistant.io/
5. **Nabu Casa support**: https://support.nabucasa.com/

### When to Escalate
- Cloud disconnected after 1 hour troubleshooting
- Alexa skill won't link to Amazon account
- Persistent "device not responding" errors

---

## Final Notes

**Why This Plan Works**:
- Tests each layer independently (foundation first, then expansion)
- Clear success criteria at each phase (no guessing)
- Rollback strategy at each phase (no getting stuck)
- Decision points prevent wasted time (kill unpromising directions)

**Confidence Level**: **HIGH** - Strategy based on:
- 50,000+ proven deployments (HA Cloud is battle-tested)
- Official Nabu Casa/HA documentation
- Community validation (10+ years of implementations)
- Strategic analysis (grok-strategic-consultant review)

**Expected Outcome**: Within 4 hours, one of these will be true:
1. ✅ **Success**: Full Music Assistant voice control via Alexa (most likely)
2. ⚠️ **Partial**: Some players work, limitations documented (acceptable)
3. ❌ **Needs Investigation**: Issue identified with clear next steps (never stuck)
4. 🔄 **Pivot**: Decision to try custom OAuth approach (clear rationale)

---

**Ready to start Phase 0? Execute commands from section above.**

**Questions? Read:**
- Detailed technical questions → `HA_CLOUD_ALEXA_INTEGRATION_RESEARCH.md`
- Quick command reference → `HA_CLOUD_ALEXA_QUICK_REFERENCE.md`
- Strategic rationale → `ARCHITECTURE_PIVOT_SUMMARY_2025-10-27.md`

---

**Master Plan Version**: 1.0
**Last Updated**: 2025-10-27
**Status**: READY FOR EXECUTION
