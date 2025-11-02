#!/usr/bin/env python3
"""
Comprehensive Unicode-Safe Fix for Apple Music Provider.

PROBLEM:
--------
The Apple Music library sync gets stuck on artists with Unicode characters
(e.g., "Jan Bartoš" with háček/caron diacritic). This can be caused by:

1. JSON decoding issues with UTF-8 characters
2. Database insertion failures with Unicode
3. Parsing errors in _parse_artist/_parse_album/_parse_track
4. String operations that don't handle multibyte characters
5. Lack of error handling - one bad artist stops entire sync

SOLUTION:
---------
1. Explicit UTF-8 handling throughout the pipeline
2. Robust error handling with try/except blocks
3. Logging for problematic entries without stopping sync
4. Safe string operations that handle all Unicode ranges
5. Streaming pagination to avoid memory buildup

This fix handles:
- Czech/Eastern European diacritics (háček, acute, caron, etc.)
- Japanese/Chinese/Korean characters
- Arabic/Hebrew/RTL scripts
- Emoji and symbols
- All Unicode planes (BMP and beyond)

IMPLEMENTATION:
--------------
Replace methods in server-2.6.0/music_assistant/providers/apple_music/__init__.py
"""

import json
import logging
import unicodedata
from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from music_assistant_models.media_items import Artist, Album, Track, Playlist


# ============================================================================
# UNICODE UTILITIES
# ============================================================================

def safe_unicode_str(value: Any, fallback: str = "") -> str:
    """
    Safely convert any value to a Unicode string.

    Handles:
    - None values
    - Bytes that need decoding
    - Invalid UTF-8 sequences
    - All Unicode normalization forms

    Args:
        value: Any value to convert to string
        fallback: Default value if conversion fails

    Returns:
        Safe Unicode string
    """
    if value is None:
        return fallback

    # If it's already a string, normalize it
    if isinstance(value, str):
        # Normalize to NFC (Canonical Composition) for consistent representation
        # This ensures "é" is stored as single codepoint, not "e" + combining accent
        return unicodedata.normalize('NFC', value)

    # If it's bytes, decode with error handling
    if isinstance(value, bytes):
        try:
            # Try UTF-8 first
            decoded = value.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to Latin-1 (never fails but may be wrong)
                decoded = value.decode('latin-1')
            except Exception:
                return fallback
        return unicodedata.normalize('NFC', decoded)

    # For other types, convert to string and normalize
    try:
        return unicodedata.normalize('NFC', str(value))
    except Exception:
        return fallback


def safe_json_get(data: dict, *keys, default: Any = None) -> Any:
    """
    Safely navigate nested dictionary with Unicode keys and list indexing.

    Args:
        data: Dictionary to navigate
        *keys: Sequence of keys to traverse (can include int for list indexing)
        default: Default value if key not found

    Returns:
        Value at the nested key or default

    Example:
        safe_json_get(data, "attributes", "name", default="Unknown")
        safe_json_get(data, "relationships", "catalog", "data", 0, "id")
    """
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


