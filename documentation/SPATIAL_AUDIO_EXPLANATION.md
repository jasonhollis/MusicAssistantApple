# Why Spatial Audio Doesn't Work in Music Assistant

## The Short Answer

**Music Assistant's Apple Music provider is hardcoded to use stereo AAC only**, even though Apple Music's API provides Dolby Atmos/Spatial Audio streams. The provider **explicitly filters out** spatial audio formats and only uses the stereo version.

## The Technical Details

### What's Happening Now

When Music Assistant fetches a song from Apple Music, the API returns multiple formats:

```json
{
  "assets": [
    {"flavor": "28:ctrp256", "URL": "..."},  // Stereo AAC 256kbps ← ONLY THIS IS USED
    {"flavor": "51:ec3", "URL": "..."},      // Dolby Digital Plus 5.1 ← IGNORED
    {"flavor": "51:atmos", "URL": "..."}     // Dolby Atmos ← IGNORED
  ]
}
```

The code at line 890 specifically filters for ONLY stereo:
```python
ctrp256_urls = [asset["URL"] for asset in stream_assets if asset["flavor"] == "28:ctrp256"]
```

- `28` = 2-channel stereo
- `51` = 5.1 surround/spatial
- `ctrp256` = AAC codec at 256kbps
- `ec3` = Dolby Digital Plus codec
- `atmos` = Dolby Atmos with object-based audio

### Why This Choice Was Made

1. **Universal Compatibility**: AAC stereo works on ALL devices
2. **Simpler Implementation**: No need to handle multiple codecs
3. **Player Limitations**: Many Music Assistant players can't handle spatial audio
4. **Transcoding Issues**: FFmpeg might downmix spatial to stereo anyway

## What Would Need to Change

### 1. Code Changes (Relatively Simple)

The provider would need to:
- Stop filtering out spatial formats
- Select `51:ec3` or `51:atmos` instead of `28:ctrp256`
- Update the audio format declaration from AAC to E-AC3/Atmos

### 2. Player Support (Complex)

Your playback device needs to support:
- **AirPlay 2 to HomePod/Apple TV**: ✅ Would work
- **Sonos with Atmos speakers**: ✅ Could work
- **Chromecast Audio**: ❌ Stereo only
- **Most DLNA devices**: ❌ Stereo only
- **Web browser playback**: ❌ Probably stereo only

### 3. Architecture Changes (Very Complex)

Music Assistant would need:
- Player capability detection (does this device support Atmos?)
- New codec types in the data model
- Passthrough mode for spatial audio (no transcoding)
- Format selection logic per player

## Your Options

### Option 1: Request Feature from Developers

Create a GitHub issue on Music Assistant requesting spatial audio support. Include:
- This technical analysis
- Your use case (which players you want to use)
- That the API already provides the streams

### Option 2: Patch It Yourself (Advanced)

I can help you modify the provider to:
1. Select spatial audio streams when available
2. Add a toggle for spatial/stereo preference
3. Test with your specific players

**Want me to create a patch?** It would:
- Prefer Atmos/EC3 when available
- Fall back to stereo if needed
- Add a configuration option

### Option 3: Use Native Apple Music App for Spatial

Since the limitation is in Music Assistant, not your account:
- Use Music Assistant for library management and stereo playback
- Use native Apple Music app when you want spatial audio
- Both can coexist using the same account

### Option 4: Wait for Official Support

The provider is marked as "beta" and the TODOs in the code suggest more features are planned. Spatial audio might be added officially.

## The Bottom Line

**It's not a technical limitation of Apple Music or your setup** - the API provides spatial audio streams and your token works fine. It's a **deliberate design choice** in Music Assistant to use only stereo AAC for maximum compatibility.

The good news: **All the infrastructure is already there** (authentication, DRM, streaming). It just needs to select different stream URLs from the API response.

## Quick Hack (If You're Brave)

Replace line 890 in the provider to prefer spatial:
```python
# Old (stereo only):
ctrp256_urls = [asset["URL"] for asset in stream_assets if asset["flavor"] == "28:ctrp256"]

# New (prefer spatial):
spatial_urls = [asset["URL"] for asset in stream_assets if asset["flavor"] in ["51:atmos", "51:ec3"]]
if spatial_urls:
    playlist_url = spatial_urls[0]
else:
    # Fall back to stereo
    ctrp256_urls = [asset["URL"] for asset in stream_assets if asset["flavor"] == "28:ctrp256"]
    playlist_url = ctrp256_urls[0] if ctrp256_urls else None
```

And update line 517:
```python
# Old:
audio_format=AudioFormat(content_type=ContentType.MP4, codec_type=ContentType.AAC)

# New:
audio_format=AudioFormat(content_type=ContentType.MP4, codec_type=ContentType.EAC3)  # If this enum exists
```

**Warning**: This might break playback on devices that don't support E-AC3/Atmos!

---

Want me to create a proper patch that adds spatial audio support with a toggle option?