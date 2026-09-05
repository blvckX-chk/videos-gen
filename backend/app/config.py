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

    # Serveur
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
