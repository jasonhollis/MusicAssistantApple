# Cross-Reference: alexa-oauth2 and MusicAssistantApple Projects

**Purpose**: Explain how MusicAssistantApple project integrates with alexa-oauth2 project
**Audience**: Developers implementing smart home handler
**Layer**: 00_ARCHITECTURE (technology-agnostic principles)
**Related**: [alexa-oauth2/HA_CORE_SUBMISSION.md](/Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/HA_CORE_SUBMISSION.md)

---

## Intent

This document explains the relationship between two projects:
1. **alexa-oauth2**: Home Assistant Alexa integration (OAuth2+PKCE, secure token storage)
2. **MusicAssistantApple**: Extends alexa-oauth2 with Music Assistant voice control

**Key Principle**: MusicAssistantApple does NOT duplicate alexa-oauth2. It EXTENDS it with smart home handler.

---

## Project Relationship

### alexa-oauth2 (Foundation)

**Location**: `/Users/jason/projects/alexa-oauth2/`

**Role**: Complete OAuth2 + PKCE integration for Home Assistant Alexa

**What it provides**:
- OAuth2 authorization flow with PKCE (RFC 7636)
- Secure token storage (Fernet + PBKDF2)
- Token refresh automation
- Nabu Casa Cloud routing for webhooks
- Config flow (UI-based setup)

**Deployment**: `/config/custom_components/alexa/` on haboxhill.local

**Status**: PRODUCTION (working and deployed)

---

### MusicAssistantApple (Extension)

**Location**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/`

**Role**: Add Music Assistant voice control to alexa-oauth2 integration

**What it adds**:
- Smart home directive handler (`smart_home.py` - ~200 lines)
- Music Assistant discovery logic (`__init__.py` modifications - ~50 lines)
- Alexa directive → Music Assistant command routing
- Music control via voice (play/pause/volume/etc.)

**Deployment**: Same location as alexa-oauth2 (`/config/custom_components/alexa/`)

**Status**: ARCHITECTURE DEFINED (implementation pending)

---

## Architecture Integration

### Complete System Flow

```
┌─────────────────────────────────────────────────────────────┐
│ USER LAYER                                                   │
│ - Amazon Alexa app (authorization)                          │
│ - Echo devices (voice commands)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ ALEXA-OAUTH2 PROJECT (DEPLOYED)                             │
│ /config/custom_components/alexa/                            │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ OAuth2 Client Layer (alexa-oauth2)                   │   │
│ │ - oauth.py: PKCE implementation                      │   │
│ │ - Token encryption (Fernet + PBKDF2)                 │   │
│ │ - Automatic token refresh                            │   │
│ │ - config_flow.py: UI setup                           │   │
│ └──────────────────────────┬───────────────────────────┘   │
│                             │                                │
│ ┌──────────────────────────▼───────────────────────────┐   │
│ │ Smart Home Handler (MusicAssistantApple - NEW)       │   │
│ │ - smart_home.py: Directive routing                   │   │
│ │ - __init__.py: MA discovery                          │   │
│ │ - Routes music directives to Music Assistant         │   │
│ │ - Routes device directives to HA devices             │   │
│ └──────────────────────────┬───────────────────────────┘   │
└────────────────────────────┼────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ Music Assistant         │   │ Standard HA Devices     │
│ /config/custom_         │   │ - Lights                │
│  components/            │   │ - Switches              │
│  music_assistant/       │   │ - Scenes                │
│ (DEPLOYED)              │   │ (existing HA entities)  │
└─────────────────────────┘   └─────────────────────────┘
```

---

## Component Responsibilities

### alexa-oauth2 Handles

**OAuth2 Authentication** ✅ DEPLOYED:
- User authorization flow
- PKCE challenge/verifier generation
- Token exchange with Amazon
- Token storage (encrypted)
- Token refresh (automatic)

**Home Assistant Integration** ✅ DEPLOYED:
- Config entry management
- Reauth flow on token expiry
- Integration with HA OAuth2 framework
- Nabu Casa Cloud webhook routing

**Core Files** (in alexa-oauth2):
- `custom_components/alexa/__init__.py` - Entry point
- `custom_components/alexa/oauth.py` - OAuth2+PKCE
- `custom_components/alexa/config_flow.py` - UI setup
- `custom_components/alexa/const.py` - Constants
- `custom_components/alexa/manifest.json` - Metadata

---

### MusicAssistantApple Adds

**Smart Home Directive Handling** ❌ NOT YET DEPLOYED:
- Receive Alexa Smart Home directives
- Route by namespace (PlaybackController, Speaker, etc.)
- Forward music commands to Music Assistant
- Generate Alexa responses

**Music Assistant Integration** ❌ NOT YET DEPLOYED:
- Discover Music Assistant integration
- Maintain reference to MA instance
- Map Alexa directives → MA commands
- Handle MA unavailability gracefully

**New Files** (to be added to alexa-oauth2):
- `custom_components/alexa/smart_home.py` (~200 lines) - NEW
- Modifications to `custom_components/alexa/__init__.py` (~50 lines)

---

## Dependency Rule Compliance

### Correct Dependencies (Follows Dependency Rule ✅)

**MusicAssistantApple depends ON alexa-oauth2**:
- ✅ Extends existing OAuth implementation
- ✅ Adds functionality to existing integration
- ✅ Uses OAuth tokens provided by alexa-oauth2
- ✅ References alexa-oauth2 ADRs and principles

**alexa-oauth2 does NOT depend on MusicAssistantApple**:
- ✅ Works standalone without Music Assistant
- ✅ Music Assistant support is optional feature
- ✅ Graceful degradation if MA unavailable

### Incorrect Dependencies (Would Violate Dependency Rule ❌)

**What we're NOT doing**:
- ❌ Separate OAuth server (duplicates alexa-oauth2)
- ❌ Direct Music Assistant OAuth integration (wrong layer)
- ❌ Apple Music API integration (MA already has provider)

---

## Implementation Mapping

### From alexa-oauth2 (Reference)

**OAuth Patterns to Reuse**:
```python
# alexa-oauth2/custom_components/alexa/oauth.py

