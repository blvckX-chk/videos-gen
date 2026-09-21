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
from .routers.campaign import router as campaign_router
from .routers.chat import router as chat_router
from .routers.copy import router as copy_router
from .routers.design import router as design_router
from .routers.identity import router as identity_router
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
app.include_router(design_router)
app.include_router(campaign_router)
app.include_router(identity_router)
app.include_router(copy_router)
app.include_router(chat_router)

logger = logging.getLogger("videos_gen.startup")


@app.on_event("startup")
async def _rehydrate_stores() -> None:
    """Recharge tous les stores depuis SQLite → l'état survit à un redémarrage.

    Chaque module de stockage porte un `rehydrate()` idempotent. On les appelle
    une fois au boot ; un module qui échoue ne bloque pas les autres.
    """
    from .audio import storage as audio_store
    from .campaign import storage as campaign_store
    from .design import storage as design_store
    from .identity import charters as charters_store
    from .services import documents as documents_store
    from .services import jobs as jobs_store

    for name, mod in (
        ("documents", documents_store),
        ("jobs", jobs_store),
        ("design", design_store),
        ("audio", audio_store),
        ("campaigns", campaign_store),
        ("chartes", charters_store),
    ):
        try:
            n = mod.rehydrate()
            logger.info("Réhydratation %s : %d enregistrement(s)", name, n)
        except Exception:  # noqa: BLE001
            logger.exception("Échec réhydratation du store %s", name)

# Fichiers statiques : assets rasterisés (pages/cases) + vidéos rendues +
# clips audio + images du module design. Chromium (Remotion) doit pouvoir
# fetcher /assets/<doc_id>/<file>.jpg pendant le rendu.
_storage = storage_root()
for sub in ("assets", "renders", "audio", "audio_sources", "design"):
    (_storage / sub).mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=_storage / "assets"), name="assets")
app.mount("/renders", StaticFiles(directory=_storage / "renders"), name="renders")
app.mount("/audio", StaticFiles(directory=_storage / "audio"), name="audio")
app.mount("/audio_sources", StaticFiles(directory=_storage / "audio_sources"), name="audio_sources")
app.mount("/design", StaticFiles(directory=_storage / "design"), name="design")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
