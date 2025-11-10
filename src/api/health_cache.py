"""
In-memory cache for storing the health status of external dependencies.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.data_ingestion.psi import fetch_current_psi
from src.data_ingestion.firms import fetch_recent_fires
from src.data_ingestion.weather import fetch_current_weather


# Async wrappers for sync API functions
async def fetch_current_psi_async():
    """Async wrapper for fetch_current_psi."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, fetch_current_psi)


async def fetch_recent_fires_async():
    """Async wrapper for fetch_recent_fires."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, fetch_recent_fires)


async def fetch_current_weather_async():
    """Async wrapper for fetch_current_weather."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        # Singapore coordinates
        return await loop.run_in_executor(pool, fetch_current_weather, 1.3521, 103.8198)


class HealthCache:
    """
    Cache for health check results with on-demand refresh.

    Configuration:
    - TTL: 3 minutes (180 seconds)
    - Timeout per API check: 10 seconds
    - Refresh mode: On-demand (when /health is called and cache is stale)
    """

    def __init__(self, ttl_seconds: int = 180):
        self.cache: Optional[Dict[str, Any]] = None
        self.last_updated: Optional[datetime] = None
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = asyncio.Lock()
        self.check_timeout = 10.0  # 10 second timeout per check

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status from cache or refresh if stale.

        Returns cached result if fresh (< TTL age).
        Otherwise, performs fresh checks with 10s timeout each, running in parallel.
        """
        # Return cached result if fresh
        if self.cache and self.last_updated:
            if datetime.now() - self.last_updated < self.ttl:
                return self.cache

        # Refresh cache (with lock to prevent concurrent refreshes)
        async with self.lock:
            # Double-check after acquiring lock
            if self.cache and self.last_updated and datetime.now() - self.last_updated < self.ttl:
                return self.cache

            # Run all checks in parallel with timeout
            results = await asyncio.gather(
                self._check_psi(),
                self._check_fires(),
                self._check_weather(),
                return_exceptions=True
            )

            self.cache = {
                "status": "healthy" if all(r is True for r in results) else "degraded",
                "checks": {
                    "psi_api": results[0] is True,
                    "fires_api": results[1] is True,
                    "weather_api": results[2] is True
                },
                "timestamp": datetime.now().isoformat()
            }
            self.last_updated = datetime.now()
            return self.cache

    async def _check_psi(self) -> bool:
        """Check PSI API with timeout."""
        try:
            result = await asyncio.wait_for(
                fetch_current_psi_async(),
                timeout=self.check_timeout
            )
            return result is not None
        except Exception:
            return False

    async def _check_fires(self) -> bool:
        """Check FIRMS API with timeout."""
        try:
            result = await asyncio.wait_for(
                fetch_recent_fires_async(),
                timeout=self.check_timeout
            )
            return result is not None
        except Exception:
            return False

    async def _check_weather(self) -> bool:
        """Check Weather API with timeout."""
        try:
            result = await asyncio.wait_for(
                fetch_current_weather_async(),
                timeout=self.check_timeout
            )
            return result is not None
        except Exception:
            return False


# Global cache instance
health_cache = HealthCache(ttl_seconds=180)
