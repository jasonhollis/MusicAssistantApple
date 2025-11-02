# Broken API Contract: Library Completeness
**Purpose**: Document the violated contract between backend and frontend for complete library data delivery
**Audience**: API developers, frontend developers, system integrators
**Layer**: 03_INTERFACES
**Status**: 🔴 CONTRACT VIOLATED - DATA COMPLETENESS GUARANTEE BROKEN
**Created**: 2025-10-25
**Related**: [CRITICAL_ISSUE_DATA_COMPLETENESS_VIOLATION.md](../00_ARCHITECTURE/CRITICAL_ISSUE_DATA_COMPLETENESS_VIOLATION.md)

---

## Intent

This document defines the **implied contract** between Music Assistant's backend API and frontend UI for library data delivery, and documents how this contract is currently **fundamentally violated**.

A well-designed API contract guarantees that when a client requests library data, it receives **complete** data or **explicit indication of incompleteness**. The current system violates this contract by silently delivering incomplete data.

---

## The API Contract (Expected)

### Contract Statement

```
MUSIC ASSISTANT LIBRARY API CONTRACT
====================================

Given:
  - Client requests library items (artists, albums, playlists, tracks)
  - Backend has complete data in database

Then Backend MUST either:
  1. Return ALL items the client is authorized to see
  OR
  2. Return partial results WITH explicit pagination metadata:
     - total_count: Total items available
     - returned_count: Items in this response
     - has_more: Boolean indicating more items exist
     - next_page: URL/offset for next page

And Backend MUST NOT:
  - Silently truncate results without indication
  - Report success when delivery is incomplete
  - Return inconsistent data across different interfaces
```

---

## Current Contract Violation

### What Should Happen

**Client Request**:
```http
GET /api/music/artists/library_items?limit=50000
```

**Expected Backend Response**:
```json
{
  "items": [
    /* ALL 2000+ artists A-Z */
  ],
  "metadata": {
    "total_count": 2000,
    "returned_count": 2000,
    "has_more": false,
    "limit": 50000,
    "offset": 0
  }
}
```

**Expected Frontend Behavior**:
- Display all 2000 artists
- Show pagination controls if `has_more: true`
- Display "Showing X of Y" counter

---

### What Actually Happens (BROKEN)

**Client Request**:
```http
GET /api/music/artists/library_items?limit=50000
```

**Actual Backend Response** (SUSPECTED):
```json
{
  "items": [
    /* ~700 artists A-J only */
  ],
  "metadata": {
    "total_count": 700,    // ⚠️ WRONG - Should be 2000
    "returned_count": 700,
    "has_more": false,     // ⚠️ WRONG - Should be true
    "limit": 50000,
    "offset": 0
  }
}
```

OR (alternatively):

```json
{
  "items": [
    /* Only 700 of 2000 artists */
  ]
  /* NO metadata at all - client assumes completeness */
}
```

**Actual Frontend Behavior**:
- Displays only 700 artists
- No indication more exist
- No pagination controls
- User assumes library is complete

**CONTRACT VIOLATION**: Backend claims completeness when data is incomplete

---

## API Endpoint Analysis

### Endpoint: `/api/music/artists/library_items`

**Purpose**: Retrieve artist library items

**Expected Parameters**:
```typescript
interface LibraryItemsRequest {
  limit?: number;        // Max items to return (default: 500)
  offset?: number;       // Skip N items (default: 0)
  order_by?: string;     // Sort field
  provider?: string;     // Filter by provider
  favorite?: boolean;    // Filter favorites only
  search?: string;       // Text search filter
}
```

**Expected Response**:
```typescript
interface LibraryItemsResponse {
  items: Artist[];           // Array of artist objects
  total_count: number;       // Total artists in library
  returned_count: number;    // Artists in this response
  has_more: boolean;         // More pages available
  limit: number;             // Request limit
  offset: number;            // Request offset
}
```

**Actual Response Structure** (NEEDS VERIFICATION):
```typescript
// Unknown - requires network capture
// Suspected: Missing pagination metadata
// Suspected: Incorrect total_count
```

---

