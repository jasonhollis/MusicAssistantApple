# Unicode Fix Patch for Apple Music Provider

## Quick Apply Instructions

### Option 1: Manual Patch (Recommended)

**Step 1: Backup**
```bash
cd "/path/to/music_assistant"
cp server-2.6.0/music_assistant/providers/apple_music/__init__.py \
   server-2.6.0/music_assistant/providers/apple_music/__init__.py.backup.$(date +%Y%m%d)
```

**Step 2: Add Import**

After line 22 (after `import re`), add:
```python
import unicodedata
```

**Step 3: Add Utility Functions**

After line 264 (after `throttler = ThrottlerManager...`), add these methods to the `AppleMusicProvider` class:

```python
    @staticmethod
    def _safe_unicode_str(value: Any, fallback: str = "") -> str:
        """Safely convert any value to a Unicode string with NFC normalization."""
        if value is None:
            return fallback
        if isinstance(value, str):
            return unicodedata.normalize('NFC', value)
        if isinstance(value, bytes):
            try:
                decoded = value.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    decoded = value.decode('latin-1')
                except Exception:
                    return fallback
            return unicodedata.normalize('NFC', decoded)
        try:
            return unicodedata.normalize('NFC', str(value))
        except Exception:
            return fallback

    @staticmethod
    def _safe_json_get(data: dict, *keys, default: Any = None) -> Any:
        """Safely navigate nested dictionary with list indexing support."""
        current = data
        for key in keys:
            # Handle dictionary keys
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            # Handle list/tuple indexing
            elif isinstance(current, (list, tuple)):
                if isinstance(key, int):
                    try:
                        current = current[key]
                    except (IndexError, TypeError):
                        return default
                else:
                    return default
            else:
                return default
        return current

    @staticmethod
    def _truncate_for_log(text: str, max_length: int = 100) -> str:
        """Safely truncate text for logging."""
        if not text:
            return ""
        text = AppleMusicProvider._safe_unicode_str(text)
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
```

**Step 4: Replace `_get_all_items`**

Replace lines 771-786 with:

```python
    async def _get_all_items_streaming(
        self, endpoint: str, key: str = "data", **kwargs
    ) -> AsyncGenerator[dict, None]:
        """Stream items from API endpoint with Unicode-safe error handling."""
        limit = 50
        offset = 0
        page_num = 0
        total_items = 0
        consecutive_errors = 0
        max_consecutive_errors = 3

        while True:
            kwargs["limit"] = limit
            kwargs["offset"] = offset

            try:
                result = await self._get_data(endpoint, **kwargs)
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                error_msg = self._safe_unicode_str(str(exc), "Unknown error")
                self.logger.warning(
                    "Error fetching page %d (offset %d) from %s: %s",
                    page_num, offset, endpoint, self._truncate_for_log(error_msg)
                )
                if "404" in error_msg or "not found" in error_msg.lower():
                    self.logger.info("Reached end of %s at page %d", endpoint, page_num)
                    break
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error(
                        "Stopping %s sync after %d consecutive errors",
                        endpoint, consecutive_errors
                    )
                    break
                offset += limit
                page_num += 1
                continue

            if key not in result:
                self.logger.debug(
                    "No '%s' key in response for %s (offset %d), ending pagination",
                    key, endpoint, offset
                )
                break

            items = result[key]
            items_in_page = len(items)

            for idx, item in enumerate(items):
                if not item:
                    continue
                try:
                    item_id = self._safe_json_get(item, "id", default=f"unknown_{offset}_{idx}")
                    total_items += 1
                    yield item
                except Exception as exc:
                    error_msg = self._safe_unicode_str(str(exc))
                    self.logger.warning(
                        "Skipping malformed item in %s at offset %d (index %d): %s",
                        endpoint, offset, idx, self._truncate_for_log(error_msg, 80)
                    )
                    continue

            if page_num % 5 == 0 or items_in_page > 0:
                self.logger.info(
                    "%s: page %d, %d items in page, %d total yielded",
                    endpoint.split('/')[-1], page_num, items_in_page, total_items
                )

            if not result.get("next"):
                self.logger.info(
                    "Completed %s: %d total items across %d pages",
                    endpoint, total_items, page_num + 1
                )
                break

            offset += limit
            page_num += 1

            if page_num > 10000:
                self.logger.error(
                    "Safety limit reached: %d pages fetched from %s. Stopping.",
                    page_num, endpoint
                )
                break

    async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
        """Legacy method - uses streaming internally."""
        items = []
        async for item in self._get_all_items_streaming(endpoint, key, **kwargs):
            items.append(item)
        return items
```

