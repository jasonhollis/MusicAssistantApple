# ADR-011: Music Assistant Home Assistant Alexa Integration Architecture

**Date**: 2025-10-27
**Status**: FINAL ✅
**Supersedes**: ADR-010 (Implementation details)
**Author**: Architectural Analysis

---

## Intent

Define the exact implementation steps for integrating Music Assistant addon with Home Assistant's native Alexa integration via Home Assistant Cloud, eliminating the flawed custom OAuth approach.

This ADR answers: "What code changes does Music Assistant need? What configuration does HA need? How do we connect them?"

---

## The Integration Pattern

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Amazon Alexa (Cloud)                                        │
│ "Alexa, play Taylor Swift on Music Assistant"              │
└──────────────────┬──────────────────────────────────────────┘
                   │ (HTTPS + OAuth token)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Home Assistant Cloud (Nabu Casa)                            │
│ - OAuth endpoint (identity verification)                    │
│ - Entity proxy (entity state sync)                          │
│ - Command routing (intent → service call)                   │
└──────────────────┬──────────────────────────────────────────┘
                   │ (Local network)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Home Assistant Core (haboxhill.local:8123)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Alexa Integration Component                          │  │
│  │ - Entity discovery (scans all media_player entities) │  │
│  │ - Capability exposure (PLAY, PAUSE, VOLUME_SET)     │  │
│  │ - Service call translation (Alexa → HA service)     │  │
│  │ - State synchronization (HA → Alexa)                │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │ (IPC/Python)                    │
│  ┌────────────────────────▼─────────────────────────────┐  │
│  │ Media Player: Music Assistant Addon                  │  │
│  │ - Entity ID: media_player.music_assistant_main      │  │
│  │ - State: playing/paused/idle/off                    │  │
│  │ - Attributes: source, volume, playlist, etc.        │  │
│  │ - Services: play, pause, volume_set, select_source  │  │
│  └─────────────────────────────────────────────────────┘  │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Music        │
                    │ Assistant    │
                    │ (Port 8095)  │
                    │              │
                    │ Playback     │
                    │ + Library    │
                    └──────────────┘
```

### Data Flow for a Single Voice Command

```
"Alexa, play Taylor Swift on Music Assistant"
  ↓
1. Alexa Cloud: Parse voice intent
2. Alexa Cloud: Look up "Music Assistant" entity in user's HA Cloud account
3. HA Cloud: Verify OAuth token (user authenticated)
4. HA Cloud: Forward command to HA Core (local network via VPN/tunnel)
5. HA Core Alexa Integration: Translate intent to service call
   - Entity: media_player.music_assistant_main
   - Service: media_player.play_media
   - Params: media_content_id="Taylor Swift", media_content_type="artist"
6. Music Assistant Addon: Receive service call
7. Music Assistant Addon: Call Apple Music API to search for Taylor Swift
8. Music Assistant Addon: Start playback
9. Music Assistant Addon: Update entity state to "playing"
10. State propagates back to HA Core → HA Cloud → Alexa (for voice feedback)
```

---

## Implementation Requirements

### 1. Music Assistant Addon Must Expose `media_player` Entities

**Current Status**: Likely already done (addon has web UI)
**What's needed**: Verify addon properly registers with HA entity registry

**Entity Requirements**:

```python
# In Music Assistant addon's __init__.py or setup component
from homeassistant.components.media_player import MediaPlayerEntity

