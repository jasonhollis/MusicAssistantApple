# Apply Pagination Fix - Operations Guide

**Purpose**: Step-by-step procedures for applying the streaming pagination fix to Music Assistant
**Audience**: System administrators, DevOps engineers, advanced users
**Layer**: 05_OPERATIONS
**Related**:
- [../04_INFRASTRUCTURE/APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md](../04_INFRASTRUCTURE/APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md)
- [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

## Intent

This guide provides concrete operational procedures for applying the streaming pagination fix to a running Music Assistant instance. It includes backup procedures, verification steps, and rollback instructions.

## Prerequisites

Before beginning, ensure:

- [ ] You have shell access to Music Assistant server
- [ ] You have backup of Music Assistant installation
- [ ] You have identified Music Assistant installation directory
- [ ] You can restart Music Assistant service
- [ ] You have tested the fix in development/test environment (recommended)

## System Requirements

**Music Assistant Version**: 2.6.0 or later
**Python Version**: 3.11+
**Disk Space**: 100 MB free (for backup)
**Downtime**: ~5 minutes (restart required)

## Pre-Flight Checklist

### 1. Locate Installation Directory

**Common Locations**:
```bash
# Docker installation
/usr/src/app/music_assistant/

# Home Assistant Add-on
/usr/local/lib/python3.11/site-packages/music_assistant/

# Manual Python installation
/path/to/venv/lib/python3.11/site-packages/music_assistant/

# Development installation
/path/to/music-assistant/server/music_assistant/
```

**Find it**:
```bash
# Method 1: Using find
find /usr -name "apple_music" -type d 2>/dev/null | grep providers

# Method 2: Using Python
python3 -c "import music_assistant.providers.apple_music as am; print(am.__file__)"

# Method 3: Check running process
ps aux | grep music_assistant
```

**Expected Output**: `/path/to/music_assistant/providers/apple_music/__init__.py`

### 2. Verify Current Version

```bash
# Navigate to provider directory
cd /path/to/music_assistant/providers/apple_music/

# Check file exists
ls -lh __init__.py

# Check approximate line count (should be ~800-900 lines)
wc -l __init__.py

# Verify it's the Apple Music provider
head -20 __init__.py | grep -i "apple music"
```

**Expected**: File exists, ~800-900 lines, contains Apple Music provider code.

### 3. Check Current Behavior (Pre-Fix)

```bash
# Check Music Assistant logs for sync activity
tail -100 /path/to/music_assistant.log | grep -i "library/artists"

# Look for indicators of issue:
# - "Fetched page X" messages stopping early
# - No completion message for large libraries
# - Timeout errors around page 15-20
```

## Backup Procedures

### Critical: Always Backup First

```bash
# Set variables
MA_DIR="/path/to/music_assistant"  # UPDATE THIS
BACKUP_DIR="/path/to/backups"      # UPDATE THIS
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup entire provider file
cp "$MA_DIR/providers/apple_music/__init__.py" \
   "$BACKUP_DIR/apple_music_init_${TIMESTAMP}.py.backup"

# Verify backup
ls -lh "$BACKUP_DIR/apple_music_init_${TIMESTAMP}.py.backup"
diff "$MA_DIR/providers/apple_music/__init__.py" \
     "$BACKUP_DIR/apple_music_init_${TIMESTAMP}.py.backup"
```

**Verification**: Diff should show no differences (files identical).

### Backup Database (Recommended)

```bash
# Music Assistant database location (varies by installation)
DB_PATH="/path/to/music_assistant/database.db"  # UPDATE THIS

# Backup database
cp "$DB_PATH" "$BACKUP_DIR/database_${TIMESTAMP}.db.backup"

# Verify backup
ls -lh "$BACKUP_DIR/database_${TIMESTAMP}.db.backup"
```

**Note**: Database backup optional but recommended in case issues require full restore.

## Application Procedures

### Option 1: Apply Complete Patch File

**If you have the patch file** (`apple_music_streaming_pagination_fix.py`):

```bash
# Navigate to provider directory
cd /path/to/music_assistant/providers/apple_music/

# Backup original (done above)
# Already completed in backup section

# Apply patch using provided script
# (Assumes patch script available)
python3 /path/to/apply_streaming_fix.py

# Verify changes applied
grep -n "_get_all_items_streaming" __init__.py
```

**Expected**: Should show new `_get_all_items_streaming` method.

### Option 2: Manual Code Changes

**If applying changes manually**, follow these steps:

#### Step 1: Add Streaming Method

```bash
# Edit file
nano /path/to/music_assistant/providers/apple_music/__init__.py

# Or use vim
vim /path/to/music_assistant/providers/apple_music/__init__.py
```

**Add after line 770** (after `_get_all_items` method):

See [../04_INFRASTRUCTURE/APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md](../04_INFRASTRUCTURE/APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md) for complete `_get_all_items_streaming()` code.

**Quick verification**:
```bash
# Count lines in method (should be ~120-130 lines)
sed -n '/async def _get_all_items_streaming/,/^    def /p' __init__.py | wc -l
```

#### Step 2: Update get_library_artists()

**Replace lines 330-335**:

See Implementation doc for complete updated `get_library_artists()` code.

**Verification**:
```bash
# Check method uses streaming
grep -A 5 "async def get_library_artists" __init__.py | grep "_get_all_items_streaming"
```

**Expected**: Should show `_get_all_items_streaming` call.

#### Step 3: Update get_library_albums()

**Replace lines 337-346**:

See Implementation doc for complete updated `get_library_albums()` code.

**Verification**:
```bash
grep -A 5 "async def get_library_albums" __init__.py | grep "_get_all_items_streaming"
```

#### Step 4: Update get_library_playlists()

**Replace lines 373-381**:

See Implementation doc for complete updated `get_library_playlists()` code.

**Verification**:
```bash
grep -A 5 "async def get_library_playlists" __init__.py | grep "_get_all_items_streaming"
```

#### Step 5: (Optional) Update _get_all_items() for Compatibility

**Replace lines 771-786**:

See Implementation doc for backward-compatible wrapper.

**Note**: This step is optional but recommended for safety.

### Syntax Validation

**Before restarting, validate Python syntax**:

```bash
# Check for syntax errors
python3 -m py_compile /path/to/music_assistant/providers/apple_music/__init__.py

# If no output, syntax is valid
# If errors, review and fix before proceeding
```

**Expected**: No output (success) or syntax errors to fix.

## Restart Music Assistant

### Docker Installation

```bash
# Restart container
docker restart music-assistant

# Or docker-compose
cd /path/to/docker-compose/
docker-compose restart music-assistant

# Watch logs
docker logs -f music-assistant
```

### Home Assistant Add-on

```bash
# Via Home Assistant UI
# Navigate to: Settings -> Add-ons -> Music Assistant -> Restart

# Or via CLI
ha addons restart music_assistant

# Check logs
ha addons logs music_assistant
```

### Systemd Service

```bash
# Restart service
sudo systemctl restart music-assistant

# Check status
sudo systemctl status music-assistant

# Watch logs
sudo journalctl -u music-assistant -f
```

### Manual/Development

```bash
# Stop running instance (Ctrl+C or kill PID)
pkill -f music_assistant

# Start again
cd /path/to/music-assistant/
python3 -m music_assistant.server
```

## Verification Steps

### 1. Check Service Started Successfully

```bash
# Docker
docker ps | grep music-assistant
# Should show "Up X seconds"

# Systemd
systemctl is-active music-assistant
# Should show "active"

# Check logs for errors
tail -50 /path/to/music_assistant.log | grep -i error
# Should show no errors related to import or syntax
```

### 2. Trigger Library Sync

**Via Web UI**:
1. Navigate to Music Assistant web interface
2. Go to Settings -> Providers -> Apple Music
3. Click "Reload" or "Re-sync library"

**Via API** (if exposed):
```bash
curl -X POST http://localhost:8095/api/sync/apple_music/library
```

### 3. Monitor Sync Progress

```bash
# Watch logs in real-time
tail -f /path/to/music_assistant.log | grep -E "(Fetched page|Streamed page|library/artists)"

# Look for:
# - "Streamed page X from me/library/artists: Y items total"
# - Progress beyond page 20 (was failing around page 15-20 before)
# - "Completed streaming me/library/artists: X items in Y pages"
```

**Good indicators**:
```
DEBUG Streamed page 0 from me/library/artists: 50 items total
DEBUG Streamed page 5 from me/library/artists: 250 items total
DEBUG Streamed page 10 from me/library/artists: 500 items total
DEBUG Streamed page 15 from me/library/artists: 750 items total  # Was failing here before!
DEBUG Streamed page 20 from me/library/artists: 1000 items total
INFO Completed streaming me/library/artists: 2000 items in 40 pages  # Success!
```

### 4. Verify Data Completeness

**Check artist count**:
```bash
# Via database (SQLite)
sqlite3 /path/to/music_assistant/database.db \
  "SELECT COUNT(*) FROM artists WHERE provider='apple_music';"

# Expected: Should match total from logs
# Example: 2000 (if logs show "2000 items in 40 pages")
```

**Check alphabetical coverage**:

Via Web UI:
1. Navigate to Artists view
2. Scroll to end of list
3. Note last artist name
4. **Expected**: Should start with letters T-Z, not I-J

**Query database for letter distribution**:
```bash
sqlite3 /path/to/music_assistant/database.db <<EOF
SELECT
  UPPER(SUBSTR(name, 1, 1)) as first_letter,
  COUNT(*) as count
FROM artists
WHERE provider='apple_music'
GROUP BY first_letter
ORDER BY first_letter;
EOF
```

**Expected**: Should show artists across A-Z, not stopping at I-J.

### 5. Compare Before/After Counts

```bash
# If you captured count before fix
echo "Before: 700 artists (example)"
echo "After: $(sqlite3 /path/to/database.db 'SELECT COUNT(*) FROM artists WHERE provider="apple_music"')"

# Calculate improvement
# Expected: 2-3x increase for large libraries
```

## Success Criteria

Fix is successful if:

- [x] Service starts without errors
- [x] Sync progresses beyond page 15-20 (was failing here)
- [x] Logs show "Completed streaming" message
- [x] Artist count in database > 700 (if large library)
- [x] Last artist alphabetically in T-Z range (not I-J)
- [x] No memory warnings or out-of-memory errors
- [x] Sync completes within expected time (see [Reference](../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md))

## Troubleshooting

### Issue: Syntax Error on Restart

**Symptoms**:
```
SyntaxError: invalid syntax
File "/path/to/__init__.py", line XXX
```

**Solution**:
1. Review error line number
2. Check for:
   - Missing colons `:`
   - Incorrect indentation (Python is sensitive!)
   - Missing quotes or parentheses
3. Compare with backup
4. Re-apply changes carefully

**Quick fix**:
```bash
# Restore from backup
cp /path/to/backup/apple_music_init_TIMESTAMP.py.backup \
   /path/to/music_assistant/providers/apple_music/__init__.py

# Try again more carefully
```

### Issue: Import Errors

**Symptoms**:
```
ImportError: cannot import name 'PageFetchError'
ModuleNotFoundError: No module named 'asyncio'
```

**Solution**:

Check if needed imports exist:
```bash
# Check for required imports
grep "^import asyncio" __init__.py
grep "^from typing import AsyncGenerator" __init__.py
```

**Add if missing** (near top of file):
```python
import asyncio
from typing import AsyncGenerator
```

### Issue: Sync Still Stops Early

**Diagnosis**:
```bash
# Check if streaming method is actually being called
grep "Streamed page" /path/to/music_assistant.log

# If NOT present, check method calls
grep "_get_all_items_streaming" /path/to/music_assistant/providers/apple_music/__init__.py
```

**Possible causes**:
1. Old code still in use (changes not applied)
2. Different provider being used (not Apple Music)
3. Different issue (not pagination related)

**Solution**:
- Verify changes applied to correct file
- Check provider in use: `grep "provider.*apple" /path/to/music_assistant.log`
- Review logs for actual error

### Issue: Memory Usage High

**Diagnosis**:
```bash
# Monitor memory during sync
top -p $(pgrep -f music_assistant)

# Or with Docker
docker stats music-assistant
```

**Expected**: Memory should remain relatively constant during sync (~100-200 MB for service + overhead).

**If growing continuously**:
- Verify `_get_all_items_streaming` is being used (not old batch method)
- Check for downstream code accumulating items
- Review memory with `docker stats` or `top`

**Solution**:
- Double-check implementation uses streaming
- Verify callers use `async for` (not accumulating in list)

### Issue: Sync Too Slow

**Expected Times** (from [Reference](../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md)):
- 1,000 artists: ~40 seconds
- 2,000 artists: ~80 seconds
- 5,000 artists: ~200 seconds

**If exceeding by 2x**:
```bash
# Check rate limiting
grep "rate_limit" /path/to/music_assistant/providers/apple_music/__init__.py

# Expected: 1 request per 2 seconds
```

**Possible causes**:
- Network latency
- API rate limiting (Apple throttling)
- Excessive retries (network issues)

**Solution**:
- Check network connectivity to Apple Music API
- Review logs for retry attempts
- Verify rate limit configuration (should be 1 req / 2s)

## Rollback Procedure

If issues occur, rollback to original code:

```bash
# Stop service
sudo systemctl stop music-assistant
# Or docker: docker stop music-assistant

# Restore backup
cp /path/to/backup/apple_music_init_TIMESTAMP.py.backup \
   /path/to/music_assistant/providers/apple_music/__init__.py

# Verify restoration
diff /path/to/music_assistant/providers/apple_music/__init__.py \
     /path/to/backup/apple_music_init_TIMESTAMP.py.backup
# Should show no differences

# Restart service
sudo systemctl start music-assistant
# Or docker: docker start music-assistant

# Verify service running
systemctl status music-assistant
# Or docker: docker ps | grep music-assistant
```

**Result**: Service returns to original behavior (pre-fix).

**Note**: Rollback does not affect database - previously synced data remains.

## Post-Fix Operations

### Monitor for Issues

**First 24 Hours**:
```bash
# Watch for errors
tail -f /path/to/music_assistant.log | grep -i error

# Monitor memory
watch "ps aux | grep music_assistant"

# Check sync completion
grep "Completed streaming" /path/to/music_assistant.log
```

### Re-Sync All Providers (Optional)

After confirming fix works for Apple Music:

1. Navigate to Settings -> Providers
2. For each connected provider (Spotify, Tidal, etc.):
   - Click "Reload" or "Re-sync"
   - Verify completion in logs

**Note**: Fix applies to Apple Music provider only. Other providers may need similar fixes if affected.

### Update Documentation

Document in your system:
- Date fix applied: `_____________`
- Music Assistant version: `_____________`
- Fix version: `1.0` (from ADR_001)
- Backup location: `/path/to/backup/apple_music_init_TIMESTAMP.py.backup`
- Verification: Artist count increased from `_____` to `_____`

## Maintenance

### Future Updates

When updating Music Assistant:

1. **Before updating**:
   - Note current artist/album counts
   - Backup custom provider file
   - Document any customizations

2. **After updating**:
   - Check if update includes pagination fix
   - If yes: No action needed
   - If no: Re-apply fix to new version
   - Verify counts match or increase

### Monitoring Checklist

**Weekly**:
- [ ] Check sync completion in logs
- [ ] Verify artist/album counts stable or increasing
- [ ] Review error logs for issues

**Monthly**:
- [ ] Full re-sync of all providers
- [ ] Verify all data accessible via UI
- [ ] Review memory usage trends

**After Provider Updates**:
- [ ] Test sync after Apple Music API changes
- [ ] Verify pagination still working
- [ ] Check logs for new error patterns

## Emergency Contacts

**If critical issues occur**:

1. **Music Assistant Support**:
   - GitHub: https://github.com/music-assistant/server
   - Discord: https://discord.gg/kaVm8hGpne
   - Forum: https://github.com/music-assistant/server/discussions

2. **Report Issue**:
   - Include: Music Assistant version, error logs, system info
   - Reference: "Streaming pagination fix (ADR_001)"
   - Attach: Relevant log snippets

3. **Emergency Rollback**:
   - Follow rollback procedure above
   - Document issue for later investigation
   - Report to developers

## See Also

**Implementation Details**: [../04_INFRASTRUCTURE/APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md](../04_INFRASTRUCTURE/APPLE_MUSIC_PAGINATION_IMPLEMENTATION.md)

**Architecture Decision**: [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

**Reference Data**: [../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md](../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md)

**Troubleshooting**: [TROUBLESHOOTING_PAGINATION.md](TROUBLESHOOTING_PAGINATION.md) (if exists)