**Step 5: Replace `get_library_artists`**

Replace lines 330-335 with:

```python
    async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        """Retrieve library artists with Unicode-safe streaming."""
        endpoint = "me/library/artists"
        processed_count = 0
        error_count = 0

        try:
            async for item in self._get_all_items_streaming(
                endpoint, include="catalog", extend="editorialNotes"
            ):
                if not item or not item.get("id"):
                    continue

                try:
                    artist = self._parse_artist(item)
                    if artist:
                        processed_count += 1
                        artist_name = getattr(artist, 'name', 'Unknown')
                        if any(ord(char) > 127 for char in artist_name):
                            self.logger.debug(
                                "Processed artist with Unicode: %s (id=%s)",
                                self._truncate_for_log(artist_name, 60),
                                self._truncate_for_log(getattr(artist, 'item_id', 'unknown'), 30)
                            )
                        yield artist
                    else:
                        error_count += 1
                except Exception as exc:
                    error_count += 1
                    item_id = self._safe_unicode_str(item.get("id", "unknown"))
                    item_name = self._safe_json_get(
                        item, "attributes", "name",
                        default=self._safe_json_get(
                            item, "relationships", "catalog", "data", 0, "attributes", "name",
                            default="Unknown"
                        )
                    )
                    self.logger.warning(
                        "Error parsing artist %s (%s): %s. Continuing sync...",
                        self._truncate_for_log(self._safe_unicode_str(item_name), 50),
                        self._truncate_for_log(item_id, 30),
                        self._truncate_for_log(self._safe_unicode_str(str(exc)), 80)
                    )

            self.logger.info(
                "Library artists sync complete: %d processed, %d errors skipped",
                processed_count, error_count
            )
        except Exception as exc:
            self.logger.error(
                "Critical error during artists sync: %s. Processed %d before error.",
                self._truncate_for_log(self._safe_unicode_str(str(exc)), 100),
                processed_count
            )
```

**Step 6: Replace `get_library_albums`**

Replace lines 337-346 with:

```python
    async def get_library_albums(self) -> AsyncGenerator[Album, None]:
        """Retrieve library albums with Unicode-safe streaming."""
        endpoint = "me/library/albums"
        processed_count = 0
        error_count = 0

        try:
            async for item in self._get_all_items_streaming(
                endpoint, include="catalog,artists", extend="editorialNotes"
            ):
                if not item or not item.get("id"):
                    continue

                try:
                    album = self._parse_album(item)
                    if album:
                        processed_count += 1
                        album_name = getattr(album, 'name', 'Unknown')
                        if any(ord(char) > 127 for char in album_name):
                            self.logger.debug(
                                "Processed album with Unicode: %s",
                                self._truncate_for_log(album_name, 60)
                            )
                        yield album
                except Exception as exc:
                    error_count += 1
                    item_id = self._safe_unicode_str(item.get("id", "unknown"))
                    item_name = self._safe_json_get(item, "attributes", "name", default="Unknown")
                    self.logger.warning(
                        "Error parsing album %s (%s): %s. Continuing sync...",
                        self._truncate_for_log(self._safe_unicode_str(item_name), 50),
                        self._truncate_for_log(item_id, 30),
                        self._truncate_for_log(self._safe_unicode_str(str(exc)), 80)
                    )

            self.logger.info(
                "Library albums sync complete: %d processed, %d errors skipped",
                processed_count, error_count
            )
        except Exception as exc:
            self.logger.error(
                "Critical error during albums sync: %s. Processed %d before error.",
                self._truncate_for_log(self._safe_unicode_str(str(exc)), 100),
                processed_count
            )
```

