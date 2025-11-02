# Sync Provider Library

**Purpose**: Define the workflow for synchronizing music library data from external providers
**Audience**: Product managers, backend developers, QA engineers
**Layer**: 01_USE_CASES
**Related**: [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

## Intent

Users connect external music services (Apple Music, Spotify, etc.) to Music Assistant and expect their complete library to be synchronized and kept up-to-date. The synchronization process must handle libraries of any size without data loss, silent failures, or performance degradation.

## Actors

**Primary Actor**: Music Assistant System (automated)
**Secondary Actor**: Music Listener (initiates sync)
**External System**: Music Provider API (Apple Music, Spotify, etc.)

## Preconditions

1. User has authenticated with music provider
2. Valid API credentials/tokens exist
3. Network connectivity to provider API available
4. Music Assistant database is accessible
5. Sufficient storage space for library metadata

## Use Case: Initial Library Sync

### Goal

Synchronize complete music library from external provider to Music Assistant database for the first time.

### Primary Flow

1. User connects music provider account (or system initiates scheduled sync)
2. System authenticates with provider API
3. System begins fetching library items by category:
   - Artists
   - Albums
   - Tracks
   - Playlists
4. For each category:
   a. System fetches one page of items (e.g., 50 items)
   b. System validates and parses each item
   c. System stores successfully parsed items in database
   d. System logs any item-level errors
   e. System fetches next page
   f. Repeat until all pages retrieved
5. System logs sync completion with statistics
6. User can access synced library through UI

### Success Criteria

- All available items from provider are stored in database
- Database counts match provider API totals (within margin for concurrent changes)
- Sync completes within reasonable time (< 1 minute per 1000 items)
- Per-item errors logged but don't abort sync
- User can immediately access synced data

### Timing Expectations

| Library Size | Expected Sync Time | Acceptable Range |
|--------------|-------------------|------------------|
| 500 items | ~1 minute | 30s - 2min |
| 1,000 items | ~2 minutes | 1min - 4min |
| 2,500 items | ~5 minutes | 3min - 10min |
| 5,000 items | ~10 minutes | 5min - 20min |
| 10,000 items | ~20 minutes | 10min - 40min |

**Note**: Time varies based on API rate limits and network latency.

## Alternative Flows

### Alternative 1: Incremental Sync

**Trigger**: User has previously synced, running update sync

1. System fetches items modified since last sync timestamp
2. System updates existing database records
3. System adds new items
4. System marks deleted items as inactive

**Success Criteria**: Database reflects current provider state

### Alternative 2: Selective Category Sync

**Trigger**: User chooses to sync only specific categories

1. User selects categories to sync (e.g., only artists and albums)
2. System syncs selected categories only
3. Other categories remain unchanged

**Success Criteria**: Selected categories updated, others unaffected

### Alternative 3: Resumable Sync After Interruption

**Trigger**: Sync interrupted (network loss, system restart, etc.)

1. System detects incomplete prior sync
2. System determines last successfully synced item
3. System resumes from next item
4. System completes remaining items

**Success Criteria**: No duplicate items, all items eventually synced

## Failure Flows

### Failure 1: Silent Partial Sync

**Trigger**: Sync stops mid-process without error indication

**Symptoms**:
- Sync appears complete (no error message)
- Database contains partial data (e.g., artists A-J only)
- Total count in UI does not match provider totals
- User unaware of incompleteness

**System Impact**:
- Database integrity appears intact
- No error logs generated (or logged as success)
- Subsequent syncs may not correct the issue

**User Impact**:
- Cannot access 50-70% of library
- May believe items never existed in provider
- Lost confidence in system reliability

**Root Cause Examples**:
- Timeout during batch accumulation
- Memory exhaustion causing silent failure
- Exception caught and suppressed without logging
- Pagination logic stops prematurely

**Correct Behavior**: System MUST log error, indicate partial completion, provide retry mechanism

### Failure 2: Memory Exhaustion During Sync

**Trigger**: Large library causes memory accumulation

**Symptoms**:
- System becomes progressively slower during sync
- Memory usage grows continuously
- System eventually crashes or kills process
- Out-of-memory error (if logged)

**System Impact**:
- Sync cannot complete for large libraries
- System instability
- May affect other Music Assistant operations

**User Impact**:
- Cannot sync large libraries
- Unpredictable failures
- System appears broken

**Root Cause Examples**:
- Accumulating all items in memory before processing
- Memory leaks in parsing logic
- Unbounded caching

**Correct Behavior**: System MUST use constant memory (O(1) relative to library size)

### Failure 3: Timeout Without Retry

**Trigger**: Network or API timeout during fetch

**Symptoms**:
- Error message: "Request timeout"
- Sync stops completely
- No automatic retry
- Partial data in database

**System Impact**:
- Sync incomplete
- May leave inconsistent state

**User Impact**:
- Must manually retry
- Frustration with unreliable sync
- Uncertain about data completeness

**Root Cause Examples**:
- Single request timeout affecting entire operation
- No retry logic for transient failures
- Timeout threshold too short for large requests

**Correct Behavior**: System MUST retry transient failures, use per-page timeouts, provide clear error messages

### Failure 4: API Rate Limit Exceeded

**Trigger**: Too many API requests in short time period

**Symptoms**:
- HTTP 429 errors
- Sync aborts or hangs
- Error: "Rate limit exceeded"

**System Impact**:
- Cannot complete sync
- May get temporarily banned from API

**User Impact**:
- Sync fails repeatedly
- Long delays before retry possible

**Root Cause Examples**:
- Insufficient rate limiting in client
- Burst requests overwhelming API
- Not respecting retry-after headers

**Correct Behavior**: System MUST implement rate limiting, respect API limits, handle 429 gracefully with backoff

## Business Rules

### Rule 1: Completeness Over Speed

**Statement**: Sync MUST prioritize completeness over speed. A slow sync that retrieves all items is preferable to a fast sync that silently truncates data.

**Rationale**: Missing data is worse than slow sync. Users can wait, but cannot access data that was never synced.

**Verification**: After sync, database count matches provider API total count

### Rule 2: Incremental Progress

**Statement**: Successfully synced items MUST be saved even if subsequent items fail.

**Rationale**: Partial progress is valuable. Losing all progress due to single item failure is unacceptable.

**Verification**: After sync failure, database contains successfully processed items up to failure point

### Rule 3: Transparent Failures

**Statement**: Any sync failure or incompleteness MUST be explicitly communicated to user and logged.

**Rationale**: Silent failures destroy user trust. Users must know when data is incomplete.

**Verification**: Failed sync shows error in UI and logs diagnostic information

### Rule 4: Idempotent Sync

**Statement**: Running sync multiple times MUST produce same result without duplicates.

**Rationale**: Users may retry sync for various reasons. Duplicate data corrupts library.

**Verification**: Sync twice, verify no duplicate items in database

### Rule 5: Bounded Resource Usage

**Statement**: Sync memory usage MUST NOT grow proportionally with library size.

**Rationale**: Large libraries are common. Unbounded memory usage makes sync impossible for large libraries.

**Verification**: Monitor memory during sync of 1000 vs 10,000 items (should be equivalent)

## Data Validation Rules

### Artist Validation

**Required Fields**:
- Unique identifier (provider ID)
- Artist name

**Optional Fields**:
- Images
- Genres
- Biography

**Validation**:
- Skip items missing required fields (log warning)
- Use defaults for missing optional fields
- Normalize name (trim whitespace, etc.)

### Album Validation

**Required Fields**:
- Unique identifier
- Album title
- Artist reference

**Optional Fields**:
- Release date
- Album art
- Track count

**Validation**:
- Skip albums without valid artist reference (log error)
- Use placeholder for missing album art
- Validate date formats

### Track Validation

**Required Fields**:
- Unique identifier
- Track title
- Duration
- Album reference

**Optional Fields**:
- Track number
- Disc number
- ISRC

**Validation**:
- Skip tracks without album reference
- Default duration to 0 if missing (log warning)
- Validate duration is positive number

### Playlist Validation

**Required Fields**:
- Unique identifier
- Playlist name

**Optional Fields**:
- Description
- Artwork
- Track list

**Validation**:
- Allow empty playlists
- Validate track references exist in database
- Skip playlists with invalid names

## Error Handling Strategy

### Item-Level Errors

**Policy**: Log and skip, continue with remaining items

**Examples**:
- Malformed data from API
- Missing required fields
- Invalid references

**Action**:
1. Log warning with item ID and error details
2. Increment error counter
3. Continue processing next item
4. Include error count in final sync report

### Page-Level Errors

**Policy**: Retry with backoff, abort if persistent

**Examples**:
- Network timeout
- API rate limit
- Temporary service unavailable

**Action**:
1. Log error with page details
2. Wait with exponential backoff (2s, 4s, 8s, 16s)
3. Retry up to 3 times
4. If still failing, abort sync with error
5. Save progress up to failure point

### Category-Level Errors

**Policy**: Continue with other categories

**Examples**:
- Provider doesn't support category (e.g., no playlists)
- Permission denied for specific category

**Action**:
1. Log error with category name
2. Skip category
3. Continue with remaining categories
4. Report partial sync completion

### Sync-Level Errors

**Policy**: Abort and report failure

**Examples**:
- Authentication failure
- Database connection lost
- Out of memory

**Action**:
1. Log error with full context
2. Abort sync immediately
3. Show error in UI
4. Provide retry mechanism
5. Preserve any completed categories

## Progress Observability

### Required Progress Information

1. **Current Activity**: "Syncing artists...", "Syncing albums..."
2. **Item Count**: "150 of ~1,000 artists synced"
3. **Percentage**: "15% complete" (if total known)
4. **Time Estimate**: "~5 minutes remaining" (if calculable)
5. **Error Count**: "3 items skipped due to errors"

### Progress Logging

**Frequency**: Log every N items or every M seconds, whichever comes first

**Example**:
```
[INFO] Starting artist sync
[DEBUG] Fetched page 0: 50 artists
[DEBUG] Fetched page 5: 250 artists
[DEBUG] Fetched page 10: 500 artists
[WARN] Failed to parse artist xyz123: missing required field 'name'
[DEBUG] Fetched page 20: 1000 artists
[INFO] Artist sync complete: 1000 artists, 1 error
```

### User-Facing Progress

**Initial Sync**:
- Progress bar with percentage
- Current category and item count
- Estimated time remaining

**Background Sync**:
- Subtle indicator (icon animation)
- Notification on completion
- Error badge if failures occurred

## Postconditions

### Success Postconditions

1. Database contains all available library items from provider
2. Item counts match provider API totals (within margin)
3. All items are accessible through UI
4. Sync completion logged with statistics
5. Last sync timestamp updated
6. No errors in error log (or only item-level warnings)

### Failure Postconditions

1. Error logged with diagnostic details
2. Partial data saved (if any items succeeded)
3. User notified of failure with actionable message
4. Retry mechanism available
5. System state remains consistent (no corruption)

### Partial Success Postconditions

1. Successfully synced items available in UI
2. Error count reported to user
3. Specific failures logged for debugging
4. User can choose to retry or proceed with partial data

## Related Use Cases

- [BROWSE_COMPLETE_ARTIST_LIBRARY.md](BROWSE_COMPLETE_ARTIST_LIBRARY.md) - Access synced data
- [SEARCH_MUSIC_LIBRARY.md](SEARCH_MUSIC_LIBRARY.md) - Find specific synced items
- [UPDATE_LIBRARY.md](UPDATE_LIBRARY.md) - Incremental sync updates
- [VIEW_SYNC_STATUS.md](VIEW_SYNC_STATUS.md) - Monitor sync progress

## Quality Attributes

### Completeness

**Measurement**: (Items in database) / (Items in provider) × 100%
**Target**: ≥ 99.9% (allowing for items that fail validation)

### Reliability

**Measurement**: Percentage of syncs that complete without errors
**Target**: ≥ 95% for stable network conditions

### Performance

**Measurement**: Items synced per minute
**Target**: ≥ 50 items/minute (accounting for API rate limits)

### Scalability

**Measurement**: Maximum library size successfully synced
**Target**: No practical limit (tested up to 10,000+ items)

### Observability

**Measurement**: User can determine sync status and completeness
**Target**: 100% of sync states visible to user

## Validation Scenarios

### Scenario 1: Fresh Account, Small Library

**Setup**: New user with 200 artists, 50 albums
**Expected**:
- Sync completes in < 1 minute
- All items appear in UI
- No errors logged
- User can immediately browse library

### Scenario 2: Fresh Account, Large Library

**Setup**: New user with 3,000 artists, 1,500 albums, 20,000 tracks
**Expected**:
- Sync completes in < 15 minutes
- Progress visible throughout sync
- All items appear in UI
- Memory usage remains constant
- Last artist alphabetically is synced (proves completeness)

### Scenario 3: Network Interruption Mid-Sync

**Setup**: Sync interrupted after 50% completion
**Expected**:
- Error message shown to user
- Successfully synced items (50%) remain in database
- Retry resumes from interruption point
- No duplicate items after completion

### Scenario 4: API Rate Limit Hit

**Setup**: Sync triggers API rate limiting
**Expected**:
- System automatically backs off
- Sync slows but continues
- Eventually completes successfully
- User sees "Syncing slower due to API limits" message

### Scenario 5: Malformed Data from API

**Setup**: 5 out of 1,000 items have invalid data
**Expected**:
- 995 items sync successfully
- 5 items skipped with warnings in log
- Sync reports "995 of 1,000 items synced (5 errors)"
- User can view error details

## See Also

**Architecture**: [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

**Architecture**: [../00_ARCHITECTURE/WEB_UI_SCALABILITY_PRINCIPLES.md](../00_ARCHITECTURE/WEB_UI_SCALABILITY_PRINCIPLES.md)

**Implementation** (to be created): `docs/04_INFRASTRUCTURE/`

**Operations** (to be created): `docs/05_OPERATIONS/`
