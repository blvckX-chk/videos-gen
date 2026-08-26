"""Fabriques de `Composition` — templates prêts à l'emploi.

Chaque template renvoie une `Composition` déclarative, sans effet de bord.
Le rendu se fait via `composer.compose()`. Palettes par défaut alignées sur
la vidéo (blueprint v1.1) : accent or ambré + fond sombre chaleureux.
"""
from __future__ import annotations

from .schema import Anchor, Composition, FORMAT_DIMS, ImageFormat, Layer, LayerType


# Palette par défaut (assortie au blueprint v1.1)
DEFAULT_PALETTE = {
    "bg1": "#14110D",
    "bg2": "#241F17",
    "fg": "#F1EBE0",
    "muted": "#AC9F8C",
    "accent": "#E4A93E",
    "accent_soft": "#3A2E15",
    "positive": "#6FC077",
    "negative": "#E06B4F",
}

# Templates alternatifs par pôle interne
POLE_PALETTES: dict[str, dict[str, str]] = {
    "default": DEFAULT_PALETTE,
    "art": {**DEFAULT_PALETTE, "accent": "#FFC93C", "bg1": "#0A0A0F", "bg2": "#141420"},
    "store": {**DEFAULT_PALETTE, "accent": "#FF7B54", "bg1": "#101010", "bg2": "#1C1C1C"},
    "forge": {**DEFAULT_PALETTE, "accent": "#5CC8FF", "bg1": "#0F1420", "bg2": "#182033"},
}


def _pal(p: dict[str, str] | None) -> dict[str, str]:
    return {**DEFAULT_PALETTE, **(p or {})}


