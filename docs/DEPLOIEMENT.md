# Déploiement de KORA (test & production)

Guide d'installation sur un VPS. KORA tourne en deux conteneurs Docker :

| Conteneur | Rôle | Port |
|-----------|------|------|
| `web` | Frontend (nginx) + reverse-proxy vers le backend | 80 (→ 443 avec TLS) |
| `backend` | API FastAPI + Remotion (vidéo) + FFmpeg + Chromium | interne (8000) |

La persistance (base SQLite + fichiers rendus/uploads) vit dans un **volume Docker
nommé `kora-storage`** : elle survit aux redémarrages et aux `docker compose up`.

---

## 0. Prérequis sur le VPS

- Un VPS Linux (Ubuntu 22.04/24.04 ou Debian 12 recommandé), **2 vCPU / 4 Go RAM
  minimum** (le rendu vidéo est gourmand ; 4 vCPU / 8 Go confortable).
- ~10 Go de disque libre (l'image backend fait ~2 Go : Chromium + Node + Python).
- Un accès SSH root (ou un utilisateur avec `sudo`).

### Installer Docker + Compose

```bash
# Debian/Ubuntu — installeur officiel Docker
curl -fsSL https://get.docker.com | sh

# Vérifier
docker --version
docker compose version
```

---

## 1. Récupérer le code

```bash
git clone https://github.com/blvckX-chk/videos-gen.git
cd videos-gen
git checkout claude/ai-video-generation-system-942dgh   # ou la branche fusionnée
```

---

## 2. Configurer

### a) Les clés / options du backend (optionnel mais recommandé)

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Tout est optionnel : sans aucune clé, le cœur gratuit (démo, Pollinations,
rule-based) fonctionne. Ajoute tes clés si tu en as (FAL, Replicate, ElevenLabs…).

### b) Les variables de déploiement (racine)

Crée un fichier `.env` **à la racine** (lu par docker compose) :

```bash
cat > .env <<'EOF'
# Secret admin — OBLIGATOIRE en production.
# Génère une valeur longue et aléatoire :  openssl rand -hex 32
ADMIN_SECRET=colle_ici_un_secret_long_et_aleatoire

# Port HTTP exposé (80 par défaut).
HTTP_PORT=80

# Origines autorisées (ton domaine ou l'IP publique).
CORS_ORIGINS=http://mon-domaine.com,http://IP_DU_VPS
EOF
```

> **Mode test vs production**
> - **Test / solo** : laisse `ADMIN_SECRET` vide → tu es **admin par défaut**,
>   sans friction (idéal pour valider que tout marche).
> - **Production** : définis `ADMIN_SECRET` → le rôle admin n'est accordé qu'avec
>   ce secret (saisi dans l'onglet *Identité* du panel) ; tout autre visiteur est
>   **free** (filigrane blvckUnlimited forcé, quotas). Les garde-fous sont alors
>   non contournables.

---

## 3. Lancer

```bash
docker compose up -d --build
```

Le premier build prend quelques minutes (téléchargement de Chromium, Node,
dépendances Python). Ensuite :

```bash
docker compose ps          # les deux services doivent être "running"/"healthy"
docker compose logs -f backend   # suivre les logs (Ctrl-C pour quitter)
```

Ouvre `http://IP_DU_VPS/` dans un navigateur → le panel KORA s'affiche.
Vérifie l'API : `curl http://IP_DU_VPS/health` → `{"status":"ok"}`.

---

## 4. Vérification rapide (smoke test)

Un script est fourni :

```bash
./scripts/smoke.sh http://localhost      # depuis le VPS
```

Il vérifie les endpoints clés (health, providers, identité, design, campagne).

Pour tester le **mode production** de l'auth :

```bash
# Sans secret → rôle free
curl -s http://localhost/api/identity/me | grep -o '"role":"[a-z]*"'
# Avec le bon secret → rôle admin
curl -s -H "X-Admin-Secret: TON_SECRET" http://localhost/api/identity/me | grep -o '"role":"[a-z]*"'
```

---

## 5. Mettre à jour

```bash
git pull
docker compose up -d --build       # reconstruit et redémarre ; le volume (données) est conservé
```

---

## 6. TLS / HTTPS (production)

Une surcharge Compose prête à l'emploi ajoute **Caddy** devant KORA : il obtient
et renouvelle automatiquement un certificat Let's Encrypt (HTTP/2 + HTTP/3).

**Pré-requis** : un enregistrement DNS **A** (et **AAAA** si IPv6) qui pointe ton
domaine vers l'IP publique du VPS. Vérifie : `dig +short mon-domaine.com`.

Puis lance avec les deux fichiers compose :

```bash
export DOMAIN=kora.mon-domaine.com
export ACME_EMAIL=moi@mon-domaine.com    # pour les avis d'expiration Let's Encrypt
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy prend alors les ports 80/443 ; le conteneur `web` n'est plus exposé
directement. Teste : `curl https://kora.mon-domaine.com/health`.

> Pour pérenniser, mets `DOMAIN` / `ACME_EMAIL` dans le `.env` racine et garde
> l'habitude de lancer avec `-f docker-compose.yml -f docker-compose.prod.yml`.
> `CORS_ORIGINS` est automatiquement calé sur `https://$DOMAIN` par la surcharge.

---

## 7. Sauvegarde des données

Tout l'état est dans le volume `kora-storage`. Sauvegarde :

```bash
docker run --rm -v videos-gen_kora-storage:/data -v "$PWD":/backup alpine \
  tar czf /backup/kora-backup-$(date +%F).tar.gz -C /data .
```

Restauration : l'inverse (`tar xzf … -C /data`).

---

## 8. Dépannage

| Symptôme | Piste |
|----------|-------|
| `web` démarre mais page blanche | `docker compose logs web` ; vérifier le build frontend |
| Rendu vidéo échoue | `docker compose logs backend` ; vérifier que `REMOTION_CHROMIUM` pointe sur le headless-shell (défini dans l'image) |
| « Interrompu par un redémarrage » sur un job | normal après un restart : les jobs en cours sont marqués échoués (relance-les) |
| Port 80 déjà pris | change `HTTP_PORT` dans `.env` racine |
| Manque d'espace disque | `docker system prune -af` (attention : supprime les images inutilisées) |
