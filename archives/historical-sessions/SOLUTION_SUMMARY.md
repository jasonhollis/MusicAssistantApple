# Apple Music Playlist Sync - Solution Summary

## TL;DR

**Problem**: Playlists sync shows "0 loaded" but artists work fine.

**Root Cause**: Bug in `_get_data()` method - returns empty dict `{}` when API returns 404 with pagination params, breaking the sync loop on first page.

**Fix**: Modified 404 handler to only return `{}` for `offset > 0`, allowing first-page errors to be raised properly.

## Quick Fix (2 minutes)

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Apply fix
python3 apple_music_playlist_sync_fix.py

# Restart
docker restart music-assistant
```

## Diagnostic First (5 minutes)

```bash
# Test API directly to confirm issue
./run_playlist_debug.sh
```

## What Was Created

| File | Purpose |
|------|---------|
| `debug_apple_playlists.py` | Test Apple Music API directly, identify exact issue |
| `run_playlist_debug.sh` | Extract tokens from Docker, run debug script |
| `apple_music_playlist_sync_fix.py` | Apply the code fix with backup |
| `PLAYLIST_SYNC_ANALYSIS.md` | Detailed technical analysis and root cause |
| `PLAYLIST_FIX_README.md` | Complete documentation and testing guide |

## The Bug Explained

### Buggy Code (Line 799-800)

```python
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    return {}  # ← BUG: This breaks pagination on first page!
```

### Why It Breaks

```
get_library_playlists()
  ↓
_get_all_items("me/library/playlists")
  ↓
_get_data(endpoint, limit=50, offset=0)
  ↓
API returns 404 (for whatever reason)
  ↓
Returns {} instead of raising error
  ↓
_get_all_items checks: if "data" not in {} → TRUE
  ↓
Loop breaks immediately
  ↓
Returns empty list []
  ↓
Sync completes with 0 playlists
```

### The Fix

```python
if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
    # Only return empty for pagination BEYOND first page
    if kwargs.get("offset", 0) > 0:
        return {}  # End of pagination
    # For first page, raise error as normal
```

## Why Artists Work But Playlists Don't

**Artists endpoint**: `me/library/artists`
- Called with `include="catalog"`, `extend="editorialNotes"`
- Extra params change API behavior

**Playlists endpoint**: `me/library/playlists`
- Called with ONLY `limit=50`, `offset=0`
- No extra params, triggers bug more easily

## Testing Checklist

- [ ] Run `./run_playlist_debug.sh` to diagnose
- [ ] Run `python3 apple_music_playlist_sync_fix.py` to apply fix
- [ ] Restart Music Assistant: `docker restart music-assistant`
- [ ] Trigger playlist sync in UI
- [ ] Check logs: `docker logs music-assistant | grep -i playlist`
- [ ] Verify playlists appear in Music Assistant UI
- [ ] Check database count is non-zero

## Expected Results

### Before Fix

```
Starting library playlists sync (streaming)
Completed playlists sync: 0 loaded
```

### After Fix

```
Starting library playlists sync (streaming)
Fetching library playlists from endpoint: me/library/playlists
Retrieved 12 library playlist items from Apple Music API
Completed playlists sync: 12 loaded
```

## Rollback Plan

```bash
# If fix causes issues
cp server-2.6.0/music_assistant/providers/apple_music/__init__.py.backup \
   server-2.6.0/music_assistant/providers/apple_music/__init__.py

docker restart music-assistant
```

## Files Modified

1. `server-2.6.0/music_assistant/providers/apple_music/__init__.py`
   - Line ~799: Modified 404 handler
   - Line ~375: Added logging

## Next Steps

1. **Immediate**: Apply fix and test
2. **If successful**: Consider submitting PR to Music Assistant project
3. **If unsuccessful**: Run debug script, review analysis document
4. **Long term**: Monitor for any edge cases or issues

## Support Files

- **Full analysis**: `PLAYLIST_SYNC_ANALYSIS.md`
- **Complete guide**: `PLAYLIST_FIX_README.md`
- **Debug tool**: `debug_apple_playlists.py`
- **Helper script**: `run_playlist_debug.sh`

## Contact

If issues persist after applying fix:
1. Run debug script and save output
2. Save logs: `docker logs music-assistant > ma_logs.txt`
3. Review analysis document for alternative scenarios
4. Check if playlists exist in Apple Music web interface
