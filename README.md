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
│       ├── providers/        # 🔌 un fichier = un moteur vidéo
│       │   ├── base.py       #    contrat commun (VideoProvider)
│       │   ├── registry.py   #    liste des providers actifs
│       │   ├── demo.py       #    gratuit, sans clé (pour tester)
│       │   ├── fal.py        #    Kling, Luma, Wan, LTX (crédits gratuits)
│       │   └── replicate.py  #    Wan, LTX, Hunyuan (crédits gratuits)
│       ├── services/
│       │   ├── prompt_enhancer.py  # prompt simple → prompt cinéma
│       │   └── jobs.py             # file de jobs + exécution async
│       └── routers/api.py    # /api/generate, /api/jobs, /api/providers…
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
