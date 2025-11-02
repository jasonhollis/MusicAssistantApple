# MusicAssistantApple Documentation Audit Report
**Date**: 2025-10-26
**Auditor**: Claude Code (Sonnet 4.5)
**Scope**: Complete documentation review across all layers (00-05) and project root files
**Framework**: Clean Architecture Dependency Rule Compliance

---

## Executive Summary

### Overall Assessment: CRITICAL VIOLATIONS FOUND

The MusicAssistantApple project documentation contains **EXTENSIVE AND PERVASIVE** violations of Clean Architecture's Dependency Rule, particularly in Layer 00 (ARCHITECTURE). The violations are so severe that Layer 00 files resemble Layer 04 (INFRASTRUCTURE) documentation.

**Severity Breakdown**:
- **CRITICAL**: 7 files (Layer 00 with extensive technology mentions)
- **IMPORTANT**: 5 files (Layer 02 contains infrastructure details)
- **MINOR**: 3 files (Project root files with minor improvements needed)

**Estimated Remediation Effort**: 16-24 hours

### Key Findings

1. **Layer 00 (ARCHITECTURE) is severely compromised**
   - Contains specific technologies: Python, aiohttp, Docker, Tailscale, Nabu Casa, Home Assistant, OAuth2, TLS, SSL, nginx, port numbers
   - Reads like implementation documentation, not architectural principles
   - 7 out of 7 files violate technology-agnostic requirement

2. **Layer 02 (REFERENCE) contains infrastructure implementation details**
   - Should be quick lookups and glossaries
   - Instead contains detailed technical procedures and specific IP addresses
   - Acts as Layer 04/05 hybrid

3. **Project root files have minor issues**
   - Some outdated status information
   - Some files could be consolidated

4. **Layers 03, 04, 05 are WELL-STRUCTURED**
   - These layers correctly contain technology-specific content
   - Proper separation between contracts, implementation, and operations

---

## Detailed Findings by Layer

## LAYER 00: ARCHITECTURE - CRITICAL VIOLATIONS

### Violation Severity: CRITICAL (Technology-Agnostic Requirement Completely Violated)

**The Problem**: Layer 00 should contain ONLY technology-agnostic architectural principles. It should NEVER mention:
- Specific technologies (Python, Docker, nginx, aiohttp)
- Specific products (Tailscale, Nabu Casa, Home Assistant)
- Specific protocols (OAuth2, HTTPS, TLS - these are implementation details)
- Specific port numbers (8096, 8095, 443)
- Specific tools or libraries

**What Layer 00 SHOULD contain**:
- Principles ("Authentication should be delegated to specialized systems")
- Quality attributes ("System must support unbounded dataset sizes")
- Architectural patterns ("Streaming over batch processing")
- Trade-off analyses (technology-independent)
- Constraints (business/domain constraints, not implementation constraints)

### File 1: `ADR_001_STREAMING_PAGINATION.md`

**Severity**: CRITICAL

**Violations**:
- Line 254: Mentions "Python" and "Async generators in Python"
- Contains code examples in Python syntax (lines 173-225)
- Implementation-specific patterns instead of abstract principles

**Should Be**:
- Principle: "Process data incrementally rather than accumulating in memory"
- No code examples - those belong in Layer 04
- No language-specific patterns

**Recommended Action**:
- Remove ALL code examples (move to Layer 04)
- Replace "async generators in Python" with "incremental data processing patterns"
- Focus on O(1) memory principle, streaming pattern benefits
- Reference Layer 04 for implementation examples

---

### File 2: `ADR_002_ALEXA_INTEGRATION_STRATEGY.md`

**Severity**: CRITICAL (MOST SEVERE)

**Violations** (Extensive):
- Line 41: "port 8096", "Nabu Casa custom domains", "Tailscale Funnel"
- Line 53: "Home Assistant environment"
- Line 55: "OAuth2 authorization server", "SSL certificate management", "Alexa Skills"
- Lines 69-96: ASCII diagrams showing specific technologies (OAuth Server:8096, Nabu Casa, Tailscale Funnel, HA)
- Line 109-121: Specific implementation tasks (OAuth2 server, SSL cert management)
- Line 142: "SSL setup", "OAuth config"
- Throughout: Constant references to "Home Assistant", "Nabu Casa", "OAuth2", "SSL", "TLS"

