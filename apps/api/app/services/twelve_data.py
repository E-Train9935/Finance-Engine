from __future__ import annotations

import httpx
from collections import deque
from threading import RLock
from time import monotonic
from fastapi import HTTPException

from app.core.config import Settings
from app.services.cache import AppCache


_provider_window: deque[float] = deque()
_provider_lock = RLock()


class TwelveDataService:
    BASE = "https://api.twelvedata.com"

    def __init__(self, settings: Settings, cache: AppCache):
        self.settings = settings
        self.cache = cache

    @property
    def configured(self) -> bool:
        return bool(self.settings.twelve_data_api_key)

    async def _get(self, path: str, params: dict) -> dict:
        if not self.configured:
            raise HTTPException(
                status_code=503,
                detail="Twelve Data is not configured. Add TWELVE_DATA_API_KEY to apps/api/.env.",
            )
        cache_key = f"td:{path}:{sorted(params.items())}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Global single-instance guard for the free market-data quota. Cached
        # requests do not consume provider capacity. Raise clearly rather than
        # hammering the upstream service and returning opaque provider errors.
        now = monotonic()
        with _provider_lock:
            while _provider_window and now - _provider_window[0] > 60.0:
                _provider_window.popleft()
            if len(_provider_window) >= self.settings.twelve_data_requests_per_minute:
                raise HTTPException(status_code=429, detail="Market-data quota guard reached. Retry in about a minute.")
            _provider_window.append(now)

        request_params = {**params, "apikey": self.settings.twelve_data_api_key}
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(f"{self.BASE}{path}", params=request_params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Market data provider failed: {exc}") from exc

        if isinstance(data, dict) and data.get("status") == "error":
            raise HTTPException(status_code=502, detail=f"Twelve Data: {data.get('message', 'unknown error')}")
        return self.cache.set(cache_key, data)

    async def quote(self, symbol: str) -> dict:
        return await self._get("/quote", {"symbol": symbol.upper()})

    async def time_series(self, symbol: str, outputsize: int = 252) -> list[dict]:
        data = await self._get(
            "/time_series",
            {
                "symbol": symbol.upper(),
                "interval": "1day",
                "outputsize": min(max(outputsize, 30), 5000),
                "order": "ASC",
                "format": "JSON",
            },
        )
        return data.get("values", []) if isinstance(data, dict) else []