class AlexaOAuth2Implementation(LocalOAuth2Implementation):
    """OAuth2 implementation with PKCE for Alexa."""

    @property
    def extra_authorize_data(self) -> dict:
        """Generate PKCE challenge for authorization request."""
        code_verifier = secrets.token_urlsafe(96)
        code_challenge = self._generate_pkce_challenge(code_verifier)

        self.hass.data[DOMAIN][STORAGE_PKCE_KEY][
            self._config_entry.entry_id
        ] = {
            "code_verifier": code_verifier,
            "created_at": time.time(),
        }

        return {
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
```

**Token Encryption to Reuse**:
```python
# alexa-oauth2 uses Home Assistant's built-in token storage
# with Fernet encryption enabled via config_entry options

# MusicAssistantApple: Just uses the same OAuth2Session
# from alexa-oauth2, no additional token handling needed
```

**Integration Setup Pattern**:
```python
# alexa-oauth2/custom_components/alexa/__init__.py

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amazon Alexa from a config entry."""

    implementation = await async_get_config_entry_implementation(hass, entry)

    session = OAuth2Session(hass, entry, implementation)

    # Verify token validity
    await session.async_ensure_token_valid()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"session": session}

    return True
```

---

### To MusicAssistantApple (Extension)

**Smart Home Handler** (NEW):
```python
# custom_components/alexa/smart_home.py (NEW FILE)

async def async_handle_message(hass, config_entry, request):
    """Handle Alexa Smart Home directive."""

    namespace = request["directive"]["header"]["namespace"]
    name = request["directive"]["header"]["name"]

    # Route music playback commands to Music Assistant
    if namespace in (
        "Alexa.PlaybackController",
        "Alexa.Speaker",
        "Alexa.PlaybackStateReporter"
    ):
        ma_data = hass.data.get(DOMAIN, {}).get(
            config_entry.entry_id, {}
        ).get("music_assistant")

        if ma_data:
            return await handle_music_directive(hass, ma_data, request)
        else:
            return alexa_error_response(
                request,
                "ENDPOINT_UNREACHABLE",
                "Music Assistant not available"
            )

    # Route other commands to standard device handlers
    # (future enhancement - HA device control)
    return alexa_success_response(request)
```

**Music Assistant Discovery** (MODIFY):
```python
# custom_components/alexa/__init__.py (MODIFICATIONS)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amazon Alexa from a config entry."""

    # ... existing OAuth setup from alexa-oauth2 ...

    # NEW: Discover Music Assistant if available
    ma_data = hass.data.get("music_assistant")
    if ma_data:
        _LOGGER.info("Music Assistant detected - enabling music control")
        hass.data[DOMAIN][entry.entry_id]["music_assistant"] = ma_data

        # Register Alexa smart home handler with MA support
        await async_setup_alexa_smart_home(hass, entry, music_assistant=ma_data)
    else:
        _LOGGER.warning("Music Assistant not found - music control unavailable")
        # Future: Register standard smart home handler (lights/switches)

    return True
```

---

## Security Inheritance

### What MusicAssistantApple Inherits from alexa-oauth2

**OAuth2 Security** ✅:
- PKCE challenge/verifier prevents authorization code interception
- Token encryption at rest (Fernet + PBKDF2)
- Automatic token refresh (prevents long-lived tokens)
- Constant-time state validation (prevents timing attacks)

**Request Validation** ✅:
- Signature validation on Alexa directives (via Nabu Casa)
- Timestamp validation prevents replay attacks
- TLS encryption in transit

**Home Assistant Security** ✅:
- Config entry encryption
- Credential storage in HA keyring
- User authentication required for setup

### What MusicAssistantApple Adds

**Directive Authorization**:
- Validate directive came through authenticated webhook
- Verify Music Assistant integration accessible
- Rate limiting (if needed)

**Music Control Authorization**:
- Verify user has access to Music Assistant
- Check player availability before routing
- Graceful error handling

---

## Testing Strategy

### alexa-oauth2 Tests (Existing)

**OAuth Tests**:
```python
# tests/test_oauth.py in alexa-oauth2

def test_pkce_challenge_generation():
    """Test PKCE challenge generation."""
    # Verify S256 hash is correct
    # Verify code_verifier is cryptographically random
    # Verify challenge/verifier relationship

def test_token_encryption():
    """Test token encryption/decryption."""
    # Verify Fernet encryption
    # Verify PBKDF2 key derivation
    # Verify tamper detection
```

**Integration Tests**:
```python
# tests/test_config_flow.py in alexa-oauth2

def test_full_oauth_flow():
    """Test complete OAuth flow."""
    # Setup → Authorize → Callback → Token exchange
    # Verify tokens stored encrypted
    # Verify config entry created
```

---

### MusicAssistantApple Tests (To Be Added)

**Smart Home Handler Tests**:
```python
# tests/test_smart_home.py (NEW)

def test_directive_routing():
    """Test Alexa directive routing."""
    # PlaybackController → Music Assistant
    # Speaker → Music Assistant
    # Other namespaces → HA devices (future)

def test_music_assistant_discovery():
    """Test MA integration discovery."""
    # MA available → Handler registered
    # MA unavailable → Graceful degradation
    # MA added later → Dynamic registration
```

**Integration Tests**:
```python
# tests/test_integration.py (NEW)

def test_end_to_end_music_control():
    """Test Alexa → HA → MA flow."""
    # Mock Alexa directive
    # Verify routing to MA
    # Verify MA command execution
    # Verify response to Alexa
```

---

## ADR Cross-References

### alexa-oauth2 ADRs (Foundation)

**ADR-001: Replace Legacy Integration**:
- **Location**: `/Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-001-REPLACE-LEGACY-INTEGRATION.md`
- **Decision**: Replace insecure legacy Alexa integration
- **Rationale**: Security vulnerabilities (CVSS 9.1)
- **Relevance**: MusicAssistantApple builds on secure foundation

**ADR-002: Token Encryption Strategy**:
- **Location**: `/Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md`
- **Decision**: Fernet + PBKDF2 for token encryption
- **Rationale**: OWASP ASVS Level 2 compliance
- **Relevance**: MusicAssistantApple inherits token security

**ADR-003: User Migration Strategy**:
- **Location**: `/Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-003-USER-MIGRATION-STRATEGY.md`
- **Decision**: Atomic migration with rollback
- **Rationale**: Zero downtime, preserve entity IDs
- **Relevance**: Music Assistant addition is non-breaking

---

### MusicAssistantApple Decisions (Extension)

**Decision 1: Extend vs Separate**:
- **Decision**: Extend alexa-oauth2 with smart home handler
- **Rejected**: Build separate OAuth server
- **Rationale**: Avoid duplication, single OAuth flow
- **Date**: 2025-11-02
- **Archive**: `archives/alexa-oauth-server-approach/` (obsolete approach)

**Decision 2: Smart Home Handler Location**:
- **Decision**: Place handler in alexa-oauth2 integration
- **Rationale**: Alexa integration handles ALL Alexa communication
- **Location**: `custom_components/alexa/smart_home.py`

**Decision 3: Music Assistant Discovery**:
- **Decision**: Automatic discovery via `hass.data`
- **Rationale**: No additional user configuration required
- **Graceful degradation**: Works with or without MA

---

## Deployment Strategy

### Phase 1: Local Development

**Workspace**: `/Users/jason/projects/alexa-oauth2/`

**Tasks**:
1. Create `custom_components/alexa/smart_home.py`
2. Modify `custom_components/alexa/__init__.py`
3. Add tests in `tests/`
4. Local testing with mock directives

---

### Phase 2: haboxhill.local Deployment

**Location**: `/config/custom_components/alexa/` on haboxhill.local

**Tasks**:
1. Copy updated files to haboxhill.local
2. Restart Home Assistant
3. Verify Alexa integration still works (OAuth)
4. Test Music Assistant discovery
5. Test with real Echo devices

---

### Phase 3: Home Assistant Core Submission

**Target**: home-assistant/core repository

**Tasks**:
1. Code quality (linting, type hints, docstrings)
2. Tests (>90% coverage)
3. Documentation (user guide, developer docs)
4. PR submission
5. Address reviewer feedback

**Note**: Both alexa-oauth2 OAuth improvements AND Music Assistant support submitted together.

---

## Success Metrics

### Integration Success

**OAuth Working** ✅ (alexa-oauth2):
- [ ] User can authorize Alexa in HA UI
- [ ] Tokens stored encrypted
- [ ] Automatic token refresh works
- [ ] No authorization errors in logs

**Music Assistant Working** ❌ (MusicAssistantApple - pending):
- [ ] MA integration discovered automatically
- [ ] Alexa directives route to MA
- [ ] Voice commands control MA players
- [ ] Multiple MA players supported

---

### Code Quality

**alexa-oauth2** ✅ (already met):
- [x] >90% test coverage
- [x] Type hints complete
- [x] Linting passes
- [x] ADRs documented

**MusicAssistantApple** ❌ (to be met):
- [ ] >90% test coverage for smart home handler
- [ ] Type hints complete
- [ ] Linting passes
- [ ] Integration tests pass

---

## Related Documentation

### alexa-oauth2 Project

**Architecture Layer** (00):
- [HA Core Submission](../../../../../../jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/HA_CORE_SUBMISSION.md)
- [ADR-001: Replace Legacy Integration](../../../../../../jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-001-REPLACE-LEGACY-INTEGRATION.md)
- [ADR-002: Token Encryption Strategy](../../../../../../jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md)
- [ADR-003: User Migration Strategy](../../../../../../jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-003-USER-MIGRATION-STRATEGY.md)

**Implementation Layer** (04):
- OAuth2 implementation (`custom_components/alexa/oauth.py`)
- Config flow (`custom_components/alexa/config_flow.py`)

---

### MusicAssistantApple Project

**Architecture Layer** (00):
- [This Document](CROSS_REFERENCE_ALEXA_OAUTH2.md) - Integration architecture

**Strategy**:
- [Integration Strategy](../../INTEGRATION_STRATEGY.md) - Detailed architecture
- [Security Analysis](../../APPLY_ALEXA_OAUTH2_FIXES.md) - OAuth server security review

**Project**:
- [README](../../README.md) - Project overview
- [PROJECT.md](../../PROJECT.md) - Goals and implementation plan
- [DECISIONS.md](../../DECISIONS.md) - Decision log

---

## Verification Checklist

### Architecture Compliance

**Dependency Rule** ✅:
- [x] MusicAssistantApple depends on alexa-oauth2
- [x] alexa-oauth2 does NOT depend on MusicAssistantApple
- [x] Music Assistant support is optional feature
- [x] No circular dependencies

**Separation of Concerns** ✅:
- [x] OAuth handled by alexa-oauth2
- [x] Smart home routing handled by MusicAssistantApple
- [x] Music playback handled by Music Assistant
- [x] Each layer testable in isolation

---

### Implementation Readiness

**Prerequisites** ✅:
- [x] alexa-oauth2 deployed on haboxhill.local
- [x] Music Assistant integration deployed
- [x] Architecture documented
- [x] Reference code reviewed

**Next Steps** ❌:
- [ ] Implement `smart_home.py`
- [ ] Modify `__init__.py`
- [ ] Write tests
- [ ] Deploy to haboxhill.local

---

## Conclusion

**MusicAssistantApple extends alexa-oauth2** with ~250 lines of code:
- ~200 lines: Smart home directive handler (`smart_home.py`)
- ~50 lines: Music Assistant discovery (`__init__.py` modifications)

**Benefits of Extension Approach**:
- Single OAuth flow (user experience)
- Leverages secure foundation (security)
- Clean separation of concerns (architecture)
- Submittable to HA Core (long-term maintainability)

**Alternative Rejected**:
- Separate OAuth server (800 lines)
- Architectural duplication
- Security issues (hardcoded user, no encryption)
- Not submittable to HA Core

**Conclusion**: Extending alexa-oauth2 is the correct architectural decision. This document ensures both projects remain aligned and follow Clean Architecture principles.

---

**Document Status**: COMPLETE
**Last Updated**: 2025-11-02
**Implementation Status**: Design complete, implementation pending