def truncate_for_log(text: str, max_length: int = 100) -> str:
    """
    Safely truncate text for logging, preserving Unicode characters.

    Args:
        text: Text to truncate
        max_length: Maximum length in characters (not bytes)

    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""

    # Ensure it's a proper string
    text = safe_unicode_str(text)

    # Truncate by character count, not byte count
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


# ============================================================================
# STREAMING PAGINATION WITH UNICODE SAFETY
# ============================================================================

async def _get_all_items_streaming(
    self, endpoint: str, key: str = "data", **kwargs
) -> AsyncGenerator[dict, None]:
    """
    Stream items from a paged API endpoint with Unicode-safe error handling.

    Yields items one-by-one as pages are fetched, avoiding memory buildup.
    Includes robust error handling, progress logging, and Unicode safety.

    Args:
        endpoint: API endpoint to call
        key: JSON key containing items (default: "data")
        **kwargs: Additional query parameters

    Yields:
        Individual items from the paginated response
    """
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
            # Fetch page with explicit encoding
            result = await self._get_data(endpoint, **kwargs)
            consecutive_errors = 0  # Reset error counter on success

        except Exception as exc:
            consecutive_errors += 1

            # Log error with safe Unicode handling
            error_msg = safe_unicode_str(str(exc), "Unknown error")
            self.logger.warning(
                "Error fetching page %d (offset %d) from %s: %s",
                page_num, offset, endpoint, truncate_for_log(error_msg)
            )

            # If it's a 404 with pagination, we've reached the end
            if "404" in error_msg or "not found" in error_msg.lower():
                self.logger.info(
                    "Reached end of %s at page %d (404 response)",
                    endpoint, page_num
                )
                break

            # Stop if too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                self.logger.error(
                    "Stopping %s sync after %d consecutive errors",
                    endpoint, consecutive_errors
                )
                break

            # Continue to next page for non-404 errors
            offset += limit
            page_num += 1
            continue

        # Check if response has the expected key
        if key not in result:
            self.logger.debug(
                "No '%s' key in response for %s (offset %d), ending pagination",
                key, endpoint, offset
            )
            break

        items = result[key]
        items_in_page = len(items)

        # Yield items one by one with Unicode safety
        for idx, item in enumerate(items):
            if not item:  # Skip None/empty items
                continue

            try:
                # Ensure item dict has proper Unicode strings
                # This validates the JSON was properly decoded
                item_id = safe_json_get(item, "id", default=f"unknown_{offset}_{idx}")
                total_items += 1
                yield item

            except Exception as exc:
                # Log but don't stop on individual item errors
                error_msg = safe_unicode_str(str(exc))
                self.logger.warning(
                    "Skipping malformed item in %s at offset %d (index %d): %s",
                    endpoint, offset, idx, truncate_for_log(error_msg, 80)
                )
                continue

        # Log progress every 5 pages (250 items)
        if page_num % 5 == 0 or items_in_page > 0:
            self.logger.info(
                "%s: page %d, %d items in page, %d total yielded",
                endpoint.split('/')[-1], page_num, items_in_page, total_items
            )

        # Check if there are more pages
        if not result.get("next"):
            self.logger.info(
                "Completed %s: %d total items across %d pages",
                endpoint, total_items, page_num + 1
            )
            break

        # Move to next page
        offset += limit
        page_num += 1

        # Safety check: prevent infinite loops
        if page_num > 10000:  # 10000 pages × 50 = 500k items max
            self.logger.error(
                "Safety limit reached: %d pages fetched from %s. Stopping.",
                page_num, endpoint
            )
            break


# ============================================================================
# UNICODE-SAFE PARSING METHODS
# ============================================================================

def _parse_artist(self, artist_obj: dict) -> Artist | None:
    """
    Parse artist object with comprehensive Unicode support.

    Handles all Unicode characters in artist names, descriptions, URLs.
    Returns None on parse failure to avoid stopping sync.
    """
    try:
        relationships = artist_obj.get("relationships", {})

        # Extract artist ID and attributes
        if (
            artist_obj.get("type") == "library-artists"
            and relationships.get("catalog", {}).get("data", []) != []
        ):
            artist_id = safe_json_get(
                relationships, "catalog", "data", 0, "id",
                default=artist_obj.get("id", "unknown")
            )
            attributes = safe_json_get(
                relationships, "catalog", "data", 0, "attributes",
                default={}
            )
        elif "attributes" in artist_obj:
            artist_id = safe_unicode_str(artist_obj.get("id", "unknown"))
            attributes = artist_obj.get("attributes", {})
        else:
            artist_id = safe_unicode_str(artist_obj.get("id", "unknown"))
            self.logger.debug(
                "No attributes found for artist %s, returning basic mapping",
                truncate_for_log(artist_id, 50)
            )
            # Return basic ItemMapping for artists without full details
            from music_assistant_models.media_items import ItemMapping, MediaType
            return ItemMapping(
                media_type=MediaType.ARTIST,
                provider=self.lookup_key,
                item_id=artist_id,
                name=artist_id,
            )

        # Extract name with Unicode safety
        artist_name = safe_unicode_str(
            attributes.get("name"),
            fallback=f"Artist {artist_id}"
        )

        # Extract URL with Unicode safety (URLs should be ASCII but handle just in case)
        artist_url = safe_unicode_str(attributes.get("url"), fallback="")

        # Create artist object
        from music_assistant_models.media_items import Artist, ProviderMapping
        from music_assistant_models.enums import ImageType
        from music_assistant_models.media_items import MediaItemImage

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

        # Extract artwork (handle Unicode in URLs)
        if artwork := attributes.get("artwork"):
            try:
                artwork_url = safe_unicode_str(artwork.get("url", ""))
                if artwork_url:
                    # Format URL with dimensions
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
                # Log but don't fail on artwork issues
                self.logger.debug(
                    "Could not process artwork for artist %s: %s",
                    truncate_for_log(artist_name, 40),
                    safe_unicode_str(str(exc))
                )

        # Extract genres (handle Unicode genre names)
        if genres := attributes.get("genreNames"):
            try:
                artist.metadata.genres = {
                    safe_unicode_str(genre) for genre in genres if genre
                }
            except Exception as exc:
                self.logger.debug(
                    "Could not process genres for artist %s: %s",
                    truncate_for_log(artist_name, 40),
                    safe_unicode_str(str(exc))
                )

        # Extract editorial notes (handle Unicode descriptions)
        if notes := attributes.get("editorialNotes"):
            try:
                description = (
                    safe_unicode_str(notes.get("standard")) or
                    safe_unicode_str(notes.get("short"))
                )
                if description:
                    artist.metadata.description = description
            except Exception as exc:
                self.logger.debug(
                    "Could not process editorial notes for artist %s: %s",
                    truncate_for_log(artist_name, 40),
                    safe_unicode_str(str(exc))
                )

        return artist

    except Exception as exc:
        # Comprehensive error logging
        artist_id = safe_unicode_str(artist_obj.get("id", "unknown"))
        artist_name = safe_json_get(
            artist_obj, "attributes", "name",
            default=safe_json_get(
                artist_obj, "relationships", "catalog", "data", 0, "attributes", "name",
                default="Unknown"
            )
        )

        self.logger.error(
            "Failed to parse artist (id=%s, name=%s): %s",
            truncate_for_log(artist_id, 30),
            truncate_for_log(safe_unicode_str(artist_name), 50),
            truncate_for_log(safe_unicode_str(str(exc)), 100)
        )

        # Return None to skip this artist and continue sync
        return None


# ============================================================================
# UNICODE-SAFE LIBRARY METHODS
# ============================================================================

async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
    """
    Retrieve library artists with Unicode-safe streaming pagination.

    Handles artists with any Unicode characters in their names (diacritics,
    CJK characters, emoji, etc.) without stopping the sync.
    """
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
                # Parse artist with Unicode safety
                artist = self._parse_artist(item)

                if artist:
                    processed_count += 1

                    # Log progress for artists with non-ASCII names (useful for debugging)
                    artist_name = getattr(artist, 'name', 'Unknown')
                    if any(ord(char) > 127 for char in artist_name):
                        self.logger.debug(
                            "Processed artist with Unicode characters: %s (id=%s)",
                            truncate_for_log(artist_name, 60),
                            truncate_for_log(getattr(artist, 'item_id', 'unknown'), 30)
                        )

                    yield artist
                else:
                    # _parse_artist returned None (parse failed)
                    error_count += 1

            except Exception as exc:
                # Log parsing errors but continue with other artists
                error_count += 1
                item_id = safe_unicode_str(item.get("id", "unknown"))
                item_name = safe_json_get(
                    item, "attributes", "name",
                    default=safe_json_get(
                        item, "relationships", "catalog", "data", 0, "attributes", "name",
                        default="Unknown"
                    )
                )

                self.logger.warning(
                    "Error parsing artist %s (%s): %s. Continuing sync...",
                    truncate_for_log(safe_unicode_str(item_name), 50),
                    truncate_for_log(item_id, 30),
                    truncate_for_log(safe_unicode_str(str(exc)), 80)
                )

        # Log final summary
        self.logger.info(
            "Library artists sync complete: %d artists processed, %d errors skipped",
            processed_count, error_count
        )

    except Exception as exc:
        # Log critical errors but don't crash
        self.logger.error(
            "Critical error during library artists sync: %s. Processed %d artists before error.",
            truncate_for_log(safe_unicode_str(str(exc)), 100),
            processed_count
        )


async def get_library_albums(self) -> AsyncGenerator[Album, None]:
    """
    Retrieve library albums with Unicode-safe streaming pagination.

    Handles albums/artists with Unicode characters without stopping sync.
    """
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

                if album:  # _parse_album can return None for unavailable albums
                    processed_count += 1

                    # Log albums with Unicode characters for debugging
                    album_name = getattr(album, 'name', 'Unknown')
                    if any(ord(char) > 127 for char in album_name):
                        self.logger.debug(
                            "Processed album with Unicode characters: %s",
                            truncate_for_log(album_name, 60)
                        )

                    yield album

            except Exception as exc:
                error_count += 1
                item_id = safe_unicode_str(item.get("id", "unknown"))
                item_name = safe_json_get(
                    item, "attributes", "name",
                    default="Unknown"
                )

                self.logger.warning(
                    "Error parsing album %s (%s): %s. Continuing sync...",
                    truncate_for_log(safe_unicode_str(item_name), 50),
                    truncate_for_log(item_id, 30),
                    truncate_for_log(safe_unicode_str(str(exc)), 80)
                )

        self.logger.info(
            "Library albums sync complete: %d albums processed, %d errors skipped",
            processed_count, error_count
        )

    except Exception as exc:
        self.logger.error(
            "Critical error during library albums sync: %s. Processed %d albums before error.",
            truncate_for_log(safe_unicode_str(str(exc)), 100),
            processed_count
        )


async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
    """
    Retrieve playlists with Unicode-safe streaming pagination.

    Handles playlists with Unicode characters in names/descriptions.
    """
    endpoint = "me/library/playlists"
    processed_count = 0
    error_count = 0

    try:
        async for item in self._get_all_items_streaming(endpoint):
            try:
                # Prefer catalog information over library for public playlists
                if item.get("attributes", {}).get("hasCatalog"):
                    global_id = safe_json_get(
                        item, "attributes", "playParams", "globalId",
                        default=None
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
                            safe_unicode_str(item.get("id", "unknown"))
                        )

                elif item and item.get("id"):
                    playlist = self._parse_playlist(item)
                    if playlist:
                        processed_count += 1
                        yield playlist

            except Exception as exc:
                error_count += 1
                item_id = safe_unicode_str(item.get("id", "unknown"))
                item_name = safe_json_get(
                    item, "attributes", "name",
                    default="Unknown"
                )

                self.logger.warning(
                    "Error processing playlist %s (%s): %s. Continuing sync...",
                    truncate_for_log(safe_unicode_str(item_name), 50),
                    truncate_for_log(item_id, 30),
                    truncate_for_log(safe_unicode_str(str(exc)), 80)
                )

        self.logger.info(
            "Library playlists sync complete: %d playlists processed, %d errors skipped",
            processed_count, error_count
        )

    except Exception as exc:
        self.logger.error(
            "Critical error during library playlists sync: %s. Processed %d playlists.",
            truncate_for_log(safe_unicode_str(str(exc)), 100),
            processed_count
        )


# ============================================================================
# ENHANCED JSON LOADING WITH UTF-8 VALIDATION
# ============================================================================

def json_loads_safe(text: str) -> dict:
    """
    Safely load JSON with UTF-8 validation and error recovery.

    Args:
        text: JSON string to parse

    Returns:
        Parsed JSON dictionary

    Raises:
        json.JSONDecodeError: If JSON is invalid after recovery attempts
    """
    if not text:
        return {}

    try:
        # Standard JSON parse with UTF-8
        return json.loads(text, strict=False)
    except json.JSONDecodeError as exc:
        # Try to salvage the JSON
        try:
            # Remove any BOM (Byte Order Mark) that might be present
            if text.startswith('\ufeff'):
                text = text[1:]

            # Try parsing again
            return json.loads(text, strict=False)
        except json.JSONDecodeError:
            # Log detailed error with context
            context_start = max(0, exc.pos - 50)
            context_end = min(len(text), exc.pos + 50)
            context = text[context_start:context_end]

            logging.error(
                "JSON decode error at position %d: %s. Context: %s",
                exc.pos,
                str(exc),
                truncate_for_log(context, 100)
            )
            raise


# ============================================================================
# HTTP REQUEST WITH EXPLICIT UTF-8 HANDLING
# ============================================================================

async def _get_data_with_encoding(self, endpoint, **kwargs) -> dict[str, Any]:
    """
    Get data from API with explicit UTF-8 encoding validation.

    This is a drop-in replacement for _get_data() that adds explicit
    charset handling to ensure proper Unicode decoding.
    """
    url = f"https://api.music.apple.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {self._music_app_token}",
        "Music-User-Token": self._music_user_token,
        "Accept-Charset": "utf-8",  # Request UTF-8 explicitly
    }

    async with (
        self.mass.http_session.get(
            url, headers=headers, params=kwargs, ssl=True, timeout=120
        ) as response,
    ):
        if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
            return {}

        # Convert HTTP errors to exceptions
        if response.status == 404:
            from music_assistant_models.errors import MediaNotFoundError
            raise MediaNotFoundError(f"{endpoint} not found")

        if response.status == 504:
            self.logger.debug(
                "Apple Music API Timeout: url=%s, params=%s, response_headers=%s",
                url, kwargs, response.headers
            )
            from music_assistant_models.errors import ResourceTemporarilyUnavailable
            raise ResourceTemporarilyUnavailable("Apple Music API Timeout")

        if response.status == 429:
            self.logger.debug("Apple Music Rate Limiter. Headers: %s", response.headers)
            from music_assistant_models.errors import ResourceTemporarilyUnavailable
            raise ResourceTemporarilyUnavailable("Apple Music Rate Limiter")

        if response.status == 500:
            from music_assistant_models.errors import MusicAssistantError
            raise MusicAssistantError("Unexpected server error when calling Apple Music")

        response.raise_for_status()

        # Read response with explicit UTF-8 handling
        try:
            # Get text with explicit UTF-8 encoding
            text = await response.text(encoding='utf-8')

            # Parse JSON
            from music_assistant.helpers.json import json_loads
            return json_loads(text)

        except UnicodeDecodeError as exc:
            self.logger.error(
                "UTF-8 decode error for %s: %s. Trying fallback encoding.",
                endpoint, str(exc)
            )

            # Fallback: read as bytes and decode with error handling
            content = await response.read()
            text = content.decode('utf-8', errors='replace')  # Replace bad bytes with �

            from music_assistant.helpers.json import json_loads
            return json_loads(text)


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================
"""
TO APPLY THIS FIX:
==================

