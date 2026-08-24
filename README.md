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
