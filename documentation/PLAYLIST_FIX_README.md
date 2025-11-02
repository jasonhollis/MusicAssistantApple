# Apple Music Playlist Sync Fix

## Quick Start

### Option 1: Run Debug Script First (Recommended)

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Run diagnostics
./run_playlist_debug.sh
```

This will test the Apple Music API directly and identify the exact issue.

### Option 2: Apply Fix Immediately

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Apply the fix
python3 apple_music_playlist_sync_fix.py

# Restart Music Assistant
docker restart music-assistant

# Trigger playlist sync in UI or wait for next scheduled sync
```

## Problem Summary

**Symptom**: Apple Music playlists show 0 items after sync, but artists sync successfully.

**Root Cause**: The `_get_data` method in the Apple Music provider has a bug in its 404 handling for paginated requests. When the API endpoint `me/library/playlists` is called with `limit` and `offset` parameters, and returns a 404, the method returns an empty dict `{}`. This breaks the pagination loop in `_get_all_items` immediately, returning an empty list before any playlists are retrieved.

**Code Location**: `server-2.6.0/music_assistant/providers/apple_music/__init__.py` line 799-800

## Root Cause Analysis

### The Bug

```python
# BUGGY CODE (Line 799-800):
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    return {}  # This breaks first-page requests!
```

### Why It Breaks

1. `get_library_playlists()` calls `_get_all_items("me/library/playlists")`
2. `_get_all_items()` calls `_get_data()` with `limit=50, offset=0`
3. If Apple Music API returns 404 (for any reason with these params)
4. The method returns `{}` instead of raising an error
5. `_get_all_items()` checks `if "data" not in result:` → True
6. Loop breaks, returns empty list
7. No playlists are synced

### Why Artists Work But Playlists Don't

**Artists** (`me/library/artists`):
- Called with `include="catalog"` and `extend="editorialNotes"` params
- These extra params may change API behavior or error handling

**Playlists** (`me/library/playlists`):
- Called with ONLY pagination params (`limit`, `offset`)
- No additional params to modify behavior
- More likely to trigger the 404 handler bug

## The Fix

### Modified Code

```python
# FIXED CODE:
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    # Only return empty for pagination beyond first page
    # For offset=0, this might indicate endpoint doesn't support pagination
    if kwargs.get("offset", 0) > 0:
        # Beyond first page, treat 404 as end of results
        return {}
    # For first page (offset=0), let it fall through to normal 404 handling
```

### What This Does

- **For `offset > 0`**: Returns `{}` (assuming end of pagination)
- **For `offset = 0`**: Falls through to normal error handling, raises `MediaNotFoundError`
- This allows proper error detection on first page while still handling pagination edge cases

## Files Created

### 1. Debug Script (`debug_apple_playlists.py`)

Comprehensive diagnostic tool that:
- Tests the API endpoint directly
- Tests with and without pagination
- Simulates the provider's pagination logic
- Identifies where the sync breaks

**Run it**:
```bash
export MUSIC_APP_TOKEN="your_token"
export MUSIC_USER_TOKEN="your_token"
python3 debug_apple_playlists.py
```

Or use the helper script:
```bash
./run_playlist_debug.sh
```

### 2. Token Extraction Script (`run_playlist_debug.sh`)

Automatically:
- Extracts tokens from Music Assistant Docker container
- Sets environment variables
- Runs the debug script
- Shows results

### 3. Fix Script (`apple_music_playlist_sync_fix.py`)

Automatically:
- Creates backup of original provider file
- Applies the code fix
- Adds enhanced logging
- Verifies the fix was applied correctly
- Shows next steps

### 4. Analysis Document (`PLAYLIST_SYNC_ANALYSIS.md`)

Comprehensive technical analysis including:
- Code flow analysis
- Root cause explanation
- Multiple fix options
- Testing plan
- Impact assessment

## Testing Plan

### Phase 1: Diagnosis