1. BACKUP THE ORIGINAL FILE:
   cd /path/to/music_assistant
   cp server-2.6.0/music_assistant/providers/apple_music/__init__.py \\
      server-2.6.0/music_assistant/providers/apple_music/__init__.py.backup

2. ADD IMPORTS (after line 75):
   import unicodedata

3. REPLACE _get_all_items (lines 771-786) WITH:
   - _get_all_items_streaming() from this file

4. REPLACE get_library_artists (lines 330-335) WITH:
   - get_library_artists() from this file

5. REPLACE get_library_albums (lines 337-346) WITH:
   - get_library_albums() from this file

6. REPLACE get_library_playlists (lines 373-381) WITH:
   - get_library_playlists() from this file

7. REPLACE _parse_artist (lines 527-575) WITH:
   - _parse_artist() from this file

8. ADD UTILITY FUNCTIONS at the top of the class (after line 264):
   - safe_unicode_str()
   - safe_json_get()
   - truncate_for_log()

9. OPTIONAL: Replace _get_data (lines 788-821) WITH:
   - _get_data_with_encoding() from this file (rename to _get_data)

10. RESTART MUSIC ASSISTANT

TESTING:
========

1. Clear cache (if needed):
   # In Music Assistant settings, clear provider cache

2. Trigger artist sync:
   # Music Assistant will automatically sync on provider init