# --------------------------------------------------------------------------- #
# 1) Quote card — grosse citation + auteur.
# --------------------------------------------------------------------------- #
def quote_card(text: str, author: str | None = None,
               format: ImageFormat = ImageFormat.SQUARE,
               palette: dict[str, str] | None = None) -> Composition:
    p = _pal(palette)
    w, h = FORMAT_DIMS[format]
    return Composition(
        name="Quote card",
        format=format,
        background=p["bg1"],
        layers=[
            Layer(type=LayerType.GRADIENT, color=p["bg1"], color2=p["bg2"], gradient_angle=120),
            Layer(type=LayerType.TEXT, text="“", font_size=w // 4,
                  font_weight="bold", text_color=p["accent"],
                  anchor=Anchor.TOP_LEFT, dx=int(w * 0.06), dy=int(h * 0.05),
                  max_width=w // 3),
            Layer(type=LayerType.TEXT, text=text, font_size=max(48, w // 16),
                  font_weight="bold", text_color=p["fg"], text_align="left",
                  max_width=int(w * 0.82), line_height=1.15, shadow=True,
                  anchor=Anchor.CENTER, dx=0, dy=-30),
            Layer(type=LayerType.SHAPE, shape="rect", width=int(w * 0.12), height=4,
                  fill=p["accent"], anchor=Anchor.BOTTOM_LEFT,
                  dx=int(w * 0.09), dy=-int(h * 0.13)),
            Layer(type=LayerType.TEXT, text=author or "", font_size=max(22, w // 44),
                  font_weight="regular", text_color=p["accent"],
                  max_width=int(w * 0.7),
                  anchor=Anchor.BOTTOM_LEFT, dx=int(w * 0.09), dy=-int(h * 0.09)),
        ],
    )


# --------------------------------------------------------------------------- #
# 2) Stat card — un très gros chiffre + label + contexte court.
# --------------------------------------------------------------------------- #
def stat_card(number: str, label: str, context: str | None = None,
              format: ImageFormat = ImageFormat.SQUARE,
              palette: dict[str, str] | None = None,
              trend: str | None = None) -> Composition:
    """`trend` optionnel : "up" (positif), "down" (négatif)."""
    p = _pal(palette)
    w, h = FORMAT_DIMS[format]
    trend_color = p["positive"] if trend == "up" else p["negative"] if trend == "down" else p["accent"]
    trend_char = "↗" if trend == "up" else "↘" if trend == "down" else ""

    return Composition(
        name=f"Stat — {label}",
        format=format,
        background=p["bg1"],
        layers=[
            Layer(type=LayerType.GRADIENT, color=p["bg1"], color2=p["bg2"], gradient_angle=180),
            # petit label en haut
            Layer(type=LayerType.TEXT, text=label.upper(), font_size=max(20, w // 48),
                  font_weight="bold", text_color=p["muted"], text_align="center",
                  max_width=int(w * 0.85), letter_spacing=2.0,
                  anchor=Anchor.TOP, dx=0, dy=int(h * 0.18)),
            # LE chiffre
            Layer(type=LayerType.TEXT, text=number, font_size=max(160, w // 4),
                  font_weight="bold", text_color=p["fg"], text_align="center",
                  max_width=int(w * 0.9),
                  anchor=Anchor.CENTER, dx=0, dy=-int(h * 0.02)),
            # tendance
            Layer(type=LayerType.TEXT, text=trend_char, font_size=max(60, w // 12),
                  font_weight="bold", text_color=trend_color, text_align="center",
                  max_width=int(w * 0.3),
                  anchor=Anchor.CENTER, dx=int(w * 0.35), dy=-int(h * 0.02)),
            # contexte en bas
            Layer(type=LayerType.TEXT, text=context or "", font_size=max(24, w // 36),
                  font_weight="regular", text_color=p["muted"], text_align="center",
                  max_width=int(w * 0.75), line_height=1.3,
                  anchor=Anchor.BOTTOM, dx=0, dy=-int(h * 0.14)),
            # liseret accent
            Layer(type=LayerType.SHAPE, shape="rect", width=int(w * 0.14), height=4,
                  fill=p["accent"], anchor=Anchor.BOTTOM, dx=0, dy=-int(h * 0.07)),
        ],
    )


# --------------------------------------------------------------------------- #
# 3) Summary card — carrousel-style : titre + 3-5 points clés numérotés.
# --------------------------------------------------------------------------- #
def summary_card(title: str, bullets: list[str],
                 subtitle: str | None = None,
                 format: ImageFormat = ImageFormat.SQUARE,
                 palette: dict[str, str] | None = None) -> Composition:
    """Carte de synthèse — parfaite pour résumer un PDF en 3-5 puces."""
    p = _pal(palette)
    w, h = FORMAT_DIMS[format]
    bullets = bullets[:5]  # borne haute pour rester lisible

    layers: list[Layer] = [
        Layer(type=LayerType.SOLID, color=p["bg1"]),
        # subtil gradient d'ambiance en haut
        Layer(type=LayerType.GRADIENT, color=p["bg2"], color2=p["bg1"],
              gradient_angle=270, height=int(h * 0.35)),
    ]

    top_y = int(h * 0.07)
    if subtitle:
        layers.append(Layer(
            type=LayerType.TEXT, text=subtitle.upper(),
            font_size=max(18, w // 55), font_weight="bold",
            text_color=p["accent"], text_align="left",
            max_width=int(w * 0.86), letter_spacing=2.0,
            anchor=Anchor.TOP_LEFT, dx=int(w * 0.07), dy=top_y,
        ))
        top_y += int(h * 0.045)

    # Titre
    layers.append(Layer(
        type=LayerType.TEXT, text=title,
        font_size=max(52, w // 15), font_weight="bold",
        text_color=p["fg"], text_align="left",
        max_width=int(w * 0.86), line_height=1.1,
        anchor=Anchor.TOP_LEFT, dx=int(w * 0.07), dy=top_y,
    ))
    # Liseret sous le titre
    layers.append(Layer(
        type=LayerType.SHAPE, shape="rect", width=int(w * 0.12), height=4,
        fill=p["accent"], anchor=Anchor.TOP_LEFT,
        dx=int(w * 0.07), dy=top_y + int(h * 0.18),
    ))

    # Points clés
    if bullets:
        bullet_start = top_y + int(h * 0.24)
        step = int(h * 0.6 / max(len(bullets), 3))
        for i, b in enumerate(bullets):
            y = bullet_start + i * step
            # petit numéro en accent
            layers.append(Layer(
                type=LayerType.TEXT, text=f"{i + 1:02d}",
                font_size=max(26, w // 32), font_weight="bold",
                text_color=p["accent"], text_align="left",
                max_width=int(w * 0.1),
                anchor=Anchor.TOP_LEFT, dx=int(w * 0.07), dy=y,
            ))
            # texte de la puce
            layers.append(Layer(
                type=LayerType.TEXT, text=b,
                font_size=max(24, w // 38), font_weight="regular",
                text_color=p["fg"], text_align="left",
                max_width=int(w * 0.75), line_height=1.3,
                anchor=Anchor.TOP_LEFT, dx=int(w * 0.16), dy=y - 2,
            ))

    return Composition(
        name=f"Résumé — {title[:40]}",
        format=format,
        background=p["bg1"],
        layers=layers,
    )


# --------------------------------------------------------------------------- #
# 4) Product card — visuel produit + nom + prix + tagline.
# --------------------------------------------------------------------------- #
def product_card(name: str, price: str,
                 tagline: str | None = None,
                 product_asset_id: str | None = None,
                 product_asset_url: str | None = None,
                 format: ImageFormat = ImageFormat.SQUARE,
                 palette: dict[str, str] | None = None) -> Composition:
    """Fiche produit — l'image produit occupe le haut, infos en bas.
    Marche encore mieux si l'image est sans fond (rembg en amont)."""
    p = _pal(palette)
    w, h = FORMAT_DIMS[format]

    layers: list[Layer] = [
        # fond dégradé
        Layer(type=LayerType.GRADIENT, color=p["bg2"], color2=p["bg1"], gradient_angle=180),
    ]
    # cadre produit centré haut, ~55 % de la hauteur — image OU placeholder
    if product_asset_id or product_asset_url:
        layers.append(Layer(
            type=LayerType.IMAGE,
            asset_id=product_asset_id, asset_url=product_asset_url,
            width=int(w * 0.72), height=int(h * 0.55),
            fit="contain", anchor=Anchor.TOP, dy=int(h * 0.07),
        ))
    else:
        # Placeholder : cartouche dégradé + monogramme lettre du produit
        layers.append(Layer(
            type=LayerType.GRADIENT, color=p["accent_soft"], color2=p["bg2"],
            gradient_angle=45, width=int(w * 0.72), height=int(h * 0.55),
            anchor=Anchor.TOP, dy=int(h * 0.07),
        ))
        initial = (name or "?")[:1].upper()
        layers.append(Layer(
            type=LayerType.TEXT, text=initial,
            font_size=int(h * 0.32), font_weight="bold",
            text_color=p["accent"], text_align="center",
            max_width=int(w * 0.72),
            anchor=Anchor.TOP, dy=int(h * 0.15),
        ))
    layers += [
        # zone info en bas
        Layer(type=LayerType.SOLID, color=p["bg1"], opacity=0.85,
              width=w, height=int(h * 0.32),
              anchor=Anchor.BOTTOM),
        # nom du produit
        Layer(type=LayerType.TEXT, text=name,
              font_size=max(44, w // 18), font_weight="bold",
              text_color=p["fg"], text_align="left",
              max_width=int(w * 0.6), line_height=1.1,
              anchor=Anchor.BOTTOM_LEFT, dx=int(w * 0.07), dy=-int(h * 0.15)),
        # tagline
        Layer(type=LayerType.TEXT, text=tagline or "",
              font_size=max(20, w // 44), font_weight="regular",
              text_color=p["muted"], text_align="left",
              max_width=int(w * 0.55), line_height=1.3,
              anchor=Anchor.BOTTOM_LEFT, dx=int(w * 0.07), dy=-int(h * 0.06)),
        # prix (pastille accent en bas droite)
        Layer(type=LayerType.SHAPE, shape="rect",
              width=int(w * 0.28), height=int(h * 0.09),
              fill=p["accent"],
              anchor=Anchor.BOTTOM_RIGHT, dx=-int(w * 0.06), dy=-int(h * 0.09)),
        Layer(type=LayerType.TEXT, text=price,
              font_size=max(32, w // 24), font_weight="bold",
              text_color=p["bg1"], text_align="center",
              max_width=int(w * 0.28),
              anchor=Anchor.BOTTOM_RIGHT, dx=-int(w * 0.06), dy=-int(h * 0.115)),
    ]  # noqa: E501

    return Composition(
        name=f"Produit — {name[:40]}",
        format=format,
        background=p["bg1"],
        layers=layers,
    )


# --------------------------------------------------------------------------- #
# Registre des templates (pour l'API et l'agent).
# --------------------------------------------------------------------------- #
TEMPLATE_SPECS: dict[str, dict] = {
    "quote_card": {
        "label": "Carte de citation",
        "description": "Grosse citation + auteur, look éditorial.",
        "params": ["text", "author?"],
    },
    "stat_card": {
        "label": "Chiffre-clé",
        "description": "Un très gros chiffre + label + contexte + tendance optionnelle.",
        "params": ["number", "label", "context?", "trend?"],
    },
    "summary_card": {
        "label": "Résumé numéroté",
        "description": "Titre + 3-5 puces numérotées, format carrousel.",
        "params": ["title", "bullets", "subtitle?"],
    },
    "product_card": {
        "label": "Fiche produit",
        "description": "Photo produit + nom + prix + tagline.",
        "params": ["name", "price", "tagline?", "product_asset_id?"],
    },
}


def build_template(name: str, params: dict) -> Composition:
    """Fabrique la Composition d'un template par son nom + params dict."""
    fmt = ImageFormat(params.pop("format", "square")) if "format" in params else ImageFormat.SQUARE
    palette = params.pop("palette", None)

    if name == "quote_card":
        return quote_card(text=params["text"], author=params.get("author"),
                          format=fmt, palette=palette)
    if name == "stat_card":
        return stat_card(number=params["number"], label=params["label"],
                         context=params.get("context"), trend=params.get("trend"),
                         format=fmt, palette=palette)
    if name == "summary_card":
        return summary_card(title=params["title"], bullets=params.get("bullets", []),
                            subtitle=params.get("subtitle"),
                            format=fmt, palette=palette)
    if name == "product_card":
        return product_card(name=params["name"], price=params["price"],
                            tagline=params.get("tagline"),
                            product_asset_id=params.get("product_asset_id"),
                            product_asset_url=params.get("product_asset_url"),
                            format=fmt, palette=palette)
    raise ValueError(f"Template inconnu : {name}")
