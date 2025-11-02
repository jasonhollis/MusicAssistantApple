# Documentation Remediation Guide - MusicAssistantApple Project
**Purpose**: Comprehensive guide to fix all Clean Architecture violations
**Date**: 2025-10-26
**Status**: ACTIVE - Remediation in progress
**Estimated Effort**: 8-11 hours total

**Related**:
- [Documentation Realignment Report](DOCUMENTATION_REALIGNMENT_REPORT.md) - Initial audit
- [Clean Architecture Guide](../CLAUDE.md) - Framework principles

---

## Executive Summary

This guide provides a systematic approach to fixing ALL Clean Architecture violations identified in the MusicAssistantApple project documentation. The audit found **44 documentation files** with various levels of compliance issues.

**Key Finding**: While the documentation structure follows Clean Architecture well overall, **Layer 00 (ARCHITECTURE) contains extensive technology-specific details** that violate the Dependency Rule. These must be abstracted or moved to Layer 04.

---

## Critical Violations Requiring Immediate Fix

### VIOLATION 1: Layer 00 Contains Technology Implementation Details

**File**: `docs/00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md`
**Size**: 34,594 bytes (870 lines)
**Severity**: CRITICAL - Core Dependency Rule violation

**Problem**: This document mentions specific technologies throughout:
- "Login with Amazon (LWA) OAuth2" - specific protocol
- "alexa-cookie library" - specific implementation
- "aiohttp" - specific framework
- "Python 3", "Redis", "AWS Lambda" - specific technologies
- Code examples with implementation details
- Specific API endpoints and URLs

**What Layer 00 Should Contain**:
- Abstract authentication patterns (not "OAuth 2.0" but "delegated authorization pattern")
- Security principles (not "PKCE" but "authorization code protection mechanisms")
- Trade-offs between approaches (not "LWA vs cookies" but "official vs unofficial patterns")
- Strategic considerations (cost, maintenance, security) without naming tools

**Remediation Strategy**:

**Option A: Split Into Multiple Documents** (RECOMMENDED)
1. **Keep in Layer 00** (abstracted):
   - "Authentication Pattern Strategy for Third-Party Voice Assistants"
   - Focus on principles: delegation, direct integration, ecosystem leverage
   - Trade-offs: security, maintenance, user experience (abstract terms only)
   - Decision criteria framework (no technology names)

2. **Move to Layer 01** (use cases):
   - "Voice Assistant Account Linking Workflows"
   - User goals: link account, control music via voice
   - Success/failure scenarios (tech-agnostic)

3. **Move to Layer 02** (reference):
   - "Third-Party Authentication Methods Comparison Table"
   - Quick lookup: official vs unofficial approaches
   - Can mention specific methods but as reference data

4. **Move to Layer 04** (infrastructure):
   - "OAuth 2.0 Implementation Options for Alexa"
   - All technical details: LWA, cookies, PKCE, code examples
   - Technology stack recommendations
   - Implementation guidance with specific tools

**Option B: Complete Rewrite** (THOROUGH)
- Delete current file entirely
- Create new abstract Layer 00 document
- Extract all technical details to new Layer 04 documents
- Create cross-references

**Estimated Effort**: 3-4 hours (Option A), 5-6 hours (Option B)

**Action Items**:
1. [ ] Create new abstract Layer 00 document: `VOICE_ASSISTANT_AUTHENTICATION_PRINCIPLES.md`
2. [ ] Extract technical details to Layer 04: `ALEXA_OAUTH_IMPLEMENTATION_GUIDE.md`
3. [ ] Extract comparison table to Layer 02: `AUTHENTICATION_METHODS_COMPARISON.md`
4. [ ] Extract user workflows to Layer 01: `VOICE_CONTROL_ACCOUNT_LINKING.md`
5. [ ] Archive original file: `docs/archives/2025-10-26-ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md`
6. [ ] Update all cross-references to point to new files

---

### VIOLATION 2: ADR 002 Contains Implementation Details

**File**: `docs/00_ARCHITECTURE/ADR_002_ALEXA_INTEGRATION_STRATEGY.md`
**Size**: 24,986 bytes (623 lines)
**Severity**: MODERATE - Mixed abstraction levels

