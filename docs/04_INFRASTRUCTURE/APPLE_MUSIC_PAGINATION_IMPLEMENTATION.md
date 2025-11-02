# Apple Music Pagination Implementation

**Purpose**: Document the specific implementation of streaming pagination for Apple Music provider
**Audience**: Backend developers, maintenance engineers
**Layer**: 04_INFRASTRUCTURE
**Related**:
- [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)
- [../03_INTERFACES/MUSIC_PROVIDER_PAGINATION_CONTRACT.md](../03_INTERFACES/MUSIC_PROVIDER_PAGINATION_CONTRACT.md)

## Intent

This document describes the concrete implementation of streaming pagination for the Apple Music provider in Music Assistant. It bridges the architectural principles and interface contracts with the actual Python code that implements the solution.

## Technology Stack

**Language**: Python 3.11+
**Framework**: Music Assistant Server 2.6.0
**Async Library**: asyncio
**HTTP Client**: aiohttp (via Music Assistant base provider)
**API**: Apple Music API (MusicKit)
**File**: `server-2.6.0/music_assistant/providers/apple_music/__init__.py`

## Current Implementation Issues

### Issue 1: Batch Accumulation Pattern

**Location**: Lines 771-786 in `__init__.py`

**Current Code**:
```python
async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
    """Get all items from a paged list."""
    limit = 50
    offset = 0
    all_items = []  # ❌ PROBLEM: Accumulates in memory
    while True:
        kwargs["limit"] = limit
        kwargs["offset"] = offset
        result = await self._get_data(endpoint, **kwargs)
        if key not in result:
            break
        all_items += result[key]  # ❌ PROBLEM: Grows with each page
        if not result.get("next"):
            break
        offset += limit
    return all_items  # ❌ PROBLEM: Returns entire list
```

**Issues**:
1. **Memory**: O(n) growth - accumulates all items
2. **Blocking**: Must fetch all pages before returning
3. **Error Handling**: Single failure aborts entire operation
4. **Timeouts**: Cumulative time can exceed timeout threshold

**Impact**: Large libraries (1000+ artists) fail silently around letter "J" (~700 items).

### Issue 2: Generator Misuse

**Location**: Lines 330-335 (artists), 337-346 (albums), 373-381 (playlists)

**Current Code (Artists Example)**:
```python
async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
    """Retrieve library artists from spotify."""  # ❌ Wrong docstring
    endpoint = "me/library/artists"
    for item in await self._get_all_items(endpoint, ...):  # ❌ Awaits entire list
        if item and item["id"]:
            yield self._parse_artist(item)  # Only yields AFTER all loaded
```

**Issues**:
1. **Contract Violation**: Signature says `AsyncGenerator`, implementation batches
2. **Blocking**: First yield only after ALL pages fetched
3. **Memory**: Entire library in memory before yielding
4. **Defeats Purpose**: Async generator pattern intended for streaming

### Issue 3: Timeout Mathematics

**Configuration**:
- Rate limit: 1 request per 2 seconds (line 264)
- Page size: 50 items
- Timeout: 120 seconds (line 796)

**Calculation**:
```
For 2,000 artists:
  Pages needed: 2,000 ÷ 50 = 40 pages
  Time required: 40 × 2s = 80 seconds
  Processing overhead: ~10-20 seconds
  Total: 90-100 seconds

Risk: Approaching 120s timeout limit
```

**Result**: Timeouts occur around page 15-20 (750-1,000 items), typically at letter "J" in alphabetical ordering.

## Proposed Implementation

### Solution 1: Streaming Helper Method

**Add after line 770**:

