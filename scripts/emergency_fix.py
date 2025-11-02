#!/usr/bin/env python3
"""Emergency fix - revert _get_all_items_streaming to _get_all_items"""

print("🚨 EMERGENCY FIX: Fixing method name error")
print("=" * 60)

# Read the file
filepath = "/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py"
with open(filepath, 'r') as f:
    content = f.read()

# Fix the broken method names
original_content = content
content = content.replace("self._get_all_items_streaming(", "self._get_all_items(")
content = content.replace("async for item in self._get_all_items(", "for item in await self._get_all_items(")

# Count fixes
fixes_made = original_content.count("_get_all_items_streaming")

if fixes_made > 0:
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"✅ Fixed {fixes_made} incorrect method calls")
    print("✅ Reverted to working _get_all_items method")
    print("\nArtists and playlists should work again after restart!")
else:
    print("⚠️ No fixes needed - method names already correct")

print("\n" + "=" * 60)
print("RESTART REQUIRED: Run this to apply fix:")
print("docker restart addon_d5369777_music_assistant")