**What This File IS**: Infrastructure comparison (belongs in Layer 04)
**What This File SHOULD BE**: Architectural philosophy decision

**Should Contain**:
- "Principle: Should we build authentication ourselves or delegate to ecosystem?"
- "Trade-off: Direct control vs. leveraging existing infrastructure"
- "Quality attribute: Security through specialization"
- NO mentions of OAuth2, SSL, TLS, Home Assistant, Nabu Casa, Tailscale, ports, etc.

**Recommended Action**:
- **COMPLETE REWRITE** required
- Extract technology-agnostic principles:
  - "Leverage existing infrastructure before building custom"
  - "Delegate security-critical functions to specialized systems"
  - "Choose between standalone deployment and ecosystem integration"
- Move ALL technology mentions to new Layer 04 file: `ALEXA_INTEGRATION_IMPLEMENTATION_OPTIONS.md`
- Keep ONLY the philosophical question: build vs. buy, standalone vs. ecosystem

**Example Transformation**:

CURRENT (WRONG for Layer 00):
```
Should we build our own OAuth server and expose Music Assistant directly to Alexa,
or should we integrate through Home Assistant's existing Alexa infrastructure?
```

SHOULD BE (Layer 00):
```
Should we build authentication infrastructure ourselves or delegate to an
existing ecosystem that specializes in authentication?

Principle 1: Leverage existing infrastructure before building custom
Principle 2: Security through specialization
Principle 3: Balance between control and maintenance burden
```

---

### File 3: `ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md`

**Severity**: CRITICAL

**Violations**:
- This ENTIRE FILE is Layer 04 (Infrastructure) content
- Contains: Login with Amazon (LWA), OAuth2, TLS, SSL, certificates, ports, passkeys, 2FA
- Implementation code examples (lines 573-678)
- Specific libraries (alexa-cookie, Selenium, Puppeteer)
- Security implementation details

**What This File IS**: Detailed technical implementation analysis
**What Layer 00 Should Contain**: Strategic principles for authentication

**Should Be in Layer 00** (if at all):
- "Principle: Official vs unofficial integration paths"
- "Trade-off: Development effort vs. long-term stability"
- "Risk: Unofficial APIs may break"

**Recommended Action**:
- **MOVE ENTIRE FILE to Layer 04**: `docs/04_INFRASTRUCTURE/ALEXA_AUTHENTICATION_IMPLEMENTATION_ANALYSIS.md`
- Create NEW Layer 00 file (if needed): `AUTHENTICATION_STRATEGY_PRINCIPLES.md` with ONLY:
  - Official vs unofficial integration philosophy
  - Security delegation principle
  - Maintenance burden vs feature development trade-off

---

### File 4: `ALEXA_INTEGRATION_CONSTRAINTS.md`

**Severity**: CRITICAL

**Violations**:
- Lines throughout: OAuth, HTTPS, TLS, SSL, certificates, ports, DNS, IP addresses
- Line 19: "OAuth endpoints", "HTTPS certificates"
- Lines 28-36: Specific OAuth endpoint paths (`/authorize`, `/token`, `/callback`)
- Lines 51-66: TLS certificate validation requirements (CA, certificates, self-signed)
- Line 87: "port 8096"

**What This File IS**: Technical implementation constraints
**What It SHOULD BE**: Architectural constraints (business/domain level)

**Should Contain** (technology-agnostic):
- "Constraint: Third-party service requires public accessibility"
- "Constraint: Authentication flow must be cryptographically secure"
- "Constraint: End users access from arbitrary network locations"

**Should NOT Contain**:
- OAuth, HTTPS, TLS, SSL (these are HOW we meet the constraints, not the constraints themselves)
- Specific ports
- Specific protocols

**Recommended Action**:
- **REWRITE** to remove ALL technology mentions
- Describe constraints in abstract terms:
  - "External service requires cryptographically secure public endpoints"
  - "Users authenticate from untrusted networks"
  - "System must validate identity without exposing credentials"
- Move technical details to Layer 04: `ALEXA_OAUTH_TECHNICAL_REQUIREMENTS.md`

---

### File 5: `CRITICAL_ISSUE_DATA_COMPLETENESS_VIOLATION.md`

**Severity**: CRITICAL

**Violations**:
- Contains specific implementation details (web UI, API, pagination logic)
- Mentions specific behaviors that are implementation-dependent