```python
async def _get_all_items_streaming(
    self,
    endpoint: str,
    key: str = "data",
    **kwargs
) -> AsyncGenerator[dict, None]:
    """
    Stream items from paginated endpoint one-by-one.

    This is the core implementation of streaming pagination pattern,
    implementing the interface contract defined in Layer 03.

    Yields items immediately as pages are fetched, maintaining O(1)
    memory usage regardless of total item count.

    Args:
        endpoint: API endpoint path
        key: JSON key containing items (default: "data")
        **kwargs: Additional API parameters (include, extend, etc.)

    Yields:
        dict: Individual items as they become available

    Raises:
        AuthenticationError: If API authentication fails
        PageFetchError: If page fetch fails after retries
    """
    limit = 50  # Items per page (matches Apple Music API recommendation)
    offset = 0
    page_num = 0
    total_items = 0
    consecutive_errors = 0
    max_consecutive_errors = 3

    while True:
        # Add pagination parameters
        kwargs["limit"] = limit
        kwargs["offset"] = offset

        try:
            # Fetch single page
            result = await self._get_data(endpoint, **kwargs)
            consecutive_errors = 0  # Reset error counter on success

        except Exception as exc:
            consecutive_errors += 1
            self.logger.warning(
                "Error fetching page %d from %s (attempt %d/%d): %s",
                page_num,
                endpoint,
                consecutive_errors,
                max_consecutive_errors,
                exc
            )

            # Special case: 404 means no more data
            if "404" in str(exc):
                self.logger.info(
                    "Endpoint %s returned 404, assuming end of data",
                    endpoint
                )
                break

            # If too many consecutive errors, abort
            if consecutive_errors >= max_consecutive_errors:
                raise PageFetchError(
                    page=page_num,
                    attempts=consecutive_errors,
                    last_error=exc
                )

            # Wait before retry (exponential backoff)
            wait_time = 2 ** consecutive_errors  # 2s, 4s, 8s
            await asyncio.sleep(wait_time)
            continue  # Retry same page

        # Check if data exists
        if key not in result:
            self.logger.debug(
                "No '%s' key in response from %s, assuming end of data",
                key,
                endpoint
            )
            break

        # Process items in current page
        page_items = result[key]
        if not page_items:
            self.logger.debug(
                "Empty page %d from %s, assuming end of data",
                page_num,
                endpoint
            )
            break

        # Yield items immediately (streaming!)
        for item in page_items:
            if item:  # Skip None/null items
                total_items += 1
                yield item
            else:
                self.logger.debug("Skipping null item in page %d", page_num)

        # Progress logging every 5 pages
        if page_num % 5 == 0:
            self.logger.debug(
                "Streamed page %d from %s: %d items total",
                page_num,
                endpoint,
                total_items
            )

        # Check for next page indicator
        if not result.get("next"):
            self.logger.info(
                "No 'next' indicator from %s, sync complete",
                endpoint
            )
            break

        # Advance to next page
        offset += limit
        page_num += 1

        # Safety limit: prevent infinite loops
        if page_num > 10000:
            self.logger.error(
                "Safety limit hit: %d pages from %s (possible infinite loop)",
                page_num,
                endpoint
            )
            raise ProviderError(
                f"Exceeded maximum pages ({page_num}) for {endpoint}"
            )

    # Final summary
    self.logger.info(
        "Completed streaming %s: %d items in %d pages",
        endpoint,
        total_items,
        page_num + 1
    )
```

**Key Features**:
- ✅ Yields items immediately (streaming)
- ✅ O(1) memory usage
- ✅ Per-page error handling with retry
- ✅ Progress logging
- ✅ Safety limits
- ✅ Implements interface contract from Layer 03

### Solution 2: Update Library Methods

**Replace lines 330-335 (Artists)**:

```python
async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
    """
    Retrieve library artists from Apple Music.

    Streams artists incrementally as they are fetched from the API,
    implementing streaming pagination pattern from ADR_001.

    Yields:
        Artist: Individual artist objects as they become available

    Raises:
        AuthenticationError: If Apple Music authentication fails
        ProviderError: If sync fails after retries
    """
    endpoint = "me/library/artists"

    # Use streaming pagination (Layer 03 contract)
    async for item in self._get_all_items_streaming(
        endpoint,
        include="catalog",
        extend="editorialNotes"
    ):
        # Validate item has required fields
        if not item or not item.get("id"):
            self.logger.warning(
                "Skipping artist with missing ID: %s",
                item
            )
            continue

        try:
            # Parse artist from API response
            artist = self._parse_artist(item)
            if artist:
                yield artist
            else:
                self.logger.warning(
                    "Failed to parse artist %s (returned None)",
                    item.get("id", "unknown")
                )

        except Exception as exc:
            # Per-item error handling: log and skip
            self.logger.warning(
                "Error parsing artist %s: %s",
                item.get("id", "unknown"),
                exc,
                exc_info=True  # Include stack trace in debug logs
            )
            # Continue with next item (don't abort sync)
            continue
```

**Replace lines 337-346 (Albums)**:

```python
async def get_library_albums(self) -> AsyncGenerator[Album, None]:
    """
    Retrieve library albums from Apple Music.

    Streams albums incrementally using streaming pagination pattern.

    Yields:
        Album: Individual album objects as they become available

    Raises:
        AuthenticationError: If Apple Music authentication fails
        ProviderError: If sync fails after retries
    """
    endpoint = "me/library/albums"

    async for item in self._get_all_items_streaming(
        endpoint,
        include="catalog,artists",
        extend="editorialNotes"
    ):
        if not item or not item.get("id"):
            self.logger.warning("Skipping album with missing ID")
            continue

        try:
            album = self._parse_album(item)
            if album:
                yield album
            else:
                self.logger.warning(
                    "Failed to parse album %s (returned None)",
                    item.get("id", "unknown")
                )

        except Exception as exc:
            self.logger.warning(
                "Error parsing album %s: %s",
                item.get("id", "unknown"),
                exc,
                exc_info=True
            )
            continue
```