**Problem**: While mostly abstract, contains implementation details:
- Lines 68-90: Specific system diagrams with port numbers, container names
- Lines 100-131: Specific technology requirements (OAuth2 server, SSL, AWS Lambda)
- Lines 441-478: Implementation guidance with technical details

**What Layer 00 ADRs Should Contain**:
- The architectural decision question (abstract)
- Options considered (abstract patterns, not tools)
- Principles at stake
- Trade-offs (conceptual, not technical)
- Decision criteria (abstract)
- Consequences (high-level)

**Remediation Strategy**:

**Option A: Remove Implementation Details** (RECOMMENDED)
1. Keep decision question and options (abstract patterns)
2. Move system diagrams to Layer 04
3. Move implementation guidance to Layer 05
4. Keep principles and consequences (abstract)
5. Reference Layer 04 docs for technical details

**Option B: Mark as "Mixed Layer Document" with Clear Separation**
1. Add section markers: "[ARCHITECTURE DECISION]" vs "[IMPLEMENTATION NOTES]"
2. Move implementation notes to appendix
3. Add clear disclaimer that appendix is Layer 04 material

**Estimated Effort**: 1-2 hours (Option A), 30 minutes (Option B)

**Action Items**:
1. [ ] Remove lines 68-90 (system diagrams) → Move to Layer 04
2. [ ] Remove lines 100-131 (technical requirements) → Move to Layer 04
3. [ ] Remove lines 441-478 (implementation guidance) → Move to Layer 05
4. [ ] Create new Layer 04 document: `HOME_ASSISTANT_INTEGRATION_TECHNICAL_DESIGN.md`
5. [ ] Update ADR to reference Layer 04 document for implementation details

---

### VIOLATION 3: Missing Layer 01 Use Case Documentation

**Missing Files**:
- `docs/01_USE_CASES/ALEXA_VOICE_CONTROL.md` (CRITICAL GAP)
- `docs/01_USE_CASES/LINK_VOICE_ASSISTANT_ACCOUNT.md` (IMPORTANT GAP)

**Severity**: HIGH - Critical use cases undocumented

**What's Missing**:
1. **Actor**: Alexa user (voice commands)
2. **Goal**: Control Music Assistant playback via voice
3. **Preconditions**: Account linked via OAuth
4. **Success scenarios**: Play, pause, skip, volume, TTS
5. **Failure scenarios**: Account not linked, server unavailable, token expired
6. **Business rules**: OAuth token must be valid, Music Assistant must be running

**Remediation Strategy**:

**Create Missing Use Case Documents**:

**File 1: ALEXA_VOICE_CONTROL.md**
```markdown
# Use Case: Control Music Playback via Alexa Voice Commands

**Actor**: Home user with Alexa device
**Goal**: Play, pause, and control music from Music Assistant using voice

## Preconditions
- User has linked Alexa account to Music Assistant (via OAuth)
- Music Assistant server is running and accessible
- OAuth access token is valid (not expired)
- User's Alexa device is online

## Success Scenarios

### Scenario 1: Play Music by Artist
1. User says: "Alexa, ask Music Assistant to play The Beatles"
2. Alexa forwards request to Music Assistant skill
3. Music Assistant skill validates OAuth token
4. Music Assistant searches library for "The Beatles"
5. Music Assistant begins playback
6. Alexa confirms: "Playing The Beatles on Music Assistant"

[Continue with more scenarios...]

## Failure Scenarios

### Scenario F1: Account Not Linked
1. User says: "Alexa, ask Music Assistant to play jazz"
2. Alexa checks for linked account
3. No OAuth token found
4. Alexa responds: "Please link your Music Assistant account in the Alexa app"

[Continue with more failure scenarios...]

## Business Rules
- BR1: OAuth access token must be valid (not expired)
- BR2: Music Assistant server must respond within 5 seconds
- BR3: If token expired, must redirect user to re-link account
- BR4: Voice commands only work when Music Assistant is running

## Verification
- [ ] User can control playback via voice commands
- [ ] Alexa provides clear feedback on success/failure
- [ ] Token expiry is handled gracefully
- [ ] User understands when and why re-linking is needed
```