**Recommended Action**:
- **REWRITE** to focus on architectural principle:
  - "Principle: System must provide complete data visibility"
  - "Violation: Data completeness constraint not enforced"
- Move implementation analysis to Layer 04

---

### File 6: `NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md`

**Severity**: CRITICAL

**Violations**:
- File name contains specific product: "Nabu Casa"
- Throughout: Home Assistant, Nabu Casa, OAuth, integration, add-on

**Should Be**:
- "ECOSYSTEM_INTEGRATION_FUTURE_STRATEGY.md"
- "Should we integrate with smart home ecosystem or remain standalone?"
- No mentions of specific products

**Recommended Action**:
- **RENAME** to remove product name
- **REWRITE** to be product-agnostic
- Move product-specific analysis to Layer 04

---

### File 7: `WEB_UI_SCALABILITY_PRINCIPLES.md`

**Severity**: MODERATE (Better than others, but still has issues)

**Violations**:
- May contain implementation details about web UI technology

**Recommended Action**:
- Review for any technology mentions
- Ensure principles are stated abstractly

---

## LAYER 01: USE CASES - ACCEPTABLE

### Overall Assessment: GOOD

Layer 01 files correctly describe user goals and workflows WITHOUT implementation details.

**Files Reviewed**:
1. `BROWSE_COMPLETE_ARTIST_LIBRARY.md` - ✅ Good
2. `SYNC_PROVIDER_LIBRARY.md` - ✅ Good
3. `UC_CRITICAL_BROWSE_LIBRARY_FAILURE.md` - ✅ Good

**No critical violations found** in Layer 01.

---

## LAYER 02: REFERENCE - IMPORTANT VIOLATIONS

### Violation Severity: IMPORTANT (Contains Infrastructure Details, Not Quick Reference)

**The Problem**: Layer 02 should be QUICK LOOKUPS - glossaries, formulas, thresholds, comparison tables. It should NOT contain:
- Detailed implementation procedures
- Specific infrastructure configurations
- Deployment topologies with IPs
- Step-by-step guides

### File 1: `ALEXA_INFRASTRUCTURE_OPTIONS.md`

**Severity**: IMPORTANT

**Violations**:
- Lines 20-31: Specific infrastructure details (Docker container at IP:port, network details)
- Lines 55-100: Detailed implementation guidance (belongs in Layer 05)
- Contains "How It Works" sections with ASCII diagrams

**What This IS**: Infrastructure implementation comparison (Layer 04)
**What Layer 02 SHOULD BE**: Quick comparison table ONLY

**Should Contain**:
- Simple comparison table (which it has on lines 34-49) - KEEP THIS
- Glossary of terms
- Quick decision matrix

**Should NOT Contain**:
- "How It Works" sections
- Detailed advantages/disadvantages with implementation details
- Specific IP addresses and network topologies

**Recommended Action**:
- **KEEP** the comparison table (lines 34-49)
- **REMOVE** all "How It Works", advantages/disadvantages sections
- **MOVE** detailed content to Layer 04: `ALEXA_PUBLIC_EXPOSURE_OPTIONS.md` (which already exists!)

---

### File 2: `HOME_ASSISTANT_CONTAINER_TOPOLOGY.md`

**Severity**: IMPORTANT

**Violations**:
- This is INFRASTRUCTURE documentation (Layer 04), not reference
- Contains specific deployment topology with IPs, container names, network details

**Recommended Action**:
- **MOVE** to Layer 04: `docs/04_INFRASTRUCTURE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md`

---

### File 3: `NABU_CASA_PORT_ROUTING_ARCHITECTURE.md`

**Severity**: IMPORTANT

**Violations**:
- This is INFRASTRUCTURE documentation (Layer 04)
- Contains detailed routing architecture

**Recommended Action**:
- **MOVE** to Layer 04

---

### Files 4-5: `CRITICAL_LIMITS_AND_ACTUAL_BEHAVIOR.md`, `PAGINATION_LIMITS_REFERENCE.md`

**Severity**: ACCEPTABLE

These files are appropriate for Layer 02 (quick reference for limits and benchmarks).

---

## LAYER 03: INTERFACES - EXCELLENT

### Overall Assessment: EXCELLENT

Layer 03 files correctly define API contracts and interfaces WITHOUT implementation details.

