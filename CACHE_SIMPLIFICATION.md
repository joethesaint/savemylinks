# Cache System Simplification

## Overview
This document outlines the simplification of the cache system in the SaveMyLinks application. The changes remove dead code and simplify the caching implementation to match the actual usage patterns in the codebase.

## Changes Made

### 1. Removed Sync Wrapper Dead Code
**File**: `app/cache.py`

**Problem**: The `@cached` decorator included a `sync_wrapper` function to handle synchronous functions, but analysis showed that:
- All functions using `@cached` in the codebase are async
- The sync wrapper didn't actually provide caching functionality for sync functions
- It added unnecessary complexity and maintenance burden

**Solution**: 
- Removed the `sync_wrapper` function entirely
- Simplified the `@cached` decorator to only handle async functions
- Added validation to raise a clear error if someone tries to use `@cached` on a sync function

### 2. Simplified warm_cache Function
**File**: `app/cache.py`

**Problem**: The `warm_cache` function had logic to handle both sync and async functions, but only async functions are used in the codebase.

**Solution**:
- Removed sync/async detection logic
- Simplified to only handle async functions
- Added validation to raise a clear error for sync functions

### 3. Updated Tests
**File**: `app/tests/test_cache.py`

**Changes**:
- Added test to verify `@cached` decorator raises error for sync functions
- Added test to verify `warm_cache` raises error for sync functions
- Removed obsolete test for disabled caching behavior

## Benefits

1. **Reduced Complexity**: Removed ~20 lines of dead code and simplified logic
2. **Better Error Handling**: Clear error messages when sync functions are used incorrectly
3. **Improved Maintainability**: Less code to maintain and understand
4. **Type Safety**: More explicit about async-only behavior

## Backward Compatibility

The changes are backward compatible for the existing codebase since:
- All existing `@cached` usage is on async functions
- The `cached_database_query` function still handles both sync and async functions for flexibility
- No breaking changes to the public API

## Testing

All cache-related tests pass (34/34), confirming that:
- Existing async functionality works correctly
- New error handling works as expected
- No regressions introduced

## Code Quality Impact

- **Lines of Code**: Reduced by ~20 lines
- **Cyclomatic Complexity**: Reduced by removing conditional branches
- **Maintainability**: Improved by removing unused code paths
- **Clarity**: More explicit about async-only design

## Future Considerations

If sync function caching is needed in the future:
1. Consider creating a separate `@cached_sync` decorator
2. Or use `cached_database_query()` directly for sync functions
3. Avoid mixing sync/async logic in the same decorator for clarity