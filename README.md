# 🎬 videos-gen

Génère des **vidéos IA les plus réalistes possibles** à partir de simples prompts.
Application web multi-providers, pensée pour démarrer **sans budget** puis monter
en gamme quand tu ajoutes des clés API.

## ✨ Principes

- **Multi-providers** : une seule interface, plusieurs moteurs de génération.
  On branche le meilleur modèle disponible (gratuit ou payant) sans changer le reste.
- **Amélioration automatique du prompt** — le levier n°1 du réalisme, et **gratuit** :
  un prompt simple (« un chat qui court ») est réécrit en prompt cinématographique
  détaillé (caméra, objectif, lumière, matériaux…).
- **Sans budget d'abord** : le provider *Démo* fonctionne sans aucune clé, et
  fal.ai / Replicate offrent des **crédits gratuits** pour du vrai réalisme.

## 🏗️ Architecture

```
videos-gen/
├── backend/                  # API FastAPI (Python)
│   └── app/
│       ├── main.py           # app + CORS + routes
│       ├── config.py         # config via .env
│       ├── models.py         # schémas (Job, GenerateRequest…)
│       ├── ingestion/        # 📥 PDF → Document structuré (Slice 1)
│       │   ├── base.py       #    contrat Extractor
│       │   ├── registry.py   #    choix de l'extracteur (PyMuPDF, +Docling/BD)
│       │   ├── pymupdf_extractor.py
│       │   ├── panels.py     #    segmentation des cases de BD (XY-cut OpenCV)
│       │   ├── detect.py     #    détection de type (report/slides/sci/comic)
│       │   └── schema.py     #    Document, DocumentPage, DocType, Panel
│       ├── storyboard/       # 🎞️ Brief+Document → storyboard (Slice 2)
│       │   ├── generator.py  #    rule_based + LLM, une case/shot pour la BD
│       │   ├── textutils.py  #    extraction de points clés
│       │   └── schema.py     #    Storyboard, Scene, Shot, ShotType
│       ├── providers/        # 🔌 un fichier = un moteur vidéo (b-roll IA)
│       │   ├── base.py       #    contrat commun (VideoProvider)
│       │   ├── registry.py   #    liste des providers actifs
│       │   ├── demo.py       #    gratuit, sans clé (pour tester)
│       │   ├── fal.py        #    Kling, Luma, Wan, LTX (crédits gratuits)
│       │   └── replicate.py  #    Wan, LTX, Hunyuan (crédits gratuits)
│       ├── services/
│       │   ├── prompt_enhancer.py  # prompt simple → prompt cinéma
│       │   ├── clarification.py    # Document → questions → Brief (Slice 1)
│       │   ├── documents.py        # store des documents ingérés
│       │   └── jobs.py             # file de jobs + exécution async
│       └── routers/          # api.py (génération) + ingest.py (Slice 1)
└── frontend/                 # UI React + Vite
    └── src/
        ├── App.jsx
        ├── components/       # PromptForm, JobCard
        └── lib/api.js        # client HTTP
```

Le flux d'une génération :

```
prompt utilisateur
      │
      ▼
[ enhance_prompt ]  ← rule_based (gratuit) | Claude | OpenAI
      │  prompt cinématographique
      ▼
[ provider.generate() ]  ← fal | replicate | demo | (ton provider)
      │  URL de la vidéo
      ▼
    job "succeeded"  →  affichée dans la galerie
```

## 🧩 Slice 1 — Ingestion PDF + Clarification (implémenté)

Première brique du pipeline **document → vidéo**. Le système prend un **PDF**
(rapport, présentation, article scientifique, ou **BD/manga**), détecte son
type, et pose des questions **adaptatives** pour cadrer la vidéo avec le
soumissionnaire. La sortie est un objet **`Brief`** : le contrat qui pilotera
le storyboard et le rendu (Slice 2).

```
PDF ──▶ Extracteur ──▶ Détection type ──▶ Questions adaptatives ──▶ Brief
        (PyMuPDF)       (report/slides/       (LLM ou règle-based)   (JSON typé)
                         scientific/comic)
```

- **Ingestion** : `backend/app/ingestion/` — extracteurs branchables
  (`Extractor` + registry). PyMuPDF par défaut ; Docling / extracteur BD à
  ajouter sans toucher au reste.
- **Détection de type** : heuristiques explicables (`detect.py`) — densité de
  texte, couverture d'images, orientation, lexique scientifique. Les **BD**
  sont repérées par leurs planches image-heavy à faible texte.