### Endpoint: `/api/music/playlists/library_items`

**Status**: 🔴 **COMPLETELY BROKEN**

**Expected**: Return playlist library items

**Actual**:
- Returns: 0 playlists (should be 100+)
- Database: Contains playlists
- UI Display: Empty list

**CONTRACT VIOLATION**: Complete failure to deliver data

---

### Endpoint: `/api/music/search` (WORKING - REFERENCE)

**Status**: ✅ **CONTRACT HONORED**

**Purpose**: Search for library items

**Request**:
```http
GET /api/music/search?q=Madonna
```

**Response**:
```json
{
  "artists": [
    {
      "item_id": "123",
      "name": "Madonna",
      "provider": "apple_music"
      /* ... */
    }
  ]
  /* Returns correct results even for K-Z artists */
}
```

**Conclusion**: Search endpoint correctly returns ALL matching results, proving:
1. Backend CAN access all data
2. K-Z artists exist in database
3. API transport CAN deliver K-Z artists
4. Browse endpoint is specifically broken

---

## Contract Requirements

### Requirement 1: Complete Data Delivery

**Specification**:
```
IF client requests data with limit >= total_count
THEN backend MUST return ALL items
```

**Current Status**: ❌ VIOLATED
- Client requests: `limit=50000`
- Total items: 2000
- Should return: 2000 items
- Actually returns: ~700 items

---

### Requirement 2: Explicit Pagination Metadata

**Specification**:
```
IF backend returns partial results
THEN response MUST include:
  - total_count (total available)
  - returned_count (in this response)
  - has_more (boolean)
  - next_page indicator
```

**Current Status**: ❌ VIOLATED (or MISSING)
- No indication of incompleteness
- No pagination metadata visible
- Client cannot detect truncation

---

### Requirement 3: Consistency Across Interfaces

**Specification**:
```
GIVEN same data source (database)
WHEN accessed via different interfaces (browse vs search)
THEN results MUST be consistent
```

**Current Status**: ❌ VIOLATED

| Interface | Artists A-J | Artists K-Z | Status |
|-----------|-------------|-------------|--------|
| Browse | ✅ Visible | ❌ Missing | Broken |
| Search | ✅ Findable | ✅ Findable | Working |

---

### Requirement 4: Observable Failures

**Specification**:
```
IF system cannot deliver complete data
THEN system MUST:
  - Log warning/error
  - Return error status code OR
  - Include error indicator in response
```

**Current Status**: ❌ VIOLATED
- No errors logged
- No warnings shown
- Silent truncation
- Success reported when failing

---

## Data Flow Contract (Expected)

```
┌─────────────────────────────────────────────────────────┐
│ CLIENT (Frontend)                                       │
│ REQUEST: Get all artists (limit=50000)                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ API GATEWAY                                             │
│ - Validates request                                     │
│ - Routes to controller                                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ CONTROLLER (artists.py)                                 │
│ - Processes limit=50000                                 │
│ - Queries database for ALL artists                      │
│ - Gets 2000 artists from DB ✅                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ SERIALIZER / RESPONSE BUILDER                           │
│ - Serializes all 2000 artists to JSON                   │
│ - Adds metadata (total_count: 2000)                     │
│ - Returns complete response ✅                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ CLIENT (Frontend)                                       │
│ - Receives 2000 artists ✅                              │
│ - Displays all in UI ✅                                 │
│ - User sees complete library ✅                         │
└─────────────────────────────────────────────────────────┘
```

**Expected Outcome**: ✅ Complete data delivery

---

## Data Flow Reality (BROKEN)

```
┌─────────────────────────────────────────────────────────┐
│ CLIENT (Frontend)                                       │
│ REQUEST: Get all artists (limit=50000)                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ API GATEWAY                                             │
│ - Validates request                                     │
│ - Routes to controller                                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ CONTROLLER (artists.py)                                 │
│ - Processes limit=50000                                 │
│ - Queries database for ALL artists                      │
│ - Gets 2000 artists from DB ✅                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ ??? UNKNOWN BARRIER ???                                 │
│ - Truncates to 700 items ❌                             │
│ - Discards items 701-2000 ❌                            │
│ - No error raised ❌                                    │
│ - Silent data loss ❌                                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ CLIENT (Frontend)                                       │
│ - Receives only 700 artists ❌                          │
│ - Displays A-J only ❌                                  │
│ - No indication of incompleteness ❌                    │
│ - User sees incomplete library ❌                       │
└─────────────────────────────────────────────────────────┘
```

