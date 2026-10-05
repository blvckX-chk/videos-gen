"""Configuration centralisée, chargée depuis les variables d'environnement / .env."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Amélioration de prompt
    prompt_enhancer: str = "rule_based"  # anthropic | openai | rule_based
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Providers vidéo
    fal_key: str = ""
    replicate_api_token: str = ""
    comfyui_url: str = ""

    # Voix off premium (Slice 4)
    elevenlabs_api_key: str = ""

    # Banques de médias libres (b-roll réel, gratuit). Clés API gratuites.
    pexels_api_key: str = ""
    pixabay_api_key: str = ""

    # Serveur
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # URL interne utilisée par Remotion/Chromium (qui tourne DANS le conteneur)
    # pour récupérer les images des assets. On ne passe PAS par l'URL publique :
    # derrière un reverse-proxy/Cloudflare, Chromium bouclerait vers l'extérieur
    # et le rendu pendrait sans fin. 127.0.0.1:8000 = uvicorn local.
    internal_base_url: str = "http://127.0.0.1:8000"

    # Auth admin (baseline solo-prod).
    # - Vide (défaut) : mode dev/solo → rôle ADMIN par défaut, sans friction.
    # - Défini : mode production → ADMIN uniquement avec le bon secret ;
    #   sinon le rôle par défaut retombe à FREE et X-Role ne peut plus
    #   s'auto-promouvoir admin. Poser via l'env ADMIN_SECRET (ou .env).
    admin_secret: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
