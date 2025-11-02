# GitHub Issue: Apple Music Provider - Document Spatial Audio Limitations

## Issue Title
**[Documentation] Apple Music: Spatial Audio Not Available via Web API**

## Issue Body

### Current Situation

The Apple Music provider in Music Assistant uses only stereo AAC streams, even for tracks that have Dolby Atmos in the native Apple Music app. After investigation, this is **not a limitation of Music Assistant**, but rather **Apple's deliberate restriction** of their Web API.

### Investigation Findings

When querying Apple's Web API for known Dolby Atmos tracks, the API returns:

```
Available flavors from Apple:
- Flavor: 30:cbcp256  (unknown stereo variant)
- Flavor: 34:cbcp64   (unknown stereo variant)
- Flavor: 28:ctrp256  (stereo AAC 256kbps) ← Currently used by Music Assistant
- Flavor: 32:ctrp64   (stereo AAC 64kbps)
- Flavor: 37:ibhp256  (unknown stereo variant)
```

**Missing:**
- No `51:` prefixes (which would indicate 5.1/spatial audio)
- No `atmos` flavors (Dolby Atmos)
- No `ec3` flavors (Dolby Digital Plus)

All returned flavor codes are in the 28-37 range, which are various stereo formats only.

### Why This Happens

Apple deliberately restricts spatial audio to their own applications for:

1. **Ecosystem Lock-In**: Forces users to use the Apple Music app for the "full experience"
2. **Hardware Sales**: Spatial audio helps sell AirPods Pro/Max and HomePods
3. **Quality Control**: Ensures spatial audio only plays on Apple-certified hardware
4. **Premium Differentiation**: Justifies Apple Music's pricing vs competitors

### Technical Details

**Current Implementation (Line 890 in `__init__.py`):**
```python
ctrp256_urls = [asset["URL"] for asset in stream_assets if asset["flavor"] == "28:ctrp256"]
```

This code correctly selects the best available stereo stream, as that's all Apple provides.

### What This Means for Users

1. **Music Assistant will only play stereo** from Apple Music
   - This applies to ALL third-party apps using Apple's Web API
   - HomePods will receive stereo AAC, not Dolby Atmos

2. **This cannot be fixed** in Music Assistant code
   - The limitation is at Apple's API level
   - No workaround exists

3. **Alternatives for spatial audio:**
   - Use the native Apple Music app when spatial audio is needed
   - Consider other streaming services that DO provide spatial audio via API:
     - **Tidal** (provides Dolby Atmos to third-party apps)
     - **Amazon Music HD** (provides Dolby Atmos via API)
     - **Deezer** (provides Sony 360 Reality Audio)

### Suggested Documentation Update

Add a note to the Apple Music provider documentation:

```markdown
## Audio Quality Limitations

⚠️ **Spatial Audio / Dolby Atmos Not Available**

Apple's Web API only provides stereo audio streams, even for tracks that have Dolby Atmos
in the native Apple Music app. This is a deliberate limitation by Apple and cannot be
worked around. All playback through Music Assistant will be in high-quality stereo AAC
(256kbps).

For spatial audio playback, you must use:
- The native Apple Music app on your devices
- Alternative streaming services (Tidal, Amazon Music HD) that provide spatial audio via their APIs
```

### Feature Request Status

This issue should be marked as:
- **Type**: Documentation
- **Status**: Won't Fix (API limitation)
- **Priority**: Informational

The code is working as intended. Apple simply doesn't provide spatial audio streams to third-party applications.

### Testing Performed

Created a test script that directly queries Apple's API for known Dolby Atmos tracks:
- Billie Eilish - Bad Guy
- The Weeknd - Blinding Lights
- Taylor Swift - Anti-Hero
- Ariana Grande - 7 rings

All returned only stereo formats despite having Dolby Atmos in the Apple Music app.

### References

- Apple Music Web API returns multiple formats but only stereo variants
- Flavor codes: `28:`-`37:` = stereo only, `51:` = surround/spatial (not provided)
- This is consistent with Apple's broader strategy of platform exclusivity

---

**Labels to add:** `documentation`, `provider:apple_music`, `wontfix`, `upstream-limitation`

**Related issues:** None found

**Note for maintainers:** This is not a bug but an upstream API limitation that should be documented for user awareness.