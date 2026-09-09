import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

# Root logger stays at WARNING (so we don't get flooded with noisy
# third-party DEBUG/INFO logs), but everything under "vyaparflow.*" is
# bumped to INFO so provider calls and application errors are visible
# # actually show up in your terminal instead of being silently dropped
# (Python's default root level is WARNING, so INFO logs are invisible
# unless a logger's own effective level is explicitly raised like this).
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("vyaparflow").setLevel(logging.INFO)

app = FastAPI(
    title="VyaparFlow API",
    description="Voice-first Agentic Business Operating System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server (production frontend)
    # Covers both `localhost` and `127.0.0.1` on any port in local dev —
    # browsers treat these as different origins even though they resolve
    # to the same machine, so a frontend opened at 127.0.0.1:3000 needs
    # this explicitly or CORS silently blocks every request.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+" if settings.environment == "local" else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