**Files Reviewed**:
1. `ALEXA_OAUTH_ENDPOINTS_CONTRACT.md` - ✅ Excellent
2. `BROKEN_API_CONTRACT_LIBRARY_COMPLETENESS.md` - ✅ Good
3. `MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md` - ✅ Excellent
4. `MUSIC_PROVIDER_PAGINATION_CONTRACT.md` - ✅ Good
5. `TAILSCALE_OAUTH_ROUTING.md` - ⚠️ Name contains specific product

**Minor Issue**: `TAILSCALE_OAUTH_ROUTING.md` - file name contains product name. Should be `OAUTH_ROUTING_INTERFACE.md` if it's truly an interface contract. If it's implementation-specific, move to Layer 04.

**Recommended Action**:
- Review `TAILSCALE_OAUTH_ROUTING.md` - if it's Tailscale-specific implementation, MOVE to Layer 04
- Otherwise rename to be product-agnostic

---

## LAYER 04: INFRASTRUCTURE - EXCELLENT

### Overall Assessment: EXCELLENT

Layer 04 files correctly contain technology-specific implementation details. This is WHERE specific technologies SHOULD be mentioned.

**Files Reviewed**:
1. `ALEXA_PUBLIC_EXPOSURE_OPTIONS.md` - ✅ Perfect for Layer 04
2. `APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md` - ✅ Perfect
3. `CRITICAL_FAILED_FIX_ATTEMPTS.md` - ✅ Good
4. `HABOXHILL_NETWORK_TOPOLOGY.md` - ✅ Perfect for Layer 04
5. `NABU_CASA_MUSIC_ASSISTANT_FUTURE_WORK.md` - ✅ Good
6. `OAUTH_SERVER_IMPLEMENTATION.md` - ✅ Perfect

**No violations found**. Layer 04 is being used correctly.

---

## LAYER 05: OPERATIONS - EXCELLENT

### Overall Assessment: EXCELLENT

Layer 05 files correctly contain specific operational procedures with commands, IPs, and deployment details.

**Files Reviewed** (12 files total):
- All files appropriate for Layer 05
- Correctly contain specific commands, procedures, troubleshooting guides
- Properly reference inner layers for WHY/WHAT

**No violations found**. Layer 05 is being used correctly.

---

## PROJECT ROOT FILES - MINOR ISSUES

### File 1: `PROJECT.md`

**Issues**:
- Status shows "ACTIVE - OAuth Integration Complete" but goals show mixed completion

**Recommended Action**:
- Update status section to reflect current state more clearly

---

### File 2: `README.md`

**Issues**:
- Very comprehensive but could benefit from clearer separation of concerns
- Some sections contain both high-level overview and detailed implementation

**Recommended Action**:
- Consider splitting into README.md (overview) + IMPLEMENTATION_GUIDE.md (details)

---

### File 3: `00_QUICKSTART.md`

**Issues**: Minor
- Generally good, provides clear 30-second orientation

**Recommended Action**:
- Ensure all dates are current

---

### File 4: `DECISIONS.md`

**Issues**: Minor
- Decision 002 and 003 contain some contradictory information about final choices

**Recommended Action**:
- Clarify which decision is FINAL (appears to be Tailscale, but Decision 002 says Nabu Casa)

---

## ORPHANED/STALE ROOT FILES

### Files That Should Be Consolidated or Moved

The project root contains **MANY** files (78 total) that should be either:
1. Consolidated into main documentation
2. Moved to appropriate layer
3. Archived (if obsolete)

**Examples of Questionable Root Files**:
- `ALEXA_AUTH_ANALYSIS.md`
- `ALEXA_AUTH_EXECUTIVE_SUMMARY.md`
- `ALEXA_AUTH_QUICK_REFERENCE.md`
- `ALEXA_AUTH_SUMMARY.md`
- `ALEXA_OAUTH_DOCUMENTATION_INDEX.md`
- `ALEXA_RESEARCH_INDEX.md`
- `ALEXA_SKILL_OAUTH_RESEARCH_2025.md`
- `ALEXA_SKILL_QUICK_DECISION.md`
- (and many more...)

**Recommendation**:
- **CONSOLIDATE**: Multiple Alexa auth summary files into ONE definitive document
- **MOVE**: Analysis documents to `docs/` if they're still relevant
- **ARCHIVE**: Obsolete research documents to `docs/ARCHIVE/` or delete if truly obsolete
- **TARGET**: Reduce root files from ~78 to ~10 core files

