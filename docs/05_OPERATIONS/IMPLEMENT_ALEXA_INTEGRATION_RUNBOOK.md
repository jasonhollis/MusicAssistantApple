# Music Assistant Alexa Integration - Implementation Runbook

**STATUS**: 🟢 READY TO EXECUTE
**DURATION**: 60 minutes actual work
**COMPLEXITY**: Low-Medium
**Risk Level**: Low (non-destructive, can rollback)

---

## QUICK START (Copy-Paste Commands)

**If Music Assistant addon already exposes `media_player` entities:**

```bash
# 1. SSH to haboxhill.local
ssh root@haboxhill.local

# 2. Verify entities exist
ha core state | grep media_player | grep -i music

# Expected: Output showing media_player entities like:
# media_player.music_assistant_main is paused

# If nothing returned → STOP, go to "Addon Integration" section below

# 3. Configure Alexa (via Home Assistant UI - see Step 1 below)

# 4. Test service calls
# (See Step 2 below)

# 5. Trigger Alexa discovery
# (See Step 3 below)

# 6. Test voice commands
# (See Step 4 below)
```

---

## PHASE 1: ADDON INTEGRATION (Only if entities missing)

**Skip this section if `ha core state | grep media_player | grep music` returns results**

### Problem: Music Assistant addon not exposing entities to HA

**Root cause**: Addon integration component not properly registering `media_player` entities

**Fix**: Music Assistant addon needs to expose entities. Here's what needs to be in the addon's integration code:

### File 1: `addon_root/music_assistant/__init__.py`

```python
"""Home Assistant integration for Music Assistant."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN

DOMAIN = "music_assistant"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Music Assistant integration."""

    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Music Assistant from a config entry."""

    # Forward setup to media_player platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, [MEDIA_PLAYER_DOMAIN])
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Music Assistant config entry."""

    await hass.config_entries.async_unload_platforms(entry, [MEDIA_PLAYER_DOMAIN])

    return True
```

### File 2: `addon_root/music_assistant/media_player.py`

```python
"""Media player entities for Music Assistant."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Media Player platform for Music Assistant."""

    # Get Music Assistant API client
    # (Adjust based on your addon's actual API)
    music_assistant = hass.data.get("music_assistant_api")

    if not music_assistant:
        # Initialize Music Assistant API connection
        # This assumes Music Assistant is running on localhost:8095
        from music_assistant import MusicAssistantClient

        music_assistant = MusicAssistantClient(
            host="localhost",
            port=8095
        )
        hass.data["music_assistant_api"] = music_assistant

    # Create media_player entities for each zone
    entities = []

    # Get zones from Music Assistant (adjust to match your API)
    zones = await music_assistant.get_zones()

    for zone in zones:
        entity = MusicAssistantMediaPlayer(hass, music_assistant, zone)
        entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class MusicAssistantMediaPlayer(MediaPlayerEntity):
    """Music Assistant media player entity."""

    _attr_device_class = "speaker"
    _attr_icon = "mdi:music"

    def __init__(self, hass: HomeAssistant, api, zone):
        """Initialize the media player."""
        self.hass = hass
        self._api = api
        self._zone = zone

        self._attr_unique_id = f"music_assistant_{zone.id}"
        self._attr_name = f"Music Assistant {zone.name}"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {("music_assistant", self._zone.id)},
            "name": self._attr_name,
            "manufacturer": "Music Assistant",
            "model": "Media Provider",
        }

    @property
    def state(self) -> MediaPlayerState | None:
        """Return current playback state."""
        zone_state = self._api.get_zone_state(self._zone.id)

        if not zone_state:
            return MediaPlayerState.OFF

        if zone_state.is_playing:
            return MediaPlayerState.PLAYING
        elif zone_state.is_paused:
            return MediaPlayerState.PAUSED
        else:
            return MediaPlayerState.IDLE

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return supported features."""
        return (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.SHUFFLE_SET
            | MediaPlayerEntityFeature.REPEAT_SET
        )

    @property
    def volume_level(self) -> float | None:
        """Return volume level."""
        zone_state = self._api.get_zone_state(self._zone.id)
        if not zone_state:
            return None
        return zone_state.volume_level / 100.0

    @property
    def is_volume_muted(self) -> bool:
        """Return whether volume is muted."""
        zone_state = self._api.get_zone_state(self._zone.id)
        if not zone_state:
            return False
        return zone_state.is_muted

    @property
    def media_title(self) -> str | None:
        """Return title of current track."""
        zone_state = self._api.get_zone_state(self._zone.id)
        if not zone_state or not zone_state.current_track:
            return None
        return zone_state.current_track.title

    @property
    def media_artist(self) -> str | None:
        """Return artist of current track."""
        zone_state = self._api.get_zone_state(self._zone.id)
        if not zone_state or not zone_state.current_track:
            return None
        return zone_state.current_track.artist

    @property
    def source(self) -> str | None:
        """Return current source."""
        zone_state = self._api.get_zone_state(self._zone.id)
        if not zone_state:
            return None
        return zone_state.current_source

    @property
    def source_list(self) -> list[str] | None:
        """Return list of available sources."""
        # Get all configured music providers
        return self._api.get_available_sources()

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs
    ) -> None:
        """Play media."""
        await self._api.play_media(
            zone_id=self._zone.id,
            media_type=media_type,
            media_id=media_id
        )

    async def async_media_play(self) -> None:
        """Play."""
        await self._api.play(self._zone.id)

    async def async_media_pause(self) -> None:
        """Pause."""
        await self._api.pause(self._zone.id)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        await self._api.set_volume(
            zone_id=self._zone.id,
            volume=int(volume * 100)
        )

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute/unmute."""
        await self._api.set_muted(self._zone.id, mute)

    async def async_select_source(self, source: str) -> None:
        """Select source."""
        await self._api.select_source(self._zone.id, source)

    async def async_update(self) -> None:
        """Update entity state."""
        # This is called periodically to refresh state
        # Adjust based on your Music Assistant API
        pass
```