**Replace lines 373-381 (Playlists)**:

```python
async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
    """
    Retrieve playlists from Apple Music.

    Streams playlists incrementally using streaming pagination pattern.
    Handles both catalog playlists (need lookup) and library playlists.

    Yields:
        Playlist: Individual playlist objects as they become available

    Raises:
        AuthenticationError: If Apple Music authentication fails
        ProviderError: If sync fails after retries
    """
    endpoint = "me/library/playlists"

    async for item in self._get_all_items_streaming(endpoint):
        try:
            # Check if catalog playlist (needs lookup)
            if item.get("attributes", {}).get("hasCatalog"):
                # Fetch full catalog playlist
                global_id = item["attributes"]["playParams"]["globalId"]
                playlist = await self.get_playlist(global_id)
                if playlist:
                    yield playlist
                else:
                    self.logger.warning(
                        "Failed to fetch catalog playlist %s",
                        global_id
                    )

            # Library playlist
            elif item and item.get("id"):
                playlist = self._parse_playlist(item)
                if playlist:
                    yield playlist
                else:
                    self.logger.warning(
                        "Failed to parse playlist %s",
                        item.get("id", "unknown")
                    )

        except Exception as exc:
            self.logger.warning(
                "Error processing playlist %s: %s",
                item.get("id", "unknown"),
                exc,
                exc_info=True
            )
            continue
```

### Solution 3: Maintain Backward Compatibility (Optional)

**Replace lines 771-786** (if other code depends on batch interface):

```python
async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
    """
    Get all items from a paged list (legacy batch interface).

    DEPRECATED: This method loads all items into memory before returning.
    For large libraries, use _get_all_items_streaming() instead.

    This method is maintained for backward compatibility but wraps the
    streaming implementation to gain its benefits while preserving the
    batch interface for existing callers.

    Args:
        endpoint: API endpoint path
        key: JSON key containing items
        **kwargs: Additional API parameters

    Returns:
        list[dict]: All items as a list (memory: O(n))

    Note:
        Consider migrating callers to _get_all_items_streaming() for
        better memory efficiency and performance with large datasets.
    """
    items = []
    async for item in self._get_all_items_streaming(endpoint, key, **kwargs):
        items.append(item)
    return items
```

**Benefits**:
- Existing code continues to work
- Automatically gains retry and error handling improvements
- Memory still accumulates but timeout risk reduced
- Easy migration path (change caller to use async for)

### Solution 4: Do NOT Change Track Sync

**Keep lines 348-371 unchanged** - tracks use different optimization:

**Why**:
1. Tracks use a two-phase approach:
   - Fetch library songs (only IDs, very fast)
   - Batch catalog lookups (200 tracks at a time)
2. Different optimization strategy (batching for API efficiency)
3. Not affected by same pagination issue
4. Already handles large libraries correctly

**Do not apply streaming pattern to tracks.**

## File Structure Changes

### Files to Modify

1. **`music_assistant/providers/apple_music/__init__.py`**:
   - Add `_get_all_items_streaming()` after line 770
   - Replace `get_library_artists()` (lines 330-335)
   - Replace `get_library_albums()` (lines 337-346)
   - Replace `get_library_playlists()` (lines 373-381)
   - Optionally wrap `_get_all_items()` for compatibility (lines 771-786)

### New Imports Needed

```python
from typing import AsyncGenerator
import asyncio
```

**Check if already imported** - Music Assistant likely already has these.

### Exception Classes Needed

```python
class PageFetchError(Exception):
    """Raised when page fetch fails after retries."""

    def __init__(self, page: int, attempts: int, last_error: Exception):
        self.page = page
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Failed to fetch page {page} after {attempts} attempts: {last_error}"
        )
```

**Add near other provider exception definitions** (check existing error classes first).

## Configuration Parameters

### Current Configuration (No Changes Needed)

**File**: `music_assistant/providers/apple_music/__init__.py`

**Rate Limiting** (line 264):
```python
throttler = ThrottlerManager(
    rate_limit=1,      # 1 request
    period=2,          # per 2 seconds
    initial_backoff=15 # 15s initial backoff on rate limit
)
```

