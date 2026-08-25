"""Point d'entrée FastAPI de videos-gen."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .render.service import storage_root
from .routers.api import router as api_router
from .routers.ingest import router as ingest_router
from .routers.render import router as render_router

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="videos-gen",
    description="Génération de vidéos IA réalistes à partir de prompts, multi-providers.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ingest_router)
app.include_router(render_router)

# Fichiers statiques : assets rasterisés (pages/cases) + vidéos rendues.
# Chromium (Remotion) doit pouvoir fetcher /assets/<doc_id>/<file>.jpg.
_storage = storage_root()
(_storage / "assets").mkdir(parents=True, exist_ok=True)
(_storage / "renders").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=_storage / "assets"), name="assets")
app.mount("/renders", StaticFiles(directory=_storage / "renders"), name="renders")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