**Actual Outcome**: ❌ Silent data truncation

**Critical Question**: Where is the unknown barrier?

---

## Contract Validation Tests

### Test 1: Complete Data Delivery

**Test**:
```bash
# Request all artists
curl -s "http://localhost:8095/api/music/artists/library_items?limit=50000" \
  | jq '.items | length'
```

**Expected**: `2000` (or database count)
**Actual**: ⚠️ **NEEDS VERIFICATION**
**Status**: ⚠️ **NOT TESTED**

---

### Test 2: Metadata Accuracy

**Test**:
```bash
curl -s "http://localhost:8095/api/music/artists/library_items?limit=50000" \
  | jq '{total: .total_count, returned: (.items | length), has_more: .has_more}'
```

**Expected**:
```json
{
  "total": 2000,
  "returned": 2000,
  "has_more": false
}
```

**Actual**: ⚠️ **NEEDS VERIFICATION**
**Status**: ⚠️ **NOT TESTED**

---

### Test 3: Pagination Correctness

**Test**:
```bash
# Page 1
curl -s "http://localhost:8095/api/music/artists/library_items?limit=100&offset=0" \
  | jq '.items[0].name'

# Page 20 (should be K-Z artists)
curl -s "http://localhost:8095/api/music/artists/library_items?limit=100&offset=2000" \
  | jq '.items[0].name'
```

**Expected**: Page 20 contains K-Z artists
**Actual**: ⚠️ **NEEDS VERIFICATION**
**Status**: ⚠️ **NOT TESTED**

---

### Test 4: Search-Browse Consistency

**Test**:
```bash
# Via search
curl -s "http://localhost:8095/api/music/search?q=Madonna" \
  | jq '.artists[0].item_id'

# Via browse
curl -s "http://localhost:8095/api/music/artists/library_items?limit=50000" \
  | jq '.items[] | select(.name == "Madonna") | .item_id'
```

**Expected**: Both return same item_id
**Actual**: Search works, browse likely missing Madonna
**Status**: ⚠️ **NEEDS VERIFICATION**

---

## Proposed Contract Specification

### Endpoint Signature (Corrected)

```typescript
/**
 * Get library items with guaranteed completeness
 */
interface GET_/api/music/artists/library_items {
  request: {
    limit?: number;         // Max items per page (default: 100)
    offset?: number;        // Skip N items (default: 0)
    order_by?: string;      // Sort field (default: "sort_name")
    provider?: string;      // Filter by provider
    favorite?: boolean;     // Filter favorites only
    search?: string;        // Search query
  };

  response: {
    items: Artist[];        // Artist objects

    // REQUIRED pagination metadata
    pagination: {
      total_count: number;      // Total items in library
      returned_count: number;   // Items in this response
      limit: number;            // Applied limit
      offset: number;           // Applied offset
      has_more: boolean;        // More pages exist
      next_offset?: number;     // Offset for next page
    };

    // REQUIRED completeness guarantee
    completeness: {
      is_complete: boolean;     // True if ALL data returned
      coverage_percent: number; // % of total returned (0-100)
      truncation_reason?: string; // If incomplete, why?
    };
  };

  // ERROR handling
  errors?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  }[];
}
```

---

### Contract Enforcement

**Backend MUST**:
```python
def get_library_items(limit: int, offset: int) -> LibraryResponse:
    # Get total count from DB
    total_count = db.query(Artist).count()

    # Get requested items
    items = db.query(Artist).limit(limit).offset(offset).all()

    # Calculate completeness
    returned_count = len(items)
    is_complete = (offset + returned_count >= total_count)
    has_more = not is_complete

    return {
        "items": items,
        "pagination": {
            "total_count": total_count,      # MUST be accurate
            "returned_count": returned_count,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None
        },
        "completeness": {
            "is_complete": is_complete,
            "coverage_percent": (returned_count / total_count) * 100
        }
    }
```

