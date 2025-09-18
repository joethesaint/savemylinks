"""
Tests for caching functionality.

This module tests the caching system including LRU cache, decorators,
cache management, and utility functions.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from app.cache import (
    CacheEntry,
    LRUCache,
    get_cache,
    cached,
    cache_key,
    invalidate_cache_pattern,
    warm_cache,
    CacheManager,
    cached_database_query,
    cache_on_success,
    cache_maintenance_task,
    _generate_cache_key
)


class TestCacheEntry:
    """Test CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        value = "test_value"
        entry = CacheEntry(value, ttl=300)
        
        assert entry.value == value
        assert entry.ttl == 300
        assert entry.access_count == 0
        assert entry.created_at <= time.time()
        assert entry.last_accessed == entry.created_at
    
    def test_cache_entry_no_ttl(self):
        """Test cache entry without TTL."""
        entry = CacheEntry("value")
        assert entry.ttl is None
        assert not entry.is_expired
    
    def test_cache_entry_not_expired(self):
        """Test cache entry that hasn't expired."""
        entry = CacheEntry("value", ttl=300)
        assert not entry.is_expired
    
    def test_cache_entry_expired(self):
        """Test cache entry that has expired."""
        with patch('time.time') as mock_time:
            # Create entry at time 1000
            mock_time.return_value = 1000
            entry = CacheEntry("value", ttl=300)
            
            # Move time forward past TTL
            mock_time.return_value = 1400  # 400 seconds later
            assert entry.is_expired
    
    def test_cache_entry_access(self):
        """Test accessing cache entry."""
        entry = CacheEntry("test_value")
        
        with patch('time.time', return_value=1500):
            result = entry.access()
            
            assert result == "test_value"
            assert entry.access_count == 1
            assert entry.last_accessed == 1500
    
    def test_cache_entry_age(self):
        """Test cache entry age calculation."""
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000
            entry = CacheEntry("value")
            
            mock_time.return_value = 1050
            assert entry.age == 50


class TestLRUCache:
    """Test LRUCache class."""
    
    @pytest.fixture
    def cache(self):
        """Create a test cache instance."""
        return LRUCache(max_size=3, default_ttl=None)
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, cache):
        """Test basic set and get operations."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
        assert cache.size == 1
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss."""
        result = await cache.get("nonexistent")
        assert result is None
        assert cache._misses == 1
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache):
        """Test cache hit."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
        assert cache._hits == 1
    
    @pytest.mark.asyncio
    async def test_cache_ttl_override(self, cache):
        """Test TTL override on set."""
        await cache.set("key1", "value1", ttl=100)
        
        # Check entry has correct TTL
        entry = cache._cache["key1"]
        assert entry.ttl == 100
    
    @pytest.mark.asyncio
    async def test_cache_expired_entry(self, cache):
        """Test expired entry is removed on access."""
        with patch('time.time') as mock_time:
            # Set entry at time 1000
            mock_time.return_value = 1000
            await cache.set("key1", "value1", ttl=300)
            
            # Try to get at time 1400 (expired)
            mock_time.return_value = 1400
            result = await cache.get("key1")
            
            assert result is None
            assert cache.size == 0
            assert cache._expired_removals == 1
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when max size exceeded."""
        # Fill cache to max size
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Add one more (should evict key1)
        await cache.set("key4", "value4")
        
        assert cache.size == 3
        assert await cache.get("key1") is None  # Evicted
        assert await cache.get("key4") == "value4"  # New entry
        assert cache._evictions == 1
    
    @pytest.mark.asyncio
    async def test_cache_lru_order(self, cache):
        """Test LRU ordering with access."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 (makes it most recent)
        await cache.get("key1")
        
        # Add key4 (should evict key2, not key1)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key4") == "value4"  # New entry
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, cache):
        """Test cache deletion."""
        await cache.set("key1", "value1")
        
        deleted = await cache.delete("key1")
        assert deleted is True
        assert cache.size == 0
        
        # Try to delete non-existent key
        deleted = await cache.delete("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, cache):
        """Test cache clear."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        await cache.clear()
        assert cache.size == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache):
        """Test cleanup of expired entries."""
        with patch('time.time') as mock_time:
            # Set entries at time 1000
            mock_time.return_value = 1000
            await cache.set("key1", "value1", ttl=300)
            await cache.set("key2", "value2", ttl=600)
            await cache.set("key3", "value3")  # No TTL
            
            # Move to time 1400 (key1 expired, key2 and key3 still valid)
            mock_time.return_value = 1400
            
            removed = await cache.cleanup_expired()
            
            assert removed == 1
            assert cache.size == 2
            assert await cache.get("key1") is None
            assert await cache.get("key2") == "value2"
            assert await cache.get("key3") == "value3"
    
    def test_hit_rate_calculation(self, cache):
        """Test hit rate calculation."""
        # No requests yet
        assert cache.hit_rate == 0.0
        
        # Set some stats manually
        cache._hits = 7
        cache._misses = 3
        
        assert cache.hit_rate == 0.7
    
    def test_get_stats(self, cache):
        """Test getting cache statistics."""
        cache._hits = 10
        cache._misses = 5
        cache._evictions = 2
        cache._expired_removals = 1
        
        stats = cache.get_stats()
        
        expected = {
            'size': 0,
            'max_size': 3,
            'hits': 10,
            'misses': 5,
            'hit_rate': 2/3,
            'evictions': 2,
            'expired_removals': 1,
            'default_ttl': None
        }
        
        assert stats == expected


