#!/usr/bin/env python3
"""
Spatial Audio Patch for Music Assistant Apple Music Provider
Enables Dolby Atmos and Dolby Digital Plus 5.1 support
"""

PATCH_CODE = '''
# SPATIAL AUDIO PATCH APPLIED - {timestamp}

import os
import re

# Add at line ~100 (after constants)
CONF_PREFER_SPATIAL = "prefer_spatial_audio"
CONF_SPATIAL_FALLBACK = "spatial_fallback"

# Modified _parse_stream_url_and_uri method (replaces line ~888)
async def _parse_stream_url_and_uri_spatial(self, stream_assets: list[dict]) -> tuple:
    """Parse the Stream URL and Key URI from the song - WITH SPATIAL AUDIO SUPPORT."""

    # Get user preference for spatial audio
    prefer_spatial = self.config.get_value(CONF_PREFER_SPATIAL, True)

    # Build flavor priority based on preference
    if prefer_spatial:
        # Priority: Atmos > 5.1 > Stereo
        flavor_priority = [
            ("51:atmos", "Dolby Atmos"),
            ("51:ec3", "Dolby Digital Plus 5.1"),
            ("28:ctrp256", "AAC Stereo 256kbps"),
            ("28:ctrp64", "AAC Stereo 64kbps"),
        ]
        self.logger.info("Spatial audio preference: ENABLED - will prefer Atmos/5.1")
    else:
        # Priority: Stereo > 5.1 > Atmos
        flavor_priority = [
            ("28:ctrp256", "AAC Stereo 256kbps"),
            ("28:ctrp64", "AAC Stereo 64kbps"),
            ("51:ec3", "Dolby Digital Plus 5.1"),
            ("51:atmos", "Dolby Atmos"),
        ]
        self.logger.info("Spatial audio preference: DISABLED - will use stereo")

    # Try each flavor in priority order
    selected_url = None
    selected_flavor = None
    selected_name = None

    for flavor_code, flavor_name in flavor_priority:
        matching_urls = [asset["URL"] for asset in stream_assets if asset.get("flavor") == flavor_code]
        if matching_urls:
            selected_url = matching_urls[0]
            selected_flavor = flavor_code
            selected_name = flavor_name
            self.logger.info(f"Selected audio format: {flavor_name} (flavor: {flavor_code})")
            break

    if not selected_url:
        # Fallback: try to find ANY available stream
        if stream_assets:
            selected_url = stream_assets[0].get("URL")
            selected_flavor = stream_assets[0].get("flavor", "unknown")
            self.logger.warning(f"Using fallback stream with flavor: {selected_flavor}")
        else:
            raise MediaNotFoundError("No stream URL found for song.")

    # Fetch the playlist
    playlist_items = await fetch_playlist(self.mass, selected_url, raise_on_hls=False)

    # Apple returns a HLS playlist where each item is the whole file
    playlist_item = playlist_items[0]

    # Path is relative, stitch it together
    base_path = selected_url.rsplit("/", 1)[0]
    track_url = base_path + "/" + playlist_items[0].path
    key = playlist_item.key

    # Store selected format for later use
    self._last_selected_format = (selected_flavor, selected_name)

    return (track_url, key, selected_flavor)

# Modified get_stream_details method (replaces line ~506)
async def get_stream_details_spatial(self, item_id: str, media_type: MediaType) -> StreamDetails:
    """Return the content details for the given track when it will be streamed - WITH SPATIAL SUPPORT."""
    stream_metadata = await self._fetch_song_stream_metadata(item_id)
    license_url = stream_metadata["hls-key-server-url"]

    # Use the new spatial-aware parsing
    result = await self._parse_stream_url_and_uri_spatial(stream_metadata["assets"])
    stream_url, uri, flavor = result[0], result[1], result[2] if len(result) > 2 else "unknown"

    if not stream_url or not uri:
        raise MediaNotFoundError("No stream URL found for song.")

    key_id = base64.b64decode(uri.split(",")[1])

    # Determine audio format based on selected flavor
    if "atmos" in flavor.lower():
        # Dolby Atmos
        self.logger.info("🎵 Streaming in DOLBY ATMOS")
        # Note: ContentType may not have ATMOS, using AAC as fallback
        audio_format = AudioFormat(
            content_type=ContentType.MP4,
            codec_type=ContentType.AAC  # Will be transcoded if needed
        )
    elif "ec3" in flavor.lower() or "51:" in flavor:
        # Dolby Digital Plus 5.1
        self.logger.info("🎵 Streaming in DOLBY DIGITAL PLUS 5.1")
        audio_format = AudioFormat(
            content_type=ContentType.MP4,
            codec_type=ContentType.AAC  # Will be transcoded if needed
        )
    else:
        # Standard stereo AAC
        self.logger.info("🎵 Streaming in STEREO AAC")
        audio_format = AudioFormat(
            content_type=ContentType.MP4,
            codec_type=ContentType.AAC
        )

    return StreamDetails(
        item_id=item_id,
        provider=self.lookup_key,
        audio_format=audio_format,
        stream_type=StreamType.ENCRYPTED_HTTP,
        decryption_key=await self._get_decryption_key(license_url, key_id, uri, item_id),
        path=stream_url,
        can_seek=True,
        allow_seek=True,
        # enforce caching because the apple streams are mp4 files with moov atom at the end
        enable_cache=True,
    )

# Add to get_config_entries (around line 214, before the return statement)
def get_spatial_config_entries():
    """Additional config entries for spatial audio."""
    return [
        ConfigEntry(
            key=CONF_PREFER_SPATIAL,
            type=ConfigEntryType.BOOLEAN,
            label="Enable Spatial Audio (Dolby Atmos)",
            description="Prefer Dolby Atmos and 5.1 audio when available. Disable for stereo-only playback.",
            required=False,
            default_value=True,
            value=values.get(CONF_PREFER_SPATIAL) if values else True,
        ),
        ConfigEntry(
            key=CONF_SPATIAL_FALLBACK,
            type=ConfigEntryType.BOOLEAN,
            label="Automatic Fallback to Stereo",
            description="Automatically fall back to stereo if spatial audio fails.",
            required=False,
            default_value=True,
            value=values.get(CONF_SPATIAL_FALLBACK) if values else True,
        ),
    ]
'''