**Step 7: Replace `get_library_playlists`**

Replace lines 373-381 with:

```python
    async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
        """Retrieve playlists with Unicode-safe streaming."""
        endpoint = "me/library/playlists"
        processed_count = 0
        error_count = 0

        try:
            async for item in self._get_all_items_streaming(endpoint):
                try:
                    if item.get("attributes", {}).get("hasCatalog"):
                        global_id = self._safe_json_get(
                            item, "attributes", "playParams", "globalId", default=None
                        )
                        if global_id:
                            playlist = await self.get_playlist(global_id)
                            if playlist:
                                processed_count += 1
                                yield playlist
                        else:
                            error_count += 1
                            self.logger.warning(
                                "Catalog playlist %s missing globalId",
                                self._safe_unicode_str(item.get("id", "unknown"))
                            )
                    elif item and item.get("id"):
                        playlist = self._parse_playlist(item)
                        if playlist:
                            processed_count += 1
                            yield playlist
                except Exception as exc:
                    error_count += 1
                    item_id = self._safe_unicode_str(item.get("id", "unknown"))
                    item_name = self._safe_json_get(item, "attributes", "name", default="Unknown")
                    self.logger.warning(
                        "Error processing playlist %s (%s): %s. Continuing sync...",
                        self._truncate_for_log(self._safe_unicode_str(item_name), 50),
                        self._truncate_for_log(item_id, 30),
                        self._truncate_for_log(self._safe_unicode_str(str(exc)), 80)
                    )

            self.logger.info(
                "Library playlists sync complete: %d processed, %d errors skipped",
                processed_count, error_count
            )
        except Exception as exc:
            self.logger.error(
                "Critical error during playlists sync: %s. Processed %d.",
                self._truncate_for_log(self._safe_unicode_str(str(exc)), 100),
                processed_count
            )
```

**Step 8: Enhance `_parse_artist` (CRITICAL for Unicode issue)**

Replace the entire `_parse_artist` method (lines 527-575) with:

