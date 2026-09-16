from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, Query

from app.core.config import Settings, get_settings
from app.schemas.company import DcfAssumptions
from app.services.analytics import company_metrics, dcf_scenario, diagnostics, market_statistics
from app.services.cache import AppCache
from app.services.sec import SecService
from app.services.twelve_data import TwelveDataService

router = APIRouter(prefix="/api/v1")

_cache: AppCache | None = None


def services(settings: Settings = Depends(get_settings)):
    global _cache
    if _cache is None:
        _cache = AppCache(ttl=settings.cache_ttl_seconds)
    return SecService(settings, _cache), TwelveDataService(settings, _cache)


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "ok": True,
        "service": settings.app_name,
        "environment": settings.environment,
        "market_data_configured": bool(settings.twelve_data_api_key),
        "sec_configured": bool(settings.sec_user_agent),
    }


@router.get("/search")
async def search_companies(q: str = Query(min_length=1, max_length=80), svc=Depends(services)):
    sec, _ = svc
    return {"results": await sec.search(q)}


@router.get("/company/{ticker}/overview")
async def company_overview(ticker: str, svc=Depends(services)):
    sec, market = svc
    company, facts = await asyncio.gather(sec.resolve(ticker), sec.company_facts(ticker))
    snapshot = sec.normalized_snapshot(facts)

    quote = None
    prices: list[dict] = []
    if market.configured:
        quote_result, prices_result = await asyncio.gather(market.quote(ticker), market.time_series(ticker), return_exceptions=True)
        if not isinstance(quote_result, Exception):
            quote = quote_result
        if not isinstance(prices_result, Exception):
            prices = prices_result

    price = None
    if quote:
        try:
            price = float(quote.get("close") or quote.get("price"))
        except (TypeError, ValueError):
            pass
    if price is None and prices:
        try:
            price = float(prices[-1]["close"])
        except (TypeError, ValueError, KeyError):
            pass

    metrics = company_metrics(snapshot, price)
    return {
        "company": company,
        "quote": quote,
        "snapshot": snapshot,
        "metrics": metrics,
        "market_statistics": market_statistics(prices),
        "price_series": prices,
        "diagnostics": diagnostics(snapshot, metrics),
        "data_provenance": {
            "fundamentals": "SEC EDGAR companyfacts",
            "market_data": "Twelve Data" if market.configured else "Not configured",
        },
    }


@router.get("/company/{ticker}/filings")
async def company_filings(ticker: str, svc=Depends(services)):
    sec, _ = svc
    return {"filings": await sec.filings(ticker)}


@router.get("/company/{ticker}/filing-search")
async def filing_search(
    ticker: str,
    q: str = Query(min_length=2, max_length=160),
    accession: str | None = Query(default=None),
    svc=Depends(services),
):
    sec, _ = svc
    return await sec.filing_search(ticker, q, accession)


@router.get("/compare")
async def compare(tickers: str = Query(min_length=1, max_length=80), svc=Depends(services)):
    sec, market = svc
    symbols = list(dict.fromkeys([x.strip().upper() for x in tickers.split(",") if x.strip()]))[:5]

    async def one(symbol: str):
        company = await sec.resolve(symbol)
        facts = await sec.company_facts(symbol)
        snapshot = sec.normalized_snapshot(facts)
        price = None
        if market.configured:
            try:
                quote = await market.quote(symbol)
                price = float(quote.get("close") or quote.get("price"))
            except Exception:
                pass
        return {"ticker": symbol, "company": company, "snapshot": snapshot, "metrics": company_metrics(snapshot, price), "price": price}

    rows = await asyncio.gather(*(one(s) for s in symbols), return_exceptions=True)
    results = []
    for symbol, row in zip(symbols, rows):
        if isinstance(row, Exception):
            results.append({"ticker": symbol, "error": str(row)})
        else:
            results.append(row)
    return {"results": results}


@router.post("/company/{ticker}/scenario/dcf")
async def dcf(ticker: str, assumptions: DcfAssumptions, svc=Depends(services)):
    sec, _ = svc
    facts = await sec.company_facts(ticker)
    snapshot = sec.normalized_snapshot(facts)
    result = dcf_scenario(snapshot, snapshot.get("shares"), assumptions.model_dump())
    return result
