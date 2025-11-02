#!/usr/bin/env python3
"""
Fix for Apple Music library pagination issue.

PROBLEM:
--------
The current _get_all_items() method loads ALL items into memory before yielding,
causing timeouts and memory issues with large libraries (thousands of artists).

Artists stop loading around "J" because:
1. All items accumulated in memory (all_items list)
2. 120-second timeout with rate limiting (1 req/2sec)
3. Generator pattern not truly streaming

SOLUTION:
---------
Replace batch loading with true streaming pagination that:
1. Yields items as each page is fetched (reduces memory)
2. Avoids timeout by streaming results incrementally
3. Adds progress logging for debugging
4. Handles errors gracefully per-page

IMPLEMENTATION:
--------------
Replace the methods in server-2.6.0/music_assistant/providers/apple_music/__init__.py
"""

from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from music_assistant_models.media_items import Artist, Album, Track, Playlist


# ============================================================================
# OPTION 1: STREAMING PAGINATION (RECOMMENDED)
# ============================================================================
# Replace lines 771-786 in __init__.py with this:

async def _get_all_items_streaming(
    self, endpoint: str, key: str = "data", **kwargs
) -> AsyncGenerator[dict, None]:
    """
    Stream items from a paged API endpoint.

    Yields items one-by-one as pages are fetched, avoiding memory buildup.
    Includes progress logging and per-page error handling.

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

    while True:
        kwargs["limit"] = limit
        kwargs["offset"] = offset

        try:
            result = await self._get_data(endpoint, **kwargs)
        except Exception as exc:
            # Log error but don't stop entire sync
            self.logger.warning(
                "Error fetching page %d (offset %d) from %s: %s",
                page_num, offset, endpoint, exc
            )
            # If it's a 404 with pagination, we've reached the end
            if "404" in str(exc) or "not found" in str(exc).lower():
                break
            # For other errors, stop to avoid infinite loop
            raise

        # Check if response has the expected key
        if key not in result:
            self.logger.debug(
                "No '%s' key in response for %s (offset %d), ending pagination",
                key, endpoint, offset
            )
            break

        items = result[key]
        items_in_page = len(items)

        # Yield items one by one
        for item in items:
            if item:  # Skip None/empty items
                total_items += 1
                yield item

        # Log progress every 5 pages
        if page_num % 5 == 0:
            self.logger.debug(
                "Fetched page %d from %s: %d items (total so far: %d)",
                page_num, endpoint, items_in_page, total_items
            )

        # Check if there are more pages
        if not result.get("next"):
            self.logger.info(
                "Completed fetching from %s: %d total items across %d pages",
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


# Replace get_library_artists (lines 330-335) with:
async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
    """Retrieve library artists from Apple Music using streaming pagination."""
    endpoint = "me/library/artists"

    async for item in self._get_all_items_streaming(
        endpoint, include="catalog", extend="editorialNotes"
    ):
        if item and item.get("id"):
            try:
                yield self._parse_artist(item)
            except Exception as exc:
                # Log parsing errors but continue with other artists
                self.logger.warning(
                    "Error parsing artist %s: %s",
                    item.get("id", "unknown"), exc
                )


# Replace get_library_albums (lines 337-346) with:
async def get_library_albums(self) -> AsyncGenerator[Album, None]:
    """Retrieve library albums from Apple Music using streaming pagination."""
    endpoint = "me/library/albums"

    async for item in self._get_all_items_streaming(
        endpoint, include="catalog,artists", extend="editorialNotes"
    ):
        if item and item.get("id"):
            try:
                album = self._parse_album(item)
                if album:  # _parse_album can return None for unavailable albums
                    yield album
            except Exception as exc:
                self.logger.warning(
                    "Error parsing album %s: %s",
                    item.get("id", "unknown"), exc
                )


# Replace get_library_playlists (lines 373-381) with:
async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
    """Retrieve playlists from Apple Music using streaming pagination."""
    endpoint = "me/library/playlists"

    async for item in self._get_all_items_streaming(endpoint):
        try:
            # Prefer catalog information over library for public playlists
            if item["attributes"]["hasCatalog"]:
                yield await self.get_playlist(item["attributes"]["playParams"]["globalId"])
            elif item and item.get("id"):
                yield self._parse_playlist(item)
        except Exception as exc:
            self.logger.warning(
                "Error processing playlist %s: %s",
                item.get("id", "unknown"), exc
            )


# ============================================================================
# OPTION 2: KEEP ORIGINAL _get_all_items FOR BACKWARD COMPATIBILITY
# ============================================================================
# If other code depends on _get_all_items returning a list, keep both:

async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
    """
    Get all items from a paged list (legacy method).

    For large libraries, prefer _get_all_items_streaming() to avoid
    memory buildup and timeouts.
    """
    items = []
    async for item in self._get_all_items_streaming(endpoint, key, **kwargs):
        items.append(item)
    return items


# ============================================================================
# OPTION 3: CHUNKED BATCH APPROACH (ALTERNATIVE)
# ============================================================================
# If you prefer batching over pure streaming, use this instead:

async def _get_all_items_chunked(
    self, endpoint: str, key: str = "data", chunk_size: int = 5, **kwargs
) -> AsyncGenerator[list[dict], None]:
    """
    Stream items in chunks from a paged API endpoint.

    Yields batches of items every `chunk_size` pages, balancing memory
    usage and processing efficiency.

    Args:
        endpoint: API endpoint to call
        key: JSON key containing items
        chunk_size: Number of pages to fetch before yielding (default: 5)
        **kwargs: Additional query parameters

    Yields:
        Lists of items (batches)
    """
    limit = 50
    offset = 0
    page_num = 0
    chunk_items = []

    while True:
        kwargs["limit"] = limit
        kwargs["offset"] = offset

        try:
            result = await self._get_data(endpoint, **kwargs)
        except Exception as exc:
            # Yield accumulated items before error
            if chunk_items:
                yield chunk_items
            self.logger.warning(
                "Error at offset %d from %s: %s", offset, endpoint, exc
            )
            break

        if key not in result:
            break

        # Accumulate items
        chunk_items.extend(result[key])
        page_num += 1

        # Yield chunk every `chunk_size` pages
        if page_num % chunk_size == 0:
            self.logger.debug(
                "Yielding chunk: %d items from %s (page %d)",
                len(chunk_items), endpoint, page_num
            )
            yield chunk_items
            chunk_items = []

        # Check for more pages
        if not result.get("next"):
            # Yield remaining items
            if chunk_items:
                yield chunk_items
            break

        offset += limit


# Usage example for chunked approach:
async def get_library_artists_chunked(self) -> AsyncGenerator[Artist, None]:
    """Retrieve library artists using chunked batching."""
    endpoint = "me/library/artists"

    async for items_batch in self._get_all_items_chunked(
        endpoint, chunk_size=5, include="catalog", extend="editorialNotes"
    ):
        for item in items_batch:
            if item and item.get("id"):
                yield self._parse_artist(item)


# ============================================================================
# RECOMMENDED APPROACH
# ============================================================================
"""
OPTION 1 (Streaming) is RECOMMENDED because:

1. **Memory Efficient**: Yields items one-by-one, no accumulation
2. **Timeout Resistant**: Streams results incrementally, no 120s risk
3. **True Async Generator**: Proper use of AsyncGenerator pattern
4. **Progress Logging**: Debug visibility into sync progress
5. **Error Resilience**: Per-item error handling won't stop entire sync
6. **Scalability**: Works with libraries of any size (1k-100k items)

To apply:
1. Replace _get_all_items() with _get_all_items_streaming()
2. Update get_library_artists/albums/playlists to use async for
3. Add per-item error handling as shown
4. Test with large library (should now load all artists A-Z)

For tracks (get_library_tracks), keep the existing batch approach since
it needs to fetch catalog data in bulk (lines 348-371).
"""