class MusicAssistantMediaPlayer(MediaPlayerEntity):
    """Media player entity for Music Assistant."""

    def __init__(self, hass, name, music_assistant_api):
        self._hass = hass
        self._name = name
        self._api = music_assistant_api
        self._attr_unique_id = f"music_assistant_{name.lower()}"

    @property
    def name(self) -> str:
        """Return the name of the media player."""
        return self._name

    @property
    def state(self) -> str:
        """Return current playback state."""
        # MUST return one of: 'playing', 'paused', 'idle', 'off', 'unknown'
        return self._api.get_state()

    @property
    def supported_features(self) -> int:
        """Return supported features as MediaPlayerEntityFeature flags."""
        from homeassistant.components.media_player import MediaPlayerEntityFeature

        return (
            MediaPlayerEntityFeature.PLAY |
            MediaPlayerEntityFeature.PAUSE |
            MediaPlayerEntityFeature.VOLUME_SET |
            MediaPlayerEntityFeature.VOLUME_MUTE |
            MediaPlayerEntityFeature.SELECT_SOURCE |
            MediaPlayerEntityFeature.PLAY_MEDIA
        )

    @property
    def source(self) -> str | None:
        """Return currently playing source (Apple Music, Spotify, etc)."""
        return self._api.get_current_source()

    @property
    def source_list(self) -> list[str] | None:
        """Return list of available sources."""
        return ["Apple Music", "Spotify", "Local Library"]

    @property
    def volume_level(self) -> float | None:
        """Return current volume level (0.0 to 1.0)."""
        return self._api.get_volume() / 100.0

    @property
    def is_volume_muted(self) -> bool:
        """Return True if muted."""
        return self._api.is_muted()

    @property
    def media_title(self) -> str | None:
        """Return title of current track."""
        return self._api.get_current_track_title()

    @property
    def media_artist(self) -> str | None:
        """Return artist of current track."""
        return self._api.get_current_artist()

    @property
    def device_class(self) -> str | None:
        """Return device class for grouping/discovery."""
        return "speaker"  # or "tv" if supports video

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        """Play media."""
        await self._api.play_media(media_type, media_id)

    async def async_media_play(self) -> None:
        """Play (resume) playback."""
        await self._api.play()

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self._api.pause()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        await self._api.set_volume(int(volume * 100))

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute/unmute."""
        await self._api.set_muted(mute)

    async def async_select_source(self, source: str) -> None:
        """Select playback source."""
        await self._api.select_source(source)
```

**Addon Manifest Requirements**:

```json
{
  "name": "Music Assistant",
  "version": "1.0.0",
  "slug": "music_assistant",
  "description": "Music provider aggregator",
  "codeowners": ["@yourname"],
  "config": {},
  "requirements": [
    "homeassistant>=2024.1.0"
  ],
  "services": {},
  "ports": {
    "8095/tcp": 8095
  },
  "ports_description": {
    "8095/tcp": "Music Assistant web interface"
  }
}
```

### 2. Home Assistant Alexa Integration Must Discover Entities

**Status**: BUILT IN to Home Assistant (no changes needed)
**How it works**:

Home Assistant's Alexa integration automatically:
1. Scans all `media_player.*` entities in the entity registry
2. Filters for supported features (PLAY, PAUSE, VOLUME_SET)
3. Exposes them to Alexa with appropriate friendly names
4. Routes Alexa voice commands as HA service calls

**Configuration**:

```yaml
# In /config/configuration.yaml
alexa:
  smart_home:
    enabled: true
    entity_configs:
      media_player.music_assistant_main:
        display_categories: SPEAKER
        friendly_name: "Living Room Music"
        description: "Music Assistant via Alexa"

# In Home Assistant Cloud settings (UI):
# - Enable Alexa integration
# - Go to Devices & Services → Alexa Smart Home
# - Ensure Music Assistant entities are enabled (toggle on)
# - Click "Ask Alexa to sync devices"
```

### 3. Home Assistant Cloud Must Be Active

**Status**: USER RESPONSIBILITY (they have subscription)
**What's needed**:

- [ ] HA Cloud subscription active
- [ ] Alexa integration enabled in HA Cloud
- [ ] User account linked to Alexa app
- [ ] "Sync" performed after entity creation

---

## Implementation Checklist

### Step 1: Verify Music Assistant Entities Exist (5 min)

```bash
# SSH to haboxhill.local
ssh root@haboxhill.local

# Check Home Assistant entity registry
ha core state | grep media_player | grep -i music

# Expected output:
# media_player.music_assistant_main is playing
```

**IF ENTITIES EXIST** → Go to Step 2
**IF ENTITIES MISSING** → Check addon logs:
```bash
ha addon logs music_assistant
# Look for "entity registered" or "integration loaded" messages
# If missing, addon may not expose entities properly - requires code fix
```

---

### Step 2: Configure Alexa Integration (10 min)

**Via HA UI**:
1. Navigate to **Settings** → **Devices & Services**
2. Find **Alexa Smart Home** (may be under Cloud section)
3. Click **Manage Entities**
4. Search for "music_assistant"
5. Toggle **ON** for each Music Assistant entity
6. Set friendly names (e.g., "Living Room Speaker")
7. Click **Update**

**Via YAML** (alternative):
```yaml
# /config/automations.yaml or create /config/alexa_config.yaml
alexa:
  smart_home:
    enabled: true
    entity_configs:
      media_player.music_assistant_main:
        display_categories: SPEAKER
        friendly_name: "Music Library"
```

**After configuration**:
```bash
# Restart HA to apply config changes
ha core restart

# Wait 30 seconds for HA Cloud sync
sleep 30

# Check HA Cloud logs (if accessible)
ha addon logs cloud

# Expected: "Entities synced" or similar message
```

---

### Step 3: Test Entity Exposure (5 min)

**From HA Dev Tools**:
1. Go to **Developer Tools** → **States**
2. Search for `media_player.music_assistant`
3. Verify state shows one of: `playing`, `paused`, `idle`, `off`
4. Verify attributes include: `friendly_name`, `supported_features`, `volume_level`, `source`

**Example entity state**:
```
entity_id: media_player.music_assistant_main
state: paused
attributes:
  friendly_name: Music Library
  supported_features: 149463
  volume_level: 0.7
  source: Apple Music
  device_class: speaker
  icon: mdi:music
```

**IF STATE CORRECT** → Go to Step 4
**IF STATE MISSING/MALFORMED** → Debug addon entity registration (requires code fix)

---

### Step 4: Test Direct Service Calls (5 min)

**Via HA Developer Tools → Services**:

```yaml
service: media_player.media_play
target:
  entity_id: media_player.music_assistant_main

# Verify: Entity state changes to 'playing', Music Assistant actually plays audio
```

```yaml
service: media_player.media_pause
target:
  entity_id: media_player.music_assistant_main

# Verify: Entity state changes to 'paused', Music Assistant stops
```

```yaml
service: media_player.set_volume_level
target:
  entity_id: media_player.music_assistant_main
data:
  volume_level: 0.5

# Verify: Volume changes to 50%
```

**IF SERVICE CALLS WORK** → Go to Step 5
**IF SERVICE CALLS FAIL** → Music Assistant addon not handling service calls properly (code fix needed)

---

### Step 5: Trigger Alexa Device Discovery (10 min)

**Via Alexa App**:
1. Open Alexa app on phone/device
2. Go to **Devices** section
3. Click **+** button → **Add Device**
4. Select **Music System**
5. Wait for discovery (30-60 seconds)

**Alternative (Voice Command)**:
```
"Alexa, discover devices"
```

**Verify Discovery**:
- Look for "Music Library" (or your friendly_name) in device list
- Should show as "Speaker" or "Music System"
- Click to open device card

**IF DISCOVERY WORKS** → Go to Step 6
**IF DISCOVERY FAILS** → Check HA Cloud Alexa logs, verify entity exposure

---

### Step 6: Test Voice Commands (10 min)

```bash
# Test basic playback control
"Alexa, play on Music Library"
"Alexa, pause Music Library"
"Alexa, set volume 50 percent on Music Library"

# Test music search (requires music search integration)
"Alexa, play Taylor Swift on Music Library"
"Alexa, play the Eagles on Music Library"

# Test playlist
"Alexa, play my favorites on Music Library"

# Test multi-room (if multiple zones)
"Alexa, play music in the living room"
"Alexa, play music in the bedroom"
```

**Success Criteria**:
- [ ] Voice commands understood (no "I'm not sure what you said")
- [ ] Playback starts/stops within 2 seconds
- [ ] Volume adjusts smoothly
- [ ] Source switches correctly
- [ ] No errors in Music Assistant logs

---

## Failure Modes & Diagnosis

### Problem: Entities Don't Appear in HA

**Diagnosis**:
```bash
ssh root@haboxhill.local

# Check addon is running
ha addon info music_assistant
# Look for "State: started"

# Check addon logs
ha addon logs music_assistant
# Look for "entity registered" or "integration loaded"
# Look for errors starting with "ERROR" or "Exception"

# Check entity registry
ha core state | grep music_assistant
# Should return one or more lines with media_player entities
```

**Solutions**:
- Addon not registering entities → Code fix in Music Assistant integration component
- Addon crashed/not running → Check HA logs: `ha core logs | tail -50`
- Entity name mismatch → Check integration code for entity naming pattern

---

### Problem: Entities Show But Alexa Won't Discover Them

**Diagnosis**:
```bash
# Check HA Cloud Alexa component
ha addon logs cloud | tail -50

# Check if entities are marked for exposure
# Via HA UI: Settings → Devices & Services → Alexa → Manage Entities
# Look for Music Assistant entities in list
```

**Solutions**:
- Entities not enabled for Alexa → Toggle ON in Alexa settings
- Entity friendly name unclear → Rename to "Music Library" or "Living Room Speaker"
- HA Cloud sync failed → Restart HA Cloud addon: `ha addon restart cloud`

---

### Problem: Alexa Discovers Entities But Commands Fail

**Diagnosis**:
```bash
# Check HA logs when command issued
ha core logs | grep -i "alexa\|music_assistant"

# Test service call directly (bypass Alexa)
# Via Developer Tools → Services
service: media_player.media_play
target:
  entity_id: media_player.music_assistant_main

# If direct call works but Alexa fails → Translation layer issue
# If direct call fails → Addon not handling service calls
```

**Solutions**:
- Service call translation error → Check Alexa component code
- Addon timeout on service calls → Check Music Assistant performance, increase timeout
- State not updating → Music Assistant not updating entity state after service call

---

## Rollback Plan (If Something Breaks)

```bash
# 1. Disable Alexa integration temporarily
ssh root@haboxhill.local
ha core config reload

# 2. Remove custom OAuth server/port 8096
docker ps | grep music_assistant
docker exec [container-id] pkill -f oauth_server.py
# Or remove from systemd if native service

# 3. Remove Tailscale Funnel (if configured)
tailscale funnel off

# 4. Restart HA to clear state
ha core restart

# 5. Re-enable Alexa after Music Assistant re-stabilizes
```

---

## Success Criteria

**Phase Complete When**:
- [ ] Music Assistant entities visible in HA entity registry
- [ ] Direct service calls (play/pause/volume) work via Developer Tools
- [ ] Alexa discovers Music Assistant device
- [ ] Voice command "Alexa, play on [Music Library]" works
- [ ] Voice command "Alexa, pause [Music Library]" works
- [ ] Voice command "Alexa, set volume 50 percent on [Music Library]" works
- [ ] All commands complete within 2 seconds
- [ ] Music Assistant actually plays audio on successful command
- [ ] No custom OAuth code needed
- [ ] No Tailscale Funnel routing needed
- [ ] No port 8096 server running

---

## Key Files & References

### Home Assistant Integration Documentation
- `homeassistant/components/media_player/` - Media player entity interface
- `homeassistant/components/alexa/` - Alexa integration (smart home discovery)
- `homeassistant/helpers/entity.py` - Base entity class

### Music Assistant Integration Pattern
```python
# addon/__init__.py structure
async def async_setup(hass, config):
    """Set up Music Assistant integration."""

    # 1. Initialize Music Assistant API client
    api = MusicAssistantAPI(...)

    # 2. Register media_player entities for each zone
    for zone in api.get_zones():
        entity = MusicAssistantMediaPlayer(hass, zone)
        hass.data[DOMAIN][zone.id] = entity

    # 3. Register update listener (for state sync)
    api.add_listener(update_callback)

    # 4. Set up services (if any custom HA services needed)

    return True
```

---

## Timeline

| Activity | Duration | Prerequisites |
|----------|----------|----------------|
| Verify entities exist | 5 min | SSH access to haboxhill.local |
| Configure Alexa integration | 10 min | HA Cloud subscription active |
| Test entity exposure | 5 min | Entities verified |
| Test service calls | 5 min | Entities verified |
| Trigger Alexa discovery | 10 min | All above complete |
| Test voice commands | 10 min | Alexa discovery complete |
| Document findings | 15 min | Testing complete |
| **TOTAL** | **~60 minutes** | - |

---

## Post-Implementation

### Remove Custom OAuth Code
```bash
# Delete port 8096 OAuth server
rm /config/oauth_server.py
rm /config/oauth_clients.json
rm /config/start_oauth_server.py

# Remove from addon startup (if configured in manifest)
# Delete from systemd (if native service)

# Disable Tailscale Funnel
tailscale funnel --off

# Verify port 8096 no longer listening
netstat -an | grep 8096
# Should return empty (no listening ports)
```

### Document the Solution
Create integration guide for community:
```
docs/05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_INTEGRATION_GUIDE.md
- Step-by-step configuration
- Troubleshooting flowchart
- Voice command examples
- Known limitations
```

### Extract for Future Integrations
Create reference template:
```
docs/00_ARCHITECTURE/CUSTOM_MEDIA_PROVIDER_ALEXA_PATTERN.md
- How to integrate any custom media provider with Alexa
- Entity interface requirements
- Service call mapping
- State synchronization patterns
```

---

## References

- Home Assistant Media Player: https://developers.home-assistant.io/docs/core/entity/media-player/
- Home Assistant Alexa Integration: https://www.home-assistant.io/integrations/alexa/
- Home Assistant Cloud: https://www.home-assistant.io/cloud/
- Amazon Alexa Smart Home API: https://developer.amazon.com/en-US/docs/alexa/smart-home/
- Music Assistant Docs: https://music-assistant.io/

---

**STATUS**: Ready for implementation
**NEXT STEP**: Execute Phase 1 verification (5 minutes - entity check)
