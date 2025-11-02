# Apple Music Playlist Sync Issue - Root Cause Analysis

## Problem Statement

Apple Music playlists are not syncing in Music Assistant despite:
- Artists syncing successfully
- Authentication working (same tokens used)
- Log showing "Starting library playlists sync (streaming)"
- Log showing "Completed playlists sync: 0 loaded"

## Code Analysis

### Current Implementation

The Apple Music provider implements `get_library_playlists()` at line 373-381:

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

### The `_get_all_items` Method (Lines 771-786)

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

### The `_get_data` Method - Critical Bug (Lines 788-821)

```python
@throttle_with_retries
async def _get_data(self, endpoint, **kwargs) -> dict[str, Any]:
    """Get data from api."""
    url = f"https://api.music.apple.com/v1/{endpoint}"
    headers = {"Authorization": f"Bearer {self._music_app_token}"}
    headers["Music-User-Token"] = self._music_user_token
    async with (
        self.mass.http_session.get(
            url, headers=headers, params=kwargs, ssl=True, timeout=120
        ) as response,
    ):
        if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
            return {}  # <-- BUG: This breaks pagination!
        # ... rest of error handling
```

## Root Cause Identified

**Line 799-800**: The 404 handler for pagination is BREAKING the sync!

```python
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    return {}
```

### Why This Breaks Playlist Sync

1. `get_library_playlists()` calls `_get_all_items("me/library/playlists")`
2. `_get_all_items()` makes first call with `limit=50, offset=0`
3. If Apple Music API returns 404 for this specific endpoint with pagination params
4. `_get_data()` returns `{}` (empty dict)
5. `_get_all_items()` checks `if key not in result:` → `if "data" not in {}:` → **TRUE**
6. Loop breaks immediately, returns empty list `[]`
7. `get_library_playlists()` gets empty list, yields nothing
8. Sync completes with 0 playlists

### Why Artists Work But Playlists Don't

**Artists use different pagination:**
- Artists endpoint: `me/library/artists` (line 332-335)
- Uses `include="catalog"` and `extend="editorialNotes"` params
- These additional params may change API behavior

**Playlists:**
- Endpoint: `me/library/playlists` (line 375-376)
- NO additional params passed to `_get_all_items()`
- Clean endpoint with just pagination might trigger 404 differently

### Hypothesis

One of these scenarios is occurring:

1. **Apple Music API quirk**: The `me/library/playlists` endpoint returns 404 when called with `limit` and `offset` params if the user has no library playlists (but might have catalog playlists)

2. **Empty library detection**: The 404 response is Apple's way of saying "no library playlists" (but this should be 200 with empty data array)

3. **Missing required parameters**: The playlists endpoint might require additional params (like `include` or `extend`) to work with pagination

4. **Token scope issue**: The user token might not have permission for library playlists (but catalog playlists might work)

## Diagnostic Steps

### Step 1: Run Debug Script

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"
./run_playlist_debug.sh
```

This will test:
1. Direct API call without pagination
2. API call with pagination params (reproducing the bug)
3. Catalog playlists (to verify API access works)
4. Simulation of `_get_all_items` logic

### Step 2: Expected Outcomes

**If API returns 404 with pagination:**
- Bug confirmed: The 404 handler is too broad
- Fix: Modify the 404 handler to not return empty dict for initial pagination

**If API returns 200 with empty data:**
- User has no library playlists
- But provider should handle this gracefully (not break sync)

**If API returns 200 with playlists:**
- Something else is filtering them out
- Check the `hasCatalog` logic in `get_library_playlists()`

## Proposed Fixes

### Fix 1: Remove or Modify the 404 Pagination Handler

**Problem**: The current logic assumes 404 with pagination = "no more items"
**Reality**: 404 with initial pagination (offset=0) = "endpoint doesn't support these params"

```python
# CURRENT (BROKEN):
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    return {}

# FIX OPTION A: Only handle 404 for non-zero offsets
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    # Only return empty for pagination beyond first page
    if kwargs.get("offset", 0) > 0:
        return {}
    # For first page, let it fall through to normal 404 handling
    raise MediaNotFoundError(f"{endpoint} not found")

# FIX OPTION B: Remove pagination 404 handler entirely
# (Let it raise MediaNotFoundError for genuinely missing endpoints)
```

### Fix 2: Add Logging to Identify the Issue

```python
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    self.logger.warning(
        "Got 404 with pagination for %s (limit=%s, offset=%s) - returning empty",
        endpoint,
        kwargs.get("limit"),
        kwargs.get("offset")
    )
    return {}
```

### Fix 3: Make `get_library_playlists` More Robust

```python
async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
    """Retrieve playlists from the provider."""
    endpoint = "me/library/playlists"

    # Try with additional params first (like artists endpoint does)
    items = await self._get_all_items(endpoint, include="catalog")

    if not items:
        self.logger.info("No library playlists found for user")
        return

    for item in items:
        try:
            # Prefer catalog information over library information in case of public playlists
            if item["attributes"]["hasCatalog"]:
                yield await self.get_playlist(item["attributes"]["playParams"]["globalId"])
            elif item and item["id"]:
                yield self._parse_playlist(item)
        except Exception as e:
            self.logger.warning("Failed to parse playlist: %s", e)
            continue
```

### Fix 4: Alternative - Try Without Pagination First

```python
async def _get_all_items(self, endpoint, key="data", **kwargs) -> list[dict]:
    """Get all items from a paged list."""
    # First try without pagination to see if endpoint supports it
    try:
        result = await self._get_data(endpoint, **kwargs)
        if key in result and len(result[key]) < 50:
            # All items fit in one response, return immediately
            return result[key]
    except MediaNotFoundError:
        # Endpoint doesn't exist
        raise

    # Need pagination
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

## Testing Plan

1. **Run debug script** to identify exact API behavior
2. **Apply Fix 1 (Option A)** - Only return empty for offset > 0
3. **Add logging** to confirm behavior
4. **Test sync** and check logs
5. **Verify playlists** appear in Music Assistant

## Additional Notes

### Why This Wasn't Caught Before

- Artists work because they use `include="catalog"` param
- Albums work similarly with `include="catalog,artists"`
- Tracks work with different logic (fetches catalog IDs first)
- Playlists are the ONLY endpoint called with pure pagination, no extra params

### Impact Assessment

- **Severity**: HIGH - Complete feature broken
- **Affected**: All Apple Music users trying to sync playlists
- **Workaround**: None (users cannot access their playlists)
- **Fix Complexity**: LOW - 1-5 line change

### Related Code

- Provider base: `server-2.6.0/music_assistant/models/music_provider.py`
- Playlist controller: `server-2.6.0/music_assistant/controllers/media/playlists.py`
- Apple Music provider: `server-2.6.0/music_assistant/providers/apple_music/__init__.py`