**File 2: LINK_VOICE_ASSISTANT_ACCOUNT.md**
```markdown
# Use Case: Link Voice Assistant Account to Music Assistant

**Actor**: Home user setting up voice control
**Goal**: Complete one-time account linking to enable voice commands

## Preconditions
- User has Alexa account
- User has Music Assistant running
- OAuth server is accessible publicly (via Tailscale/Nabu Casa)
- User has Alexa app installed on mobile device

## Success Scenario
1. User opens Alexa app
2. User navigates to Skills & Games
3. User searches for "Music Assistant" skill (or uses private URL)
4. User enables the skill
5. User taps "Link Account"
6. Alexa redirects to Music Assistant OAuth server
7. User sees account linking confirmation screen
8. User approves account linking
9. OAuth server generates authorization code
10. OAuth server redirects back to Alexa with code
11. Alexa exchanges code for access token
12. Account linking complete
13. User can now use voice commands

[Continue with failure scenarios...]
```

**Estimated Effort**: 2 hours (both files)

**Action Items**:
1. [ ] Create `ALEXA_VOICE_CONTROL.md` in Layer 01
2. [ ] Create `LINK_VOICE_ASSISTANT_ACCOUNT.md` in Layer 01
3. [ ] Update `BROWSE_COMPLETE_ARTIST_LIBRARY.md` to add Alexa scenario

---

### VIOLATION 4: Missing Layer 02 Quick Reference

**Missing File**: `docs/02_REFERENCE/OAUTH_ENDPOINTS_REFERENCE.md`
**Severity**: MODERATE - Operators lack quick lookup

**What's Missing**:
- Quick reference table for OAuth endpoints
- URL templates for different environments
- Common OAuth client configurations
- Expected response codes
- Troubleshooting quick lookup
- Example curl commands

**Remediation Strategy**:

**Create Quick Reference Document**:

```markdown
# OAuth Endpoints Quick Reference

**Purpose**: Quick lookup for OAuth endpoint URLs, parameters, and responses
**Audience**: Operators, Developers, QA
**Layer**: 02_REFERENCE

## Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Server health check | No |
| `/alexa/authorize` | GET | Authorization request | User session |
| `/alexa/token` | POST | Token exchange | Client credentials |

## Deployment URLs

| Environment | Base URL | Notes |
|-------------|----------|-------|
| Local Dev | `http://localhost:8096` | Container-internal only |
| Tailscale | `https://haboxhill.tail1cba6.ts.net` | Public via Funnel |
| Nabu Casa | `https://music.jasonhollis.com` | Public via reverse proxy (future) |

## Client Configuration

| Parameter | Value | Source |
|-----------|-------|--------|
| client_id | `amazon-alexa` | oauth_clients.json |
| client_secret | `Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM` | oauth_clients.json |
| redirect_uris | See table below | Amazon Alexa |
| scopes | `music.read music.control` | OAuth server default |

### Alexa Redirect URIs
- `https://pitangui.amazon.com/auth/o2/callback` (US North America)
- `https://layla.amazon.com/api/skill/link/MKXZK47785HJ2` (US mobile)
- `https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2` (Japan)

## Quick Diagnostics

| Status Code | Meaning | Action |
|-------------|---------|--------|
| 200 | Success | Continue |
| 302 | Redirect | Follow Location header |
| 400 | Bad request | Check parameters |
| 401 | Unauthorized | Check client credentials |
| 503 | Server unavailable | Check if OAuth server running |

## Example Commands

### Health Check
\`\`\`bash
curl http://localhost:8096/health
# Expected: {"status": "ok", ...}
\`\`\`

### Authorization Request (Simulated)
\`\`\`bash
curl -v "http://localhost:8096/alexa/authorize?client_id=amazon-alexa&redirect_uri=https://pitangui.amazon.com/auth/o2/callback&state=random123&code_challenge=abc&code_challenge_method=S256"
# Expected: 302 redirect with code parameter
\`\`\`

### Token Exchange (Simulated)
\`\`\`bash
curl -X POST http://localhost:8096/alexa/token \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE" \
  -d "redirect_uri=https://pitangui.amazon.com/auth/o2/callback" \
  -d "client_id=amazon-alexa" \
  -d "client_secret=SECRET" \
  -d "code_verifier=VERIFIER"
# Expected: {"access_token": "...", ...}
\`\`\`

## Token Lifetimes

| Token Type | Lifetime | Notes |
|------------|----------|-------|
| Authorization Code | 5 minutes | Single-use, then deleted |
| Access Token | 1 hour | Used for API requests |
| Refresh Token | Long-lived | Used to get new access tokens |

## Common Issues Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| "Connection refused" | OAuth server not running | Restart server |
| "Invalid client" | Wrong client_secret | Check oauth_clients.json |
| "PKCE verification failed" | code_verifier mismatch | Verify Alexa sends correct verifier |
| "Authorization code expired" | >5 min delay | Reduce time between authorize and token |
```