- **Clarification** : `services/clarification.py` — questions communes +
  questions **spécifiques au type**. Pour une BD : style d'animation (motion
  comic), voix par personnage, bruitages. Mode LLM (Claude/OpenAI) si clé,
  sinon fallback gratuit.

### Endpoints
| Méthode | Route | Rôle |
|--------|-------|------|
| POST | `/api/ingest` | Upload PDF → `Document` + questions de clarification |
| GET | `/api/documents/{id}` | Détail d'un document ingéré |
| POST | `/api/brief` | `document_id` + réponses → `Brief` |
| POST | `/api/documents/{id}/panels` | Segmente les cases d'une BD (`direction=ltr\|rtl`) |
| POST | `/api/storyboard` | `Brief` → storyboard multi-format |

### 💥 Support des BD / mangas
Le système gère les bandes dessinées de bout en bout pour le Slice 1 :

1. **Détection** : les planches (pages très couvertes par des images, peu de
   texte) sont classées `comic`, et la clarification bascule sur des questions
   « motion comic » (style d'animation, voix par personnage, bruitages).
2. **Segmentation des cases** (`ingestion/panels.py`) : détection des cases par
   **XY-cut récursif sur les gouttières** (vision classique, OpenCV — léger,
   offline, sans GPU ni modèle). Calcule le **bounding box normalisé** de chaque
   case et l'**ordre de lecture** — `ltr` (BD occidentale) ou `rtl` (manga).
   Endpoint : `POST /api/documents/{id}/panels?direction=ltr|rtl`.
   L'UI superpose les cases numérotées sur chaque planche.

Prochaine amélioration BD : **détection + OCR des bulles** et modèle
state-of-the-art (Magi / DASS) branché via la même interface — utile pour des
mangas à cases sans bordure que le XY-cut segmente « au mieux ».

## 🎞️ Slice 2 — Storyboard multi-format (implémenté)

`Brief` + `Document` → **storyboard JSON** : le plan de tournage que le rendu
Remotion exécutera (Slice 3). Pensé **multi-format dès le départ** (9:16
vertical prioritaire, 1:1, 16:9) et calibré pour de la **vidéo courte**
(Reels / TikTok / Shorts).

```
Brief + Document ──▶ Générateur ──▶ Storyboard
                     (rule_based        (scènes → shots typés :
                      ou LLM)            titre, texte, page, case,
                                         durée, transition, template)
```

- **Générateur** (`storyboard/generator.py`) : mode `rule_based` gratuit
  (déterministe) ou LLM (Claude/OpenAI) avec repli automatique.
  - **Documents texte** : carton titre → points clés par section → outro.
  - **BD/motion-comic** : **une case par shot dans l'ordre de lecture** dès
    que les cases ont été segmentées (`doc.panels`), quel que soit le type
    détecté.
- **Durées** calées sur `brief.duration_seconds`, bornées pour un rythme court.
- **Template** choisi selon le type : `corporate`, `explainer`, `deck`,
  `motion_comic`, `default`.
- Endpoint : `POST /api/storyboard` (corps = objet `Brief`).
- **UI** : bouton « Générer le storyboard » → timeline des scènes/shots avec
  durées, références page/case, et formats cibles.

## 🎥 Slice 3 — Rendu Remotion vertical (implémenté)

Le storyboard produit au Slice 2 est enfin rendu en **vraie vidéo MP4** — vertical
1080×1920 par défaut, cœur 100 % gratuit, avec les décisions du blueprint v1.1
intégrées dès la fondation.

```
Storyboard ──▶ Rasterisation ──▶ Remotion (Node/React) ──▶ MP4
              (pages/cases        (composition, shots,
               en JPEG HD)         Ken Burns, watermark)
```

- **Projet Remotion** : `remotion/` — TypeScript + React 18.
  - `src/Root.tsx` déclare la composition, adapte la résolution au format cible
    (9:16 / 1:1 / 16:9) via `calculateMetadata`.
  - `src/shots/` — un composant par `ShotType` (title, text, page, panel, outro).
  - `src/templates.ts` — palettes/typos par pôle (`default`, `corporate`,
    `explainer`, `deck`, `motion_comic`).
- **Backend `app/render/`** :
  - `assets.py` — rasterise pages entières et cases rognées en JPEG HD.
  - `service.py` — job asynchrone qui prépare les assets, écrit les props JSON,
    lance `npx remotion render` en subprocess, capture la sortie et met à jour
    le job.
- **Champ `tier`** (`free` / `premium`) et **compteur de coût** posés sur
  chaque `Job` — un job `free` reste à **0 centime**. Les entrées de coût
  (`CostEntry`) sont prêtes à accueillir les appels ElevenLabs, HeyGen, etc.
  au Slice 4.
- **Statique** : `/renders/*.mp4` (vidéos) et `/assets/<doc_id>/*.jpg` (pages
  rasterisées) sont servis par FastAPI.
- **Chromium** : Remotion utilise le `headless_shell` fourni par
  l'environnement (path via `DEFAULT_CHROMIUM` dans `render/service.py`).

### Endpoints
| Méthode | Route | Rôle |
|--------|-------|------|
| POST | `/api/render` | `{storyboard, tier, client_id}` → job de rendu |
| GET | `/api/render/{id}` | Statut du rendu (polling) |

**UI** : bouton « 🎥 Rendre la vidéo » sous le storyboard, sélecteur de tier
Free/Premium, statut et lecteur du MP4 dès qu'il est prêt.

## 🎧 Audio toolkit (extraire / isoler / réutiliser)

Module autonome + intégré au pipeline PDF→vidéo. Trois opérations :

- **Extraire l'audio d'une vidéo** — upload MP4/MOV, extraction MP3 via ffmpeg.
- **Isoler voix vs musique** — séparation par **Demucs** (open-source SOTA,
  Apache-2.0). Modèle téléchargé au 1er usage (~80 Mo).
- **Remuxer un audio sur une vidéo** — remplacer, mixer (ducking 15 %) ou
  **supprimer** entièrement la piste. Fonctionne sur les vidéos uploadées
  ET sur les MP4 rendus par le pipeline (Slice 3).

Une **bibliothèque partagée** de clips (`original`, `vocals`, `instrumental`,
`custom`) est utilisable depuis l'onglet Audio toolkit ET depuis le rendu
Storyboard (choisir une piste de fond après avoir rendu le MP4).

### Endpoints
| Méthode | Route | Rôle |
|--------|-------|------|
| GET | `/api/audio/info` | Capacités du serveur (Demucs présent ?) |
| GET | `/api/audio/library` | Liste des clips |
| POST | `/api/audio/upload-video` | Upload vidéo → extraction audio auto |
| POST | `/api/audio/upload-audio` | Ajout direct d'un fichier audio |
| POST | `/api/audio/clips/{id}/separate` | Séparation voix/musique (Demucs, async) |
| POST | `/api/audio/apply` | Coller un audio (ou le supprimer) sur une vidéo |
| GET | `/api/audio/jobs/{id}` | Statut d'un job long |

### Installation Demucs
```bash
cd backend && . .venv/bin/activate
pip install demucs   # attention : pull PyTorch (~2 Go)
```
Sans Demucs : extraction et remux fonctionnent, la séparation renvoie 503.

## 🎨 Graphic Design (fondation du toolkit)

Module de visuels statiques — sœur graphique de la vidéo. Alimente le CM
(posts IG/FB, stories, thumbnails YouTube, quote cards) et prépare le terrain
pour un futur super-agent orchestré.

**Fondation livrée** — opérations déterministes, ~0 dépendance lourde :

- **Génération d'images** via un pattern multi-providers extensible
  (miroir du module vidéo) :
  - `pollinations` — gratuit, sans clé, sans compte (défaut du tier free)
  - `fal_image` — Flux/SDXL via fal.ai (crédits gratuits + facturé)
  - Ajouter un provider = créer une sous-classe `ImageProvider` + registry
- **Templates** — fabrique de `Composition` déclarative. Livré : **quote card**
  (grosse citation + auteur + accent), alimenté par les points clés extraits
  au Slice 1.
- **Composer** (`design/composer.py`) — empile des `Layer` (solid, gradient,
  image, text, shape) sur un canvas de la taille du format cible, avec
  ancrage, opacité, coins arrondis, watermark blvckUnlimited assorti à la vidéo.
- **Traitement PIL** :
  - Redimensionnement / recadrage intelligent (`fit_cover`, focus règle des tiers)
  - Décliner un asset en plusieurs formats en un job
  - Overlays typographiques (wrap texte, shadow, stroke, alignement)
  - Retrait de fond via **`rembg`** (u2net, ~170 Mo, CPU OK, Apache-2.0) — optionnel
- **Bibliothèque** — assets `generated`, `uploaded`, `processed`, `composed`.
  Réutilisables dans le pipeline vidéo (ils exposent une URL PNG normale).

### Formats livrés
| Nom | Dimensions | Usage |
|---|---|---|
| `square` | 1080 × 1080 | Post IG/FB |
| `story` | 1080 × 1920 | Story / cover de Reel |
| `landscape` | 1280 × 720 | Thumbnail YouTube |
| `large_square` | 2048 × 2048 | Print / retail |
| `a4` | 2480 × 3508 | Impression 300 DPI |

### Endpoints
| Méthode | Route | Rôle |
|--------|-------|------|
| GET | `/api/design/info` | Formats + providers + capacité rembg |
| GET | `/api/design/assets` | Bibliothèque |
| POST | `/api/design/upload` | Upload image |
| POST | `/api/design/generate` | Génération IA (tier free/premium) |
| POST | `/api/design/remove-bg` | Retrait de fond (rembg) |
| POST | `/api/design/resize` | Décliner en plusieurs formats |
| POST | `/api/design/compose` | Rendu d'une `Composition` complète |
| POST | `/api/design/templates/quote-card` | Quote card prête à l'emploi |
| GET | `/api/design/jobs/{id}` | Statut d'un job |

Garde-fou **tier v1.1** : un job `free` ne peut pas invoquer un provider payant.

### Templates livrés
| Nom | Rôle |
|---|---|
| `quote_card` | Grosse citation + auteur + accent |
| `stat_card` | Un chiffre-clé XL + label + contexte + tendance (↗/↘) |
| `summary_card` | Titre + 3-5 puces numérotées (format carrousel) |
| `product_card` | Photo produit (ou monogramme placeholder) + nom + prix + tagline |

Endpoint générique : `POST /api/design/templates/render` (`template`, `params`)
et registre exposé via `GET /api/design/templates`.

### 🤖 Super-agent graphique
Par-dessus le toolkit : un LLM reçoit une intention (« crée une série de
visuels pour promouvoir le rapport ») + un `document_id` optionnel, et
planifie une séquence de templates + générations.

- **Plan éditable avant exécution** (validation humaine, blueprint v1.1).
- Mode `rule_based` (gratuit, sans clé) qui exploite les points clés + les
  chiffres extraits du document, ou LLM (Claude/OpenAI) avec repli.
- Garde-fou tier free : un plan `free` ne peut planifier que des étapes
  gratuites (templates + Pollinations).

Endpoints :
- `POST /api/design/agent/plan` — dry-run (renvoie le plan)
- `POST /api/design/agent/run` — exécute un plan (renvoie un job)

## 🚀 Démarrage rapide

### Tout-en-un (dev)
```bash
./dev.sh
```
Backend sur `http://localhost:8000` (docs auto sur `/docs`), frontend sur
`http://localhost:5173`.

### Manuel

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optionnel : ajoute tes clés
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Ouvre `http://localhost:5173`, choisis le provider **Démo**, tape un prompt,
génère. Tout marche sans aucune clé.

## 🔑 Passer au réalisme (crédits gratuits)

| Provider  | Modèles                       | Clé (.env)            | Où l'obtenir |
|-----------|-------------------------------|-----------------------|--------------|
| fal.ai    | Kling, Luma Ray, Wan, LTX     | `FAL_KEY`             | https://fal.ai/dashboard/keys |
| Replicate | Wan, LTX-Video, Hunyuan       | `REPLICATE_API_TOKEN` | https://replicate.com/account/api-tokens |

Ajoute la clé dans `backend/.env`, relance le backend, le provider devient
sélectionnable dans l'UI.

### Amélioration de prompt via LLM (optionnel)
Par défaut l'amélioration est **règle-based** (gratuite). Pour une qualité
supérieure, mets dans `.env` :
```
PROMPT_ENHANCER=anthropic     # ou "openai"
ANTHROPIC_API_KEY=...
```

## ➕ Ajouter un nouveau provider

1. Crée `backend/app/providers/mon_provider.py` en héritant de `VideoProvider`
   (implémente `is_available()` et `async generate(job) -> url`).
2. Enregistre-le dans `providers/registry.py`.

C'est tout — l'UI et l'API le détectent automatiquement.

## 🗺️ Pistes d'amélioration (roadmap)

- Pipeline hybride : upscaling (Real-ESRGAN) + interpolation d'images (RIFE) + audio
- Génération de scènes multi-plans (script → shots → montage avec ffmpeg)
- Intégration ComfyUI local (open-source, GPU) pour du 100 % gratuit
- Persistance des jobs (Redis/DB) et file de tâches (arq/Celery)
- Génération audio / voix off synchronisée

## ⚖️ Notes

- Le provider *Démo* renvoie des clips libres de droits — il sert à tester la
  chaîne, pas à générer du contenu réaliste.
- Génère uniquement des contenus que tu es autorisé à créer ; évite deepfakes
  de personnes réelles et usages trompeurs.