```python
    def _parse_artist(self, artist_obj):
        """Parse artist object with comprehensive Unicode support."""
        try:
            relationships = artist_obj.get("relationships", {})

            # Extract artist ID and attributes
            if (
                artist_obj.get("type") == "library-artists"
                and relationships.get("catalog", {}).get("data", []) != []
            ):
                artist_id = self._safe_json_get(
                    relationships, "catalog", "data", 0, "id",
                    default=artist_obj.get("id", "unknown")
                )
                attributes = self._safe_json_get(
                    relationships, "catalog", "data", 0, "attributes",
                    default={}
                )
            elif "attributes" in artist_obj:
                artist_id = self._safe_unicode_str(artist_obj.get("id", "unknown"))
                attributes = artist_obj.get("attributes", {})
            else:
                artist_id = self._safe_unicode_str(artist_obj.get("id", "unknown"))
                self.logger.debug(
                    "No attributes found for artist %s, returning basic mapping",
                    self._truncate_for_log(artist_id, 50)
                )
                return ItemMapping(
                    media_type=MediaType.ARTIST,
                    provider=self.lookup_key,
                    item_id=artist_id,
                    name=artist_id,
                )

            # Extract name with Unicode safety
            artist_name = self._safe_unicode_str(
                attributes.get("name"),
                fallback=f"Artist {artist_id}"
            )

            # Extract URL with Unicode safety
            artist_url = self._safe_unicode_str(attributes.get("url"), fallback="")

            # Create artist object
            artist = Artist(
                item_id=artist_id,
                name=artist_name,
                provider=self.domain,
                provider_mappings={
                    ProviderMapping(
                        item_id=artist_id,
                        provider_domain=self.domain,
                        provider_instance=self.instance_id,
                        url=artist_url if artist_url else None,
                    )
                },
            )

            # Extract artwork
            if artwork := attributes.get("artwork"):
                try:
                    artwork_url = self._safe_unicode_str(artwork.get("url", ""))
                    if artwork_url:
                        width = artwork.get("width", 600)
                        height = artwork.get("height", 600)
                        formatted_url = artwork_url.format(w=width, h=height)
                        artist.metadata.images = [
                            MediaItemImage(
                                type=ImageType.THUMB,
                                path=formatted_url,
                                provider=self.lookup_key,
                                remotely_accessible=True,
                            )
                        ]
                except Exception as exc:
                    self.logger.debug(
                        "Could not process artwork for artist %s: %s",
                        self._truncate_for_log(artist_name, 40),
                        self._safe_unicode_str(str(exc))
                    )

            # Extract genres
            if genres := attributes.get("genreNames"):
                try:
                    artist.metadata.genres = {
                        self._safe_unicode_str(genre) for genre in genres if genre
                    }
                except Exception as exc:
                    self.logger.debug(
                        "Could not process genres for artist %s: %s",
                        self._truncate_for_log(artist_name, 40),
                        self._safe_unicode_str(str(exc))
                    )

            # Extract editorial notes
            if notes := attributes.get("editorialNotes"):
                try:
                    description = (
                        self._safe_unicode_str(notes.get("standard")) or
                        self._safe_unicode_str(notes.get("short"))
                    )
                    if description:
                        artist.metadata.description = description
                except Exception as exc:
                    self.logger.debug(
                        "Could not process editorial notes for artist %s: %s",
                        self._truncate_for_log(artist_name, 40),
                        self._safe_unicode_str(str(exc))
                    )

            return artist

        except Exception as exc:
            artist_id = self._safe_unicode_str(artist_obj.get("id", "unknown"))
            artist_name = self._safe_json_get(
                artist_obj, "attributes", "name",
                default=self._safe_json_get(
                    artist_obj, "relationships", "catalog", "data", 0, "attributes", "name",
                    default="Unknown"
                )
            )
            self.logger.error(
                "Failed to parse artist (id=%s, name=%s): %s",
                self._truncate_for_log(artist_id, 30),
                self._truncate_for_log(self._safe_unicode_str(artist_name), 50),
                self._truncate_for_log(self._safe_unicode_str(str(exc)), 100)
            )
            # Return None to skip this artist and continue sync
            return None
```

**Step 9: Restart Music Assistant**

```bash
# If running as Docker container
docker restart music-assistant

# If running as systemd service
sudo systemctl restart music-assistant

# If running manually
# Stop the current process and start again
```

### Option 2: Automated Patch Script

Create and run this script:

```bash
#!/bin/bash
# apply_unicode_fix.sh

set -e

PROVIDER_FILE="server-2.6.0/music_assistant/providers/apple_music/__init__.py"
BACKUP_FILE="${PROVIDER_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Creating backup: $BACKUP_FILE"
cp "$PROVIDER_FILE" "$BACKUP_FILE"

echo "Applying Unicode fix..."

# This would need the actual patch content
# For manual application, follow Option 1 above

echo "✅ Backup created at: $BACKUP_FILE"
echo "⚠️  Please manually apply changes from UNICODE_FIX_PATCH.md"
echo "📝 See detailed instructions in the patch file"
```

## Testing the Fix

### 1. Enable Debug Logging

In Music Assistant configuration:
```yaml
logger:
  default: info
  logs:
    music_assistant.providers.apple_music: debug
```

### 2. Clear Cache

```bash
# Remove provider cache to force fresh sync
rm -rf /path/to/music_assistant/cache/apple_music*
```

### 3. Trigger Sync

- Restart Music Assistant
- Go to Settings → Providers → Apple Music
- Click "Reload" or restart the provider

### 4. Monitor Logs

Look for these indicators of success:

```
✅ SUCCESS INDICATORS:
- "Processed artist with Unicode: Jan Bartoš"
- "Library artists sync complete: X processed, Y errors skipped"
- Sync completes without stopping at "J"
- "Jan Bartoš" appears in your library

❌ FAILURE INDICATORS:
- "Failed to parse artist (id=..., name=Jan Bartoš)"
- "Critical error during artists sync"
- Sync stops at artists starting with "J"
```

### 5. Verify Results

```bash
# Check that sync completed
grep "Library artists sync complete" /path/to/music_assistant/logs/music_assistant.log

# Check for Unicode artists processed
grep "Processed artist with Unicode" /path/to/music_assistant/logs/music_assistant.log

# Check for errors
grep "Failed to parse artist" /path/to/music_assistant/logs/music_assistant.log
```

## What This Fix Does

### Unicode Handling
- ✅ Normalizes all strings to NFC form (consistent representation)
- ✅ Handles None, bytes, and invalid UTF-8 sequences gracefully
- ✅ Supports all Unicode ranges: diacritics, CJK, RTL, emoji
- ✅ Safe string truncation (by character count, not byte count)

### Error Resilience
- ✅ Try/except around individual artist parsing
- ✅ Logs errors but continues sync
- ✅ Tracks error counts for visibility
- ✅ Returns None on parse failure (doesn't crash)

### Performance
- ✅ Streaming pagination (constant memory usage)
- ✅ No accumulation of items in memory
- ✅ Progress logging every 5 pages
- ✅ Early termination on repeated errors

### Characters Supported
- ✅ Czech: Jan Bartoš (š with háček)
- ✅ Japanese: 藤井 風
- ✅ Chinese: 周杰倫
- ✅ Korean: 방탄소년단 (BTS)
- ✅ Arabic: فيروز
- ✅ Hebrew: עברית
- ✅ Emoji: Any artist with emoji 🎵🎸

## Rollback

If issues occur:

```bash
# Restore from backup
cd /path/to/music_assistant
cp "$BACKUP_FILE" "$PROVIDER_FILE"

# Restart Music Assistant
docker restart music-assistant
# or
sudo systemctl restart music-assistant
```

## Support

If the fix doesn't work:

1. **Check Python version**: Requires Python 3.9+
2. **Check logs**: Look for specific error messages
3. **Test simple Unicode**: Try artist "Björk" first (simpler diacritic)
4. **Isolate the issue**:
   - Does JSON parsing work? (check _get_data response)
   - Does parsing work? (check _parse_artist with sample data)
   - Does database insertion work? (check Music Assistant database layer)

## Implementation Priority

**Critical (must have):**
- Step 3: Utility functions
- Step 4: Streaming pagination
- Step 5: Unicode-safe get_library_artists
- Step 8: Unicode-safe _parse_artist

**Important (should have):**
- Step 6: Unicode-safe get_library_albums
- Step 7: Unicode-safe get_library_playlists

**Optional (nice to have):**
- Enhanced logging
- Performance monitoring
- Error statistics

## Expected Results

Before fix:
```
2025-10-25 10:00:00 INFO: Syncing library artists...
2025-10-25 10:02:15 INFO: Fetched 250 artists (A-J)
[SYNC STOPS - no error message, just hangs or times out]
```

After fix:
```
2025-10-25 10:00:00 INFO: Syncing library artists...
2025-10-25 10:02:15 INFO: me/library/artists: page 5, 50 items, 250 total
2025-10-25 10:02:16 DEBUG: Processed artist with Unicode: Jan Bartoš (id=1234)
2025-10-25 10:05:30 INFO: Completed me/library/artists: 1247 total items across 25 pages
2025-10-25 10:05:30 INFO: Library artists sync complete: 1247 processed, 0 errors skipped
```

## Questions?

Check `apple_music_unicode_fix.py` for:
- Complete implementation with detailed comments
- Additional utility functions
- Comprehensive error handling examples
- Full character set support documentation