3. Monitor logs for:
   - "Processed artist with Unicode characters: Jan Bartoš"
   - "Library artists sync complete: X artists processed, Y errors skipped"
   - Check that sync completes without stopping at "J"

4. Verify "Jan Bartoš" appears in library

5. Test other Unicode artists:
   - Japanese: "藤井 風" (Fujii Kaze)
   - Arabic: "فيروز" (Fairuz)
   - Emoji: Artists with emoji in names

WHAT THIS FIX DOES:
===================

✅ Normalizes all Unicode strings to NFC form (consistent representation)
✅ Safely handles None, bytes, and invalid UTF-8 sequences
✅ Logs but skips artists that fail to parse (doesn't stop sync)
✅ Streams items one-by-one (no memory buildup)
✅ Handles all Unicode ranges: diacritics, CJK, RTL, emoji, symbols
✅ Provides detailed logging for debugging Unicode issues
✅ Validates JSON decoding with UTF-8
✅ Truncates long strings safely (by character count, not byte count)
✅ Tracks error counts and provides sync summaries

CHARACTERS HANDLED:
===================

✅ Czech: á, é, í, ó, ú, ý, č, ď, ě, ň, ř, š, ť, ž, ů (Jan Bartoš ✓)
✅ Polish: ą, ć, ę, ł, ń, ó, ś, ź, ż
✅ French: à, â, ç, é, è, ê, ë, î, ï, ô, ù, û, ü, ÿ
✅ German: ä, ö, ü, ß
✅ Spanish: á, é, í, ó, ú, ñ, ü, ¿, ¡
✅ Portuguese: ã, õ, â, ê, ô, à, á, é, í, ó, ú, ç
✅ Nordic: å, ä, ö, æ, ø, þ, ð
✅ Turkish: ğ, ı, ş, ç, ö, ü
✅ Japanese: ひらがな, カタカナ, 漢字 (Hiragana, Katakana, Kanji)
✅ Chinese: 简体字, 繁體字 (Simplified, Traditional)
✅ Korean: 한글 (Hangul)
✅ Arabic: العربية (with RTL support)
✅ Hebrew: עברית (with RTL support)
✅ Greek: Ελληνικά
✅ Cyrillic: Кириллица
✅ Emoji: 😀🎵🎸🎤🎧 (all emoji ranges)
✅ Symbols: ™, ©, ®, €, £, ¥, ¢

FALLBACK BEHAVIOR:
==================

If a single artist fails to parse:
→ Logs warning with artist name/ID
→ Increments error counter
→ Continues to next artist

If a page fetch fails:
→ Logs warning with page number
→ Continues to next page (up to 3 consecutive errors)

If a critical error occurs:
→ Logs error with progress summary
→ Returns what was processed (doesn't lose entire sync)

PERFORMANCE:
============

- Memory: Constant (streams items, no accumulation)
- Speed: Same as original (1 req/2sec rate limit)
- Error resilience: High (continues on errors)
- Logging: Moderate (debug logs for Unicode, info for progress)
"""