### File 3: `addon_root/manifest.json`

```json
{
  "name": "Music Assistant",
  "version": "1.0.0",
  "slug": "music_assistant",
  "description": "Music aggregator and playback controller",
  "url": "https://music-assistant.io/",
  "codeowners": ["@yourname"],
  "config": {},
  "documentation": "https://music-assistant.io/",
  "requirements": [
    "homeassistant>=2024.1.0"
  ],
  "services": {},
  "ports": {
    "8095/tcp": 8095
  },
  "ports_description": {
    "8095/tcp": "Music Assistant Web Interface"
  },
  "image": "ghcr.io/music-assistant/server:{arch}",
  "build": {},
  "options": {},
  "schema": {}
}
```

### Verify fix worked:

```bash
ssh root@haboxhill.local

# Restart addon to load new code
ha addon restart music_assistant

# Wait 10 seconds
sleep 10

# Check HA logs for entity registration
ha core logs | grep -i "music_assistant" | tail -20

# Verify entities now exist
ha core state | grep media_player | grep -i music

# Should now return media_player entities
```

**If entities now appear**: Proceed to PHASE 2 below
**If entities still missing**: Check addon logs for Python errors

---

## PHASE 2: CONFIGURE ALEXA INTEGRATION (10 minutes)

### Step 1: Enable Alexa Entity Management

**Via Home Assistant UI** (easiest):

1. Go to **Settings** → **Devices & Services**
2. Look for **Cloud** section (usually in list)
3. Click on **Cloud**
4. Find **Alexa Smart Home** configuration
5. Click **Manage Entities**
6. Search for "music_assistant"
7. Toggle **ON** for each entity (should see green toggle)
8. Edit friendly name to something clear: "Music Library" or "Living Room Speaker"
9. Click **Update** or **Save**

**Expected result**:
- Blue checkmark next to Music Assistant entities
- Friendly names set appropriately

### Step 2: Verify Configuration Saved

```bash
ssh root@haboxhill.local

# Check HA Cloud Alexa config
ha addon logs cloud | grep -i "music_assistant" | tail -5

# Restart HA Cloud addon to sync
ha addon restart cloud

# Wait 15 seconds for sync
sleep 15

# Check sync status
ha addon logs cloud | grep -i "sync\|entity" | tail -10
```

### Step 3: Verify in HA Developer Tools

1. Go to **Developer Tools** → **States**
2. Search for `media_player.music_assistant`
3. Should see entity in list with current state

**Example state**:
```
entity_id: media_player.music_assistant_main
state: idle
last_changed: 2025-10-27T17:30:00+00:00
last_updated: 2025-10-27T17:30:00+00:00
attributes:
  friendly_name: Music Library
  icon: mdi:music
  supported_features: 149463
  device_class: speaker
  source: null
  source_list: [Apple Music, Spotify, Local Library]
  volume_level: 0.7
  is_volume_muted: false
  media_title: null
  media_artist: null
```

