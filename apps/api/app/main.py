from pathlib import Path
from collections import defaultdict, deque
from time import monotonic
from threading import RLock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()
_rate_windows: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = RLock()

app = FastAPI(title="FINENGINE API", version="2.0.0", docs_url="/api/docs", redoc_url=None)

app.add_middleware(GZipMiddleware, minimum_size=1200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)


@app.middleware("http")
async def lightweight_rate_limit(request: Request, call_next):
    # Protect free upstream market-data quotas on a single-instance portfolio deployment.
    # Replace with Redis/API-gateway rate limiting before horizontally scaling.
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded or (request.client.host if request.client else "unknown")
    expensive = request.url.path.endswith("/overview") or request.url.path == "/api/v1/compare"
    limit = 18 if expensive else 120
    window_seconds = 60.0
    key = f"{client_ip}:{'expensive' if expensive else 'general'}"
    now = monotonic()
    with _rate_lock:
        bucket = _rate_windows[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})
        bucket.append(now)
    return await call_next(request)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    assets = STATIC_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
