"""Point d'entrée FastAPI de videos-gen."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .render.service import storage_root
from .routers.api import router as api_router
from .routers.audio import router as audio_router
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
app.include_router(audio_router)

# Fichiers statiques : assets rasterisés (pages/cases) + vidéos rendues +
# clips audio de l'audio toolkit. Chromium (Remotion) doit pouvoir fetcher
# /assets/<doc_id>/<file>.jpg pendant le rendu.
_storage = storage_root()
for sub in ("assets", "renders", "audio", "audio_sources"):
    (_storage / sub).mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=_storage / "assets"), name="assets")
app.mount("/renders", StaticFiles(directory=_storage / "renders"), name="renders")
app.mount("/audio", StaticFiles(directory=_storage / "audio"), name="audio")
app.mount("/audio_sources", StaticFiles(directory=_storage / "audio_sources"), name="audio_sources")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
