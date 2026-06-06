import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

START_TIME = time.time()

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from services.event_hub_service import close_producer
    await close_producer()


app = FastAPI(
    title="AML Event Injector",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.state.limiter = limiter
app.state.start_time = START_TIME
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────
allowed_origins = list(filter(None, [
    os.getenv("FRONTEND_URL"),
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://127.0.0.1:8000",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_credentials=True,
    allow_headers=["*"],
)

# ── API Routes (registered BEFORE static mount) ───────────────
from routes.events import router as events_router
from routes.health import router as health_router

app.include_router(events_router, prefix="/api/events")
app.include_router(health_router, prefix="/api")

# ── Serve static assets ───────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    is_dev = os.getenv("ENVIRONMENT", "production") == "development"
    print(f"\n🚀 AML Event Injector running on http://localhost:{port}")
    print(f"   Event Hub : {os.getenv('EVENT_HUB_NAME', 'NOT SET')}")
    print(f"   Docs      : http://localhost:{port}/docs\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=is_dev)
