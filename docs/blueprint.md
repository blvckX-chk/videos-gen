# Le moteur vidéo blvckUnlimited

> **Note d'architecture · v1.3** — 30 août 2026
> Comment le système `videos-gen` s'articule en moteur de production central — du brief client au fichier prêt à publier — et réponses, section par section, au questionnaire de cadrage.

- **Établi pour** : blvckUnlimited · Cotonou
- **Périmètre** : ComeUp · Community management · Pôles internes
- **Statut** : 6 modules livrés · roadmap v1.2 recadrée

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
| Filigrane | **Forcé sur gratuit** | Retirable : admin + premium seulement |
| Qualité auto | **Vérification (QC)** | Contrôles avant la review humaine |
| Review | **Avec recommandations** | Demande de modif → régénération |
| Charte client | **Proposée si absente** | Génération après clarification |

---

## ★ Bilan v1.2 — ce qui est réellement construit

Le blueprint v1.1 décrivait un pipeline PDF→vidéo en 6 slices. Depuis, le projet a **changé de nature** : c'est devenu un **moteur créatif multi-modal** piloté par un super-agent. Trois modules majeurs non prévus ont été livrés.

| Module | Livré | Rôle |
|---|---|---|
| Ingestion + clarification | ✅ | PDF → type → Brief. Cases BD (XY-cut, ordre de lecture). |
| Storyboard | ✅ | Brief + doc → plan multi-format 9:16/1:1/16:9. |
| Rendu Remotion | ✅ | Storyboard → MP4 vertical. `tier` + compteur de coût. |
| Audio toolkit | ✅ | Extraire / séparer voix-musique (Demucs) / remuxer. Bibliothèque. |
| Graphic Design | ✅ | Composer + 4 templates + providers image + retrait de fond. |
| Super-agent unifié | ✅ | Intention → campagne mixte (Reel + posts + stories + thumbnails). |

> **Insight** — Le **super-agent est désormais le sommet du système**. Règle d'architecture : toute nouvelle capacité bas niveau doit devenir « plannable » par l'agent.

## ! Gaps senior

| # | Gap | Impact |
|---|---|---|
| 1 | **Les Reels sont muets** | Bloqueur UX — contenu sans son mort à la publication. → Slice 4. |
| 2 | **Qualité non vérifiée** | Bloqueur confiance — rien ne détecte un visuel raté (texte coupé, « 2025. »). → Slice 6. |
| 3 | **Aucune notion de client / rôle** | Bloqueur commercial — tout sort en charte blvckU, pas de filigrane différencié ni de limites. → Slices 5 & 8. |
| 4 | **Aucune persistance** | Bloqueur opérationnel — un redémarrage perd tout l'état. → Slice 7. |
| 5 | **Pas de review partagée** | Plan éditable oui, mais pas d'inbox globale d'approbation. → Slice 8. |

> **Honnêteté** — La vérification **détecte les échecs, elle ne crée pas la qualité**. Les derniers visuels décevants venaient de données de test pauvres (PDF synthétique → « 2025. ») ET d'un besoin de polissage des templates. Le QC attrape les ratés flagrants ; la finition des templates reste un chantier continu.

## § Rôles, filigrane & limites

Deux axes distincts : le **rôle** (droits & limites) et le **tier de coût** (quels providers). Le rôle contraint le tier.

| Rôle | Filigrane blvckUnlimited | Limites | Providers |
|---|---|---|---|
| **admin** (toi) | Retirable (commandes freelance) | Aucune | Tous (free + premium) |
| **premium** | Contrôlé — retirable / remplaçable par sa charte (contrôles à définir) | Élevées | Free + premium (pay-as-you-serve) |
| **free** | **Forcé, non-retirable** | Quota (générations/jour), pas de batch, résolution plafonnée | Gratuits uniquement |

- **Filigrane forcé côté rendu** — appliqué au niveau du service (rendu vidéo + composer image), pas dans l'UI : un rôle `free` ne peut **techniquement** pas produire un livrable sans filigrane.
- **Entitlements dérivés du rôle** — `{watermark_removable, daily_quota, max_resolution, batch_allowed, allowed_tier}` vérifiés à chaque job.
- **Contrôles premium à définir** — probablement : retrait filigrane, filigrane personnalisé, file prioritaire, HD, providers premium facturés.

> **À toi** — Précise les **quotas gratuits** (ex. 5 générations/jour ?) et la **liste des contrôles premium**. Ossature au Slice 5 ; auth complète avec la persistance (Slice 7).

## ✓ Vérification & review