**Estimated Effort**: 1 hour

**Action Items**:
1. [ ] Create `OAUTH_ENDPOINTS_REFERENCE.md` in Layer 02
2. [ ] Update README.md to link to quick reference

---

## Moderate Violations Requiring Updates

### VIOLATION 5: Outdated Project Root Files

**Files with Issues**:
1. `PROJECT.md` - Status says "ACTIVE - Initial Setup" (outdated)
2. `README.md` - OAuth marked "Ready to Deploy" (already deployed)
3. `00_QUICKSTART.md` - Doesn't mention OAuth work (outdated)

**Severity**: MODERATE - Project status unclear

**Remediation Strategy**:

**Update PROJECT.md**:
```markdown
**Status**: ACTIVE - OAuth Implementation Complete, Pagination Fix Complete
**Phase**: Production Deployment & Testing
**Started**: 2025-10-24
**OAuth Completed**: 2025-10-26
**Category**: automation

## Project Overview

Music Assistant integration improvements for Apple Music and Amazon Alexa:

1. **Apple Music Pagination** (COMPLETE ✅)
   - Fixed library browsing pagination issues
   - Resolved data completeness violations
   - Implemented streaming pagination

2. **Alexa Voice Control via OAuth** (COMPLETE ✅)
   - Implemented OAuth 2.0 Authorization Code Grant with PKCE
   - Deployed standalone OAuth server on port 8096
   - Configured Tailscale Funnel for public HTTPS exposure
   - Created Alexa Skill account linking integration

## Current State

**OAuth Implementation**:
- OAuth server deployed and tested (2025-10-26)
- Endpoints: /health, /alexa/authorize, /alexa/token
- Public URL: https://haboxhill.tail1cba6.ts.net
- Client: amazon-alexa (configured in Alexa Developer Console)
- Status: PRODUCTION READY, pending end-to-end Alexa testing

**Pagination Fix**:
- Implementation complete (2025-10-25)
- Status: AWAITING DEPLOYMENT to production Music Assistant instance

## Success Criteria

- [x] OAuth server responds to health checks
- [x] OAuth authorization code flow works
- [x] OAuth token exchange works with PKCE
- [x] Client authentication validates correctly
- [ ] Alexa Skill account linking tested end-to-end
- [ ] Voice commands control Music Assistant playback
- [ ] Pagination fix deployed and verified in production
```

**Update README.md**:
```markdown
## Current State

### OAuth Implementation ✅ COMPLETE (2025-10-26)
- Standalone OAuth 2.0 server with PKCE support
- Deployed on port 8096 in Music Assistant container
- Public HTTPS exposure via Tailscale Funnel
- Client credentials configured for Amazon Alexa
- Ready for Alexa Skill account linking test

[Rest of OAuth section with links to documentation...]

### Pagination Fix ✅ COMPLETE (2025-10-25)
- Streaming pagination implementation
- Awaiting deployment to production

[Rest of pagination section...]
```

**Update 00_QUICKSTART.md**:
```markdown
## What Is This?

This project tracks two major improvements to Music Assistant:

1. **Apple Music Pagination Bug** - Library browsing issues causing incomplete data
   - Status: FIXED ✅ (2025-10-25)
   - Solution: Streaming pagination implementation

2. **Alexa Voice Control Integration** - OAuth server for Alexa Skill account linking
   - Status: IMPLEMENTED ✅ (2025-10-26)
   - Solution: Standalone OAuth 2.0 server with PKCE, deployed via Tailscale Funnel

## Current Status (2025-10-26)

**OAuth Implementation**: COMPLETE ✅
- OAuth server deployed and tested
- Endpoints operational on port 8096
- Public HTTPS access configured
- Awaiting end-to-end Alexa testing

**Pagination Fix**: COMPLETE ✅
- Code implemented and tested
- Awaiting production deployment

## Documentation Structure

[Update this section to include OAuth docs in each layer...]
```

**Estimated Effort**: 1 hour (all three files)

