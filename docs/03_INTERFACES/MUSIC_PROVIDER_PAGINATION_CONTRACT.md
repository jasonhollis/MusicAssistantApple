# Music Provider Pagination Contract

**Purpose**: Define the stable interface contract for paginated data retrieval from music providers
**Audience**: Backend developers, integration engineers, API consumers
**Layer**: 03_INTERFACES
**Related**: [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

## Intent

This document specifies the interface contract for retrieving paginated library data from music providers. The contract defines the stable API that must remain consistent regardless of implementation changes, ensuring backward compatibility and proper separation of concerns.

## Core Interface: Async Generator for Library Items

### Method Signature

```python
async def get_library_items(
    self,
    category: str,
    page_size: int = 50,
    include_metadata: bool = True
) -> AsyncGenerator[LibraryItem, None]:
    """
    Stream library items from provider.

    This is the stable interface contract. Implementation may change,
    but this signature and behavior contract must remain stable.

    Args:
        category: Item category ('artists', 'albums', 'tracks', 'playlists')
        page_size: Items per page (default: 50, max: 100)
        include_metadata: Whether to fetch extended metadata

    Yields:
        LibraryItem: Individual library items as they become available

    Raises:
        AuthenticationError: If provider authentication fails
        RateLimitError: If API rate limit exceeded (should be handled internally)
        ProviderError: For provider-specific errors
    """
```

### Contract Guarantees

**MUST**:
1. Yield items incrementally as they become available
2. Handle pagination internally (opaque to caller)
3. Implement rate limiting internally
4. Continue yielding items until all retrieved or error occurs
5. Log but skip individual items that fail validation
6. Raise exception only for category-level or provider-level failures

**MUST NOT**:
1. Load all items into memory before yielding first item
2. Block for unbounded time periods
3. Silently truncate data without raising exception
4. Yield duplicate items in normal operation
5. Expose pagination details to caller

**MAY**:
1. Prefetch next page while processing current page
2. Cache items for short duration
3. Batch API requests for efficiency
4. Implement different strategies for different categories

### Behavior Contract

#### Streaming Semantics

**Time to First Item**:
- MUST yield first item within 5 seconds of method call
- MUST NOT wait for entire dataset before yielding

**Incremental Progress**:
- Each yielded item represents committed progress
- Caller MAY consume items immediately
- Caller MUST NOT assume all items available upfront

**Completion Indication**:
- Generator exhaustion indicates all items retrieved
- Exception indicates failure (partial or complete)
- No items yielded + no exception = empty category

#### Error Handling Contract

**Item-Level Errors**:
- MUST log warning with item details
- MUST skip item and continue with next
- MUST NOT raise exception
- MUST include error count in final metrics

**Page-Level Errors** (transient):
- MUST retry with exponential backoff
- MUST retry up to 3 times
- MUST raise exception if all retries fail
- SHOULD preserve progress up to failure point

**Category-Level Errors**:
- MUST raise exception immediately
- MUST include diagnostic details in exception
- MAY preserve partial progress in implementation

#### Memory Contract

**Memory Usage**:
- MUST maintain O(1) memory relative to total items
- Memory footprint determined by page_size, not total count
- MUST NOT accumulate items in unbounded collection

**Resource Cleanup**:
- MUST release resources when generator exhausted
- MUST release resources when generator destroyed
- SHOULD implement context manager protocol

## Data Transfer Objects (DTOs)

### LibraryItem

**Base Interface**:
```python
@dataclass
class LibraryItem:
    """Base interface for all library items."""

    # Required fields (MUST be present)
    id: str                    # Unique identifier from provider
    provider: str              # Provider name ('apple_music', 'spotify', etc.)
    category: str              # Item category ('artist', 'album', 'track', 'playlist')
    name: str                  # Display name

    # Optional fields (MAY be None)
    metadata: Dict[str, Any] | None = None
    images: List[ImageDTO] | None = None
    external_url: str | None = None

    # Metadata fields
    synced_at: datetime        # When item was retrieved
    version: str               # Contract version (for future compatibility)
```

**Contract Rules**:
- Required fields MUST never be None
- Optional fields MAY be None
- Unknown fields MUST be preserved in metadata dict
- Field types MUST NOT change (breaking change)
- New optional fields MAY be added (non-breaking change)

### ArtistDTO

```python
@dataclass
class ArtistDTO(LibraryItem):
    """Artist-specific library item."""

    # Category is always 'artist'
    category: str = 'artist'

    # Artist-specific fields (optional)
    genres: List[str] | None = None
    biography: str | None = None
    similar_artists: List[str] | None = None  # List of artist IDs
```

### AlbumDTO

```python
@dataclass
class AlbumDTO(LibraryItem):
    """Album-specific library item."""

    category: str = 'album'

    # Album-specific required fields
    artist_id: str             # Reference to artist

    # Album-specific optional fields
    artist_name: str | None = None
    release_date: date | None = None
    track_count: int | None = None
    album_type: str | None = None  # 'album', 'single', 'compilation'
```

### PlaylistDTO

```python
@dataclass
class PlaylistDTO(LibraryItem):
    """Playlist-specific library item."""

    category: str = 'playlist'

    # Playlist-specific fields
    description: str | None = None
    track_ids: List[str] | None = None
    owner: str | None = None
    is_public: bool = False
    is_collaborative: bool = False
```

### TrackDTO

```python
@dataclass
class TrackDTO(LibraryItem):
    """Track-specific library item."""

    category: str = 'track'

    # Track-specific required fields
    duration_ms: int           # Duration in milliseconds
    album_id: str              # Reference to album

    # Track-specific optional fields
    artist_ids: List[str] | None = None
    album_name: str | None = None
    artist_names: List[str] | None = None
    track_number: int | None = None
    disc_number: int | None = None
    isrc: str | None = None
    explicit: bool = False
```

### ImageDTO

```python
@dataclass
class ImageDTO:
    """Image metadata."""

    url: str                   # Required: Image URL
    width: int | None = None
    height: int | None = None
    size: str | None = None    # 'small', 'medium', 'large'
```

## Exception Contract

### Exception Hierarchy

```python
class ProviderError(Exception):
    """Base exception for all provider errors."""
    pass

class AuthenticationError(ProviderError):
    """Provider authentication failed."""
    pass

class RateLimitError(ProviderError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after  # Seconds until retry allowed
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")

class ValidationError(ProviderError):
    """Item failed validation."""

    def __init__(self, item_id: str, reason: str):
        self.item_id = item_id
        self.reason = reason
        super().__init__(f"Validation failed for {item_id}: {reason}")

class PageFetchError(ProviderError):
    """Failed to fetch page after retries."""

    def __init__(self, page: int, attempts: int, last_error: Exception):
        self.page = page
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed to fetch page {page} after {attempts} attempts")

class CategoryNotSupportedError(ProviderError):
    """Provider does not support this category."""

    def __init__(self, provider: str, category: str):
        self.provider = provider
        self.category = category
        super().__init__(f"{provider} does not support category '{category}'")
```

### Error Handling Contract

**Caller Responsibilities**:
- MUST handle AuthenticationError (cannot be retried without re-auth)
- SHOULD handle RateLimitError (may indicate system issue)
- SHOULD handle PageFetchError (may indicate network issue)
- MAY handle CategoryNotSupportedError (expected for some providers)

**Implementation Responsibilities**:
- MUST NOT raise ValidationError to caller (log and skip item)
- MUST retry RateLimitError internally (raise only if persistent)
- MUST retry PageFetchError internally (raise only after max retries)
- MUST raise AuthenticationError immediately (no retry)

## Progress Reporting Interface

### Optional: Progress Callback

```python
from typing import Protocol

class ProgressCallback(Protocol):
    """Optional progress reporting interface."""

    def on_page_fetched(
        self,
        category: str,
        page: int,
        items_in_page: int,
        total_items_so_far: int
    ) -> None:
        """Called after each page successfully fetched."""
        ...

    def on_item_error(
        self,
        category: str,
        item_id: str,
        error: Exception
    ) -> None:
        """Called when individual item fails validation."""
        ...

    def on_complete(
        self,
        category: str,
        total_items: int,
        error_count: int,
        duration_seconds: float
    ) -> None:
        """Called when sync completes (success or failure)."""
        ...
```

**Contract**:
- Progress callback is OPTIONAL
- If provided, implementation MUST call at appropriate times
- Callback exceptions MUST be logged but MUST NOT abort sync
- Callback SHOULD execute quickly (< 100ms)

## Backward Compatibility Rules

### Non-Breaking Changes (Allowed)

1. Adding new optional fields to DTOs
2. Adding new exception types (subclasses of existing)
3. Adding new optional parameters to methods (with defaults)
4. Adding new progress callback methods (with default no-op)
5. Improving performance while maintaining behavior
6. Adding internal caching or optimization

### Breaking Changes (Forbidden)

1. Removing or renaming required fields
2. Changing field types
3. Changing method signatures (required parameters)
4. Changing exception inheritance hierarchy
5. Changing from async generator to batch return
6. Removing support for previously supported categories

### Deprecation Process

If breaking change is necessary:

1. Mark old interface as deprecated (runtime warning)
2. Provide new interface alongside old
3. Maintain both for minimum 6 months
4. Document migration path
5. Remove old interface only in major version bump

## Versioning Contract

### Interface Version

```python
PROVIDER_INTERFACE_VERSION = "1.0.0"
```

**Semantic Versioning**:
- Major: Breaking changes (requires client update)
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

**Version Communication**:
- Each LibraryItem MUST include version field
- Clients MAY reject items with incompatible versions
- Implementations MUST support all minor versions within major version

## Testing Contract

### Implementation MUST Pass

**Completeness Tests**:
- [ ] Returns all items from provider (verified against provider API)
- [ ] No duplicate items in normal operation
- [ ] All required fields populated for every item

**Streaming Tests**:
- [ ] Yields first item within 5 seconds
- [ ] Memory usage constant regardless of library size
- [ ] Can process 10,000+ items without failure

**Error Handling Tests**:
- [ ] Skips invalid items without aborting
- [ ] Retries transient failures (network, rate limit)
- [ ] Raises appropriate exceptions for category failures

**Performance Tests**:
- [ ] Processes ≥ 50 items per minute (accounting for rate limits)
- [ ] Memory usage < 5 MB for any library size
- [ ] CPU usage reasonable during sync

## Migration from Batch to Streaming

### Old Interface (Deprecated)

```python
async def get_library_items(category: str) -> List[LibraryItem]:
    """
    DEPRECATED: Batch loading interface.

    This interface loads all items before returning, causing memory
    and timeout issues with large libraries.

    Use the async generator version instead.
    """
    warnings.warn(
        "Batch loading interface is deprecated, use streaming version",
        DeprecationWarning
    )
    items = []
    async for item in get_library_items_streaming(category):
        items.append(item)
    return items
```

### Migration Guide for Callers

**Before**:
```python
items = await provider.get_library_items('artists')
for item in items:
    process(item)
```

**After**:
```python
async for item in provider.get_library_items('artists'):
    process(item)
```

**Key Change**: Loop changes from sync `for` to async `async for`.

## See Also

**Architecture**: [../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md](../00_ARCHITECTURE/ADR_001_STREAMING_PAGINATION.md)

**Reference**: [../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md](../02_REFERENCE/PAGINATION_LIMITS_REFERENCE.md)

**Use Cases**: [../01_USE_CASES/SYNC_PROVIDER_LIBRARY.md](../01_USE_CASES/SYNC_PROVIDER_LIBRARY.md)

**Implementation**: `docs/04_INFRASTRUCTURE/` (references this contract)
