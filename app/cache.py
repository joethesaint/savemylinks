"""
Caching System for SaveMyLinks

This module provides a comprehensive caching system with:
- Function-level caching with decorators
- TTL (Time To Live) management
- Memory-efficient LRU cache
- Cache statistics and monitoring
- Async support for database operations
"""

import asyncio
import functools
import hashlib 
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Union, Tuple
from collections import OrderedDict
from datetime import datetime, timedelta
import weakref

from app.config import get_settings

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with metadata."""
    
    def __init__(self, value: Any, ttl: Optional[int] = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """Mark the entry as accessed and return its value."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    @property
    def age(self) -> float:
        """Get the age of the cache entry in seconds."""
        return time.time() - self.created_at


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache with TTL support.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expired_removals = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                self._expired_removals += 1
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            
            return entry.access()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        async with self._lock:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Create new entry
            entry = CacheEntry(value, ttl)
            self._cache[key] = entry
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            # Evict oldest entries if over max size
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
    
    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all entries from the cache."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """Remove all expired entries and return the count removed."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._expired_removals += 1
            
            return len(expired_keys)
    
    @property
    def size(self) -> int:
        """Get the current cache size."""
        return len(self._cache)
    
    @property
    def hit_rate(self) -> float:
        """Calculate the cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': self.size,
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self.hit_rate,
            'evictions': self._evictions,
            'expired_removals': self._expired_removals,
            'default_ttl': self.default_ttl
        }


# Global cache instance
_cache_instance: Optional[LRUCache] = None


def get_cache() -> LRUCache:
    """Get or create the global cache instance."""
    global _cache_instance
    
    if _cache_instance is None:
        settings = get_settings()
        _cache_instance = LRUCache(
            max_size=getattr(settings, 'CACHE_MAX_SIZE', 1000),
            default_ttl=getattr(settings, 'CACHE_DEFAULT_TTL', 300)
        )
    
    return _cache_instance


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Generate a unique cache key for function arguments."""
    # Create a string representation of the function and its arguments
    func_name = f"{func.__module__}.{func.__qualname__}"
    
    # Convert arguments to a hashable representation
    try:
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # Fallback for non-serializable arguments
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))
    
    # Create hash of the combined string
    combined = f"{func_name}:{args_str}:{kwargs_str}"
    return hashlib.md5(combined.encode()).hexdigest()


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds. If None, uses cache default.
        key_prefix: Optional prefix for cache keys.
    
    Example:
        @cached(ttl=300)  # Cache for 5 minutes
        async def get_user_links(user_id: int):
            # Expensive database operation
            return await db.query(Link).filter(Link.user_id == user_id).all()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if caching is enabled
            settings = get_settings()
            if not getattr(settings, 'CACHE_ENABLED', True):
                return await func(*args, **kwargs)
            
            cache = get_cache()
            cache_key = f"{key_prefix}{_generate_cache_key(func, args, kwargs)}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, we need to handle async cache operations
            settings = get_settings()
            if not getattr(settings, 'CACHE_ENABLED', True):
                return func(*args, **kwargs)
            
            # This is a simplified version for sync functions
            # In a real application, you might want to use a sync cache for sync functions
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_key(*key_parts: Any) -> str:
    """
    Generate a cache key from multiple parts.
    
    Example:
        key = cache_key("user", user_id, "links", "active")
    """
    parts_str = ":".join(str(part) for part in key_parts)
    return hashlib.md5(parts_str.encode()).hexdigest()