**Action Items**:
1. [ ] Update `PROJECT.md` with OAuth completion status
2. [ ] Update `README.md` with OAuth implementation summary
3. [ ] Update `00_QUICKSTART.md` with OAuth work completed
4. [ ] Update all three with accurate current state

---

### VIOLATION 6: Temporary Documentation Files in Project Root

**Files to Archive**:
1. `OAUTH_IMPLEMENTATION_STATUS.md` - Temporary implementation log
2. `ALEXA_AUTH_EXECUTIVE_SUMMARY.md` - Duplicate of content in Layer 00
3. `ALEXA_AUTH_QUICK_REFERENCE.md` - Should be in Layer 02
4. `ALEXA_AUTH_SUMMARY.md` - Duplicate content
5. `ALEXA_RESEARCH_INDEX.md` - Temporary research file
6. `ALEXA_SKILL_OAUTH_RESEARCH_2025.md` - Research notes, should be archived
7. `ALEXA_SKILL_QUICK_DECISION.md` - Decision already in DECISIONS.md

**Severity**: LOW - Clutters root directory but doesn't violate architecture

**Remediation Strategy**:

**Create Archives Directory**:
```bash
mkdir -p docs/archives/oauth-research-2025-10
```

**Move Files**:
```bash
# Archive OAuth research and temporary status files
mv OAUTH_IMPLEMENTATION_STATUS.md docs/archives/oauth-research-2025-10/
mv ALEXA_AUTH_EXECUTIVE_SUMMARY.md docs/archives/oauth-research-2025-10/
mv ALEXA_AUTH_QUICK_REFERENCE.md docs/archives/oauth-research-2025-10/
mv ALEXA_AUTH_SUMMARY.md docs/archives/oauth-research-2025-10/
mv ALEXA_RESEARCH_INDEX.md docs/archives/oauth-research-2025-10/
mv ALEXA_SKILL_OAUTH_RESEARCH_2025.md docs/archives/oauth-research-2025-10/
mv ALEXA_SKILL_QUICK_DECISION.md docs/archives/oauth-research-2025-10/
```

**Create Archive Index**:
```markdown
# OAuth Research Archive - October 2025

This directory contains research notes, temporary status files, and working documents created during the OAuth implementation phase (2025-10-25 to 2025-10-26).

**Status**: ARCHIVED - Work complete, documentation integrated into proper layers

## Files

- `OAUTH_IMPLEMENTATION_STATUS.md` - Implementation log (superseded by Layer 04 docs)
- `ALEXA_AUTH_EXECUTIVE_SUMMARY.md` - Research summary (incorporated into ADR 002)
- `ALEXA_AUTH_QUICK_REFERENCE.md` - Temporary reference (superseded by Layer 02 quick ref)
- `ALEXA_AUTH_SUMMARY.md` - Working notes (content in DECISIONS.md)
- `ALEXA_RESEARCH_INDEX.md` - Research index (superseded by README.md)
- `ALEXA_SKILL_OAUTH_RESEARCH_2025.md` - Detailed research (content in Layer 00 docs)
- `ALEXA_SKILL_QUICK_DECISION.md` - Decision notes (superseded by DECISIONS.md)

## Current Documentation

For current OAuth implementation documentation, see:
- Architecture: `docs/00_ARCHITECTURE/ADR_002_ALEXA_INTEGRATION_STRATEGY.md`
- Interfaces: `docs/03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md`
- Infrastructure: `docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md`
- Operations: `docs/05_OPERATIONS/OAUTH_SERVER_STARTUP.md`
- Decisions: `DECISIONS.md` (Decisions 002-006)
```

**Estimated Effort**: 30 minutes

**Action Items**:
1. [ ] Create `docs/archives/oauth-research-2025-10/` directory
2. [ ] Move 7 temporary files to archives
3. [ ] Create `docs/archives/oauth-research-2025-10/README.md` index
4. [ ] Update project root README.md to note archive location

---

## Minor Violations and Improvements

### VIOLATION 7: Layer 05 Files Need Updates

**Files Needing Updates**:
1. `ALEXA_OAUTH_SETUP_PROGRESS.md` - Shows "Pending" but work complete
2. `TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md` - Needs OAuth integration steps

**Severity**: LOW - Operational docs slightly outdated

**Remediation**:

**Update ALEXA_OAUTH_SETUP_PROGRESS.md**:
- Change Phase 1 status from "Pending" to "COMPLETE ✅ (2025-10-26)"
- Add Phase 1 completion summary
- Update current status to reflect deployment complete
- Add next steps: end-to-end Alexa testing

**Update TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md**:
- Add section on OAuth server integration
- Document OAuth endpoints accessible via Funnel
- Add verification steps for OAuth through Funnel
- Include troubleshooting for OAuth + Funnel issues

**Estimated Effort**: 30 minutes (both files)

---

## Remediation Roadmap

### Phase 1: Critical Fixes (Priority 1) - 4-5 hours

**Week 1 Goals**:
1. Fix Layer 00 ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md (3-4 hours)
   - Create abstract Layer 00 principles document
   - Move technical details to Layer 04
   - Extract reference tables to Layer 02
   - Extract use cases to Layer 01
   - Archive original file

2. Create missing Layer 02 quick reference (1 hour)
   - Create OAUTH_ENDPOINTS_REFERENCE.md
   - Include all OAuth endpoints, URLs, parameters
   - Add troubleshooting quick lookup

3. Create missing Layer 05 operational docs (1 hour)
   - Create OAUTH_SERVER_STARTUP.md (if not exists)
   - Update ALEXA_OAUTH_SETUP_PROGRESS.md status

### Phase 2: Important Updates (Priority 2) - 2-3 hours

**Week 2 Goals**:
1. Fix ADR 002 mixed abstraction levels (1-2 hours)
   - Remove implementation details
   - Move diagrams to Layer 04
   - Update cross-references

2. Create missing Layer 01 use cases (2 hours)
   - Create ALEXA_VOICE_CONTROL.md
   - Create LINK_VOICE_ASSISTANT_ACCOUNT.md
   - Update BROWSE_COMPLETE_ARTIST_LIBRARY.md

3. Update project root files (1 hour)
   - Update PROJECT.md with OAuth completion
   - Update README.md with OAuth summary
   - Update 00_QUICKSTART.md with OAuth info

### Phase 3: Cleanup (Priority 3) - 1-2 hours

**Week 3 Goals**:
1. Archive temporary documentation (30 min)
   - Create archives directory
   - Move 7 temporary files
   - Create archive index

2. Update Layer 05 operational docs (30 min)
   - Update progress tracking files
   - Update implementation guides

3. Verify all cross-references (30 min)
   - Check all inter-document links
   - Update broken references
   - Ensure proper layer dependencies

### Phase 4: Final Verification (Priority 4) - 1 hour

**Week 4 Goals**:
1. Verify Dependency Rule compliance (30 min)
   - Audit all Layer 00 files
   - Check no outer layer references
   - Verify abstractions are pure

2. Final documentation review (30 min)
   - Check all layers complete
   - Verify no gaps
   - Update README.md with complete docs index

3. Create completion report (30 min)
   - Document all fixes applied
   - List any remaining minor issues
   - Update DOCUMENTATION_REALIGNMENT_REPORT.md

---

## Verification Checklist

After completing remediation, verify:

### Layer 00 (Architecture) Compliance
- [ ] No technology-specific names in architecture docs
- [ ] All principles are abstract and technology-agnostic
- [ ] ADRs focus on "why" not "how"
- [ ] No references to outer layers
- [ ] No code examples in architecture docs

### Layer 01 (Use Cases) Compliance
- [ ] All use cases describe actor goals
- [ ] No implementation details in use cases
- [ ] Use cases are technology-agnostic
- [ ] Success and failure scenarios documented
- [ ] Business rules clearly stated