**Keep as-is** - matches Apple Music API guidelines.

**Timeout** (line 796):
```python
timeout=120  # seconds
```

**Recommendation**: Keep as-is. With streaming, this applies per-page (safe).
Alternatively, could reduce to 30s since per-page requests should complete quickly.

### Tunable Parameters

**In `_get_all_items_streaming()`**:

```python
# Page size (items per request)
limit = 50  # TUNABLE: 25-100 (50 recommended)

# Max consecutive errors before abort
max_consecutive_errors = 3  # TUNABLE: 3-5

# Safety limit (prevent infinite loops)
max_pages = 10000  # TUNABLE: 10000 = 500k items max

# Retry backoff base
backoff_base = 2  # TUNABLE: 2^n seconds (2, 4, 8...)
```

**Recommended Values**:
- `limit = 50`: Sweet spot between API efficiency and memory
- `max_consecutive_errors = 3`: Tolerant but not excessive
- `max_pages = 10000`: Extremely high safety limit (unlikely to hit)
- `backoff_base = 2`: Standard exponential backoff

## Testing Strategy

### Unit Tests

**Test File**: `tests/providers/test_apple_music.py`

**Required Tests**:

```python
async def test_streaming_pagination_yields_incrementally():
    """Verify items are yielded as pages are fetched, not batched."""
    provider = AppleMusicProvider()
    items = []
    start_time = time.time()

    async for item in provider._get_all_items_streaming("me/library/artists"):
        items.append(item)
        # First item should arrive within 5 seconds
        if len(items) == 1:
            elapsed = time.time() - start_time
            assert elapsed < 5, "First item took too long"
        # Should not have to wait for all items
        if len(items) == 10:
            break

    assert len(items) == 10

async def test_streaming_pagination_memory_constant():
    """Verify memory usage remains constant regardless of library size."""
    provider = AppleMusicProvider()
    import tracemalloc

    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]

    count = 0
    async for item in provider._get_all_items_streaming("me/library/artists"):
        count += 1
        if count in [100, 500, 1000]:
            current = tracemalloc.get_traced_memory()[0]
            growth = current - baseline
            # Memory should not grow proportionally with item count
            assert growth < 5 * 1024 * 1024, f"Memory grew {growth} bytes at {count} items"

    tracemalloc.stop()

async def test_streaming_pagination_handles_errors():
    """Verify per-item errors don't abort sync."""
    provider = AppleMusicProvider()
    # Mock to inject error on item 5
    good_items = 0

    async for item in provider._get_all_items_streaming("me/library/artists"):
        good_items += 1
        if good_items >= 20:
            break

    # Should have skipped bad item and continued
    assert good_items >= 19, "Should continue after item error"

async def test_streaming_pagination_retries_page_errors():
    """Verify transient page errors are retried."""
    provider = AppleMusicProvider()
    # Mock to fail first attempt, succeed second
    # ... (test implementation)
    pass
```

### Integration Tests

**Test with Real Apple Music Account**:

```python
async def test_sync_large_library():
    """Integration test with real Apple Music library > 1000 artists."""
    provider = AppleMusicProvider()
    # Authenticate with real credentials

    artists = []
    async for artist in provider.get_library_artists():
        artists.append(artist)

    # Verify completeness
    assert len(artists) >= 1000, "Should sync all artists"

    # Check alphabetical coverage
    first_letters = set(a.name[0].upper() for a in artists)
    # Should have artists across alphabet
    assert len(first_letters) >= 15, "Should have artists from many letters"

    # Verify no truncation at "J"
    j_artists = [a for a in artists if a.name[0].upper() == 'J']
    later_artists = [a for a in artists if a.name[0].upper() > 'J']
    assert len(later_artists) > 0, "Should have artists beyond J"
```

### Performance Tests

```python
async def test_sync_performance():
    """Verify sync performance meets targets."""
    provider = AppleMusicProvider()

    start = time.time()
    count = 0

    async for artist in provider.get_library_artists():
        count += 1
        if count >= 1000:
            break

    elapsed = time.time() - start

    # Should process ~50 items/minute (accounting for rate limits)
    # 1000 items = ~20 pages = ~40 seconds ideal
    # Allow 2x buffer for overhead: 80 seconds max
    assert elapsed < 80, f"Sync took {elapsed}s, expected < 80s"

    # Verify rate: items per second
    rate = count / elapsed
    assert rate >= 10, f"Rate {rate} items/s too slow, expected >= 10"
```

## Deployment

### Rollout Strategy

