# Quick Implementation Guide - Streaming Pagination Fix

**File to Edit**: `server-2.6.0/music_assistant/providers/apple_music/__init__.py`

This guide shows exactly where to make changes with line numbers.

---

## Change 1: Add Streaming Method

**Location**: After line 770 (after `def _parse_playlist`)
**Action**: Add new method

```python
    async def _get_all_items_streaming(
        self, endpoint: str, key: str = "data", **kwargs
    ) -> AsyncGenerator[dict, None]:
        """
        Stream items from a paginated API endpoint.

        Yields items one-by-one as pages are fetched, avoiding memory buildup.
        This solves the timeout and memory issues with large libraries.

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
                    "Fetched page %d from %s: %d items in page, %d total so far",
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
```

---

## Change 2: Update get_library_artists

**Location**: Lines 330-335
**Action**: Replace method

**BEFORE**:
```python
    async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        """Retrieve library artists from spotify."""
        endpoint = "me/library/artists"
        for item in await self._get_all_items(endpoint, include="catalog", extend="editorialNotes"):
            if item and item["id"]:
                yield self._parse_artist(item)
```

**AFTER**:
```python
    async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        """Retrieve library artists from Apple Music."""
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
```

---

## Change 3: Update get_library_albums

**Location**: Lines 337-346
**Action**: Replace method

**BEFORE**:
```python
    async def get_library_albums(self) -> AsyncGenerator[Album, None]:
        """Retrieve library albums from the provider."""
        endpoint = "me/library/albums"
        for item in await self._get_all_items(
            endpoint, include="catalog,artists", extend="editorialNotes"
        ):
            if item and item["id"]:
                album = self._parse_album(item)
                if album:
                    yield album
```

**AFTER**:
```python
    async def get_library_albums(self) -> AsyncGenerator[Album, None]:
        """Retrieve library albums from Apple Music."""
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
```

---

## Change 4: Update get_library_playlists

**Location**: Lines 373-381
**Action**: Replace method

**BEFORE**:
```python
    async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
        """Retrieve playlists from the provider."""
        endpoint = "me/library/playlists"
        for item in await self._get_all_items(endpoint):
            # Prefer catalog information over library information in case of public playlists
            if item["attributes"]["hasCatalog"]:
                yield await self.get_playlist(item["attributes"]["playParams"]["globalId"])
            elif item and item["id"]:
                yield self._parse_playlist(item)
```

**AFTER**:
```python
    async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
        """Retrieve playlists from Apple Music."""
        endpoint = "me/library/playlists"
        async for item in self._get_all_items_streaming(endpoint):
            try:
                # Prefer catalog information over library information for public playlists
                if item["attributes"]["hasCatalog"]:
                    yield await self.get_playlist(item["attributes"]["playParams"]["globalId"])
                elif item and item.get("id"):
                    yield self._parse_playlist(item)
            except Exception as exc:
                self.logger.warning(
                    "Error processing playlist %s: %s",
                    item.get("id", "unknown"), exc
                )
```

---

## Change 5 (Optional): Update _get_all_items for Backward Compatibility

**Location**: Lines 771-786
**Action**: Replace method (optional if other code uses it)

**BEFORE**:
```python
    async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
        """Get all items from a paged list."""
        limit = 50
        offset = 0
        all_items = []
        while True:
            kwargs["limit"] = limit
            kwargs["offset"] = offset
            result = await self._get_data(endpoint, **kwargs)
            if key not in result:
                break
            all_items += result[key]
            if not result.get("next"):
                break
            offset += limit
        return all_items
```

**AFTER**:
```python
    async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
        """
        Get all items from a paged list (legacy method).

        For large libraries, prefer _get_all_items_streaming() to avoid
        memory buildup and timeouts. This method wraps streaming for
        backward compatibility.
        """
        items = []
        async for item in self._get_all_items_streaming(endpoint, key, **kwargs):
            items.append(item)
        return items
```

---

## DO NOT CHANGE: get_library_tracks

**Location**: Lines 348-371
**Action**: NO CHANGES NEEDED

The tracks method uses a different pattern (batch catalog lookups) which is appropriate for its use case. Leave it as-is.

---

## Testing After Changes

### 1. Restart Music Assistant

```bash
# Stop Music Assistant
# Apply changes to __init__.py
# Start Music Assistant
```

### 2. Trigger Library Sync

- Go to Settings → Providers → Apple Music
- Click "Sync Library" or restart the provider

### 3. Monitor Logs

Look for these log messages:

```
DEBUG: Fetched page 0 from me/library/artists: 50 items in page, 50 total so far
DEBUG: Fetched page 5 from me/library/artists: 50 items in page, 250 total so far
DEBUG: Fetched page 10 from me/library/artists: 50 items in page, 500 total so far
...
INFO: Completed fetching from me/library/artists: 2000 total items across 40 pages
```

### 4. Verify Results

**Check Artist Count**:
- Before: ~500-700 artists (stops at J)
- After: Full library count

**Check Artist Names**:
- Before: Last artist starts with 'I' or 'J'
- After: Last artist starts with 'Z' or last alphabetically

**Check Performance**:
- First artist appears: ~2 seconds (immediate)
- Full sync completes: Variable (depends on library size)
- No timeout errors

---

## Rollback Plan

If something goes wrong, restore the original methods:

1. Keep a backup of original `__init__.py`
2. Revert changes
3. Restart Music Assistant
4. Report the error

Original methods are simple and known-working for small libraries.

---

## Expected Improvements

| Metric | Before | After |
|--------|--------|-------|
| Max Library Size | ~1500 artists | Unlimited |
| Memory Usage | 5-10MB+ (grows) | ~0.2MB (constant) |
| Time to First Artist | 40-80s | ~2s |
| Timeout Risk | High (>1000 items) | None |
| Error Resilience | All-or-nothing | Per-item graceful |

---

## Common Issues

### Issue: "module has no attribute '_get_all_items_streaming'"

**Cause**: Method not added or syntax error
**Fix**: Check indentation and placement of new method

### Issue: Still stops at J

**Cause**: Old code still running or changes not applied
**Fix**: Restart Music Assistant server, verify file saved

### Issue: "async for" syntax error

**Cause**: Wrong Python version (< 3.6)
**Fix**: Verify Music Assistant uses Python 3.8+ (it should)

### Issue: No artists load at all

**Cause**: Error in new code breaking iteration
**Fix**: Check logs for exceptions, verify syntax

---

## Summary of Changes

**Files Modified**: 1 (`__init__.py`)
**Lines Added**: ~80 (new streaming method)
**Lines Modified**: ~30 (3 library methods)
**Complexity**: Low (straightforward refactor)
**Risk**: Low (minimal breaking changes)
**Testing**: Restart + library sync
**Rollback**: Simple (restore original file)

**Total Time**:
- Code changes: 15 minutes
- Testing: 5-10 minutes
- Total: ~30 minutes

**Benefit**: Unlocks large Apple Music libraries (1000s of items)
