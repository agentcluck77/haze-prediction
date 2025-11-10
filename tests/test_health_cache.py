import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from src.api.health_cache import HealthCache


@pytest.mark.asyncio
async def test_health_cache_initialization():
    cache = HealthCache(ttl_seconds=180)
    assert cache.cache is None
    assert cache.last_updated is None
    assert cache.ttl == timedelta(seconds=180)


@pytest.mark.asyncio
async def test_health_cache_first_call_performs_checks():
    cache = HealthCache(ttl_seconds=180)

    with patch('src.api.health_cache.fetch_current_psi_async', new_callable=AsyncMock) as mock_psi, \
         patch('src.api.health_cache.fetch_recent_fires_async', new_callable=AsyncMock) as mock_fires, \
         patch('src.api.health_cache.fetch_current_weather_async', new_callable=AsyncMock) as mock_weather:

        mock_psi.return_value = {"some": "data"}
        mock_fires.return_value = [{"fire": "data"}]
        mock_weather.return_value = {"weather": "data"}

        result = await cache.get_health_status()

        assert result["status"] == "healthy"
        assert result["checks"]["psi_api"] is True
        assert result["checks"]["fires_api"] is True
        assert result["checks"]["weather_api"] is True
        assert "timestamp" in result

        mock_psi.assert_called_once()
        mock_fires.assert_called_once()
        mock_weather.assert_called_once()


@pytest.mark.asyncio
async def test_health_cache_returns_cached_result_when_fresh():
    cache = HealthCache(ttl_seconds=180)

    with patch('src.api.health_cache.fetch_current_psi_async', new_callable=AsyncMock) as mock_psi, \
         patch('src.api.health_cache.fetch_recent_fires_async', new_callable=AsyncMock) as mock_fires, \
         patch('src.api.health_cache.fetch_current_weather_async', new_callable=AsyncMock) as mock_weather:

        mock_psi.return_value = {"some": "data"}
        mock_fires.return_value = [{"fire": "data"}]
        mock_weather.return_value = {"weather": "data"}

        # First call
        result1 = await cache.get_health_status()

        # Second call should use cache
        result2 = await cache.get_health_status()

        # API should only be called once
        assert mock_psi.call_count == 1
        assert mock_fires.call_count == 1
        assert mock_weather.call_count == 1

        assert result1 == result2


@pytest.mark.asyncio
async def test_health_cache_refreshes_when_stale():
    cache = HealthCache(ttl_seconds=1)  # 1 second TTL for testing

    with patch('src.api.health_cache.fetch_current_psi_async', new_callable=AsyncMock) as mock_psi, \
         patch('src.api.health_cache.fetch_recent_fires_async', new_callable=AsyncMock) as mock_fires, \
         patch('src.api.health_cache.fetch_current_weather_async', new_callable=AsyncMock) as mock_weather:

        mock_psi.return_value = {"some": "data"}
        mock_fires.return_value = [{"fire": "data"}]
        mock_weather.return_value = {"weather": "data"}

        # First call
        await cache.get_health_status()

        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(1.5)

        # Second call should refresh
        await cache.get_health_status()

        # API should be called twice
        assert mock_psi.call_count == 2
        assert mock_fires.call_count == 2
        assert mock_weather.call_count == 2


@pytest.mark.asyncio
async def test_health_cache_handles_api_failures():
    cache = HealthCache(ttl_seconds=180)

    with patch('src.api.health_cache.fetch_current_psi_async', new_callable=AsyncMock) as mock_psi, \
         patch('src.api.health_cache.fetch_recent_fires_async', new_callable=AsyncMock) as mock_fires, \
         patch('src.api.health_cache.fetch_current_weather_async', new_callable=AsyncMock) as mock_weather:

        mock_psi.side_effect = Exception("API Error")
        mock_fires.return_value = [{"fire": "data"}]
        mock_weather.return_value = None  # API returned no data

        result = await cache.get_health_status()

        assert result["status"] == "degraded"
        assert result["checks"]["psi_api"] is False
        assert result["checks"]["fires_api"] is True
        assert result["checks"]["weather_api"] is False
