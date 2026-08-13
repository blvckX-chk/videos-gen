"""Provider de démonstration : aucune clé, aucun coût.

Il ne génère pas vraiment de vidéo IA mais renvoie une courte vidéo libre de
droits après un délai simulé. Utile pour tester toute la chaîne (UI, jobs,
polling) sans dépendre d'une API externe.
"""
from __future__ import annotations

import asyncio
import random

from ..models import Job
from .base import VideoProvider

# Quelques clips de démonstration libres de droits (domaine public / CC0).
_SAMPLE_CLIPS = [
    "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
]


class DemoProvider(VideoProvider):
    id = "demo"
    name = "Démo (sans clé)"
    description = "Simule une génération pour tester la chaîne complète. Gratuit, aucune clé requise."
    free = True
    requires_key = None
    models = ["placeholder"]

    def is_available(self) -> bool:
        return True

    async def generate(self, job: Job) -> str:
        # Simule le temps de calcul d'un vrai modèle vidéo.
        await asyncio.sleep(3)
        rng = random.Random(job.seed)
        return rng.choice(_SAMPLE_CLIPS)