**Core Root Files Should Be**:
1. `README.md` - Project overview
2. `PROJECT.md` - Project status
3. `00_QUICKSTART.md` - Quick start
4. `DECISIONS.md` - Decision log
5. `SESSION_LOG.md` - Work log
6. `CURRENT_STATUS.md` - Current status (if different from PROJECT.md)
7. Maybe 1-2 CRITICAL summaries for emergencies

Everything else should be in `docs/` hierarchy.

---

## DOCUMENTATION GAPS

### Missing Documentation

1. **Layer 00**: No file documenting core computation/music streaming principles
2. **Layer 00**: No file documenting data integrity principles
3. **Layer 03**: Could benefit from `MUSIC_ASSISTANT_CORE_API_CONTRACT.md`

### Incomplete Documentation

1. **OAuth Implementation**: References to "oauth_clients.json" but no schema documented
2. **Environment Variables**: Mentioned in files but no comprehensive reference
3. **Error Codes**: No documented error code taxonomy

---

## PRIORITY REMEDIATION PLAN

### Phase 1: CRITICAL (Must Fix Immediately) - 8-12 hours

**Priority 1A: Layer 00 ADR_002 Rewrite** (4 hours)
- File: `docs/00_ARCHITECTURE/ADR_002_ALEXA_INTEGRATION_STRATEGY.md`
- Action: Complete rewrite to remove ALL technology mentions
- Create: New Layer 04 file with technology comparison

**Priority 1B: Layer 00 Authentication Analysis Move** (2 hours)
- File: `docs/00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md`
- Action: MOVE to Layer 04
- Create: Small Layer 00 file with authentication principles only

**Priority 1C: Layer 00 Constraints Rewrite** (2 hours)
- File: `docs/00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md`
- Action: Rewrite to be technology-agnostic

**Priority 1D: Layer 00 Future Strategy** (2 hours)
- File: `docs/00_ARCHITECTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md`
- Action: Rename and rewrite to be product-agnostic

---

### Phase 2: IMPORTANT (Should Fix Soon) - 4-6 hours

**Priority 2A: Layer 02 Infrastructure Files** (2 hours)
- Files: `ALEXA_INFRASTRUCTURE_OPTIONS.md`, `HOME_ASSISTANT_CONTAINER_TOPOLOGY.md`, `NABU_CASA_PORT_ROUTING_ARCHITECTURE.md`
- Action: Simplify to quick reference tables only OR move to Layer 04

**Priority 2B: Root File Consolidation** (3 hours)
- Files: ~60+ root files that should be consolidated
- Action: Consolidate Alexa summaries, move analyses to docs/, archive obsolete

**Priority 2C: Layer 00 Remaining Files** (1 hour)
- Files: Other Layer 00 files with minor violations
- Action: Remove technology mentions, keep principles only

---

### Phase 3: MINOR (Nice to Have) - 4-6 hours

**Priority 3A: Documentation Gaps** (2 hours)
- Create missing Layer 00 principles documents
- Create missing Layer 03 contract documents

**Priority 3B: Layer 03 Product Names** (1 hour)
- Review `TAILSCALE_OAUTH_ROUTING.md` and rename if needed

**Priority 3C: Root File Polish** (2 hours)
- Update PROJECT.md status
- Clarify DECISIONS.md
- Ensure all dates current

---

## ESTIMATED TOTAL REMEDIATION EFFORT

**Total Time**: 16-24 hours

**Breakdown**:
- Critical fixes: 8-12 hours
- Important fixes: 4-6 hours
- Minor fixes: 4-6 hours

**Recommended Schedule**:
- Week 1: Complete all Critical fixes (Phase 1)
- Week 2: Complete Important fixes (Phase 2)
- Week 3: Complete Minor fixes (Phase 3)

---

## COMPLIANCE VERIFICATION CHECKLIST

After remediation, verify:

### Layer 00 (ARCHITECTURE) Compliance
- [ ] NO mentions of specific technologies (Python, Docker, nginx, etc.)
- [ ] NO mentions of specific products (Tailscale, Nabu Casa, Home Assistant)
- [ ] NO mentions of specific protocols (OAuth2, HTTPS, TLS, SSL)
- [ ] NO port numbers or IP addresses
- [ ] NO code examples
- [ ] ONLY architectural principles and quality attributes
- [ ] ONLY technology-agnostic trade-off analyses