async def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache entries matching a pattern.
    
    Args:
        pattern: String pattern to match against cache keys.
    
    Returns:
        Number of entries invalidated.
    """
    cache = get_cache()
    
    # Get all keys (this is not ideal for large caches, but works for our use case)
    async with cache._lock:
        keys_to_delete = [
            key for key in cache._cache.keys()
            if pattern in key
        ]
    
    count = 0
    for key in keys_to_delete:
        if await cache.delete(key):
            count += 1
    
    logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
    return count


async def warm_cache(func: Callable, *args_list: Tuple[tuple, dict]) -> None:
    """
    Pre-populate cache with function results.
    
    Args:
        func: Function to cache results for.
        args_list: List of (args, kwargs) tuples to pre-compute.
    
    Example:
        await warm_cache(
            get_user_links,
            ((1,), {}),
            ((2,), {}),
            ((3,), {})
        )
    """
    logger.info(f"Warming cache for {func.__name__} with {len(args_list)} entries")
    
    for args, kwargs in args_list:
        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to warm cache for {func.__name__}: {e}")


class CacheManager:
    """
    High-level cache management utilities.
    """
    
    @staticmethod
    async def get_cache_stats() -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        cache = get_cache()
        stats = cache.get_stats()
        
        # Add memory usage estimation (rough)
        stats['estimated_memory_mb'] = cache.size * 0.001  # Very rough estimate
        
        return stats
    
    @staticmethod
    async def cleanup_expired() -> Dict[str, int]:
        """Clean up expired entries and return statistics."""
        cache = get_cache()
        removed_count = await cache.cleanup_expired()
        
        return {
            'removed_expired': removed_count,
            'current_size': cache.size
        }
    
    @staticmethod
    async def clear_all_cache() -> None:
        """Clear all cache entries."""
        cache = get_cache()
        await cache.clear()
        logger.info("All cache entries cleared")
    
    @staticmethod
    async def health_check() -> Dict[str, Any]:
        """Perform cache health check."""
        cache = get_cache()
        stats = cache.get_stats()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if stats['hit_rate'] < 0.5 and stats['hits'] + stats['misses'] > 100:
            health_status = "warning"
            issues.append("Low cache hit rate")
        
        if stats['size'] >= stats['max_size'] * 0.9:
            health_status = "warning"
            issues.append("Cache nearly full")
        
        return {
            'status': health_status,
            'issues': issues,
            'stats': stats
        }


# Utility functions for common caching patterns

@cached(ttl=300)  # 5 minutes
async def cached_database_query(query_hash: str, query_func: Callable, *args, **kwargs):
    """
    Generic cached database query wrapper.
    
    Example:
        result = await cached_database_query(
            "user_links_active",
            lambda: db.query(Link).filter(Link.user_id == user_id, Link.is_active == True).all(),
            user_id
        )
    """
    if asyncio.iscoroutinefunction(query_func):
        return await query_func(*args, **kwargs)
    else:
        return query_func(*args, **kwargs)


def cache_on_success(ttl: Optional[int] = None):
    """
    Decorator that only caches successful results (no exceptions).
    
    Example:
        @cache_on_success(ttl=600)
        async def fetch_external_data(url: str):
            # This will only be cached if no exception is raised
            response = await httpx.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            settings = get_settings()
            if not getattr(settings, 'CACHE_ENABLED', True):
                return await func(*args, **kwargs)
            
            cache = get_cache()
            cache_key = _generate_cache_key(func, args, kwargs)
            
            # Try cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            try:
                result = await func(*args, **kwargs)
                # Only cache if successful (no exception)
                await cache.set(cache_key, result, ttl)
                return result
            except Exception:
                # Don't cache exceptions, just re-raise
                raise
        
        return wrapper
    return decorator


# Background task for cache maintenance
async def cache_maintenance_task():
    """
    Background task for cache maintenance.
    Should be run periodically (e.g., every 5 minutes).
    """
    try:
        cache = get_cache()
        
        # Clean up expired entries
        removed = await cache.cleanup_expired()
        if removed > 0:
            logger.info(f"Cache maintenance: removed {removed} expired entries")
        
        # Log cache statistics
        stats = cache.get_stats()
        logger.debug(f"Cache stats: {stats}")
        
    except Exception as e:
        logger.error(f"Cache maintenance task failed: {e}")


# Export main components
__all__ = [
    'LRUCache',
    'get_cache',
    'cached',
    'cache_key',
    'invalidate_cache_pattern',
    'warm_cache',
    'CacheManager',
    'cached_database_query',
    'cache_on_success',
    'cache_maintenance_task'
]