"""ASA Discovery — FastAPI application entry point."""

import sys
from pathlib import Path

# Add project root paths so packages/ and agents/ are importable
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.sessions import router as sessions_router
from app.routes.voice import router as voice_router

app = FastAPI(
    title="ASA Discovery API",
    description="Autonomous Solutions Architect — Cloud Discovery Workshop Engine",
    version="0.1.0",
)

# CORS — allow all origins (API Gateway also handles CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "asa-discovery"}


# Register API routes
app.include_router(sessions_router, prefix="/v1")
app.include_router(voice_router)
