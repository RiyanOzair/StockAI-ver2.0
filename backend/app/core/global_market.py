"""Global market service for fetching international indices via Yahoo Finance."""
from __future__ import annotations

import asyncio
import copy
import logging
import random
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("core.global_market")

class GlobalMarketService:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    REQUEST_TIMEOUT_SECONDS = 10.0
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }

    GLOBAL_INDICES = [
        {"symbol": "^FTSE", "label": "FTSE 100", "region": "UK"},
        {"symbol": "^N225", "label": "Nikkei 225", "region": "Japan"},
        {"symbol": "^GDAXI", "label": "DAX", "region": "Germany"},
        {"symbol": "^HSI", "label": "Hang Seng", "region": "Hong Kong"},
        {"symbol": "^FCHI", "label": "CAC 40", "region": "France"},
        {"symbol": "^AXJO", "label": "S&P/ASX 200", "region": "Australia"},
        {"symbol": "^STOXX50E", "label": "Euro Stoxx 50", "region": "Europe"},
        {"symbol": "^STI", "label": "Straits Times", "region": "Singapore"},
        {"symbol": "^KS11", "label": "KOSPI", "region": "South Korea"},
        {"symbol": "000001.SS", "label": "SSE Composite", "region": "China"},
    ]

    def __init__(self) -> None:
        self._cache: dict[str, Any] | None = None
        self._cache_timestamp: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_summary(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        
        # 5-minute cache for global indices
        if self._cache and self._cache_timestamp:
            age = (now - self._cache_timestamp).total_seconds()
            if age < 300:
                return self._cache

        async with self._lock:
            if self._cache and self._cache_timestamp:
                age = (now - self._cache_timestamp).total_seconds()
                if age < 300:
                    return self._cache

            try:
                data = await self._fetch_global_data()
                self._cache = data
                self._cache_timestamp = now
                return data
            except Exception as e:
                logger.error(f"Global market fetch failed: {e}")
                if self._cache:
                    return self._cache
                return {"error": str(e), "indices": []}

    async def _fetch_global_data(self) -> dict[str, Any]:
        results = []
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT_SECONDS, headers=self.REQUEST_HEADERS) as client:
            tasks = [self._fetch_symbol(client, item["symbol"]) for item in self.GLOBAL_INDICES]
            fetched_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item, res in zip(self.GLOBAL_INDICES, fetched_results):
                if isinstance(res, Exception):
                    logger.warning(f"Failed to fetch {item['symbol']}: {res}")
                    continue
                res["label"] = item["label"]
                res["region"] = item["region"]
                results.append(res)

        return {
            "indices": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "Yahoo Finance (Free)"
        }

    async def _fetch_symbol(self, client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/{quote(symbol, safe='')}?interval=1d&range=1d"
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            raise RuntimeError(f"No result for {symbol}")

        meta = result[0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev = meta.get("chartPreviousClose", price)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change_pct": round(((price - prev) / prev * 100), 2) if prev else 0,
            "currency": meta.get("currency", "USD"),
            "market_time": int(meta.get("regularMarketTime") or 0)
        }

global_market_service = GlobalMarketService()