### Layer 02 (Reference) Compliance
- [ ] Quick lookup tables present
- [ ] No architecture philosophy (that's Layer 00)
- [ ] No detailed procedures (that's Layer 05)
- [ ] Technology references acceptable (for lookup)

### Layer 03 (Interfaces) Compliance
- [ ] All API contracts documented
- [ ] Contracts are stable (don't change with implementation)
- [ ] Examples included for clarity
- [ ] Versioning and compatibility noted

### Layer 04 (Infrastructure) Compliance
- [ ] All technology choices documented with rationale
- [ ] Implementation details comprehensive
- [ ] Design patterns explained
- [ ] References Layer 00 principles correctly

### Layer 05 (Operations) Compliance
- [ ] All operational procedures documented
- [ ] Step-by-step instructions provided
- [ ] Troubleshooting guides present
- [ ] References all layers appropriately

### Project Root Files
- [ ] PROJECT.md reflects current accurate status
- [ ] README.md indexes all documentation
- [ ] 00_QUICKSTART.md provides 30-second orientation
- [ ] DECISIONS.md captures all architectural decisions
- [ ] SESSION_LOG.md is current

### General Compliance
- [ ] No duplicate content across layers
- [ ] All cross-references are correct
- [ ] Temporary files archived
- [ ] Documentation structure is clear
- [ ] Navigation is intuitive

---

## Tools and Templates

### Template: Abstract Architecture Document (Layer 00)

```markdown
# [Principle/Pattern Name]

**Purpose**: [Why this principle exists - abstract]
**Audience**: Architects, Decision Makers
**Layer**: 00_ARCHITECTURE
**Related**: [Other architecture docs]

---

## Intent

[What problem does this principle solve? Why does it matter? Abstract terms only.]

---

## Core Principles

### Principle 1: [Name]
[Abstract description without naming technologies]

**Trade-offs**:
- Advantage: [Abstract benefit]
- Disadvantage: [Abstract cost]

### Principle 2: [Name]
[Abstract description]

---

## Decision Criteria

[How to decide when to apply this principle? Abstract framework.]

---

## Consequences

**If This Principle Is Followed**:
- Positive: [Abstract outcomes]
- Negative: [Abstract trade-offs]

**If This Principle Is Violated**:
- Risk: [Abstract risks]
- Impact: [Abstract impacts]

---

## Verification

[How to verify this principle is being followed? Abstract tests.]

---

## See Also
- [Related architecture principles]
- [Related ADRs]
```

### Template: Use Case Document (Layer 01)

```markdown
# Use Case: [User Goal]

**Actor**: [Who is performing this action]
**Goal**: [What they want to accomplish]
**Layer**: 01_USE_CASES
**Related**: [Related use cases]

---

## Preconditions

[What must be true before this use case can start? Tech-agnostic.]

---

## Success Scenario

1. [Step 1 - user action]
2. [Step 2 - system response]
3. [Step 3 - user action]
4. [Etc.]

**Postconditions**: [What is true after success?]

---

## Failure Scenarios

### Scenario F1: [Failure Type]
1. [What happens when this fails]
2. [System response]
3. [User sees...]

[More failure scenarios...]

---

## Business Rules

- BR1: [Rule without implementation details]
- BR2: [Another rule]

---

## Verification

[How to test this use case works? Acceptance criteria.]

---

## See Also
- [Related use cases]
- [Architecture principles this follows]
```

### Template: Quick Reference (Layer 02)

```markdown
# [Topic] Quick Reference

**Purpose**: Quick lookup for [specific information]
**Audience**: [Who uses this reference]
**Layer**: 02_REFERENCE

---

## Quick Lookup Tables

| Parameter | Value | Notes |
|-----------|-------|-------|
| [name] | [value] | [when to use] |

---

## Common Formulas

[Math or calculation formulas]

---

## Constants and Thresholds

| Constant | Value | Meaning |
|----------|-------|---------|
| [name] | [value] | [what it represents] |

---

## Quick Diagnostics

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| [symptom] | [cause] | [action] |

---

## See Also
- [Related references]
- [Infrastructure docs for details]
```

---

## Next Steps

1. **Review this guide** with project stakeholders
2. **Prioritize violations** based on project needs
3. **Assign Phase 1 tasks** to developers/documentarians
4. **Set milestone dates** for each phase
5. **Track progress** in SESSION_LOG.md
6. **Update this guide** as remediation progresses

---

## Questions or Issues?

If you encounter ambiguity during remediation:

1. **Check CLAUDE.md** for Clean Architecture framework guidance
2. **Reference WORKSPACE.md** for documentation best practices
3. **Ask**: "Is this describing WHAT (use case) or HOW (infrastructure)?"
4. **Ask**: "Could this apply to a different technology stack?" (Layer 00 test)
5. **Ask**: "Does this reference outer layers?" (Dependency Rule test)

---

**Document Status**: ACTIVE
**Last Updated**: 2025-10-26
**Estimated Completion**: 2025-11-09 (2 weeks for full remediation)
**Total Effort**: 8-11 hours across 4 phases

---

**END OF REMEDIATION GUIDE**
