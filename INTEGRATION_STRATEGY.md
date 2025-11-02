# Music Assistant + Alexa Integration Strategy

**Date**: 2025-11-02
**Status**: ACTIVE DEPLOYMENT
**Location**: haboxhill.local (`/config/custom_components/`)

---

## Current State (CONFIRMED)

### ✅ Already Deployed on haboxhill.local:

1. **Alexa Integration** (`/config/custom_components/alexa/`)
   - ✅ OAuth2 + PKCE implementation (from alexa-oauth2 project)
   - ✅ Secure token storage with encryption
   - ✅ Nabu Casa Cloud routing (`async_get_redirect_uri()`)
   - ✅ Proper ADRs and documentation
   - **Status**: PRODUCTION (actively working)

2. **Music Assistant Integration** (`/config/custom_components/music_assistant/`)
   - ✅ Config flow for MA server URL
   - ✅ Media player platform (exposes MA players to HA)
   - **Status**: PRODUCTION (actively working)

### ❌ NOT NEEDED: Separate OAuth Server

The `alexa_oauth_endpoints.py` file in MusicAssistantApple project is **OBSOLETE**:
- ❌ No longer needed (Alexa OAuth handled by HA integration)
- ❌ Has security vulnerabilities (hardcoded user, no encryption)
- ❌ Duplicates functionality already in `/config/custom_components/alexa/`
- **Action**: Archive this file, do NOT deploy

---

## Architecture: How It Actually Works

### Current Flow (CORRECT):

```
User → Home Assistant UI → Alexa Integration → Amazon OAuth2
                              ↓
                         Token Storage
                              ↓
User → Echo Device → Amazon → HA Alexa Integration → Music Assistant Integration → MA Server
                               (Smart Home Handler)
```

### Key Points:

1. **Single OAuth Flow**: User authorizes Alexa integration in HA (one time)
2. **HA Routes Commands**: Alexa skill sends smart home directives to HA
3. **HA → MA**: HA's Alexa integration routes music commands to Music Assistant
4. **No Separate OAuth**: Music Assistant doesn't need its own OAuth server

---

## What We Need to Add: Smart Home Music Control

### Current Gap:

The Alexa integration (`/config/custom_components/alexa/`) currently handles:
- ✅ OAuth2 authentication with Amazon
- ✅ Token storage and refresh
- ❓ Smart home device control (lights, switches, etc.) - **CHECK THIS**
- ❌ **Music control routing to Music Assistant** - **MISSING**

### Solution: Add Music Assistant Support to Alexa Integration

**File**: `/config/custom_components/alexa/__init__.py`

Add Music Assistant discovery and routing:

```python
"""Amazon Alexa integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

_LOGGER = logging.getLogger(__name__)

DOMAIN = "alexa"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amazon Alexa from a config entry."""

    # ... existing OAuth setup code ...

    # NEW: Discover Music Assistant if available
    ma_data = hass.data.get("music_assistant")
    if ma_data:
        _LOGGER.info("Music Assistant detected - enabling music control via Alexa")
        hass.data[DOMAIN][entry.entry_id]["music_assistant"] = ma_data

        # Register Alexa smart home handler with MA support
        await async_setup_alexa_smart_home(hass, entry, music_assistant=ma_data)
    else:
        _LOGGER.warning("Music Assistant not found - music control unavailable")
        # Register standard Alexa smart home handler (no music)
        await async_setup_alexa_smart_home(hass, entry, music_assistant=None)

    return True


async def async_setup_alexa_smart_home(
    hass: HomeAssistant,
    entry: ConfigEntry,
    music_assistant = None
):
    """Set up Alexa Smart Home skill handler."""
    from .smart_home import async_handle_message

    # Store MA reference for smart home handler
    hass.data[DOMAIN][entry.entry_id]["smart_home_handler"] = {
        "music_assistant": music_assistant,
        "handle_message": async_handle_message
    }

    # Register webhook for Alexa Smart Home skill
    # (This receives directives from Alexa)
    # ... webhook registration code ...
```

**NEW FILE**: `/config/custom_components/alexa/smart_home.py`

