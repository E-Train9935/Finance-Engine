# FINENGINE // Portfolio Story

## One-line description
FINENGINE is a full-stack company-intelligence platform that combines live market telemetry with SEC-reported fundamentals, peer benchmarking, filing evidence retrieval, and transparent valuation scenarios.

## Problem
Researching a public company is fragmented. A user often moves between a market-data site, SEC EDGAR, spreadsheets, and valuation templates while manually reconciling definitions and periods. That fragmentation creates wasted time and makes it easy to compare inconsistent numbers.

## What FINENGINE does differently
- Uses SEC EDGAR/XBRL as the source of truth for company-reported fundamentals.
- Keeps annual flow metrics aligned to annual 10-K periods instead of silently mixing quarterly/YTD values into valuation ratios.
- Uses a separate market-data provider only for price telemetry.
- Shows provenance and missing-data states instead of inventing replacements.
- Searches actual 10-K/10-Q text and returns evidence passages.
- Makes DCF assumptions explicit and editable rather than outputting an unexplained “fair value.”
- Avoids buy/sell recommendations and opaque stock scores.

## Architecture story
The React/Vite client is presentation-only. FastAPI owns upstream credentials, SEC retrieval, normalization, analytics, caching, filing extraction, provider quota protection, and scenario math. In production, the Vite bundle is compiled in a Node build stage and served by FastAPI from the same Docker image, which simplifies deployment and removes production CORS complexity.

## Engineering decisions worth discussing

### Why not Streamlit?
Streamlit would have been faster, but the project is intended to demonstrate product engineering as well as Python. React gives precise control over responsive layout, interaction, charting, and the visual system while Python remains the analytical core.

### Why SEC instead of relying on a finance aggregator for fundamentals?
Company-reported filings are the primary public source. Using SEC XBRL also creates a more interesting engineering problem: concept normalization, period selection, missing concepts, and provenance.

### Why deterministic Filing Lens instead of an LLM first?
Retrieval itself solves a real problem and is easier to verify. A future RAG layer can be added on top of the returned evidence. Starting with retrieval avoids turning the project into another ungrounded summarizer.

### Why a transparent DCF?
The educational value is in the assumptions. FINENGINE exposes growth, discount rate, terminal growth, and horizon, then shows exactly how the reported FCF becomes a scenario value.

### What would scale next?
- Redis for shared caching and distributed rate limiting
- Postgres for saved research workspaces
- background workers for scheduled watchlists
- TTM construction from SEC quarterly frames
- sector/industry peer discovery
- earnings-event comparison
- optional citation-locked LLM analysis of filing excerpts

## Interview demo flow
1. Search a ticker and explain SEC ticker resolution.
2. Show the company overview and data provenance.
3. Point out annual/point-in-time period normalization.
4. Compare 3–5 companies in Peer Matrix.
5. Search a 10-K for a risk or operational topic in Filing Lens.
6. Open the original SEC filing from the evidence result.
7. Change DCF assumptions and explain why the output is a scenario, not a recommendation.
8. Show `/api/docs`, Dockerfile, tests, and CI if the interviewer is technical.

## Resume-ready bullets
- Engineered a full-stack financial intelligence platform using Python/FastAPI and React/TypeScript to unify SEC-reported fundamentals, live market telemetry, peer benchmarking, filing retrieval, and assumption-driven valuation analysis.
- Built an SEC XBRL normalization pipeline that separates annual flow metrics from latest point-in-time balance-sheet facts, derives financial ratios and free cash flow, and preserves source-period provenance for traceable analysis.
- Implemented asynchronous external-data services, TTL caching, upstream quota protection, deterministic 10-K/10-Q evidence retrieval, automated tests, CI, and multi-stage Docker deployment for a portfolio-ready production architecture.
