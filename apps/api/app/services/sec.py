from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.core.config import Settings
from app.services.cache import AppCache


FACT_KEYS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
    "debt_current": ["LongTermDebtCurrent", "LongTermDebtAndFinanceLeaseObligationsCurrent", "ShortTermBorrowings"],
    "debt_noncurrent": ["LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"],
}


class SecService:
    DATA_BASE = "https://data.sec.gov"
    WWW_BASE = "https://www.sec.gov"

    def __init__(self, settings: Settings, cache: AppCache):
        self.settings = settings
        self.cache = cache
        self.headers = {
            "User-Agent": settings.sec_user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

    async def _json(self, url: str) -> dict:
        cached = self.cache.get(f"sec:{url}")
        if cached is not None:
            return cached
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"SEC EDGAR request failed: {exc}") from exc
        return self.cache.set(f"sec:{url}", data)

    async def ticker_map(self) -> list[dict]:
        data = await self._json(f"{self.WWW_BASE}/files/company_tickers.json")
        rows = []
        for value in data.values():
            rows.append({
                "ticker": str(value.get("ticker", "")).upper(),
                "name": value.get("title", ""),
                "cik": str(value.get("cik_str", "")).zfill(10),
            })
        return rows

    async def search(self, query: str, limit: int = 8) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return []
        rows = await self.ticker_map()
        exact = [r for r in rows if r["ticker"].lower() == q]
        starts = [r for r in rows if r not in exact and (r["ticker"].lower().startswith(q) or r["name"].lower().startswith(q))]
        contains = [r for r in rows if r not in exact and r not in starts and q in r["name"].lower()]
        return (exact + starts + contains)[:limit]

    async def resolve(self, ticker: str) -> dict:
        ticker = ticker.upper().strip()
        rows = await self.ticker_map()
        row = next((r for r in rows if r["ticker"] == ticker), None)
        if not row:
            raise HTTPException(status_code=404, detail=f"Unknown SEC ticker: {ticker}")
        return row

    async def company_facts(self, ticker: str) -> dict:
        company = await self.resolve(ticker)
        return await self._json(f"{self.DATA_BASE}/api/xbrl/companyfacts/CIK{company['cik']}.json")

    def _latest_fact(self, facts: dict, keys: list[str], *, forms=("10-K", "10-Q"), unit_preference=("USD", "shares", "USD/shares"), annual_only: bool = False) -> dict | None:
        usgaap = facts.get("facts", {}).get("us-gaap", {})
        candidates: list[dict] = []
        for key in keys:
            node = usgaap.get(key)
            if not node:
                continue
            units = node.get("units", {})
            selected_units: list[dict] = []
            for unit in unit_preference:
                if unit in units:
                    selected_units = units[unit]
                    break
            if not selected_units:
                selected_units = next(iter(units.values()), [])
            for item in selected_units:
                if item.get("form") not in forms or item.get("val") is None:
                    continue
                if annual_only:
                    start, end = item.get("start"), item.get("end")
                    if not start or not end:
                        continue
                    try:
                        duration = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
                    except ValueError:
                        continue
                    if duration < 300:
                        continue
                candidates.append({**item, "concept": key})
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x.get("filed", ""), x.get("end", "")), reverse=True)
        return candidates[0]

    def normalized_snapshot(self, facts: dict) -> dict:
        out: dict[str, Any] = {}
        # Flow metrics use the latest annual 10-K so ratios and DCF inputs do not
        # silently combine quarterly/YTD values with full-year values. Balance
        # sheet metrics use the latest available 10-K/10-Q point-in-time fact.
        annual_metrics = {
            "revenue", "net_income", "operating_income", "operating_cash_flow",
            "capex", "eps_diluted", "shares"
        }
        for metric, keys in FACT_KEYS.items():
            forms = ("10-K",) if metric in annual_metrics else ("10-K", "10-Q")
            item = self._latest_fact(facts, keys, forms=forms, annual_only=metric in annual_metrics)
            out[metric] = item.get("val") if item else None
            out[f"{metric}_period"] = item.get("end") if item else None
            out[f"{metric}_concept"] = item.get("concept") if item else None

        dei = facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
        dei_candidates = [x for x in dei if x.get("val") is not None and x.get("form") in {"10-K", "10-Q"}]
        dei_candidates.sort(key=lambda x: (x.get("filed", ""), x.get("end", "")), reverse=True)
        out["shares_outstanding"] = dei_candidates[0].get("val") if dei_candidates else out.get("shares")
        out["shares_outstanding_period"] = dei_candidates[0].get("end") if dei_candidates else out.get("shares_period")

        ocf = out.get("operating_cash_flow")
        capex = out.get("capex")
        out["free_cash_flow"] = (ocf - abs(capex)) if isinstance(ocf, (int, float)) and isinstance(capex, (int, float)) else None
        debt = sum(x for x in [out.get("debt_current"), out.get("debt_noncurrent")] if isinstance(x, (int, float)))
        out["total_debt"] = debt or None
        return out

    async def submissions(self, ticker: str) -> dict:
        company = await self.resolve(ticker)
        return await self._json(f"{self.DATA_BASE}/submissions/CIK{company['cik']}.json")

    async def filings(self, ticker: str, limit: int = 12) -> list[dict]:
        company = await self.resolve(ticker)
        data = await self.submissions(ticker)
        recent = data.get("filings", {}).get("recent", {})
        rows: list[dict] = []
        forms = recent.get("form", [])
        for i, form in enumerate(forms):
            if form not in {"10-K", "10-Q", "8-K"}:
                continue
            accession = recent.get("accessionNumber", [])[i]
            primary = recent.get("primaryDocument", [])[i]
            accession_compact = accession.replace("-", "")
            url = f"{self.WWW_BASE}/Archives/edgar/data/{int(company['cik'])}/{accession_compact}/{primary}"
            rows.append({
                "form": form,
                "filing_date": recent.get("filingDate", [])[i],
                "report_date": recent.get("reportDate", [])[i],
                "accession": accession,
                "primary_document": primary,
                "url": url,
            })
            if len(rows) >= limit:
                break
        return rows

    async def filing_search(self, ticker: str, query: str, accession: str | None = None, top_k: int = 6) -> dict:
        filings = await self.filings(ticker, limit=20)
        candidates = [f for f in filings if f["form"] in {"10-K", "10-Q"}]
        filing = next((f for f in candidates if f["accession"] == accession), None) if accession else (candidates[0] if candidates else None)
        if not filing:
            raise HTTPException(status_code=404, detail="No 10-K/10-Q filing available.")

        cache_key = f"filing-html:{filing['url']}"
        html = self.cache.get(cache_key)
        if html is None:
            try:
                async with httpx.AsyncClient(timeout=20.0, headers=self.headers, follow_redirects=True) as client:
                    response = await client.get(filing["url"])
                    response.raise_for_status()
                    html = response.text
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=f"Unable to fetch filing: {exc}") from exc
            self.cache.set(cache_key, html)

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "table"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        segments = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if 80 <= len(s.strip()) <= 1400]
        tokens = {t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 2}

        scored = []
        for idx, seg in enumerate(segments):
            lowered = seg.lower()
            hits = sum(lowered.count(t) for t in tokens)
            if hits:
                density = hits / max(1, len(seg.split()))
                scored.append((hits + density * 20, idx, seg))
        scored.sort(reverse=True)
        excerpts = [{"rank": i + 1, "text": seg, "score": round(score, 4)} for i, (score, _, seg) in enumerate(scored[:top_k])]
        return {"filing": filing, "query": query, "excerpts": excerpts}