**If state looks good**: Proceed to PHASE 3
**If state missing/empty**: Addon not running properly - check logs

---

## PHASE 3: TEST DIRECT SERVICE CALLS (10 minutes)

### Step 1: Test Play

**Via Developer Tools → Services**:

1. Service: `media_player.media_play`
2. Entity: `media_player.music_assistant_main`
3. Click **Call Service**

**Expected**:
- Entity state changes to "playing"
- Music actually plays in Music Assistant
- No errors in logs

### Step 2: Test Pause

```
Service: media_player.media_pause
Entity: media_player.music_assistant_main
```

**Expected**: State changes to "paused", music stops

### Step 3: Test Volume

```
Service: media_player.set_volume_level
Entity: media_player.music_assistant_main
Data: { "volume_level": 0.5 }
```

**Expected**: Volume changes to 50%, Music Assistant responds

### Step 4: Test Play Media (if supported)

```
Service: media_player.play_media
Entity: media_player.music_assistant_main
Data: {
  "media_content_type": "artist",
  "media_content_id": "Taylor Swift"
}
```

**Expected**: Music Assistant searches for Taylor Swift, starts playing

**Summary**:
- [ ] Play works
- [ ] Pause works
- [ ] Volume control works
- [ ] Play media works

If all pass: **Proceed to PHASE 4**
If any fail: Check Music Assistant addon logs for service call handling

---

## PHASE 4: TEST ALEXA DISCOVERY (10 minutes)

### Step 1: Trigger Discovery

**Via Alexa App** (easiest):
1. Open Alexa app on phone
2. Devices → + button
3. "Add Device" or "Discover Devices"
4. Wait 60 seconds

**Alternative - Voice Command**:
```
"Alexa, discover devices"
```

### Step 2: Verify Discovery

Look for:
- "Music Library" (or your friendly_name) in device list
- Shows as "Music System" or "Speaker"
- No error badges

### Step 3: Troubleshoot If Not Found

```bash
ssh root@haboxhill.local

# Check HA Cloud Alexa sync
ha addon logs cloud | grep -i "sync" | tail -10

# Restart HA Cloud
ha addon restart cloud

# Wait 20 seconds
sleep 20

# Check again
ha addon logs cloud | tail -20
```

**If still not discovering**:
- Verify entity friendly_name is set in Alexa config (Step 2 of PHASE 2)
- Check HA Cloud subscription is active
- Try "Alexa, discover devices" voice command again

**If discovery works**: Proceed to PHASE 5

---

## PHASE 5: TEST VOICE COMMANDS (10 minutes)

### Test 1: Basic Playback

```bash
"Alexa, play on Music Library"
# Expected: "OK, playing Music Library" + playback starts
# Verify: Music Assistant actually plays, state changes to "playing"

sleep 3

"Alexa, pause Music Library"
# Expected: Music pauses
# Verify: State changes to "paused", Music Assistant pauses

sleep 3

"Alexa, play on Music Library"
# Expected: Resumes playback
```

### Test 2: Volume Control

```bash
"Alexa, set volume 50 percent on Music Library"
# Expected: Volume changes to 50%
# Verify: Entity volume_level is 0.5

"Alexa, increase volume on Music Library"
# Expected: Volume increases

"Alexa, decrease volume on Music Library"
# Expected: Volume decreases
```

### Test 3: Media Search (if Music Assistant supports it)

```bash
"Alexa, play Taylor Swift on Music Library"
# Expected: Searches for Taylor Swift, starts playing
# Verify: Music Assistant is playing Taylor Swift content

"Alexa, play the Eagles on Music Library"
# Expected: Plays Eagles content

"Alexa, play my chill playlist on Music Library"
# Expected: Plays specified playlist
```

### Test 4: Multi-Zone (if applicable)

```bash
"Alexa, play in the living room"
# If you have multiple zones configured

"Alexa, pause in the bedroom"
```

### Success Checklist

- [ ] "Alexa, play on Music Library" → Works within 2 seconds
- [ ] "Alexa, pause Music Library" → Works within 2 seconds
- [ ] "Alexa, set volume 50 percent" → Works within 2 seconds
- [ ] "Alexa, play [artist name]" → Works (if supported)
- [ ] Music Assistant state updates correctly
- [ ] No errors in Music Assistant logs
- [ ] No errors in HA logs
- [ ] Alexa understands commands (no "I'm not sure what you said")