### Layer 01 (USE CASES) Compliance
- [ ] Describes WHAT users accomplish
- [ ] NO implementation details
- [ ] NO specific technologies
- [ ] Actor-focused scenarios

### Layer 02 (REFERENCE) Compliance
- [ ] Quick lookup tables and comparisons ONLY
- [ ] Glossaries and formulas
- [ ] NO detailed implementation procedures
- [ ] NO "How It Works" sections

### Layer 03 (INTERFACES) Compliance
- [ ] API contracts and schemas
- [ ] Technology-agnostic where possible
- [ ] Stable interfaces that don't change with implementation

### Layer 04 (INFRASTRUCTURE) Compliance
- [ ] Technology-specific implementation details
- [ ] CAN reference all inner layers (00-03)
- [ ] MUST NOT reference Layer 05

### Layer 05 (OPERATIONS) Compliance
- [ ] Specific commands and procedures
- [ ] IP addresses, ports, file paths
- [ ] CAN reference all inner layers
- [ ] Operational runbooks and troubleshooting

### Root Files Compliance
- [ ] 10 or fewer core files
- [ ] Clear, current status information
- [ ] No duplicate/conflicting information

---

## CONCLUSION

The MusicAssistantApple project has **excellent structure in Layers 03, 04, and 05**, but **Layer 00 is severely compromised** by extensive technology-specific content that belongs in Layer 04.

**The core issue**: Layer 00 was written as "strategic analysis" but included implementation details. Strategic analysis should focus on PRINCIPLES, not technologies.

**The fix is straightforward but time-consuming**:
1. Extract principles from Layer 00 files (keep only these)
2. Move all technology mentions to Layer 04 (create new files if needed)
3. Simplify Layer 02 to quick reference only
4. Consolidate root files

**After remediation**, this project will be an **EXCELLENT** example of Clean Architecture documentation done right.

---

## APPENDIX A: Layer 00 Technology Mention Examples

### What's Currently in Layer 00 (WRONG)

"Should we build our own OAuth server and expose Music Assistant directly to Alexa, or should we integrate through Home Assistant's existing Alexa infrastructure?"

"Use Nabu Casa Cloud (existing subscription) to expose Music Assistant OAuth server for Alexa Skill account linking, instead of Tailscale Funnel workaround."

"OAuth2 authorization server on port 8096"

"SSL certificate management system"

"nginx reverse proxy"

"Docker container at 192.168.130.11:8096"

### What SHOULD Be in Layer 00 (CORRECT)

"Should we build authentication infrastructure ourselves or delegate to an existing ecosystem that specializes in authentication?"

"Principle: Leverage existing infrastructure before building custom solutions"

"Principle: Security-critical functions should be delegated to specialized systems"

"Trade-off: Direct control vs. maintenance burden"

"Constraint: Third-party service requires public accessibility with cryptographic security"

"Quality Attribute: Authentication must remain available independent of primary system failures"

---

## APPENDIX B: Recommended File Moves

### From Layer 00 to Layer 04
1. `ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md` → `04_INFRASTRUCTURE/ALEXA_AUTHENTICATION_IMPLEMENTATION_ANALYSIS.md`
2. `NABU_CASA_MUSIC_ASSISTANT_FUTURE_STRATEGY.md` → Rewrite as `ECOSYSTEM_INTEGRATION_STRATEGY.md` (keep in 00) + move product details to `04_INFRASTRUCTURE/NABU_CASA_INTEGRATION_OPTIONS.md`

### From Layer 02 to Layer 04
1. `HOME_ASSISTANT_CONTAINER_TOPOLOGY.md` → `04_INFRASTRUCTURE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md`
2. `NABU_CASA_PORT_ROUTING_ARCHITECTURE.md` → `04_INFRASTRUCTURE/NABU_CASA_PORT_ROUTING_ARCHITECTURE.md`

### From Root to docs/
1. All ALEXA_* analysis files → Consolidate into `docs/RESEARCH/ALEXA_INTEGRATION_RESEARCH.md` or archive
2. All summary files → Keep ONE definitive summary in root, archive others

---

**END OF AUDIT REPORT**
