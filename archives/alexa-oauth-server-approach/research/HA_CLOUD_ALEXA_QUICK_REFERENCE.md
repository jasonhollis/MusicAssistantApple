# Home Assistant Cloud + Alexa - Quick Reference

**Date**: 2025-10-27
**Full Research**: See `HA_CLOUD_ALEXA_INTEGRATION_RESEARCH.md`

---

## Setup in 6 Steps

```bash
1. Settings > Home Assistant Cloud > Enable/Subscribe
2. Settings > Voice Assistants > Amazon Alexa > Enable
3. Settings > Voice Assistants > Amazon Alexa > Expose > Select entities
4. Alexa App > Skills > Search "Home Assistant" > Enable
5. Sign in with Nabu Casa credentials (NOT Amazon)
6. "Alexa, discover devices"
```

---

## Key Architecture Facts

**How Remote Access Works**:
```
Alexa → HA Cloud Relay (TCP/SNI routing) → Local HA
```
- No ports opened on your router
- All traffic encrypted (TLS)
- Relay operates at TCP level (doesn't decrypt)
- SNI header routes to correct instance

**OAuth Flow**:
```
1. User enables skill in Alexa app
2. Redirect to Nabu Casa login
3. User authenticates with Nabu Casa account
4. Authorization code returned
5. Alexa exchanges code for access token + refresh token
6. Alexa uses token for all requests (refreshes every ~60 min)
```

---

## Configuration Rules

### YAML vs UI

**CRITICAL**: YAML takes precedence. If any YAML filters exist, UI is disabled (grayed out).

**Choose ONE method**:

**UI Method** (simple):
```
Settings > Voice Assistants > Alexa > Expose > Toggle entities
```

**YAML Method** (advanced):
```yaml
# configuration.yaml
alexa:
  smart_home:
    filter:
      include_domains:
        - light
        - switch
      exclude_entities:
        - light.garage
```

### Filter Logic

- `include_domains`: Whitelist domains → excludes all others
- `exclude_domains`: Blacklist domains → includes all others
- `include_entities`: Whitelist specific entities
- `exclude_entities`: Blacklist specific entities
- Entity rules override domain rules

---

## Troubleshooting Quick Fixes

### "Alexa couldn't find any devices"

```bash
✓ Check: Settings > Voice Assistants > Alexa > Expose (any entities?)
✓ Check: Settings > Home Assistant Cloud > Status = "Connected"
✓ Check: Developer Tools > States (entities available/not "unavailable"?)
✓ Try: Restart HA Core
✓ Try: "Alexa, discover devices" (wait 30 seconds)
```

### "Unable to link account"

```bash
✓ Check: https://account.nabucasa.com (subscription active?)
✓ Try: Sign out/in Alexa app
✓ Try: Disable skill → Enable skill
✓ Try: Different browser (OAuth redirect issue)
```

### "Device not responding"

```bash
✓ Check: Settings > Home Assistant Cloud > Status = "Connected"
✓ Check: Developer Tools > States > {entity} (state valid?)
✓ Try: "Alexa, turn on {device}" (forces refresh)
✓ Check: Settings > System > Logs (filter "alexa")
```

### UI controls grayed out

```bash
Cause: YAML filters present in configuration.yaml

Solution A: Remove YAML filters
alexa:
  smart_home:
    # Delete filter section

Solution B: Manage all in YAML
(UI will remain disabled)
```

---

## Entity Discovery Details

**Supported Domains** (25+ types):
- light, switch, fan, cover, lock, climate
- media_player, vacuum, scene, script
- camera, sensor, binary_sensor, alarm_control_panel
- And more...

**Discovery Triggers**:
- Voice: "Alexa, discover devices"
- App: Devices > + > Add Device > Other > Discover
- Automatic: When skill first enabled

**Discovery Flow**:
```
1. Alexa sends Discovery.Discover directive
2. HA queries exposed entities (respects filters)
3. HA returns entity list with capabilities
4. Alexa updates device catalog
5. Devices appear in Alexa app
```

---

## Requirements

### Home Assistant Cloud

**Required**:
- HA version 2023.5+
- Nabu Casa subscription ($6.50/month)
- Internet connection

**NOT Required**:
- AWS account ❌
- SSL certificates ❌
- Port forwarding ❌
- Dynamic DNS ❌

### Manual Setup (Alternative)

**Required**:
- Amazon Developer account
- AWS account (Lambda in correct region!)
- Valid SSL certificate (Let's Encrypt OK)
- HA accessible on HTTPS:443
- **Regional match**: US → us-east-1, EU → eu-west-1

---

## Music Assistant + Alexa

**Status**: Experimental beta (October 2025)

**Requirements**:
- Docker (API bridge container)
- Reverse proxy (Nginx/Caddy)
- SSL certificates
- Custom Alexa skill (manual setup)

**Limitations**:
- Rate limiting (commands fail if used frequently)
- Unreliable state reporting
- No multi-room sync
- No advanced controls (shuffle/repeat)

**Recommendation**: Wait for stable release or use alternative (Chromecast, AirPlay)

---

## Common Misconceptions

### ❌ "I need to open ports on my router"
**✓ FALSE**: HA Cloud uses outbound connection to relay servers

### ❌ "I need AWS account for HA Cloud"
**✓ FALSE**: Only for manual setup without HA Cloud

### ❌ "I can mix YAML and UI configuration"
**✓ FALSE**: YAML overrides UI completely

### ❌ "Alexa stores my HA data"
**✓ FALSE**: Only device names/states cached temporarily

### ❌ "HA Cloud decrypts my traffic"
**✓ FALSE**: Relay operates at TCP level (SNI routing)

### ❌ "I can stream any audio to Alexa with Alexa Media Player"
**✓ FALSE**: Only TTS and preset media supported

---

## Quick Commands Reference

```bash
# Enable Alexa in HA
Settings > Voice Assistants > Amazon Alexa > Enable

# Expose entity
Settings > Voice Assistants > Alexa > Expose > Toggle {entity}

# Check HA Cloud status
Settings > Home Assistant Cloud > Status

# Validate YAML config
Developer Tools > YAML > Check Configuration

# View Alexa logs
Settings > System > Logs > Filter "alexa"

# Check entity state
Developer Tools > States > {entity_id}

# Restart HA Core
Settings > System > Restart

# Discover devices (voice)
"Alexa, discover devices"

# Test entity
"Alexa, turn on {device name}"
```

---

## URLs Reference

**Setup**:
- HA Cloud: https://www.nabucasa.com/config/amazon_alexa/
- Account: https://account.nabucasa.com

**Documentation**:
- Integration: https://www.home-assistant.io/integrations/alexa.smart_home/
- Auth API: https://developers.home-assistant.io/docs/auth_api/

**Music Assistant**:
- Alexa support: https://www.music-assistant.io/player-support/alexa/

**Community**:
- Forum: https://community.home-assistant.io/c/third-party/alexa

---

## Decision Matrix: HA Cloud vs Manual

| Factor | HA Cloud | Manual Setup |
|--------|----------|--------------|
| Cost | $6.50/month | Free (AWS free tier) |
| Setup time | 5 minutes | 1-2 hours |
| Complexity | Low | High |
| Maintenance | None | Certificates, Lambda |
| Port forwarding | Not needed | Not needed* |
| SSL certificates | Included | Self-managed |
| Updates | Automatic | Manual |
| Regional issues | Handled | Must configure |
| Support | Professional | Community |

*Lambda can reach HA via DuckDNS/Cloudflare tunnel

**Recommendation**: Use HA Cloud unless you need custom skill behavior or have privacy concerns about Nabu Casa (but note: data stays encrypted).

---

## Research Source

**Full Details**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/HA_CLOUD_ALEXA_INTEGRATION_RESEARCH.md`

**Research Date**: 2025-10-27
**Primary Sources**: Home Assistant, Nabu Casa, Music Assistant official docs
