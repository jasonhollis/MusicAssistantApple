# MusicAssistantApple Project

**Purpose**: Enable Alexa voice control for Music Assistant via Home Assistant integration
**Status**: ARCHITECTURE DEFINED - Ready for implementation
**Started**: 2025-10-24
**Architecture Confirmed**: 2025-11-02
**Category**: automation

---

## Project Overview

### The Goal

Enable users to control Music Assistant players using Amazon Alexa voice commands through Home Assistant.

**Example commands**:
- "Alexa, play music on bedroom speakers"
- "Alexa, pause the kitchen music"
- "Alexa, turn up the volume in the living room"
- "Alexa, next track on office speakers"

### Current Status

**What's Already Working** ✅:
1. **Home Assistant Alexa Integration**: Deployed on haboxhill.local
   - OAuth2 + PKCE authentication
   - Secure token storage
   - Nabu Casa Cloud routing
   - Source: `/Users/jason/projects/alexa-oauth2/`

2. **Music Assistant Integration**: Deployed on haboxhill.local
   - Connected to MA server
   - Exposes MA players as HA media_player entities

**What's Missing** ❌:
- **Smart Home Handler**: Routes Alexa directives to Music Assistant (~200 lines of Python)

---

## Architecture

### The Correct Flow

```
User → Echo Device → Amazon Alexa → HA Alexa Integration (OAuth2) →
       Smart Home Handler (MISSING) → Music Assistant Integration →
       Music Assistant Server → Music Players
```

### Key Components

**1. Home Assistant Alexa Integration** (DEPLOYED):
- **Location**: `/config/custom_components/alexa/` on haboxhill.local
- **Role**: OAuth2 authentication with Amazon
- **Features**: PKCE, token encryption, webhook routing
- **Status**: Production-ready

**2. Music Assistant Integration** (DEPLOYED):
- **Location**: `/config/custom_components/music_assistant/` on haboxhill.local
- **Role**: Connect HA to Music Assistant server
- **Features**: Player discovery, media control
- **Status**: Production-ready

**3. Smart Home Handler** (TO BE BUILT):
- **Location**: `/config/custom_components/alexa/smart_home.py` (new file)
- **Role**: Route Alexa directives to appropriate handlers
- **Features**:
  - Namespace routing (music vs device commands)
  - Alexa.PlaybackController → Music Assistant
  - Alexa.Speaker → Music Assistant
  - Error handling and response generation

---

## What We Learned (Project Evolution)

### Phase 1: Apple Music API Approach (Oct 20-25)

**Thinking**: "Let's integrate Apple Music API with Music Assistant"

**Work Done**:
- Apple Music playlist sync fixes
- Unicode handling in track names
- Spatial audio metadata
- MusicKit token generation
- ~50 Python scripts and documentation files

**Realization** (Oct 25): Music Assistant ALREADY has Apple Music provider. We don't need direct API integration.

**Archive**: `archives/apple-music-integration/`

---

### Phase 2: Separate OAuth Server Approach (Oct 26-Nov 1)

**Thinking**: "Let's build a separate OAuth server for Alexa authentication"

**Work Done**:
- Complete OAuth2 + PKCE server implementation (`alexa_oauth_endpoints.py`)
- ~800 lines of Python
- Docker deployment configuration
- Public HTTPS exposure via Tailscale Funnel
- Extensive documentation (OAuth, security, deployment)

**Discovery** (Nov 1): Home Assistant Alexa integration ALREADY deployed with OAuth2+PKCE on haboxhill.local!

**Realization** (Nov 2): Building separate OAuth server duplicates existing functionality. Just need smart home handler.

**Archive**: `archives/alexa-oauth-server-approach/`

**Security Issues Identified**:
- Hardcoded user_id (no real authentication)
- In-memory token storage (lost on restart)
- Architectural duplication

---

### Phase 3: Correct Architecture (Nov 2 - Present)

**Understanding**: Home Assistant Alexa integration handles OAuth. Music Assistant handles music providers. Just need to connect them.

**Solution**: Add smart home handler (~200 lines) to route Alexa directives to Music Assistant.

**Benefits**:
- Single OAuth flow (user links Alexa once)
- Leverages existing secure infrastructure
- Clean separation of concerns
- Submittable to Home Assistant Core

---

## Goals & Success Criteria

### Goals
- [x] Understand deployed infrastructure (COMPLETE 2025-11-02)
- [ ] Implement smart home handler (~200 lines Python)
- [ ] Test with real Alexa devices
- [ ] Submit to Home Assistant Core (home-assistant/core)

### Success Criteria

**Phase 1: Investigation** (Week 1) - IN PROGRESS
- [x] Confirm HA Alexa integration deployed
- [x] Confirm Music Assistant integration deployed
- [ ] Review HA Alexa integration code
- [ ] Review Music Assistant integration API
- [ ] Document smart home handler design

**Phase 2: Implementation** (Week 2)
- [ ] Create `/config/custom_components/alexa/smart_home.py`
- [ ] Update `/config/custom_components/alexa/__init__.py`
- [ ] Local testing with mock Alexa directives
- [ ] Directive routing logic verified