class TestCacheUtilities:
    """Test cache utility functions."""
    
    def test_generate_cache_key(self):
        """Test cache key generation."""
        def test_func():
            pass
        
        key1 = _generate_cache_key(test_func, (1, 2), {"a": "b"})
        key2 = _generate_cache_key(test_func, (1, 2), {"a": "b"})
        key3 = _generate_cache_key(test_func, (1, 3), {"a": "b"})
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different inputs should generate different keys
        assert key1 != key3
    
    def test_cache_key_function(self):
        """Test cache_key utility function."""
        key1 = cache_key("user", 123, "links")
        key2 = cache_key("user", 123, "links")
        key3 = cache_key("user", 456, "links")
        
        assert key1 == key2
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_pattern(self):
        """Test cache pattern invalidation."""
        from app.cache import _cache_instance
        
        # Clear any existing global cache
        if _cache_instance:
            await _cache_instance.clear()
        
        cache = LRUCache()
        
        # Set some entries
        await cache.set("user:123:links", "data1")
        await cache.set("user:456:links", "data2")
        await cache.set("post:789:comments", "data3")
        
        # Temporarily replace the global cache instance
        original_cache = _cache_instance
        import app.cache
        app.cache._cache_instance = cache
        
        try:
            # Invalidate user entries
            count = await invalidate_cache_pattern("user:")
            
            assert count == 2
            assert await cache.get("user:123:links") is None
            assert await cache.get("user:456:links") is None
            assert await cache.get("post:789:comments") == "data3"
        finally:
            # Restore original cache
            app.cache._cache_instance = original_cache
    
    @pytest.mark.asyncio
    async def test_warm_cache_async(self):
        """Test cache warming with async function."""
        call_count = 0
        
        @cached(ttl=300)
        async def test_func(x):
            nonlocal call_count
            call_count += 1
            return f"result_{x}"
        
        # Warm cache
        await warm_cache(
            test_func,
            ((1,), {}),
            ((2,), {}),
            ((3,), {})
        )
        
        # Should have called function 3 times
        assert call_count == 3
        
        # Subsequent calls should hit cache
        result = await test_func(1)
        assert result == "result_1"
        assert call_count == 3  # No additional calls


class TestCacheDecorators:
    """Test cache decorators."""
    
    @pytest.mark.asyncio
    async def test_cached_decorator_async(self):
        """Test cached decorator with async function."""
        call_count = 0
        
        @cached(ttl=300)
        async def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return f"result_{x}"
        
        # First call
        result1 = await expensive_function(1)
        assert result1 == "result_1"
        assert call_count == 1
        
        # Second call (should hit cache)
        result2 = await expensive_function(1)
        assert result2 == "result_1"
        assert call_count == 1  # No additional call
        
        # Different argument (should miss cache)
        result3 = await expensive_function(2)
        assert result3 == "result_2"
        assert call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.cache.get_settings')
    async def test_cached_decorator_disabled(self, mock_get_settings):
        """Test cached decorator when caching is disabled."""
        mock_settings = Mock()
        mock_settings.CACHE_ENABLED = False
        mock_get_settings.return_value = mock_settings
        
        call_count = 0
        
        @cached(ttl=300)
        async def test_func(x):
            nonlocal call_count
            call_count += 1
            return f"result_{x}"
        
        # Multiple calls should not use cache
        await test_func(1)
        await test_func(1)
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_on_success_decorator(self):
        """Test cache_on_success decorator."""
        call_count = 0
        
        @cache_on_success(ttl=300)
        async def sometimes_fails(should_fail=False):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Successful call
        result1 = await sometimes_fails(False)
        assert result1 == "success"
        assert call_count == 1
        
        # Second successful call (should hit cache)
        result2 = await sometimes_fails(False)
        assert result2 == "success"
        assert call_count == 1  # No additional call
        
        # Failed call (should not be cached)
        with pytest.raises(ValueError):
            await sometimes_fails(True)
        assert call_count == 2
        
        # Another failed call (should call function again)
        with pytest.raises(ValueError):
            await sometimes_fails(True)
        assert call_count == 3