```python
"""Alexa Smart Home skill message handler."""
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

async def async_handle_message(hass, config_entry, request: dict[str, Any]):
    """Handle Alexa Smart Home directive."""

    namespace = request["directive"]["header"]["namespace"]
    name = request["directive"]["header"]["name"]

    _LOGGER.debug(f"Alexa directive: {namespace}.{name}")

    # Route music playback commands to Music Assistant
    if namespace in ("Alexa.PlaybackController", "Alexa.Speaker", "Alexa.PlaybackStateReporter"):
        ma = hass.data["alexa"][config_entry.entry_id].get("music_assistant")

        if ma:
            return await handle_music_directive(hass, ma, request)
        else:
            return alexa_error_response(request, "ENDPOINT_UNREACHABLE", "Music Assistant not available")

    # Route other smart home commands (lights, switches, etc.)
    # ... existing device handling code ...

    return alexa_success_response(request)


async def handle_music_directive(hass, music_assistant, request: dict[str, Any]):
    """Route music directive to Music Assistant."""

    directive = request["directive"]
    namespace = directive["header"]["namespace"]
    name = directive["header"]["name"]
    endpoint_id = directive["endpoint"]["endpointId"]

    # Map Alexa directive to Music Assistant command
    if namespace == "Alexa.PlaybackController":
        if name == "Play":
            await music_assistant.player_command(endpoint_id, "play")
        elif name == "Pause":
            await music_assistant.player_command(endpoint_id, "pause")
        elif name == "Next":
            await music_assistant.player_command(endpoint_id, "next")
        elif name == "Previous":
            await music_assistant.player_command(endpoint_id, "previous")

    elif namespace == "Alexa.Speaker":
        if name == "SetVolume":
            volume = directive["payload"]["volume"]
            await music_assistant.set_volume(endpoint_id, volume)
        elif name == "AdjustVolume":
            delta = directive["payload"]["volumeSteps"]
            await music_assistant.adjust_volume(endpoint_id, delta)
        elif name == "SetMute":
            mute = directive["payload"]["mute"]
            await music_assistant.set_mute(endpoint_id, mute)

    return alexa_success_response(request)


def alexa_success_response(request: dict[str, Any]) -> dict[str, Any]:
    """Generate Alexa success response."""
    return {
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "Response",
                "messageId": request["directive"]["header"]["messageId"],
                "correlationToken": request["directive"]["header"]["correlationToken"],
                "payloadVersion": "3"
            },
            "endpoint": request["directive"]["endpoint"],
            "payload": {}
        }
    }


def alexa_error_response(request: dict[str, Any], error_type: str, message: str) -> dict[str, Any]:
    """Generate Alexa error response."""
    return {
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "ErrorResponse",
                "messageId": request["directive"]["header"]["messageId"],
                "correlationToken": request["directive"]["header"]["correlationToken"],
                "payloadVersion": "3"
            },
            "endpoint": request["directive"]["endpoint"],
            "payload": {
                "type": error_type,
                "message": message
            }
        }
    }
```

---

## Implementation Timeline

### Week 1: Investigation (THIS WEEK)

1. ✅ **Confirm current deployment** (DONE - both integrations active)
2. 🔍 **Check existing Alexa smart home handler**:
   ```bash
   ssh root@haboxhill.local "cat /config/custom_components/alexa/__init__.py"
   ```
   - Does it already have smart home webhook?
   - What namespaces does it handle?

3. 🔍 **Check Music Assistant API**:
   ```bash
   ssh root@haboxhill.local "cat /config/custom_components/music_assistant/__init__.py"
   ```
   - How to call MA player commands?
   - What's the API surface?

### Week 2: Integration Development

4. 📝 **Add smart_home.py** to Alexa integration
5. 🔗 **Add MA discovery** to Alexa `__init__.py`
6. 🧪 **Local testing**:
   - Register Alexa skill in Amazon Developer Console
   - Configure skill endpoint to point to HA
   - Test "Alexa, play music on [MA player]"

### Week 3: Testing & Refinement

7. 🎯 **End-to-end testing**:
   - Voice control via Echo device
   - Playback control (play/pause/next/previous)
   - Volume control
   - Multiple MA players

8. 📚 **Documentation**:
   - User guide: "How to use Alexa with Music Assistant"
   - Developer guide: "Alexa smart home integration architecture"

### Week 4: Submission to HA Core

9. 🚀 **Prepare PR for home-assistant/core**:
   - Clean up code (linting, type hints, tests)
   - Add integration tests
   - Write component documentation
   - Submit PR with both Alexa OAuth2 + MA support

---

## Why This Approach is Superior

### vs Building Separate OAuth Server (MusicAssistantApple/alexa_oauth_endpoints.py):

| Aspect | Separate OAuth Server ❌ | Integrated Approach ✅ |
|--------|------------------------|----------------------|
| **User Setup** | Link Alexa twice (HA + MA) | Link Alexa once (HA) |
| **Security** | Need to fix 3 vulnerabilities | Already secure (PKCE + encryption) |
| **Maintenance** | Two OAuth implementations | Single implementation |
| **HA Core** | Not submittable (duplicate) | Submittable (replaces legacy) |
| **Code Reuse** | Duplicates alexa-oauth2 | Reuses alexa-oauth2 |
| **Testing** | New code path | Existing OAuth tests |