**If all tests pass**: Integration is working! Go to CLEANUP below

**If tests fail**:
- Check HA logs: `ha core logs | tail -50 | grep -i alexa`
- Check Music Assistant logs: `ha addon logs music_assistant | tail -50`
- Verify entity state updates: Developer Tools → States

---

## CLEANUP: Remove Custom OAuth

Once Alexa integration is working, remove old custom OAuth code:

```bash
ssh root@haboxhill.local

# 1. Stop OAuth server (if running)
pkill -f oauth_server.py
# or if systemd service:
systemctl stop oauth-server 2>/dev/null

# 2. Delete OAuth files
rm -f /config/oauth_server.py
rm -f /config/oauth_clients.json
rm -f /config/start_oauth_server.py
rm -f /config/alexa_oauth_endpoints.py

# 3. Disable Tailscale Funnel (if configured)
tailscale funnel --off 2>/dev/null
tailscale serve --off 2>/dev/null

# 4. Verify no port 8096 listening
netstat -an | grep 8096
# Should return empty (no output)

# 5. Remove from port forwarding rules
# (If you configured port 8096 in nginx/reverse-proxy)

# 6. Document removal in Music Assistant addon
# Remove any startup scripts that run OAuth server
```

### Verify Cleanup

```bash
# No port 8096 listening
netstat -an | grep 8096
# (empty result)

# No OAuth process running
ps aux | grep oauth_server
# (should only show this grep command)

# HA logs show no OAuth errors
ha core logs | grep -i oauth
# (should be empty or show only old logs)

# Alexa still works (wasn't using OAuth server)
"Alexa, play on Music Library"
# Still works! (HA Cloud OAuth is being used, not custom)
```

---

## VALIDATION CHECKLIST (Final)

Before considering implementation complete:

- [ ] Music Assistant entities visible in HA entity registry
- [ ] Entities have correct attributes (supported_features, volume_level, etc.)
- [ ] Direct service calls work (play/pause/volume via Developer Tools)
- [ ] Alexa discovers Music Assistant device
- [ ] Voice command "Alexa, play on Music Library" works
- [ ] Voice command "Alexa, pause" works
- [ ] Voice command "Alexa, set volume" works
- [ ] Music Assistant actually plays audio on commands
- [ ] All commands complete within 2 seconds
- [ ] No errors in HA logs related to Alexa/Music Assistant
- [ ] No errors in Music Assistant addon logs
- [ ] Custom OAuth server (port 8096) is removed
- [ ] Tailscale Funnel is disabled
- [ ] HA Cloud Alexa is handling authentication (not custom OAuth)

---

## ROLLBACK PROCEDURE (If Something Breaks)

```bash
ssh root@haboxhill.local

# 1. Disable Alexa integration temporarily
# Settings → Devices & Services → Cloud → Disable Alexa

# 2. Restart HA to clear state
ha core restart

# 3. Wait 30 seconds
sleep 30

# 4. Restart Music Assistant addon
ha addon restart music_assistant

# 5. Check logs
ha addon logs music_assistant | tail -20
ha core logs | tail -20

# 6. Try again or revert addon code changes

# 7. Re-enable Alexa when ready
# Settings → Devices & Services → Cloud → Enable Alexa
```

---

## SUPPORT

If you encounter issues:

1. **Check logs first**:
   ```bash
   ha addon logs music_assistant | tail -50
   ha core logs | tail -50 | grep -i "alexa\|music_assistant"
   ```

2. **Verify entity state**:
   - Developer Tools → States → search "media_player"

3. **Test service calls directly**:
   - Developer Tools → Services → media_player.media_play

4. **Check Alexa app**:
   - Devices section → Look for Music Assistant
   - Check entity friendly_name matches

5. **Restart if stuck**:
   ```bash
   ha addon restart music_assistant
   ha core restart
   ha addon restart cloud
   ```

---

**START HERE**: Run `ha core state | grep media_player | grep music` on haboxhill.local

- **If entities appear** → Skip PHASE 1, go to PHASE 2
- **If entities missing** → Do PHASE 1 addon integration fix

**TOTAL TIME**: 60 minutes (including testing)
**COMPLEXITY**: Medium
**RISK**: Low (non-destructive, fully rollbackable)