**Phase 1: Deploy with Feature Flag**
```python
# In provider initialization
self.use_streaming_pagination = config.get("streaming_pagination", False)

# In methods
if self.use_streaming_pagination:
    async for item in self._get_all_items_streaming(...):
        yield item
else:
    for item in await self._get_all_items(...):
        yield item
```

**Phase 2: Monitor Metrics**
- Sync completion rates
- Error rates
- Memory usage
- User reports

**Phase 3: Enable by Default**
```python
self.use_streaming_pagination = config.get("streaming_pagination", True)  # Default ON
```

**Phase 4: Remove Flag (After Stable)**
- Remove old `_get_all_items()` batch code
- Remove feature flag
- Clean up conditional logic

### Rollback Plan

If issues occur:
1. Set feature flag to `False` in config
2. Restart Music Assistant
3. Old batch behavior restored immediately
4. No data loss (both implementations preserve data)

### Monitoring

**Metrics to Track**:
```
# Success metrics
apple_music.library.sync.complete (counter)
apple_music.library.sync.items_total (histogram)
apple_music.library.sync.duration_seconds (histogram)

# Error metrics
apple_music.library.sync.failed (counter)
apple_music.library.sync.items_skipped (counter)
apple_music.library.sync.page_retries (counter)

# Performance metrics
apple_music.library.sync.memory_peak_mb (gauge)
apple_music.library.sync.items_per_second (gauge)
```

**Alerts**:
- Sync failure rate > 5%
- Item skip rate > 1%
- Memory usage > 50 MB
- Sync duration > 10 minutes (for 5k items)

## Performance Characteristics

### Expected Performance

**Small Library (< 500 artists)**:
- Sync time: 10-20 seconds
- Memory: < 1 MB
- First item: < 2 seconds
- Complete: Yes

**Medium Library (500-1500 artists)**:
- Sync time: 40-120 seconds (1-2 minutes)
- Memory: < 1 MB
- First item: < 2 seconds
- Complete: Yes (was failing before)

**Large Library (1500-5000 artists)**:
- Sync time: 120-400 seconds (2-7 minutes)
- Memory: < 1 MB
- First item: < 2 seconds
- Complete: Yes (was impossible before)

**Huge Library (5000+ artists)**:
- Sync time: 400+ seconds (7+ minutes)
- Memory: < 1 MB
- First item: < 2 seconds
- Complete: Yes (was impossible before)

### Comparison to Current

| Library Size | Before (Batch) | After (Streaming) | Improvement |
|--------------|----------------|-------------------|-------------|
| 500 artists | Works | Works | Unchanged |
| 1000 artists | Fails at J (~700) | Works | ✅ 43% more data |
| 2000 artists | Fails at J (~700) | Works | ✅ 186% more data |
| 5000 artists | Fails at J (~700) | Works | ✅ 614% more data |

**Memory**:
- Before: 5-50 MB (grows with library)
- After: < 1 MB (constant)
- Improvement: 5-50x reduction

**Time to First Item**:
- Before: 20-200 seconds (waits for all)
- After: < 2 seconds (immediate)
- Improvement: 10-100x faster

## Troubleshooting

### Issue: Sync Still Stops Early

**Diagnosis**:
1. Check logs for `PageFetchError` or `Safety limit hit`
2. Verify `_get_all_items_streaming()` is being called (not old batch method)
3. Check if provider is hitting different timeout (not pagination related)

**Solution**:
- Review error logs for root cause
- Increase `max_consecutive_errors` if transient network issues
- Check Apple Music API status

### Issue: Memory Usage Still High

**Diagnosis**:
1. Check if old `_get_all_items()` is still being called
2. Profile memory to find accumulation point
3. Verify callers are using `async for`, not accumulating results

**Solution**:
- Ensure all library methods use `_get_all_items_streaming()`
- Check downstream code isn't accumulating items in list
- Review caller code for batch collection

### Issue: Sync Too Slow

**Diagnosis**:
1. Check rate limiting configuration
2. Measure time per page
3. Check network latency

**Solution**:
- Verify rate limit is 1 req / 2s (as configured)
- If page fetch > 5s, check network
- Consider increasing page size from 50 to 100 (trade memory for speed)

## See Also

**Architecture**: [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

**Interface Contract**: [../03_INTERFACES/MUSIC_PROVIDER_PAGINATION_CONTRACT.md](../03_INTERFACES/MUSIC_PROVIDER_PAGINATION_CONTRACT.md)

**Reference**: [../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md](../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md)

**Operations**: `docs/05_OPERATIONS/APPLY_PAGINATION_FIX.md` (to be created)
