# ADR 001: Streaming Pagination for Large Libraries

**Status**: Proposed
**Date**: 2025-10-25
**Decision Makers**: System Architects, Backend Developers
**Layer**: 00_ARCHITECTURE
**Related**: [WEB_UI_SCALABILITY_PRINCIPLES.md](WEB_UI_SCALABILITY_PRINCIPLES.md)

## Context

Music library providers must sync potentially unlimited numbers of items (artists, albums, tracks, playlists) from external services into the local Music Assistant database. The current implementation experiences failures when library size exceeds certain thresholds.

### Problem Statement

Systems that accumulate data in memory before processing exhibit failure modes that are:
- **Silent**: No error messages, appears to complete successfully
- **Arbitrary**: Failure point depends on memory, network, timeout settings
- **Invisible**: Users cannot determine if sync is complete or partial
- **Non-deterministic**: Varies with system load, network speed, API performance

### Symptoms Observed

1. Large libraries appear to sync successfully but display only partial data
2. Failure point correlates with alphabetical position (e.g., stops at letter "J")
3. Backend database contains complete data, but users cannot access it
4. No error messages or warnings indicate incomplete sync
5. Problem severity increases with library size

## Decision

**Adopt streaming pagination as the foundational pattern for all data synchronization operations.**

### Core Principles

1. **Stream, Don't Accumulate**: Process data items incrementally as they arrive, never accumulating unbounded collections in memory

2. **Constant Memory Footprint**: Memory usage must remain O(1) relative to dataset size, determined by page size not total item count

3. **Incremental Progress**: Each successfully processed item represents forward progress, independent of subsequent items

4. **Graceful Degradation**: Per-item errors do not halt processing of remaining items

5. **Observable Progress**: System provides visibility into ongoing operations

## Rationale

### Why Streaming Over Batch Processing

**Batch Processing Characteristics**:
```
Fetch all items → Accumulate in memory → Process complete set
```

**Failures**:
- Memory: O(n) growth with dataset size
- Time: O(n) blocking time before first result
- Resilience: Single item failure aborts entire operation
- Scalability: Hard upper limit determined by memory/timeout

**Streaming Characteristics**:
```
Fetch page → Process items → Fetch next page → Process items → ...
```

**Benefits**:
- Memory: O(1) determined by page size
- Time: O(1) to first result, O(n) total but non-blocking
- Resilience: Per-item error handling
- Scalability: No theoretical upper limit

### Why This Aligns With System Architecture

Music Assistant uses **async generators** throughout the codebase for library operations. The streaming pagination pattern:

1. **Honors async generator semantics**: Yield items as available, don't await complete collection
2. **Maintains architectural consistency**: Matches existing patterns in codebase
3. **Preserves interface contracts**: Async generator signatures remain unchanged
4. **Enables pipeline optimization**: Downstream processing can begin immediately

## Alternatives Considered

### Alternative 1: Increase Timeout Values

**Approach**: Extend timeout from 120s to 300s or higher

**Pros**:
- Minimal code changes
- May work for moderately larger libraries

**Cons**:
- Doesn't address memory accumulation
- Still has hard limit, just moved higher
- Poor user experience (multi-minute waits)
- Timeout increases affect all operations, not just large libraries

**Rejected Because**: Treats symptom, not root cause. Scalability remains fundamentally limited.

### Alternative 2: Chunked Batch Processing

**Approach**: Fetch N pages, process as batch, fetch next N pages, repeat

**Pros**:
- Reduces memory vs. full batch
- May improve throughput vs. item-by-item

**Cons**:
- More complex than pure streaming
- Still accumulates memory per chunk
- Timeout risk per chunk
- Requires tuning chunk size for different dataset characteristics

**Rejected Because**: Adds complexity without providing benefits over streaming. Streaming is simpler and more general.

### Alternative 3: Cursor-Based Pagination

**Approach**: Use opaque cursor tokens instead of offset-based pagination

**Pros**:
- More efficient for databases
- Better performance for very large datasets
- Eliminates "page drift" issues

**Cons**:
- External API must support cursor-based pagination
- Cannot implement client-side if API only provides offset-based
- Would require API changes (not possible for third-party services)