**Frontend MUST**:
```typescript
function displayLibrary(response: LibraryResponse) {
  // Display items
  renderItems(response.items);

  // Show completeness status
  if (!response.completeness.is_complete) {
    showWarning(
      `Showing ${response.pagination.returned_count} ` +
      `of ${response.pagination.total_count} artists. ` +
      `Load more to see complete library.`
    );
  }

  // Provide pagination controls if needed
  if (response.pagination.has_more) {
    showLoadMoreButton(response.pagination.next_offset);
  }
}
```

---

## Contract Violations Summary

| Requirement | Expected | Actual | Violation |
|-------------|----------|--------|-----------|
| Complete data delivery | 2000 items | ~700 items | ❌ YES |
| Pagination metadata | Required | Missing/Wrong | ❌ YES |
| Consistency (browse/search) | Same results | Inconsistent | ❌ YES |
| Error indication | If incomplete | Silent | ❌ YES |
| User notification | "X of Y shown" | None | ❌ YES |

**Severity**: 🔴 CRITICAL - All core requirements violated

---

## Investigation Requirements

To resolve contract violations, must verify:

### Backend Verification

- [ ] **Test API directly**: Capture raw API response via curl
- [ ] **Check response structure**: Does it include pagination metadata?
- [ ] **Verify item count**: How many artists does backend return?
- [ ] **Check database query**: Does controller query return all items?

### Transport Verification

- [ ] **Capture network traffic**: Browser DevTools Network tab
- [ ] **Check request parameters**: What does frontend actually request?
- [ ] **Check response size**: Does response contain all data?
- [ ] **Check WebSocket messages**: If using WebSocket, inspect messages

### Frontend Verification

- [ ] **Inspect component state**: Vue DevTools artist list
- [ ] **Check rendering logic**: Does frontend display all received items?
- [ ] **Find limit enforcement**: Where is 700-item limit imposed?

---

## Remediation Steps

### Short-term: Add Observability

**Goal**: Make contract violations visible

```python
# Backend logging
logger.info(
    f"Library request: limit={limit}, offset={offset}, "
    f"db_count={total_count}, returned={len(items)}"
)

if len(items) < total_count and limit >= total_count:
    logger.warning(
        f"CONTRACT VIOLATION: Requested {limit} items, "
        f"have {total_count} items, but only returning {len(items)}!"
    )
```

```typescript
// Frontend logging
console.log('Library response:', {
  requestedLimit: requestedLimit,
  receivedCount: response.items.length,
  totalCount: response.pagination?.total_count,
  hasMore: response.pagination?.has_more
});

if (response.items.length < requestedLimit && response.pagination?.has_more) {
  console.warn('Incomplete data received - more items available');
}
```

---

### Long-term: Enforce Contract

**Goal**: Guarantee complete data delivery

1. **Backend**: Return all requested data or explicit pagination
2. **Frontend**: Display completeness indicators
3. **Tests**: Automated contract verification
4. **Monitoring**: Alert on contract violations

---

## Related Interfaces

**Working Contracts**:
- Search API ✅ - Returns complete results
- Database query interface ✅ - Returns all data

**Broken Contracts**:
- Browse API ❌ - Silent truncation
- Playlist API ❌ - Returns zero items

---

## Verification

This contract is considered **HONORED** when:

- [ ] Backend returns all items when `limit >= total_count`
- [ ] Response includes accurate `total_count` metadata
- [ ] Response includes accurate `has_more` indicator
- [ ] Frontend displays completeness status to user
- [ ] Browse and search return consistent results
- [ ] Incomplete data delivery triggers warnings/errors
- [ ] Automated tests verify contract compliance

**Current Status**: 0/7 criteria met - **Contract completely violated**

---

**Last Updated**: 2025-10-25
**Status**: 🔴 CRITICAL - API CONTRACT VIOLATED - DATA COMPLETENESS NOT GUARANTEED
**Impact**: Users cannot trust browse interface to show complete library