**1. Vérification qualité automatique (QC)** — avant la review humaine. Chaque contrôle produit des drapeaux ; sous un seuil, le livrable est marqué « à revoir » et peut être régénéré automatiquement.

| Contrôle | Sur | Détecte |
|---|---|---|
| Débordement / troncature de texte | images | texte hors cadre |
| Cadre quasi-vide | images | composition ratée, layer manquant |
| Contraste texte/fond | images | texte illisible (WCAG) |
| Cohérence des données | templates | chiffre absurde, champ vide, placeholder resté |
| Présence de piste audio | vidéos | Reel muet (gap #1) |
| Durée & résolution | vidéos | trop court/long, mauvais ratio |
| Filigrane présent | tous (free) | livrable gratuit sans watermark |

**2. Review humaine avec recommandations** — inbox globale, trois actions :
- **Approuver** → validé, prêt pour Griot.
- **Demander une modification** → recommandation en langage naturel (« agrandis le titre », « le chiffre est faux ») qui repart dans l'agent/générateur → **régénération** → retour en review.
- **Rejeter** → écarté.

> **Reco** — La boucle **recommandation → régénération** est le vrai levier qualité. Les drapeaux du QC pré-remplissent des recommandations pour valider plus vite.

## ◆ Charte client

Chaque client/pôle porte une **charte** (palette, logo, police, ton, filigrane). Deux entrées :
- **Charte fournie** — formulaire d'onboarding ou kit importé.
- **Charte proposée** — si absente, le système en **génère une après clarification** : quelques questions (secteur, ambiance, 2-3 marques de référence, public) → l'agent propose **2-3 pistes** (palettes harmonisées + polices + ton) que le client choisit. La charte retenue devient la `palette` propagée dans templates + storyboard.

> **Synergie** — Réutilise les **palettes par pôle** déjà en place. Génération basée sur des **règles d'harmonie** (couleurs analogues/complémentaires, contraste AA) — déterministe et gratuit — enrichie par le LLM pour le ton.

## ⊕ Agence 360° — les 7 piliers

Point senior honnête : le système est un **moteur de production multi-modal de niveau agence**. Mais une agence 360° couvre toute la chaîne, de la stratégie amont à la mesure aval. On excelle sur **1 pilier**, partiels sur **2**, il en manque **4**.

| # | Pilier | Couvre | État |
|---|---|---|---|
| 1 | **Insight & Stratégie** | recherche, personas, positionnement, angle, plan média | ❌ manquant |
| 2 | **Créa & Copywriting** | concept, DA, accroches, CTA, copy par plateforme | 🟡 partiel |
| 3 | **Production** | vidéo, image, audio, motion, print | ✅ fort |
| 4 | **Distribution** | publication, planning, multi-plateforme | 🟡 planifié |
| 5 | **Média payant** | achat d'espace, budgets, ciblage, enchères | ❌ manquant |
| 6 | **Mesure** | tracking, attribution, reporting, ROI | ❌ manquant |
| 7 | **Optimisation** | A/B, boucle d'apprentissage sur les perfs | ❌ manquant |

**Les 4 vrais manques :**
- **Stratégie** — on produit depuis un document, pas depuis un **objectif business** (audience, angle, plan de canaux). → Slice 7.
- **Copywriting publicitaire** — pas d'accroche scroll-stop + corps + CTA, ni de copy natif par plateforme, ni d'A/B. Manque le plus facile (LLM, ~0 coût), fort impact. → Slice 6.
- **Média payant** — aucune connexion Ads Manager. Lourd (argent réel, conformité). → optionnel.
- **Mesure + Optimisation** — on ne sait pas **ce qui marche**. C'est *le* cœur du 360° (produire → publier → mesurer → réapprendre). Dépend de Griot. → Slice 12.

> **Reco** — Fort levier immédiat : **copywriting** (Slice 6) + **stratégie légère** (Slice 7), branchés sur le super-agent. Le vrai cap 360° reste la **boucle de mesure** (Slice 12), possible une fois Griot en place. Le **média payant** est optionnel (beaucoup de clients gèrent leur budget).
>
> **Élargissement production** (continu, briques déjà là) : bannières display multi-tailles, pubs audio/radio, landing pages, carrousels.

---

## Sommaire

- [★ Bilan v1.2 — le construit](#-bilan-v12--ce-qui-est-réellement-construit)
- [! Gaps senior](#-gaps-senior)
- [§ Rôles, filigrane & limites](#-rôles-filigrane--limites)
- [✓ Vérification & review](#-vérification--review)
- [◆ Charte client](#-charte-client)
- [⊕ Agence 360° — les 7 piliers](#-agence-360--les-7-piliers)
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
| 1–3 — Ingestion · Storyboard · Rendu Remotion | ✅ **livré** | PDF → Brief → storyboard multi-format → MP4 vertical. Cases BD, `tier`, compteur de coût. |
| Audio toolkit | ✅ **livré** | Extraire / séparer (Demucs) / remuxer. Bibliothèque partagée. |
| Graphic Design + super-agent unifié | ✅ **livré** | Composer, 4 templates, providers image, retrait de fond ; agent campagne mixte. |
| 4 — Voix off + sous-titres + musique | ✅ **livré** | Post-production ffmpeg : TTS (espeak/Kokoro/ElevenLabs) aligné par shot + SRT déterministe incrusté + musique atténuée. |
| **5 — Identité : rôles + chartes** | 🟡 **maintenant** | Rôles admin/premium/free + entitlements + filigrane forcé côté rendu. Chartes (fournie ou **proposée après clarification**) propagées. |
| 6 — Copywriting `[360° · pilier 2]` | ⏳ nouveau | Accroche + corps + CTA + hashtags **par plateforme**, variantes A/B, depuis brief/document. LLM, quasi gratuit. |
| 7 — Stratégie `[360° · pilier 1]` | ⏳ nouveau | Objectif business → persona → angle → plan de canaux, qui **pilote** la campagne. |
| 8 — Vérification qualité (QC) | ⏳ à venir | Contrôles auto (texte tronqué, cadre vide, contraste, données absurdes, audio absent, filigrane) → drapeaux + régénération. |
| 9 — Persistance + file | ⏳ à venir | SQLite (documents, briefs, campagnes, assets, jobs, comptes) + file arq. Ne plus rien perdre. |
| 10 — Review queue + recommandations | ⏳ à venir | Inbox globale : approuver / **demander une modif → régénération** / rejeter. + dashboard coûts par client. |
| 11 — Distribution : contrat Griot + intégration | ⏳ à venir | Manifeste JSON de sortie (webhook) ; puis câblage n8n effectif quand Griot est prêt. |
| 12 — Mesure & optimisation `[360° · piliers 6-7]` | ⏳ nouveau | Métriques via Griot (vues, clics, conversions) → dashboard client + **boucle d'apprentissage**. Le vrai cap 360°. |
| Média payant `[360° · pilier 5]` | ⏳ optionnel | Connecteur Meta/TikTok/Google Ads. Lourd, argent réel, conformité. Selon demande. |

> **Reco d'ordre** — On enchaîne **5 → 6 → 7** : **5** = commercialisation (onboarder + protéger le free), **6** = copywriting (fort levier, quasi gratuit, comble le pilier 2), **7** = stratégie (comble le pilier 1). Puis QC/persistance/review consolident, et la **mesure (12)** ferme la boucle 360° une fois Griot en place.

---

## Journal des décisions

*Évolutions du blueprint au fil des clarifications.*

| Version | Ce qui change |
|---|---|
| **v1** | Stack hybride, vertical prioritaire, validation humaine, deux tiers. Découpage en 6 slices. |
| **v1.1** | Volume < 20/sem confirmé → **1 worker**. Budget fixe blvckU = **0 $** → cœur 100 % gratuit obligatoire. Modèle **pay-as-you-serve** pour le premium → introduction du champ `tier` et d'un **compteur de coût par job** dès le Slice 3. Griot en PoC → **contrat de sortie standardisé** préparé au Slice 5. |
| **v1.2** | **Pivot super-agent créatif** : 3 modules non prévus livrés (audio, design, super-agent unifié) → l'agent devient le sommet. **5 gaps senior** identifiés. Nouvelles exigences : **rôles** admin/premium/free + **filigrane forcé** côté rendu sur le gratuit + **quotas** ; **vérification qualité** avant review ; **review avec recommandations** → régénération ; **charte client proposée** si absente. Roadmap ré-ordonnée 4→5→6→7→8→9. |
| **v1.3** | **Cap agence 360°** : Slice 4 (voix + sous-titres) livré. Analyse des **7 piliers** → production forte, manquent l'amont (stratégie, copy) et l'aval (mesure, optimisation, média payant). Nouveaux slices : **Copywriting** (6), **Stratégie** (7), **Mesure & optimisation** (12). Média payant optionnel. Roadmap étendue à 12 slices. |

---

*Blueprint blvckUnlimited · note d'architecture v1.1 · document de travail interne.*
*Les points marqués « À toi » attendent tes réponses pour figer le dimensionnement et la tarification. Le reste est prêt à être construit.*