**Rejected Because**: Not supported by target APIs (Apple Music, Spotify use offset-based pagination).

### Alternative 4: Hybrid - Batch for Small, Stream for Large

**Approach**: Detect dataset size, use batch for < 1000 items, streaming for larger

**Pros**:
- Potentially optimal performance for both cases
- Backward compatible with existing small-library behavior

**Cons**:
- Increases code complexity (two code paths)
- Size threshold is arbitrary
- Detection step adds overhead
- More edge cases to test

**Rejected Because**: Streaming works well for both small and large datasets. Single code path is simpler and more maintainable.

## Consequences

### Positive

1. **Unbounded Scalability**: No practical limit on library size
2. **Predictable Performance**: Response time independent of total dataset size
3. **Better User Experience**: Incremental progress visible, no long blocking waits
4. **Improved Resilience**: Per-item errors don't abort entire sync
5. **Lower Memory Usage**: Constant footprint regardless of library size
6. **Observable Operations**: Progress logging enables debugging and monitoring

### Negative

1. **Slightly More Code**: Streaming implementation ~20% more code than simple batch
2. **Different Error Semantics**: Partial success possible (must handle incomplete syncs)
3. **Progress Tracking Complexity**: Must track per-item success/failure, not simple success/fail

### Neutral

1. **No Performance Change for Small Libraries**: O(1) memory benefit only visible with large datasets
2. **API Rate Limiting Unchanged**: Same request rate, just different memory pattern
3. **Backward Compatibility**: Interface signatures unchanged, implementation detail

## Implementation Guidance

### Pattern Template

```
async def get_items_streaming(endpoint, page_size=50):
    """Stream items from paginated endpoint."""
    offset = 0

    while True:
        # Fetch one page
        page = await fetch_page(endpoint, limit=page_size, offset=offset)

        # Stop if no data
        if not page.has_data:
            break

        # Yield items immediately
        for item in page.items:
            if item.is_valid:
                yield item

        # Stop if no more pages
        if not page.has_next:
            break

        offset += page_size
```

### Error Handling

```
async for item in get_items_streaming(endpoint):
    try:
        result = await process_item(item)
        # Log success
    except ItemError as e:
        # Log warning, continue with next item
        log.warning(f"Failed to process {item.id}: {e}")
        continue
```

### Progress Observability

```
page_num = 0
total_items = 0

while has_more_pages:
    page = await fetch_page(...)
    total_items += len(page.items)

    if page_num % 5 == 0:
        log.info(f"Progress: {total_items} items in {page_num} pages")

    page_num += 1
```

## Verification

This decision successfully addresses the problem if:

1. **Completeness**: All items in external service appear in local database
2. **Memory**: Memory usage remains constant regardless of library size
3. **Performance**: Time to first item constant, total time linear but non-blocking
4. **Observability**: Logs indicate progress throughout operation
5. **Resilience**: Individual item failures logged but don't abort sync

### Test Scenarios

1. **Small library (< 500 items)**: Should work exactly as before
2. **Medium library (500-1500 items)**: Should complete where previously failed
3. **Large library (1500+ items)**: Should complete with observable progress
4. **Huge library (5000+ items)**: Should complete, may take time but no timeout
5. **Error injection**: Bad items should log warnings, not abort sync

## Related Decisions

- Future ADR: UI pagination controls (Layer 04 implementation)
- Future ADR: Progress indicators in web UI (Layer 05 operations)
- Future ADR: Sync resume on failure (Layer 04 implementation)

## References

- **Principle**: [WEB_UI_SCALABILITY_PRINCIPLES.md](WEB_UI_SCALABILITY_PRINCIPLES.md)
- **Pattern**: Async generators in Python
- **Anti-Pattern**: "Load all then display" pattern

## Notes

This decision applies to:
- Library artist synchronization
- Library album synchronization
- Library playlist synchronization
- Any future library item types

This decision does NOT apply to:
- Track synchronization (uses different batching strategy for API efficiency)
- Catalog search (uses API-provided pagination)
- Single-item lookups (not paginated)

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-10-25 | 1.0 | Initial decision | Architecture Team |
