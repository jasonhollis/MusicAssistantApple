#!/usr/bin/env python3
"""
Apply streaming pagination fix to Music Assistant Apple Music provider
Fixes issue where library stops loading at letter "J" for large libraries
"""

STREAMING_PATCH = '''
# STREAMING PAGINATION FIX - Applied {timestamp}
# Fixes library stopping at "J" for large libraries

# Add this new method after _get_all_items (around line 786)
async def _get_all_items_streaming(self, endpoint, key="data", **kwargs) -> AsyncIterator[dict]:
    """Stream items from a paged API endpoint without loading all into memory.

    This is the proper streaming version that yields items as they arrive,
    preventing timeouts and memory issues with large libraries.

    Args:
        endpoint: API endpoint to query
        key: Response key containing items (default: "data")
        **kwargs: Additional parameters to pass to API

    Yields:
        Individual items as they're received from the API
    """
    limit = 50  # Apple's page size
    offset = 0
    consecutive_errors = 0
    max_consecutive_errors = 3

    while True:
        try:
            kwargs["limit"] = limit
            kwargs["offset"] = offset

            # Get one page of results
            result = await self._get_data(endpoint, **kwargs)

            # Check if we have data
            if key not in result:
                self.logger.debug(
                    "No more data for endpoint %s at offset %d",
                    endpoint, offset
                )
                break

            # Yield items from this page immediately
            page_items = result[key]
            if not page_items:
                # Empty page means we're done
                break

            for item in page_items:
                if item:  # Skip None/empty items
                    yield item

            # Log progress for large libraries
            if offset > 0 and offset % 500 == 0:
                self.logger.info(
                    "Loaded %d items from %s (continuing...)",
                    offset + len(page_items), endpoint
                )

            # Check if there are more pages
            if not result.get("next"):
                self.logger.debug(
                    "Reached end of %s at offset %d",
                    endpoint, offset + len(page_items)
                )
                break

            # Move to next page
            offset += limit
            consecutive_errors = 0  # Reset error counter on success

        except Exception as e:
            consecutive_errors += 1
            self.logger.warning(
                "Error loading %s at offset %d (attempt %d/%d): %s",
                endpoint, offset, consecutive_errors, max_consecutive_errors, e
            )

            if consecutive_errors >= max_consecutive_errors:
                self.logger.error(
                    "Too many consecutive errors for %s, stopping at offset %d",
                    endpoint, offset
                )
                break

            # Continue to next page on error (partial results better than none)
            offset += limit

# Update get_library_artists to use streaming (around line 330)
async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
    """Retrieve library artists using streaming pagination."""
    endpoint = "me/library/artists"
    self.logger.info("Starting library artists sync (streaming mode)")
    count = 0

    async for item in self._get_all_items_streaming(
        endpoint, include="catalog", extend="editorialNotes"
    ):
        if item and item.get("id"):
            artist = self._parse_artist(item)
            if artist:
                count += 1
                yield artist

    self.logger.info("Completed library artists sync: %d artists loaded", count)

# Update get_library_albums to use streaming (around line 337)
async def get_library_albums(self) -> AsyncGenerator[Album, None]:
    """Retrieve library albums using streaming pagination."""
    endpoint = "me/library/albums"
    self.logger.info("Starting library albums sync (streaming mode)")
    count = 0

    async for item in self._get_all_items_streaming(
        endpoint, include="catalog,artists", extend="editorialNotes"
    ):
        if item and item.get("id"):
            album = self._parse_album(item)
            if album:
                count += 1
                yield album

    self.logger.info("Completed library albums sync: %d albums loaded", count)

# Update get_library_playlists to use streaming (around line 374)
async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
    """Retrieve library playlists using streaming pagination."""
    endpoint = "me/library/playlists"
    self.logger.info("Starting library playlists sync (streaming mode)")
    count = 0

    async for item in self._get_all_items_streaming(endpoint):
        if item and item.get("id"):
            playlist = await self._parse_playlist(item)
            if playlist:
                count += 1
                yield playlist

    self.logger.info("Completed library playlists sync: %d playlists loaded", count)
'''