class TestCacheManager:
    """Test CacheManager class."""
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self):
        """Test getting cache statistics."""
        stats = await CacheManager.get_cache_stats()
        
        assert 'size' in stats
        assert 'max_size' in stats
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats
        assert 'estimated_memory_mb' in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup expired entries."""
        cache = get_cache()
        
        # Add some entries
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000
            await cache.set("key1", "value1", ttl=300)
            await cache.set("key2", "value2", ttl=600)
            
            # Move time forward
            mock_time.return_value = 1400
            
            result = await CacheManager.cleanup_expired()
            
            assert 'removed_expired' in result
            assert 'current_size' in result
            assert result['removed_expired'] >= 0
    
    @pytest.mark.asyncio
    async def test_clear_all_cache(self):
        """Test clearing all cache."""
        cache = get_cache()
        await cache.set("test", "value")
        
        await CacheManager.clear_all_cache()
        
        assert cache.size == 0
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test cache health check when healthy."""
        cache = get_cache()
        await cache.clear()  # Start fresh
        
        health = await CacheManager.health_check()
        
        assert health['status'] == 'healthy'
        assert health['issues'] == []
        assert 'stats' in health
    
    @pytest.mark.asyncio
    async def test_health_check_low_hit_rate(self):
        """Test cache health check with low hit rate."""
        from app.cache import _cache_instance
        
        # Store original cache
        original_cache = _cache_instance
        
        try:
            # Clear and use test cache
            cache = get_cache()
            await cache.clear()
            
            # Replace global cache with test cache
            import app.cache
            app.cache._cache_instance = cache
            
            # Simulate low hit rate
            cache._hits = 30
            cache._misses = 71  # Total > 100 to trigger warning
            
            health = await CacheManager.health_check()
            
            assert health['status'] == 'warning'
            assert 'Low cache hit rate' in health['issues']
        finally:
            # Restore original cache
            import app.cache
            app.cache._cache_instance = original_cache


class TestCacheMaintenanceTask:
    """Test cache maintenance task."""
    
    @pytest.mark.asyncio
    async def test_cache_maintenance_task(self):
        """Test cache maintenance task execution."""
        cache = get_cache()
        
        # Add some entries
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000
            await cache.set("key1", "value1", ttl=300)
            await cache.set("key2", "value2", ttl=600)
            
            # Move time forward to expire key1
            mock_time.return_value = 1400
            
            # Run maintenance
            await cache_maintenance_task()
            
            # Should have cleaned up expired entries
            assert await cache.get("key1") is None
            assert await cache.get("key2") == "value2"
    
    @pytest.mark.asyncio
    async def test_cache_maintenance_task_error_handling(self):
        """Test cache maintenance task handles errors gracefully."""
        with patch('app.cache.get_cache') as mock_get_cache:
            mock_get_cache.side_effect = Exception("Test error")
            
            # Should not raise exception
            await cache_maintenance_task()


class TestCachedDatabaseQuery:
    """Test cached database query function."""
    
    @pytest.mark.asyncio
    async def test_cached_database_query_async(self):
        """Test cached database query with async function."""
        call_count = 0
        
        async def mock_query():
            nonlocal call_count
            call_count += 1
            return "query_result"
        
        # First call
        result1 = await cached_database_query("test_query", mock_query)
        assert result1 == "query_result"
        assert call_count == 1
        
        # Second call (should hit cache)
        result2 = await cached_database_query("test_query", mock_query)
        assert result2 == "query_result"
        assert call_count == 1  # No additional call
    
    @pytest.mark.asyncio
    async def test_cached_database_query_sync(self):
        """Test cached database query with sync function."""
        call_count = 0
        
        def mock_query():
            nonlocal call_count
            call_count += 1
            return "sync_result"
        
        result = await cached_database_query("sync_query", mock_query)
        assert result == "sync_result"
        assert call_count == 1