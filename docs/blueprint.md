# Le moteur vidéo blvckUnlimited

> **Note d'architecture · v1.1** — 24 août 2026
> Comment le système `videos-gen` s'articule en moteur de production central — du brief client au fichier prêt à publier — et réponses, section par section, au questionnaire de cadrage.

- **Établi pour** : blvckUnlimited · Cotonou
- **Périmètre** : ComeUp · Community management · Pôles internes
- **Statut** : cadrage — 8 décisions confirmées

## Décisions confirmées

| Décision | Valeur | Détail |
|---|---|---|
| Stack | **Hybride** | Cœur open-source + SaaS premium à l'unité |
| Format n°1 | **Vertical court** | Reels / TikTok / Shorts · 15–60 s |
| Publication | **Validation humaine** | Tu valides avant diffusion |
| Qualité | **Deux tiers** | Volume industriel + premium reconnaissable |
| Volume cible | **< 20 / semaine** | Démarrage doux · 1 worker suffit |
| Budget fixe | **0 $ / mois** | Cœur 100 % gratuit obligatoire |
| Modèle premium | **Pay-as-you-serve** | Coût SaaS répercuté au client |
| Griot | **PoC en cours** | Contrat de sortie préparé côté moteur |

---

## Sommaire

- [00 — Synthèse & schéma](#00--synthèse--schéma)
- [01 — Positionnement & clients](#01--positionnement--clients)
- [02 — Formats couverts](#02--formats-couverts)
- [03 — Volume & cadence](#03--volume--cadence)
- [04 — Langues & marchés](#04--langues--marchés)
- [05 — Stack technique](#05--stack-technique)
- [06 — Chaîne de production](#06--chaîne-de-production)
- [07 — Griot (SMM)](#07--griot--lagent-smm)
- [08 — Marque & qualité](#08--marque--qualité)
- [09 — Légal & éthique](#09--légal--éthique)
- [→ Feuille de route](#feuille-de-route)
- [Δ Journal des décisions](#journal-des-décisions)

---

## 00 — Synthèse & schéma

`videos-gen` **n'est pas le produit final** : c'est le **moteur de production** au centre de l'écosystème. En amont, des sources (brief, PDF, charte, rushes). En aval, **Griot** distribue vers les plateformes. Notre pipeline actuel — ingestion → clarification (Brief) → storyboard → rendu — couvre déjà nativement les slideshows narrés, le motion design, les capsules pédagogiques et le motion-comic (BD/BlvckArt). Le talking-head et l'UGC sont des **briques SaaS séparées** à brancher, pas à recoder.

```
       SOURCES                      MOTEUR (videos-gen)                  FORMATS               DISTRIBUTION
   ┌─────────────┐              ┌────────────────────────┐          ┌────────────┐         ┌──────────────┐
   │ PDF / doc   │              │  Ingestion (+cases BD) │          │ 9:16       │         │ Griot        │
   │ Brief       │  ────────▶   │  Brief (clarification) │  ─────▶  │ 1:1        │  ─────▶ │ (captions,   │
   │ Charte      │              │  Storyboard multi-fmt  │          │ 16:9       │         │  planning)   │
   │ Rushes      │              │  Rendu (Remotion)      │          │            │         │              │
   └─────────────┘              └────────────────────────┘          └────────────┘         │ IG · TikTok  │
                                                                                            │ YouTube · FB │
                                                                                            └──────────────┘
```

**Rail premium (à l'unité)** : HeyGen (talking-head) et ElevenLabs (voix premium / accent africain) s'injectent dans le moteur comme des providers, uniquement sur le tier haut de gamme et les pôles vitrine.

---

## 01 — Positionnement & clients

*Questions 1.1 → 1.5 — décisions business, avec mes défauts recommandés.*

Ces cinq points sont **tes décisions** : ils ne changent pas *comment* je code, mais *pour qui* et *combien*.

| # | Question | Défaut recommandé |
|---|---|---|
| 1.1 | Service ComeUp existant ou lancé avec ce système ? | **Le lancer avec** — le moteur devient ton avantage de coût/vitesse dès l'ouverture. |
| 1.2 | Clients cibles | **Beachhead** : e-commerçants, coachs, restaurateurs — besoin fort de vidéo courte, budget récurrent, brief simple. |
| 1.3 | CM externe déjà en cours ? | Ta donnée — sert à dimensionner l'infra (§3). |
| 1.4 | Marque blanche ou assumée ? | **Mixte par tier** : marque blanche pour ComeUp entry-level, « produit par blvckUnlimited » assumé sur le premium. |
| 1.5 | Prix de vente | Modèle **pack + abonnement** plutôt qu'à la vidéo seule. |

### Trois offres cibles

**Entry (ComeUp)** — pack / abonnement
- Volume, tier industriel
- Templates par secteur
- Marque blanche
- Livraison batch

**Premium** — à la vidéo / retainer
- Talking-head, voix premium
- Charte sur-mesure
- Marque assumée
- Revue soignée

**Pôles internes** — coût interne
- BlvckStore / Forge / Art / Prince
- Academy (capsules)
- Codes de marque stricts

> **À toi** — Fixe les **montants** (1.5) et confirme les cibles (1.2). Je peux intégrer une grille tarifaire dans l'onboarding une fois décidée — mais le chiffre t'appartient.

---

## 02 — Formats couverts

*Questions 2.1 → 2.10 — ce que le moteur produit, et par quelle brique.*

Priorité confirmée : **vertical court**.

| Format | Notre moteur | Brique | Priorité |
|---|---|---|---|
| 2.1 Vertical court (Reels/TikTok/Shorts) | ✅ natif | Storyboard + Remotion + templates | **P1** |
| 2.2 Carré (posts IG/FB) | ✅ natif | Même storyboard, rendu 1:1 | **P1** |
| 2.5 Publicités (ads 15–30 s) | ✅ natif | Templates ad + hook | **P1** |
| 2.9 Slideshows narrés | ✅ natif | Ingestion image + Ken Burns + voix | **P1** |
| 2.7 Motion design pur | ✅ natif | Remotion + stock | **P1** |
| 2.4 Capsules pédagogiques (Academy) | ✅ natif | Pipeline PDF→vidéo actuel | P2 |
| 2.3 Horizontal long (YouTube 5–15 min) | ⚠️ assemblage | Storyboard long + chapitrage | P2 |
| 2.6 Talking-head (avatar parlant) | ❌ SaaS | HeyGen (rail premium) | P3 |
| 2.8 UGC-style (smartphone authentique) | ❌ SaaS | Captions / Arcads + rushes réels | P3 |

> **Reco** — Un seul **storyboard** alimente 9:16, 1:1 et 16:9 — je construis le générateur **multi-cible d'emblée** (§ feuille de route, Slice 2, livré). Griot reçoit un fichier déjà formaté par plateforme plutôt que de recadrer lui-même.

---

## 03 — Volume & cadence

*Questions 3.1 → 3.5 — dimensionne l'infra.*

- **Mode batch** (3.5) — produire 20–30 vidéos d'un coup par client. Plus rentable et lisse la charge de rendu la nuit.
- **Délai standard 48–72 h** (3.4), avec option express premium 24 h.
- **File de jobs persistante + worker VPS** — notre modèle de jobs async actuel est la fondation ; passage sur Redis + arq quand le volume le justifie.

> **Cible v1.1** — **< 20 vidéos / semaine** confirmé. **1 seul worker** sur le VPS suffit, batch nocturne, aucune infra lourde à provisionner. On garde la trajectoire vers Redis/arq mais on ne l'implémente que quand le volume le justifie (palier ~50/sem).

---

## 04 — Langues & marchés

*Questions 4.1 → 4.3.*

- **FR & EN** — couverts nativement par la voix off open-source (Kokoro), gratuit et offline.
- **Marchés** — Bénin / Afrique francophone en priorité, extension France & anglophone via les mêmes templates.

> **⚠️ Alerte** — **Fon & Yoruba n'ont pas de TTS de qualité** à ce jour. Deux options réalistes : (a) **sous-titres** dans ces langues sur une voix FR/EN, ou (b) **voix humaine enregistrée**. Ne pas promettre une synthèse vocale fon/yoruba fiable.
>
> L'**accent africain francophone** (4.3) est atteignable via une voix ElevenLabs premium ou un enregistrement humain — pas via le TTS gratuit, qui sonne « métropolitain neutre ».

---

## 05 — Stack technique

*Questions 5.1 → 5.5 — architecture confirmée : hybride.*

Décision : **cœur open-source auto-hébergé pour le volume, SaaS ciblé à l'unité pour le premium, n8n en orchestrateur.**

| Couche | Cœur (volume, ~0 coût) | Premium (à l'unité) |
|---|---|---|
| Script / brief | LLM (Claude/OpenAI) | idem |
| Rendu / montage | Remotion + FFmpeg | Remotion + effets |
| Voix off | Kokoro / Coqui | ElevenLabs |
| Sous-titres | WhisperX | WhisperX |
| Talking-head | — | HeyGen |
| B-roll / visuels | fal / Replicate (crédits) | Runway / Veo |
| Orchestration | n8n (moteur ↔ Griot ↔ publication) | idem |

> **Contrainte** — **Bande passante Cotonou (5.5)** : tout le rendu lourd tourne **côté VPS**, pas sur ta machine. Tu déclenches et récupères des liens légers ; aucun upload/download vidéo massif quotidien depuis Cotonou. Ceci renforce le choix auto-hébergé serveur.

> **Cible v1.1** — **Budget fixe blvckUnlimited = 0 $**. Le cœur DOIT tourner 100 % gratuit — c'est une contrainte dure, pas une préférence. Concrètement : Kokoro (voix), Remotion (rendu), WhisperX (sous-titres), musique libre (YouTube Audio Library, Pixabay) au démarrage. Rien de payant tant qu'aucun client n'a payé.
>
> **Aucun abonnement actif aujourd'hui.** Micro-crédits ponctuels envisageables (ex. petit crédit Anthropic pour tester le storyboard LLM), mais uniquement si le gain de qualité est démontrable.

> **⚠️ Modèle v1.1** — **Pay-as-you-serve : le premium est répercuté au client.** ElevenLabs, HeyGen, Runway ne sont pas des coûts fixes blvckUnlimited : ils s'activent **uniquement pour un client qui paie** (à la vidéo ou par abonnement premium). Implication technique : le moteur doit **tracer le coût par job et par client** pour que la facturation reflète l'usage réel des APIs premium.

### Impact sur l'architecture

- **Nouveau champ `tier`** sur chaque job : `free` (défaut, cœur gratuit) ou `premium` (déclenché par un client payant). Le storyboard et le rendu adaptent leur choix de providers selon ce champ.
- **Compteur de coût par job** — chaque appel SaaS remonte son coût estimé (secondes de voix ElevenLabs, jetons LLM, secondes de rendu HeyGen). Agrégé par client et par période.
- **Garde-fous** — un job `free` ne peut pas appeler un provider payant, même par erreur. Vérification au niveau du registry des providers.

---

## 06 — Chaîne de production

*Questions 6.1 → 6.5 — le workflow.*

- **6.1 Script** — mix : un agent LLM propose depuis le brief/PDF, tu ajustes, le client valide le fond.
- **6.2 Validation** — ✅ **confirmé** : humaine avant publication. Une file de review où tu approuves/rejettes. Automatisation progressive une fois la qualité stabilisée.
- **6.3 Montage — indispensables** : sous-titres animés · transitions · musique · watermark. B-roll = bonus par tier.
- **6.4 Templates par pôle / type de client** — **oui**, pas du 100 % adaptatif. Les templates = ta signature + ta vitesse ; l'adaptatif joue *dans* le template.
- **6.5 Rushes réels** — le moteur les **intègre** (le client fournit) en plus du contenu généré ; indispensable pour l'UGC et le premium.

---

## 07 — Griot — l'agent SMM

*Questions 7.1 → 7.5 — la couche distribution.*

Griot est le maillon aval. Le moteur lui livre un **fichier déjà formaté par plateforme** ; Griot gère la mise en ligne et le social.

- **7.2 Périmètre recommandé** — Griot gère planning + captions + hashtags + réponses aux commentaires (pas seulement la publication).
- **7.3 Plateformes** — Instagram, TikTok, YouTube Shorts, Facebook en priorité ; LinkedIn/X ensuite.
- **7.5 Formatage** — le **moteur** produit les variantes (recadrage, durée) ; Griot ne fait qu'adapter la caption par plateforme. Plus fiable que de laisser Griot recadrer.

> **Cible v1.1** — **Griot existe en PoC.** Décision : je prépare **dès le Slice 5** le **contrat de sortie** côté `videos-gen` — un endpoint webhook + un manifeste JSON standard (chemins vidéo par format, caption suggérée, hashtags, moment de publication). Griot pourra le consommer quand il sera prêt sans qu'on doive modifier le moteur.
>
> Le nombre de comptes simultanés (7.4) reste à préciser mais ne bloque rien à ce stade — il définira surtout les quotas API plateformes côté Griot.

---

## 08 — Marque & qualité

*Questions 8.1 → 8.4.*

- **8.1 Codes par pôle** — chaque pôle a son template (intro, outro, palette, typo animée) appliqué strictement. C'est exactement ce que le système de templates gère.
- **8.2 Charte client** — via un **formulaire d'onboarding** (couleurs, logo, police, ton) qui alimente le Brief. Kit fourni accepté aussi.
- **8.3 Qualité** — ✅ **confirmé** : deux tiers, volume « correct industriel » pour ComeUp, « premium reconnaissable » pour le haut de gamme + pôles.

> **⚠️ Alerte** — **8.4 Labellisation « AI-generated »** : Meta et TikTok l'imposent pour le contenu synthétique ; viser le « non détectable » va **contre leurs règles** et risque le shadowban. Ligne recommandée : **maximiser le rendu humain** (rushes réels, voix soignée, montage) **tout en respectant le label** quand il s'applique. Qualité, pas dissimulation.

---

## 09 — Légal & éthique

*Questions 9.1 → 9.5 — décisions à cadrer.*

| # | Sujet | Position recommandée |
|---|---|---|
| 9.1 | Clauses IA au contrat | **Oui** — transparence, cession de droits sur le livrable, limite de responsabilité. Protège toi et le client. |
| 9.2 | Avatars IA de personnes fictives | OK sur le premium **avec mention** ; privilégier visuels non-humains ou ta propre image pour la marque blvck. |
| 9.3 | Banques musicales | Démarrer gratuit sûr (YouTube Audio Library, Pixabay), passer à Epidemic/Artlist quand le volume le justifie. **Jamais** de musique non licenciée. |
| 9.4 | Verticaux sensibles (santé, finance, politique) | **Écarter au démarrage** — risque de conformité et de modération plateforme élevé. |
| 9.5 | Échec qualité client | Process : **régénération** (gratuite) → **refonte manuelle** → refund en dernier recours. À écrire dans les CGV. |

---

## Feuille de route

*Incrémentale, chaque slice livre quelque chose de testable.*

| Slice | État | Détail |
|---|---|---|
| 1 — Ingestion & clarification | ✅ **livré** | PDF → type détecté → Brief. Extracteur de cases BD (XY-cut, ordre de lecture LTR/RTL). |
| 2 — Storyboard multi-format | ✅ **livré** | Brief + document → storyboard JSON, multi-format 9:16/1:1/16:9. Testé : rapport 5 shots, BD 10 cases dans l'ordre de lecture. |
| **3 — Rendu Remotion vertical + templates** | 🟡 **maintenant** | Premier MP4 9:16 : texte animé, Ken Burns sur pages/cases, sous-titres, watermark, template par pôle. Introduit le champ `tier` et le compteur de coût dès ce slice. |
| 4 — Voix off + musique | ⏳ à venir | Kokoro (FR/EN) gratuit sur le tier free, ElevenLabs uniquement sur le tier premium, coût tracé par job. |
| 5 — Review humaine + contrat Griot | ⏳ à venir | File d'approbation + export multi-format + **manifeste JSON de sortie** (webhook) que Griot consommera quand il sera prêt. |
| 6 — Intégration Griot effective | ⏳ à venir | Une fois Griot opérationnel : câblage n8n + queue de publication + boucle de retour sur les performances. |

> **Reco** — On enchaîne sur le **Slice 3 — rendu Remotion**. C'est là qu'apparaît le premier vrai MP4 et qu'on introduit le champ `tier` et le compteur de coût dès la fondation, pour ne pas les rétro-fitter plus tard.

---

## Journal des décisions

*Évolutions du blueprint au fil des clarifications.*

| Version | Ce qui change |
|---|---|
| **v1** | Stack hybride, vertical prioritaire, validation humaine, deux tiers. Découpage en 6 slices. |
| **v1.1** | Volume < 20/sem confirmé → **1 worker**. Budget fixe blvckU = **0 $** → cœur 100 % gratuit obligatoire. Modèle **pay-as-you-serve** pour le premium → introduction du champ `tier` et d'un **compteur de coût par job** dès le Slice 3. Griot en PoC → **contrat de sortie standardisé** préparé au Slice 5. |

---

*Blueprint blvckUnlimited · note d'architecture v1.1 · document de travail interne.*
*Les points marqués « À toi » attendent tes réponses pour figer le dimensionnement et la tarification. Le reste est prêt à être construit.*
