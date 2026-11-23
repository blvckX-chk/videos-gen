"""Tri déterministe des photos — netteté, exposition, visages, quasi-doublons.

Gratuit, instantané, sans IA : c'est la première passe qui écarte l'évident
(flou, raté d'exposition, rafales quasi identiques) avant qu'un modèle de
vision ne fasse le choix éditorial. Sur un album de 50 photos, cette passe
seule retire déjà le gros du bruit.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from .schema import PhotoAnalysis

logger = logging.getLogger("videos_gen.curation")

#: Seuils empiriques, volontairement prudents : mieux vaut signaler que jeter.
SHARPNESS_BLUR = 60.0        # variance de Laplacien en dessous = flou probable
DARK = 55.0                  # luminance moyenne en dessous = trop sombre
BRIGHT = 205.0               # au-dessus = surexposé
CLIP_MAX = 0.28              # part tolérée de pixels bouchés/cramés
DHASH_DISTANCE = 10          # distance de Hamming max pour un quasi-doublon

_face_cascade: "cv2.CascadeClassifier | None" = None


def _faces_detector() -> "cv2.CascadeClassifier | None":
    global _face_cascade
    if _face_cascade is None:
        path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not path.exists():
            return None
        _face_cascade = cv2.CascadeClassifier(str(path))
    return _face_cascade


def _dhash(gray: "np.ndarray", size: int = 8) -> int:
    """Empreinte perceptuelle : compare les pixels voisins après réduction.
    Deux photos d'une même rafale donnent des empreintes très proches."""
    small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    bits = 0
    for bit in diff.flatten():
        bits = (bits << 1) | int(bit)
    return bits


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def analyze_photo(path: Path, media_id: str) -> tuple[PhotoAnalysis, int | None]:
    """Mesure une photo. Renvoie (analyse, empreinte) — empreinte None si illisible."""
    out = PhotoAnalysis(media_id=media_id)
    img = cv2.imread(str(path))
    if img is None:
        out.issues.append("illisible")
        out.keep = False
        return out, None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out.sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    out.brightness = float(gray.mean())
    total = gray.size
    out.clipped = float(((gray < 8).sum() + (gray > 247).sum()) / max(1, total))

    det = _faces_detector()
    if det is not None:
        # image réduite : la détection est largement plus rapide et suffit ici
        scale = 900 / max(gray.shape)
        small = cv2.resize(gray, None, fx=min(1.0, scale), fy=min(1.0, scale)) \
            if scale < 1 else gray
        faces = det.detectMultiScale(small, scaleFactor=1.15, minNeighbors=5,
                                     minSize=(28, 28))
        out.faces = int(len(faces))

    if out.sharpness < SHARPNESS_BLUR:
        out.issues.append("flou")
    if out.brightness < DARK:
        out.issues.append("sombre")
    elif out.brightness > BRIGHT:
        out.issues.append("surexposé")
    if out.clipped > CLIP_MAX:
        out.issues.append("contrastes écrêtés")

    out.score = _score(out)
    out.keep = "flou" not in out.issues and "illisible" not in out.issues
    return out, _dhash(gray)


def _score(a: PhotoAnalysis) -> float:
    """Note 0-100 : netteté surtout, exposition ensuite, bonus si des gens."""
    sharp = min(1.0, a.sharpness / 400.0)                     # sature vers 400
    expo = 1.0 - min(1.0, abs(a.brightness - 128.0) / 128.0)   # idéal ~128
    clip = 1.0 - min(1.0, a.clipped / 0.5)
    people = min(1.0, a.faces / 4.0)
    raw = 0.45 * sharp + 0.25 * expo + 0.10 * clip + 0.20 * people
    return round(raw * 100, 1)


def mark_duplicates(analyses: list[PhotoAnalysis], hashes: list[int | None]) -> None:
    """Regroupe les quasi-doublons : on garde le mieux noté de chaque rafale.

    Modifie `analyses` sur place (duplicate_of / keep / issues)."""
    kept: list[tuple[int, int]] = []          # (index, empreinte) des photos retenues
    for i, (a, h) in enumerate(zip(analyses, hashes)):
        if h is None or not a.keep:
            continue
        match = next((k for k, kh in kept if _hamming(h, kh) <= DHASH_DISTANCE), None)
        if match is None:
            kept.append((i, h))
            continue
        # doublon : on conserve la meilleure des deux
        best, worst = (i, match) if a.score > analyses[match].score else (match, i)
        analyses[worst].keep = False
        analyses[worst].duplicate_of = analyses[best].media_id
        if "doublon" not in analyses[worst].issues:
            analyses[worst].issues.append("doublon")
        if best == i:
            kept = [(k, kh) for k, kh in kept if k != match]
            kept.append((i, h))