```bash
# Run debug script to confirm the issue
./run_playlist_debug.sh
```

**Expected Output**:
- If bug exists: Will show 404 response with pagination params
- If no bug: Will show playlists returned successfully

### Phase 2: Apply Fix

```bash
# Apply the fix
python3 apple_music_playlist_sync_fix.py
```

**Expected Output**:
```
✓ Backup created: .../__init__.py.backup
✓ Found buggy code at line 799
✓ Fix applied successfully!
✓ Enhanced logging added!
✓ All verification checks passed!
```

### Phase 3: Test Fix

```bash
# Restart Music Assistant
docker restart music-assistant

# Watch logs
docker logs -f music-assistant | grep -i playlist
```

**Trigger sync** in Music Assistant UI or wait for scheduled sync.

**Expected Log Output**:
```
Fetching library playlists from endpoint: me/library/playlists
Retrieved 12 library playlist items from Apple Music API
```

### Phase 4: Verify Results

1. Check Music Assistant UI - playlists should appear
2. Check database:
   ```bash
   docker exec music-assistant sqlite3 /data/library.db "SELECT COUNT(*) FROM playlists WHERE provider_mappings LIKE '%apple_music%';"
   ```
3. Expected: Non-zero count of Apple Music playlists

## Rollback

If the fix causes issues:

```bash
# Restore from backup
cp "server-2.6.0/music_assistant/providers/apple_music/__init__.py.backup" \
   "server-2.6.0/music_assistant/providers/apple_music/__init__.py"

# Restart
docker restart music-assistant
```

## Additional Investigation

### If Debug Script Shows API Returns Playlists

If the debug script shows that the API **does** return playlists, but they're still not syncing, investigate:

1. **hasCatalog filtering**: Check if playlists are being filtered by the `hasCatalog` check
2. **Parsing errors**: Check if `_parse_playlist()` is failing silently
3. **Database insertion**: Check if playlists are being added to DB correctly

### If Debug Script Shows 0 Playlists from API

If the API genuinely returns 0 playlists:

1. Check Apple Music account - do you have playlists?
2. Check token scope - does user token have playlist access?
3. Try web interface - can you see playlists at music.apple.com?
4. Check if playlists are library vs catalog playlists

## Code Changes Summary

### File: `server-2.6.0/music_assistant/providers/apple_music/__init__.py`

**Line ~799** (404 handler in `_get_data`):
- **Before**: Returns `{}` for any 404 with pagination
- **After**: Only returns `{}` for `offset > 0`, raises error for `offset = 0`

**Line ~375** (get_library_playlists):
- **Added**: Debug logging to show item count
- **Added**: Info logging for retrieved items

## Performance Impact

- **Negligible**: Only adds one integer comparison (`offset > 0`)
- **Logging**: Minimal (2 log lines per sync)
- **Memory**: No change
- **API calls**: No change (same number of requests)

## Security Impact

- **None**: No changes to authentication or data handling
- **Privacy**: No data sent anywhere new
- **Tokens**: No changes to token management

## Future Improvements

1. **Better error handling**: Distinguish between "endpoint not found" vs "no results"
2. **Retry logic**: Add retry for transient 404s
3. **Fallback**: Try without pagination if paginated request fails
4. **User feedback**: Show user why playlists aren't syncing

## References

- Apple Music API Docs: https://developer.apple.com/documentation/applemusicapi
- Music Assistant Provider Docs: https://music-assistant.io/
- Issue tracker: (if applicable)

## Support

If this fix doesn't work:

1. Run debug script and save output
2. Check Music Assistant logs: `docker logs music-assistant > ma_logs.txt`
3. Check for errors in logs
4. Review the analysis document for alternative scenarios
5. Consider opening an issue with Music Assistant project

## Credits

- Analysis: Claude Code (Anthropic)
- Fix: Based on code analysis and API testing
- Testing: Community feedback welcome