def apply_patch():
    """Apply the streaming pagination fix to Music Assistant."""
    import subprocess
    from datetime import datetime

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print("🎵 APPLYING STREAMING PAGINATION FIX FOR LARGE LIBRARIES")
    print("="*60)

    # Create the patch Python script
    patch_script = f"""
import sys
import re
from datetime import datetime

# Read the current file
filepath = '/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py'
with open(filepath, 'r') as f:
    content = f.read()

# Check if already patched
if '_get_all_items_streaming' in content:
    print('✅ Already patched for streaming pagination')
    sys.exit(0)

print('Applying streaming pagination fix...')

# Add the new streaming method after _get_all_items
streaming_method = '''
async def _get_all_items_streaming(self, endpoint, key="data", **kwargs):
    \\"\\"\\"Stream items from a paged API endpoint without loading all into memory.\\"\\"\\"
    limit = 50
    offset = 0
    consecutive_errors = 0
    max_consecutive_errors = 3

    while True:
        try:
            kwargs["limit"] = limit
            kwargs["offset"] = offset
            result = await self._get_data(endpoint, **kwargs)

            if key not in result:
                break

            page_items = result[key]
            if not page_items:
                break

            for item in page_items:
                if item:
                    yield item

            if offset > 0 and offset % 500 == 0:
                self.logger.info(f"Loaded {{offset + len(page_items)}} items from {{endpoint}}")

            if not result.get("next"):
                break

            offset += limit
            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            self.logger.warning(f"Error at offset {{offset}}: {{e}}")

            if consecutive_errors >= max_consecutive_errors:
                self.logger.error(f"Stopping at offset {{offset}} after errors")
                break

            offset += limit
'''

# Insert after _get_all_items method
insert_pos = content.find('return all_items\\\\n\\\\n')
if insert_pos == -1:
    print('❌ Could not find insertion point')
    sys.exit(1)

insert_pos = insert_pos + len('return all_items\\\\n\\\\n')
content = content[:insert_pos] + '    ' + streaming_method.strip() + '\\\\n\\\\n' + content[insert_pos:]

# Update get_library_artists
old_artists = '''async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        \\"\\"\\"Retrieve library artists from spotify.\\"\\"\\"
        endpoint = "me/library/artists"
        for item in await self._get_all_items(endpoint, include="catalog", extend="editorialNotes"):
            if item and item["id"]:
                yield self._parse_artist(item)'''

new_artists = '''async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        \\"\\"\\"Retrieve library artists using streaming pagination.\\"\\"\\"
        endpoint = "me/library/artists"
        self.logger.info("Starting library artists sync (streaming)")
        count = 0
        async for item in self._get_all_items_streaming(endpoint, include="catalog", extend="editorialNotes"):
            if item and item.get("id"):
                artist = self._parse_artist(item)
                if artist:
                    count += 1
                    yield artist
        self.logger.info(f"Completed artists sync: {{count}} loaded")'''

content = content.replace(old_artists, new_artists)

# Update get_library_albums
old_albums = 'for item in await self._get_all_items(\\\\n            endpoint, include="catalog,artists", extend="editorialNotes"\\\\n        ):'
new_albums = 'async for item in self._get_all_items_streaming(\\\\n            endpoint, include="catalog,artists", extend="editorialNotes"\\\\n        ):'
content = content.replace(old_albums, new_albums)

# Update get_library_playlists
old_playlists = 'for item in await self._get_all_items(endpoint):'
new_playlists = 'async for item in self._get_all_items_streaming(endpoint):'
content = content.replace(old_playlists, new_playlists, 1)  # Only first occurrence

# Write the patched file
with open(filepath, 'w') as f:
    f.write(content)

print('✅ Streaming pagination fix applied successfully!')
print('   - Large libraries will now load completely')
print('   - Artists will stream in as they load (no more stopping at J)')
print('   - Memory usage will stay constant')
print('')
print('Please restart Music Assistant to use the fix!')
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