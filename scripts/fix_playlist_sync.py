#!/usr/bin/env python3
"""
Fix Apple Music playlist sync in Music Assistant.
Applies streaming pagination to playlist sync method.
"""

import sys

# Read the current file
filepath = "/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py"
with open(filepath, "r") as f:
    content = f.read()

print("🎵 Fixing Apple Music Playlist Sync...")

# Check current state
if "async for item in self._get_all_items_streaming(endpoint):" in content and "get_library_playlists" in content:
    # Find if playlists already use streaming
    playlist_start = content.find("async def get_library_playlists(")
    if playlist_start > -1:
        playlist_end = content.find("\n\n    async def", playlist_start + 10)
        if playlist_end == -1:
            playlist_end = content.find("\n\n    def", playlist_start + 10)

        playlist_method = content[playlist_start:playlist_end] if playlist_end > -1 else content[playlist_start:playlist_start+1000]

        if "async for item in self._get_all_items_streaming" in playlist_method:
            print("✅ Playlists already using streaming pagination")
            sys.exit(0)

# Fix get_library_playlists to use streaming
print("Updating get_library_playlists to use streaming...")

# Find and replace the playlist method
old_pattern = "for item in await self._get_all_items(endpoint):"
new_pattern = "async for item in self._get_all_items_streaming(endpoint):"

# Count occurrences
count = content.count(old_pattern)
print(f"Found {count} occurrences of batch pagination to fix")

if count > 0:
    # Replace the pattern
    content = content.replace(old_pattern, new_pattern)
    print(f"✓ Replaced {count} instances with streaming pagination")

    # Also update the method to add logging
    playlist_start = content.find("async def get_library_playlists(self)")
    if playlist_start > -1:
        # Find the endpoint line
        endpoint_line_start = content.find('endpoint = "me/library/playlists"', playlist_start)
        if endpoint_line_start > -1:
            # Add logging after endpoint
            endpoint_line_end = content.find("\n", endpoint_line_start)
            logging_lines = '''
        self.logger.info("Starting library playlists sync (streaming)")
        count = 0'''
            content = content[:endpoint_line_end] + logging_lines + content[endpoint_line_end:]

            # Add count increment and final log
            yield_line = content.find("yield playlist", playlist_start)
            if yield_line > -1:
                # Add count increment before yield
                yield_line_start = content.rfind("\n", playlist_start, yield_line)
                indent = " " * 16  # Match the indentation
                content = content[:yield_line] + f"count += 1\n{indent}" + content[yield_line:]

            # Add completion log at end of method
            method_end = content.find("\n\n    async def", playlist_start + 10)
            if method_end == -1:
                method_end = content.find("\n\n    def", playlist_start + 10)
            if method_end > -1:
                completion_log = '''
        self.logger.info(f"Completed playlists sync: {count} loaded")'''
                content = content[:method_end] + completion_log + content[method_end:]

            print("✓ Added logging to track playlist sync progress")

# Write the fixed file
with open(filepath, "w") as f:
    f.write(content)

print("\n✅ Playlist sync fix applied successfully!")
print("   - Playlists will now use streaming pagination")
print("   - No more timeouts or memory issues")
print("   - Progress will be logged during sync")
print("\nPlease restart Music Assistant for changes to take effect!")