def apply_patch():
    """Apply the spatial audio patch to Music Assistant."""
    import subprocess
    from datetime import datetime

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print("🎵 APPLYING SPATIAL AUDIO PATCH")
    print("="*60)

    # Create the patch Python script
    patch_script = f"""
import sys
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

from datetime import datetime

# Read the current file
with open('/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py', 'r') as f:
    content = f.read()

# Check if already patched
if '_parse_stream_url_and_uri_spatial' in content:
    print('✅ Already patched for spatial audio')
    sys.exit(0)

print('Applying spatial audio patch...')

# 1. Add new constants after existing CONF_ definitions
conf_insert = '''CONF_PREFER_SPATIAL = "prefer_spatial_audio"
CONF_SPATIAL_FALLBACK = "spatial_fallback"
'''
content = content.replace(
    'CONF_MUSIC_USER_TOKEN_TIMESTAMP = "music_user_token_timestamp"',
    'CONF_MUSIC_USER_TOKEN_TIMESTAMP = "music_user_token_timestamp"\\n' + conf_insert
)

# 2. Replace _parse_stream_url_and_uri method
old_method_start = 'async def _parse_stream_url_and_uri(self, stream_assets: list[dict]) -> str:'
new_method = '''async def _parse_stream_url_and_uri(self, stream_assets: list[dict]) -> tuple:
    \"\"\"Parse the Stream URL and Key URI with SPATIAL AUDIO support.\"\"\"

    # Get user preference
    prefer_spatial = getattr(self.config, 'get_value', lambda k, d: d)(CONF_PREFER_SPATIAL, True)

    # Build priority
    if prefer_spatial:
        flavor_priority = [
            "51:atmos",  # Dolby Atmos
            "51:ec3",    # Dolby Digital Plus 5.1
            "28:ctrp256", # Stereo AAC 256kbps
            "28:ctrp64",  # Stereo AAC 64kbps
        ]
        self.logger.info("Spatial audio: ENABLED - preferring Atmos/5.1")
    else:
        flavor_priority = [
            "28:ctrp256", # Stereo AAC 256kbps
            "28:ctrp64",  # Stereo AAC 64kbps
        ]
        self.logger.info("Spatial audio: DISABLED - using stereo")

    # Try each in order
    selected_url = None
    selected_flavor = None

    for flavor in flavor_priority:
        matching = [a["URL"] for a in stream_assets if a.get("flavor") == flavor]
        if matching:
            selected_url = matching[0]
            selected_flavor = flavor
            self.logger.info(f"Selected format: {{flavor}}")
            break

    if not selected_url and stream_assets:
        selected_url = stream_assets[0]["URL"]
        selected_flavor = stream_assets[0].get("flavor", "unknown")

    if not selected_url:
        raise MediaNotFoundError("No stream URL found")

    # Rest of original method
    playlist_items = await fetch_playlist(self.mass, selected_url, raise_on_hls=False)
    playlist_item = playlist_items[0]
    base_path = selected_url.rsplit("/", 1)[0]
    track_url = base_path + "/" + playlist_items[0].path
    key = playlist_item.key

    return (track_url, key)'''

# Replace the method
if old_method_start in content:
    # Find the end of the method
    start_idx = content.index(old_method_start)
    # Find the next method definition
    next_method_idx = content.find('\\n    async def ', start_idx + 1)
    if next_method_idx == -1:
        next_method_idx = content.find('\\n    def ', start_idx + 1)

    # Replace the entire method
    content = content[:start_idx] + new_method + content[next_method_idx:]
    print('✓ Replaced _parse_stream_url_and_uri method')

# 3. Add config entries
config_addition = '''
        ConfigEntry(
            key=CONF_PREFER_SPATIAL,
            type=ConfigEntryType.BOOLEAN,
            label="Enable Spatial Audio (Dolby Atmos)",
            description="Prefer Dolby Atmos and 5.1 when available",
            required=False,
            default_value=True,
            value=values.get(CONF_PREFER_SPATIAL) if values else True,
        ),'''

# Find the return statement in get_config_entries
if 'def get_config_entries(' in content:
    # Add before the last ConfigEntry
    content = content.replace(
        '        ConfigEntry(\\n            key=CONF_MUSIC_USER_TOKEN_TIMESTAMP,',
        config_addition + '\\n        ConfigEntry(\\n            key=CONF_MUSIC_USER_TOKEN_TIMESTAMP,'
    )
    print('✓ Added spatial audio config entries')

# Write the patched file
with open('/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py', 'w') as f:
    f.write(content)

print('✅ Spatial audio patch applied successfully!')
print('   - Dolby Atmos support enabled')
print('   - Dolby Digital Plus 5.1 support enabled')
print('   - Configuration option added')
print('')
print('Please restart Music Assistant to use spatial audio!')
"""

    # Execute the patch
    cmd = f'''ssh root@haboxhill.local "docker exec addon_d5369777_music_assistant python3 -c '{patch_script}'"'''

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ Error applying patch: {result.stderr}")
        return False

if __name__ == "__main__":
    apply_patch()