### Benefits for HA Core Submission:

1. **Solves TWO problems**:
   - ✅ Replaces insecure legacy Alexa integration (OAuth2+PKCE)
   - ✅ Adds native Music Assistant support (music control)

2. **Clean architecture**:
   - Alexa integration handles OAuth + smart home routing
   - Music Assistant integration handles music playback
   - Clear separation of concerns

3. **User value**:
   - One-time Alexa setup (not two)
   - Voice control of Music Assistant
   - Standard HA integration experience

---

## Next Actions

### TODAY:

1. ✅ **Read existing Alexa integration code**:
   ```bash
   ssh root@haboxhill.local "cat /config/custom_components/alexa/__init__.py"
   ssh root@haboxhill.local "cat /config/custom_components/alexa/oauth.py"
   ```
   - Understand current structure
   - Identify where to add MA integration

2. ✅ **Read Music Assistant integration code**:
   ```bash
   ssh root@haboxhill.local "cat /config/custom_components/music_assistant/__init__.py"
   ssh root@haboxhill.local "cat /config/custom_components/music_assistant/media_player.py"
   ```
   - Understand MA API
   - Identify player command methods

3. 📝 **Create implementation plan**:
   - File-by-file changes needed
   - API mapping (Alexa directive → MA command)
   - Test cases

### THIS WEEK:

4. 🔨 **Implement smart home handler**:
   - Create `smart_home.py`
   - Add MA discovery to `__init__.py`
   - Test locally

5. 🧪 **Integration testing**:
   - Deploy to haboxhill.local
   - Test with Echo device
   - Verify all Alexa music directives work

### NEXT WEEK:

6. 🚀 **Prepare HA Core PR**:
   - Clean up code
   - Add tests
   - Write documentation
   - Submit to home-assistant/core

---

## Files to Create/Modify

### In `/Users/jason/projects/alexa-oauth2/`:

1. **NEW**: `custom_components/alexa/smart_home.py`
   - Alexa Smart Home directive handler
   - Music Assistant command routing
   - ~200 lines

2. **MODIFY**: `custom_components/alexa/__init__.py`
   - Add MA discovery (lines 50-60)
   - Register smart home handler (lines 80-100)
   - ~20 lines added

3. **NEW**: `tests/test_smart_home.py`
   - Test Alexa directive handling
   - Test MA command routing
   - ~150 lines

4. **NEW**: `docs/MUSIC_ASSISTANT_INTEGRATION.md`
   - Architecture documentation
   - User guide
   - ~100 lines

### To DELETE (Obsolete):

- `/Users/jason/Library/Mobile Documents/.../MusicAssistantApple/alexa_oauth_endpoints.py`
- All OAuth server documentation in MusicAssistantApple
- **Reason**: Duplicates functionality in `/config/custom_components/alexa/`

---

## Success Criteria

**After Implementation**:
- [ ] User links Alexa to Home Assistant (OAuth2 flow)
- [ ] Alexa skill detects Music Assistant players
- [ ] Voice command "Alexa, play music on [MA player]" works
- [ ] Playback control (play/pause/next/previous) works
- [ ] Volume control works
- [ ] Multiple MA players supported
- [ ] No separate OAuth server needed

**Production Ready**:
- [ ] Code merged to alexa-oauth2 main branch
- [ ] Tests passing (>90% coverage)
- [ ] Documentation complete
- [ ] Ready for HA Core PR submission

---

## Questions to Answer (This Week)

1. **Does Alexa integration already have smart home handler?**
   - Check `__init__.py` for webhook registration
   - Check for existing `smart_home.py` or similar

2. **What's the Music Assistant API?**
   - How to call player commands?
   - How to get list of players?
   - How to handle callbacks/events?

3. **Alexa skill configuration**:
   - What's the skill ID?
   - What's the endpoint URL?
   - What namespaces are registered?

---

**Bottom Line**: You already have BOTH integrations deployed (`alexa` and `music_assistant`). The ONLY thing missing is connecting them so Alexa directives route to Music Assistant. This is ~200 lines of Python (smart home handler), NOT a separate OAuth server. The OAuth server approach (`alexa_oauth_endpoints.py`) is architectural duplication and should be archived.

**Next Step**: Read the current integration code and create the smart home handler that routes Alexa music directives to Music Assistant.