**Phase 3: Testing** (Week 3)
- [ ] Voice commands work with Echo devices
- [ ] Playback control verified (play/pause/next/previous)
- [ ] Volume control verified
- [ ] Multiple MA players tested
- [ ] Error handling validated

**Phase 4: HA Core Submission** (Week 4)
- [ ] Code merged to alexa-oauth2 repository
- [ ] Tests passing (>90% coverage)
- [ ] Documentation complete
- [ ] PR submitted to home-assistant/core

---

## Technical Context

### Deployed Environment

**Server**: haboxhill.local (Home Assistant)
**HA Version**: 2024.x
**Integrations**:
- `custom_components/alexa/` (from alexa-oauth2 project)
- `custom_components/music_assistant/` (official MA integration)

### Reference Projects

**Primary Reference**: `/Users/jason/projects/alexa-oauth2/`
- OAuth2 + PKCE implementation
- Security patterns (Fernet encryption, PBKDF2)
- HA integration best practices
- Documentation structure (Layer 00-05)

**Home Assistant Core**:
- [HA Developer Docs](https://developers.home-assistant.io/)
- Integration patterns and best practices

**Amazon Alexa**:
- [Smart Home Skill API](https://developer.amazon.com/docs/smarthome/understand-the-smart-home-skill-api.html)
- Directive namespaces and response formats

**Music Assistant**:
- [MA Documentation](https://music-assistant.io/)
- Player API and command structure

---

## Key Architectural Decisions

### Decision 1: Extend HA Alexa Integration

**Date**: 2025-11-02

**Question**: Build separate OAuth server OR extend existing HA Alexa integration?

**Decision**: Extend HA Alexa integration with smart home handler

**Rationale**:
- Avoids OAuth duplication (already have OAuth2+PKCE)
- Single user authorization flow
- Cleaner architecture (HA handles device control)
- Submittable to HA Core
- ~200 lines vs ~800 lines

**Alternatives Rejected**:
- Separate OAuth server (archived in `archives/alexa-oauth-server-approach/`)
- Has security issues (hardcoded user, no encryption)
- Duplicates HA OAuth functionality
- Not maintainable long-term

### Decision 2: Use MA's Apple Music Provider

**Date**: 2025-10-25

**Question**: Integrate Apple Music API directly OR use Music Assistant's provider?

**Decision**: Use Music Assistant's existing Apple Music provider

**Rationale**:
- MA already handles Apple Music API
- Focus on voice control layer (Alexa → HA → MA)
- Don't rebuild what exists

**Alternatives Rejected**:
- Direct Apple Music API integration (archived in `archives/apple-music-integration/`)
- Solves different problem than we need
- MA handles music providers, we handle voice control

### Decision 3: Smart Home Handler in Alexa Integration

**Date**: 2025-11-02

**Question**: Where to implement Alexa directive routing?

**Decision**: Smart home handler within HA Alexa integration (`smart_home.py`)

**Rationale**:
- Clean separation of concerns
- Alexa integration handles ALL Alexa communication
- Music Assistant integration handles music playback
- Extensible for future smart home features

**Location**: `/config/custom_components/alexa/smart_home.py` (new file)

---

## Implementation Plan

### Week 1: Investigation (THIS WEEK)

**Goals**: Understand current code and APIs

**Tasks**:
1. ✅ Confirm HA Alexa integration structure
2. ✅ Confirm Music Assistant integration structure
3. Review HA Alexa integration code:
   - `__init__.py` - Entry point and setup
   - `oauth.py` - OAuth2+PKCE implementation
   - `config_flow.py` - User setup flow
   - Check for existing smart home handler

4. Review Music Assistant integration code:
   - `__init__.py` - MA server connection
   - `media_player.py` - Player entities
   - Understand player command API

5. Design smart home handler:
   - Directive routing logic
   - Namespace mapping
   - Error handling patterns
   - Response format

### Week 2: Implementation

**Goal**: Build smart home handler

**Files to Create**:
- `/config/custom_components/alexa/smart_home.py` (~200 lines)
  - `async_handle_message()` - Main directive handler
  - `handle_music_directive()` - Route to Music Assistant
  - `handle_device_directive()` - Route to HA devices
  - `alexa_success_response()` - Generate success response
  - `alexa_error_response()` - Generate error response

**Files to Modify**:
- `/config/custom_components/alexa/__init__.py` (~50 lines added)
  - Discover Music Assistant integration
  - Register smart home webhook
  - Pass MA reference to handler

**Testing Approach**:
- Local development with mock Alexa directives
- Unit tests for routing logic
- Integration tests with mock MA

### Week 3: Integration Testing

**Goal**: End-to-end validation with real devices

**Test Scenarios**:
1. **Playback Control**:
   - "Alexa, play music on bedroom" → MA player starts
   - "Alexa, pause bedroom" → MA player pauses
   - "Alexa, next track on bedroom" → MA skips
   - "Alexa, previous track on bedroom" → MA goes back

2. **Volume Control**:
   - "Alexa, set volume to 50 on bedroom" → MA volume 50%
   - "Alexa, volume up on bedroom" → MA volume increases
   - "Alexa, volume down on bedroom" → MA volume decreases
   - "Alexa, mute bedroom" → MA player mutes

3. **Multiple Players**:
   - Different rooms work independently
   - Commands to unavailable players return errors
   - Player state tracked correctly

4. **Error Scenarios**:
   - Unavailable player → Friendly error message
   - Invalid command → Appropriate error response
   - MA server offline → Graceful degradation

### Week 4: HA Core Submission

**Goal**: Prepare for home-assistant/core submission

**Tasks**:
1. Code quality:
   - Linting (pylint, flake8)
   - Type hints (mypy)
   - Docstrings (Google style)

2. Testing:
   - Unit tests (>90% coverage)
   - Integration tests
   - Security tests

3. Documentation:
   - User documentation
   - Developer documentation
   - ADRs (if needed)

4. Submission:
   - Create PR to alexa-oauth2 repo
   - Prepare PR for home-assistant/core
   - Address reviewer feedback

---

## Project Files

### Active Documentation

**Core Files** (committed):
- `.gitignore` - Proper exclusions
- `INTEGRATION_STRATEGY.md` - Detailed architecture
- `APPLY_ALEXA_OAUTH2_FIXES.md` - Security analysis
- `README.md` - Project overview
- `PROJECT.md` - This file
- `DECISIONS.md` - Decision log
- `SESSION_LOG.md` - Activity history

**Architecture Docs**:
- `docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md` - Integration guide
- `docs/00_ARCHITECTURE/SYSTEM_OVERVIEW.md` - Current architecture

### Archives (Learning History)

**Apple Music Integration** (`archives/apple-music-integration/`):
- ~50 files: scripts, docs, patches
- API integration work (Oct 20-25)
- Why archived: MA already handles Apple Music

**OAuth Server Approach** (`archives/alexa-oauth-server-approach/`):
- `alexa_oauth_endpoints.py` - Complete OAuth server (800 lines)
- Deployment scripts, documentation
- OAuth server work (Oct 26-Nov 1)
- Why archived: Duplicates HA Alexa integration

**Historical Sessions** (`archives/historical-sessions/`):
- ~40 status reports, summaries, audits
- Shows project evolution
- Valuable for understanding "why not X?"

---

## Risk Assessment

### Technical Risks

**Risk 1: Alexa Directive Format Changes**
- **Likelihood**: LOW (stable API)
- **Impact**: MEDIUM (need to update handler)
- **Mitigation**: Follow Alexa API best practices, version directives

**Risk 2: Music Assistant API Changes**
- **Likelihood**: MEDIUM (active development)
- **Impact**: HIGH (breaks integration)
- **Mitigation**: Use stable API surfaces, version checking

**Risk 3: HA Core Rejection**
- **Likelihood**: LOW-MEDIUM (if quality high)
- **Impact**: MEDIUM (still works as custom component)
- **Mitigation**: Follow HA guidelines, comprehensive tests, good docs

### Timeline Risks

**Risk 1: Complexity Underestimated**
- **Likelihood**: MEDIUM (~200 lines may grow)
- **Impact**: MEDIUM (delays submission)
- **Mitigation**: Incremental approach, early testing

**Risk 2: Testing Challenges**
- **Likelihood**: MEDIUM (real Alexa devices needed)
- **Impact**: MEDIUM (delays validation)
- **Mitigation**: Mock directives for unit tests, Echo device for integration tests

---

## Next Steps (Immediate)

**This Week**:
1. Read `/config/custom_components/alexa/__init__.py` on haboxhill.local
2. Read `/config/custom_components/music_assistant/__init__.py` on haboxhill.local
3. Document MA player command API
4. Design smart home handler architecture
5. Create `docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md`

**Next Week**:
1. Implement `smart_home.py`
2. Update Alexa integration `__init__.py`
3. Local testing with mock directives
4. Deploy to haboxhill.local

**Following Weeks**:
1. Integration testing with Echo devices
2. Code cleanup and documentation
3. HA Core submission preparation

---

## References

### Documentation
- [Integration Strategy](INTEGRATION_STRATEGY.md)
- [Security Analysis](APPLY_ALEXA_OAUTH2_FIXES.md)
- [Architecture Cross-Reference](docs/00_ARCHITECTURE/CROSS_REFERENCE_ALEXA_OAUTH2.md)
- [Session Log](SESSION_LOG.md)

### Code References
- [alexa-oauth2 Project](/Users/jason/projects/alexa-oauth2/)
- [HA Core Alexa Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/alexa)
- [Music Assistant Integration](https://github.com/music-assistant/hass-music-assistant)

### External Documentation
- [Alexa Smart Home API](https://developer.amazon.com/docs/smarthome/understand-the-smart-home-skill-api.html)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Music Assistant Documentation](https://music-assistant.io/)

---

**Last Updated**: 2025-11-02
**Current Phase**: Week 1 - Investigation
**Status**: ARCHITECTURE CONFIRMED, READY TO IMPLEMENT
