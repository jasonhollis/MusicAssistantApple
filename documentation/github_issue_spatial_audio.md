# GitHub Issue: Apple Music Provider Should Support Spatial Audio (Dolby Atmos)

## Issue Title
**[Feature Request] Apple Music: Add Dolby Atmos / Spatial Audio Support**

## Issue Body

### Is your feature request related to a problem?

Currently, the Apple Music provider in Music Assistant only uses stereo AAC streams, even though Apple Music's API provides Dolby Atmos and Dolby Digital Plus 5.1 streams. This means users with Atmos-capable equipment (HomePods, Sonos Arc, Apple TV, etc.) cannot enjoy spatial audio through Music Assistant.

### Describe the solution you'd like

The Apple Music provider should:
1. Detect and use Dolby Atmos (`51:atmos`) and Dolby Digital Plus (`51:ec3`) streams when available
2. Allow users to toggle between spatial and stereo preferences
3. Automatically fall back to stereo for incompatible devices

### Technical Details

**Current Implementation (Line 890 in `__init__.py`):**
```python
ctrp256_urls = [asset["URL"] for asset in stream_assets if asset["flavor"] == "28:ctrp256"]
```
This explicitly filters for ONLY stereo streams (`28:` prefix = 2-channel).

**Apple's API Response Contains:**
```json
{
  "assets": [
    {"flavor": "28:ctrp256", "URL": "..."},  // Stereo AAC - Currently used
    {"flavor": "51:ec3", "URL": "..."},      // Dolby Digital Plus 5.1 - Ignored
    {"flavor": "51:atmos", "URL": "..."}     // Dolby Atmos - Ignored
  ]
}
```

**Proposed Implementation:**
```python
# Build priority list based on user preference
flavor_priority = ["51:atmos", "51:ec3", "28:ctrp256"] if prefer_spatial else ["28:ctrp256"]

# Select first available format
for flavor in flavor_priority:
    matching = [a["URL"] for a in stream_assets if a["flavor"] == flavor]
    if matching:
        selected_url = matching[0]
        break
```

### Additional Context

- The DRM/Widevine decryption already works for spatial streams (same process)
- Many users have HomePods and other Atmos-capable devices via AirPlay 2
- Apple Music heavily promotes spatial audio as a key feature
- The API already provides these streams - we just need to select them

### Devices That Would Benefit

- HomePod / HomePod mini (via AirPlay 2)
- Apple TV 4K (via AirPlay 2)
- Sonos Arc, Beam, Era 300 (with Atmos support)
- Any device supporting E-AC-3 passthrough

### Proof of Concept

I've successfully patched my local instance to prefer spatial audio streams, and it works perfectly with HomePods. The change is minimal - just selecting different URLs from the API response.

### Suggested Configuration

Add two new config options:
```python
ConfigEntry(
    key="prefer_spatial_audio",
    type=ConfigEntryType.BOOLEAN,
    label="Enable Spatial Audio (Dolby Atmos)",
    description="Use Dolby Atmos/5.1 when available",
    default_value=True
)
```

### References

- Apple Music Web API returns multiple stream formats
- Flavor codes: `28:` = stereo, `51:` = surround/spatial
- No changes needed to authentication or DRM handling

---

**Labels to add:** `enhancement`, `provider:apple_music`, `audio-quality`

**Related issues:** None found

**Testing:** Happy to test any implementation with my HomePods and provide logs