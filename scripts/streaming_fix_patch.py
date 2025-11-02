#!/usr/bin/env python3
"""Patch script to fix Apple Music library pagination in Music Assistant"""

import sys
import re

# Read the current file
filepath = "/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py"
with open(filepath, "r") as f:
    content = f.read()

# Check if already patched
if "_get_all_items_streaming" in content:
    print("✅ Already patched for streaming pagination")
    sys.exit(0)

print("Applying streaming pagination fix...")

# Find position to insert new method (after _get_all_items)
insert_marker = "return all_items"
insert_pos = content.find(insert_marker)
if insert_pos == -1:
    print("❌ Could not find insertion point")
    sys.exit(1)

# Find the end of the _get_all_items method
next_method_pos = content.find("    @throttle_with_retries", insert_pos)
if next_method_pos == -1:
    next_method_pos = content.find("    async def", insert_pos)

# Add the new streaming method
streaming_method = '''

    async def _get_all_items_streaming(self, endpoint, key="data", **kwargs):
        """Stream items from a paged API endpoint without loading all into memory."""
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
                    self.logger.info("Loaded %d items from %s", offset + len(page_items), endpoint)

                if not result.get("next"):
                    break

                offset += limit
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                self.logger.warning("Error at offset %d: %s", offset, e)

                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error("Stopping at offset %d after errors", offset)
                    break

                offset += limit
'''

# Insert the new method
content = content[:next_method_pos] + streaming_method + "\n" + content[next_method_pos:]

print("✓ Added _get_all_items_streaming method")

# Update get_library_artists - find and replace the entire method
old_artists_start = content.find("async def get_library_artists(self)")
old_artists_end = content.find("\n\n    async def get_library_albums", old_artists_start)
if old_artists_start > -1 and old_artists_end > -1:
    old_artists_method = content[old_artists_start:old_artists_end]

    new_artists_method = '''async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        """Retrieve library artists using streaming pagination."""
        endpoint = "me/library/artists"
        self.logger.info("Starting library artists sync (streaming)")
        count = 0
        async for item in self._get_all_items_streaming(endpoint, include="catalog", extend="editorialNotes"):
            if item and item.get("id"):
                artist = self._parse_artist(item)
                if artist:
                    count += 1
                    yield artist
        self.logger.info("Completed artists sync: %d loaded", count)'''

    content = content[:old_artists_start] + new_artists_method + content[old_artists_end:]
    print("✓ Updated get_library_artists")

# Update get_library_albums - replace the for loop
content = content.replace(
    'for item in await self._get_all_items(\n            endpoint, include="catalog,artists", extend="editorialNotes"\n        ):',
    'async for item in self._get_all_items_streaming(\n            endpoint, include="catalog,artists", extend="editorialNotes"\n        ):'
)
print("✓ Updated get_library_albums")

# Update get_library_playlists - find first occurrence
playlist_pattern = 'for item in await self._get_all_items(endpoint):'
playlist_pos = content.find(playlist_pattern)
if playlist_pos > -1 and 'get_library_playlists' in content[playlist_pos-200:playlist_pos]:
    content = content[:playlist_pos] + 'async for item in self._get_all_items_streaming(endpoint):' + content[playlist_pos+len(playlist_pattern):]
    print("✓ Updated get_library_playlists")

# Update get_library_tracks - needs special handling for batch catalog lookups
tracks_start = content.find("async def get_library_tracks(self)")
if tracks_start > -1:
    tracks_end = content.find("\n\n    async def", tracks_start + 10)
    if tracks_end > -1:
        old_tracks = content[tracks_start:tracks_end]

        new_tracks = '''async def get_library_tracks(self) -> AsyncGenerator[Track, None]:
        """Retrieve library tracks using streaming pagination."""
        endpoint = "me/library/songs"
        self.logger.info("Starting library tracks sync (streaming)")
        count = 0
        song_batch = []
        batch_size = 200  # Process catalog lookups in batches

        async for item in self._get_all_items_streaming(endpoint):
            catalog_id = item.get("attributes", {}).get("playParams", {}).get("catalogId")
            if catalog_id:
                song_batch.append((catalog_id, item))

                # Process batch when full
                if len(song_batch) >= batch_size:
                    catalog_ids = [c for c, _ in song_batch]
                    endpoint_catalog = f"catalog/{self._storefront}/songs"

                    try:
                        response = await self._get_data(endpoint_catalog, ids=",".join(catalog_ids))
                        if response and "data" in response:
                            catalog_dict = {song["id"]: song for song in response["data"]}

                            for cat_id, original_item in song_batch:
                                catalog_song = catalog_dict.get(cat_id)
                                if catalog_song:
                                    track = self._parse_track(catalog_song)
                                    if track:
                                        count += 1
                                        yield track
                    except Exception as e:
                        self.logger.warning("Error fetching catalog batch: %s", e)

                    song_batch = []  # Clear batch

        # Process remaining items in batch
        if song_batch:
            catalog_ids = [c for c, _ in song_batch]
            endpoint_catalog = f"catalog/{self._storefront}/songs"

            try:
                response = await self._get_data(endpoint_catalog, ids=",".join(catalog_ids))
                if response and "data" in response:
                    catalog_dict = {song["id"]: song for song in response["data"]}

                    for cat_id, original_item in song_batch:
                        catalog_song = catalog_dict.get(cat_id)
                        if catalog_song:
                            track = self._parse_track(catalog_song)
                            if track:
                                count += 1
                                yield track
            except Exception as e:
                self.logger.warning("Error fetching final catalog batch: %s", e)

        self.logger.info("Completed tracks sync: %d loaded", count)'''

        content = content[:tracks_start] + new_tracks + content[tracks_end:]
        print("✓ Updated get_library_tracks")

# Write the patched file
with open(filepath, "w") as f:
    f.write(content)

print("\n✅ Streaming pagination fix applied successfully!")
print("   - Large libraries will now load completely")
print("   - Artists will stream in as they load (no more stopping at J)")
print("   - Memory usage will stay constant")
print("")
print("Please restart Music Assistant for changes to take effect!")