#!/usr/bin/env python3
"""Quick fix for Apple Music playlist sync - fixes the 404 handler bug"""

print("🎵 Applying Apple Music Playlist Fix...")

# Read the file
filepath = "/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py"
with open(filepath, 'r') as f:
    content = f.read()

# Find and fix the buggy 404 handler
old_code = '''        if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
            return {}'''

new_code = '''        if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
            # Only return empty for pagination beyond first page
            if kwargs.get("offset", 0) > 0:
                return {}
            # For first page (offset=0), this is a real error'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, 'w') as f:
        f.write(content)
    print("✅ Fixed the 404 handler bug!")
    print("✅ Playlists should now sync properly")
else:
    print("⚠️ Bug not found or already fixed")

print("\nRestart Music Assistant to apply the fix!")