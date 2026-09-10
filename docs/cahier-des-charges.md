# KORA — Cahier des charges

### Le moteur créatif augmenté par IA de blvckUnlimited

> Agent de création publicitaire 360°, multi-modal et autonome — du brief à la campagne complète.

| | |
|---|---|
| **Nom de code (dépôt)** | `videos-gen` |
| **Nom produit proposé** | **KORA** *(voir Annexe A — Naming)* |
| **Éditeur** | blvckUnlimited — Cotonou, Bénin |
| **Auteur du document** | Direction technique |
| **Version** | 1.0 — cadrage complet |
| **Date** | 10 septembre 2026 |
| **Statut** | Référence produit — supersède le blueprint v1.3 |
| **Confidentialité** | Interne blvckUnlimited |

---

## Sommaire

1. Résumé exécutif
2. Vision & philosophie « IA augmentée »
3. Problème & opportunité
4. Marché & concurrence (analyse honnête)
5. Proposition de valeur & avantages défendables (moat)
6. Périmètre : ce que KORA fait / ne fait pas (frontière Griot)
7. Personas & cas d'usage
8. Les 5 niveaux d'autonomie créative
9. Exigences fonctionnelles (EF)
10. Innovations & différenciateurs IA
11. Exigences non-fonctionnelles (ENF)
12. Architecture technique
13. Rôles, filigrane & entitlements
14. Vérification qualité & review
15. Modèle économique
16. Interconnexion écosystème (Griot, pôles, Academy)
17. Roadmap & piliers 360°
18. Risques & mitigations
19. Conformité, éthique & légal
20. KPIs & critères d'acceptation
21. Glossaire
22. Annexes (Naming, hypothèses ouvertes)

---

## 1. Résumé exécutif

**KORA** est un **agent de création publicitaire 360° augmenté par IA** : à partir d'un simple brief — ou d'un document (PDF, BD, présentation) — il conçoit, produit et assemble une **campagne complète multi-modale** (vidéos verticales, posts, stories, carrousels, affiches, voix off, sous-titres, musique), le tout dans la charte du client et prêt à publier.

Là où le marché offre des dizaines d'outils spécialisés (un pour la vidéo, un pour le design, un pour la voix, un pour le copywriting), KORA **orchestre toute la chaîne en un seul agent**, avec un humain qui garde le contrôle du jugement (« IA augmentée »).

Le système est pensé **cœur 100 % gratuit** (open-source auto-hébergé) pour le volume, avec un **rail premium à l'usage** (répercuté au client) pour la qualité haut de gamme. Il est conçu **pour le marché africain francophone d'abord** (Bénin, Afrique de l'Ouest), avec une attention aux contraintes locales (bande passante, langues, coût), tout en restant globalement exportable.

KORA est le **moteur de production** ; il s'interconnecte avec **Griot**, l'agent de distribution/SMM, à qui il livre des campagnes prêtes à diffuser et de qui il reçoit les données de performance qui nourrissent sa boucle d'apprentissage.

**Ambition** : devenir la référence mondiale de l'« agence-dans-une-boîte » augmentée par IA — la meilleure startup de son domaine du 21ᵉ siècle.

---

## 2. Vision & philosophie « IA augmentée »

KORA n'est pas un outil qui remplace le créatif : c'est un **studio augmenté** où l'IA fait le volume et l'humain garde le jugement.

**Cinq principes directeurs :**

1. **L'humain décide, l'IA exécute.** Chaque livrable passe par une validation humaine avec possibilité de recommander des modifications en langage naturel. L'automatisation totale se mérite, progressivement, quand la qualité est prouvée.
2. **Une équipe d'agents, pas un modèle unique.** La création est confiée à des agents spécialisés qui collaborent (stratège, copywriter, directeur artistique, monteur), pas à un seul prompt géant.
3. **Le système apprend.** Chaque campagne publiée, chaque retour de review, chaque métrique de performance rend l'agent plus juste pour le client concerné (mémoire de marque persistante).
4. **Gratuit par défaut, payant à la valeur.** Le cœur ne coûte rien ; le premium n'est activé que quand un client paie pour lui.
5. **Frugal et local.** Pensé pour tourner sur un VPS modeste, en basse bande passante, dans des langues et cultures que les incumbents ignorent.

> **IA augmentée = démultiplier un créatif humain par 100, pas le supprimer.**

---

## 3. Problème & opportunité

**Le problème.** Produire du contenu publicitaire cohérent, à volume, sur tous les formats et toutes les plateformes, est **lent, cher et fragmenté**. Une PME, un coach, un e-commerçant ou un freelance doit jongler entre un monteur, un graphiste, un rédacteur, un community manager — ou entre 6 abonnements SaaS qui ne se parlent pas. En Afrique francophone, l'accès à ces compétences est encore plus rare et coûteux.

**L'opportunité.** L'IA générative a atteint un niveau où chaque brique (image, vidéo, voix, texte) est produisible automatiquement. Mais **personne n'a industrialisé l'orchestration de bout en bout** — de la stratégie à la mesure — dans un seul agent, à un coût quasi nul, adapté aux marchés émergents. C'est la fenêtre que KORA vise.

**Timing.** Modèles open-source matures (rendu, TTS, séparation audio, génération d'image gratuite), coût de calcul en chute, explosion de la demande de contenu court sur les réseaux, et une économie freelance (ComeUp, Fiverr) en pleine croissance en Afrique.

---

## 4. Marché & concurrence — analyse honnête

**Réponse directe à la question « y a-t-il peu de concurrence ? » : non, le domaine est très disputé — mais pas là où KORA se positionne.**

La concurrence est **féroce sur chaque brique isolée**, et **mince sur l'intégration + la localisation**.

**Concurrents par brique (non exhaustif) :**

| Domaine | Acteurs |
|---|---|
| Génération vidéo | Runway, Pika, Luma, HeyGen, Synthesia |
| Design / visuels | Canva Magic Studio, Adobe Firefly/Express, AdCreative.ai |
| Voix / audio | ElevenLabs, Descript |
| Copywriting | Jasper, Copy.ai |
| Contenu social « tout-en-un » | invideo AI, Predis.ai, Ocoya, Simplified, Creatify, Arcads |

**Ce qui reste peu couvert — l'espace de KORA :**

1. **L'orchestration 360° réellement de bout en bout** : de la stratégie → copy → production multi-modale → distribution → mesure, en **un agent unique et cohérent**. La plupart des outils ne font qu'une tranche ; l'utilisateur reste l'intégrateur.
2. **Le point d'entrée « document » **: PDF / rapport / BD → campagne. Quasi personne ne part d'un document structuré.
3. **La localisation africaine francophone** : marché, langues, accents, codes culturels, contraintes de bande passante, modèle de coût adapté. Les incumbents sont US/EU-centrés et chers en devises fortes.
4. **Le modèle économique frugal** : cœur gratuit auto-hébergé + premium répercuté. Les SaaS facturent un abonnement fixe en USD, prohibitif localement.
5. **L'écosystème intégré** (KORA ↔ Griot ↔ pôles ↔ Academy) : un système, pas un abonnement de plus.

> **Verdict senior : la bataille est perdue d'avance sur « le meilleur générateur de vidéo » (les labs frontières gagneront toujours). Elle est gagnable sur « le meilleur assembleur autonome, localisé et frugal ». Le moat n'est pas un modèle — c'est l'orchestration, la localisation et l'écosystème.**

---

## 5. Proposition de valeur & avantages défendables (moat)

**Promesse client :** *« Un brief. Une campagne complète. En quelques minutes. À ta charte. Prête à publier. »*

**Avantages défendables (dans l'ordre de solidité) :**

1. **Orchestration multi-agents propriétaire** — la logique qui transforme une intention en plan multi-modal cohérent est le vrai actif ; difficile à copier, s'améliore avec l'usage.
2. **Mémoire de marque (Brand Brain)** — plus un client reste, plus KORA connaît sa voix, ses codes, ce qui performe. Coût de départ croissant (lock-in positif).
3. **Localisation profonde** — langues, accents, références culturelles africaines : barrière que les incumbents ne franchiront pas rapidement.
4. **Structure de coût** — cœur gratuit → marges impossibles à égaler pour un SaaS à coûts fixes.
5. **Écosystème** — interconnexion KORA ↔ Griot ↔ pôles : la valeur augmente avec chaque brique.
6. **Boucle d'apprentissage** — la mesure des performances réelles rend l'agent meilleur que tout outil « aveugle » qui ne sait pas ce qui a marché.

---

## 6. Périmètre — ce que KORA fait / ne fait pas

### 6.1 Dans le périmètre de KORA

KORA est le **moteur de création et de production**. Il couvre :

- Ingestion et compréhension du brief / document.
- Stratégie créative (objectif → audience → angle → plan de canaux).
- Copywriting (accroches, corps, CTA, variantes A/B) au niveau **création**.
- Production multi-modale : vidéo, image, audio, voix off, sous-titres, musique, print.
- Application de la charte de marque.
- Vérification qualité automatique + review humaine avec recommandations.
- Empaquetage des livrables en un **manifeste de publication** par plateforme (fichiers formatés + copy suggéré + métadonnées).
- Consommation des données de performance (venant de Griot) pour la boucle d'optimisation.

### 6.2 Hors périmètre KORA — délégué à Griot *(à confirmer avec toi)*

Conformément à ta consigne, les fonctions suivantes ne sont **pas** développées dans KORA car elles relèvent de **Griot** (agent SMM / distribution) — à qui elles reviennent mieux :

| Fonction | Pourquoi Griot |
|---|---|
| **Publication & planification** (calendrier, mise en ligne) | Griot détient les connexions aux plateformes et la logique de calendrier. |
| **Adaptation finale de la caption/hashtags au moment du post** | KORA *crée* le copy ; Griot l'*ajuste et le poste* selon les codes de chaque plateforme. |
| **Community management** (réponses aux commentaires, DM, modération) | Relationnel temps réel = domaine de Griot. |
| **Collecte brute des métriques plateformes** (vues, likes, clics) | Griot est connecté aux API ; il transmet les données à KORA. |

**Zone grise à trancher (2 questions ouvertes — voir Annexe B) :** l'**intelligence d'analyse/optimisation** (KORA la garde, Griot fournit la donnée brute) et le **média payant** (Griot ? module dédié ? à définir).

> **Principe d'interconnexion : KORA produit et empaquette → Griot diffuse et écoute → KORA apprend. Boucle fermée, responsabilités nettes.**

---

## 7. Personas & cas d'usage

**P1 — Toi, l'admin/opérateur.** Exécute des commandes freelance (ComeUp), gère les pôles internes. A besoin de volume, de rapidité, du retrait de filigrane, d'aucune limite.

**P2 — Le client premium.** Paie à la vidéo ou par abonnement. Veut sa charte, la qualité premium (voix ElevenLabs, HD), le filigrane retiré ou remplacé par le sien.

**P3 — L'utilisateur gratuit.** Teste le produit. Filigrane blvckUnlimited forcé, quotas, providers gratuits uniquement. Canal d'acquisition.

**P4 — Les pôles internes** (BlvckStore, BlvckForge, BlvckArt, BlvckPrince, Unlimited Academy). Chartes strictes par pôle, contenu régulier.

**Cas d'usage clés :**

- **UC1** — « Transforme ce rapport PDF en campagne de 5 visuels + 1 Reel. »
- **UC2** — « Anime cette BD en motion comic vertical avec voix off. »
- **UC3** — « Fais-moi 30 posts pour ce client e-commerce ce mois (batch). »
- **UC4** — « Ce client n'a pas de charte : propose-lui-en une. »
- **UC5** — « Décline ce visuel en carré, story et thumbnail YouTube. »
- **UC6** — « Récupère l'audio tendance, enlève la voix, colle la musique sur ma vidéo. »
- **UC7** — « Prépare la campagne complète et envoie-la à Griot pour publication. »

---

## 8. Les 5 niveaux d'autonomie créative

Cadre directeur (inspiré des niveaux de conduite autonome) qui structure la montée en confiance :

| Niveau | Nom | L'humain… | L'IA… |
|---|---|---|---|
| **L0** | Manuel assisté | fait tout | suggère |
| **L1** | Brique par brique | pilote chaque étape | exécute une brique (générer, composer) |
| **L2** | Campagne proposée | valide un plan, édite | planifie et produit la campagne entière ← **état actuel** |
| **L3** | Campagne + auto-QC | valide le résultat vérifié | produit, vérifie, régénère les ratés |
| **L4** | Autonomie supervisée | fixe des garde-fous, audite | produit et publie (via Griot) sous règles |
| **L5** | Autonomie complète | définit la stratégie annuelle | opère la marque en continu, apprend, optimise |

**KORA vise L3 à court terme, L4 avec Griot, L5 comme horizon.**

---

## 9. Exigences fonctionnelles (EF)

> Convention : `EF-<module>-<n>`. Priorité : **P1** (indispensable), **P2** (important), **P3** (souhaitable).

### 9.1 Ingestion & compréhension

- **EF-ING-1** (P1) Accepter un PDF (rapport, présentation, article, BD) jusqu'à 40 Mo.
- **EF-ING-2** (P1) Détecter automatiquement le type de document (rapport, slides, scientifique, BD, mixte) avec indice de confiance.
- **EF-ING-3** (P1) Extraire texte, structure, images et statistiques par page.
- **EF-ING-4** (P1) Pour les BD : segmenter les cases (panels) et calculer l'ordre de lecture (LTR occidental / RTL manga).
- **EF-ING-5** (P2) Accepter un brief libre (texte) sans document.
- **EF-ING-6** (P2) Accepter des rushes fournis par le client (vidéo, image, audio) comme matière première.
- **EF-ING-7** (P3) Extraire les points clés et chiffres marquants pour alimenter les livrables.

### 9.2 Clarification & brief

- **EF-BRF-1** (P1) Poser un questionnaire **adaptatif** au type de document/intention pour cadrer objectif, audience, ton, durée, langue.
- **EF-BRF-2** (P1) Produire un objet **Brief** typé, contrat de toute la production.
- **EF-BRF-3** (P2) Mode LLM (qualité) avec repli déterministe gratuit garanti.

### 9.3 Stratégie *(pilier 360° n°1 — à construire)*

- **EF-STR-1** (P1) À partir d'un objectif business, dériver **audience/persona**, **angle** créatif, **plan de canaux** recommandé.
- **EF-STR-2** (P2) Proposer un calendrier éditorial de haut niveau (cadence, mix de formats).
- **EF-STR-3** (P2) Justifier chaque recommandation (traçabilité) pour la validation humaine.

### 9.4 Copywriting *(pilier 360° n°2 — à construire)*

- **EF-COP-1** (P1) Générer accroche (scroll-stop), corps, et **CTA** par livrable.
- **EF-COP-2** (P1) Produire du copy **natif par plateforme** (TikTok ≠ LinkedIn ≠ pub Meta).
- **EF-COP-3** (P1) Générer des **variantes A/B** du copy.
- **EF-COP-4** (P2) Générer les hashtags candidats *(l'ajustement final au post reste à Griot)*.
- **EF-COP-5** (P2) Respecter la voix de marque (Brand Brain) du client.

### 9.5 Storyboard & vidéo

- **EF-VID-1** (P1) Générer un storyboard multi-format (9:16 prioritaire, 1:1, 16:9) depuis Brief + document.
- **EF-VID-2** (P1) Rendre une vidéo MP4 verticale : texte animé, Ken Burns sur pages/cases, transitions, template par pôle, filigrane.
- **EF-VID-3** (P1) Motion comic : une case par plan, dans l'ordre de lecture.
- **EF-VID-4** (P1) Ajouter voix off (TTS), sous-titres synchronisés, musique de fond atténuée.
- **EF-VID-5** (P2) B-roll génératif optionnel (décor IA) sur les plans sans contenu factuel.
- **EF-VID-6** (P3) Version longue (YouTube) avec chapitrage.

### 9.6 Audio

- **EF-AUD-1** (P1) Extraire la piste audio d'une vidéo.
- **EF-AUD-2** (P1) Séparer voix / musique (isolation de stems).
- **EF-AUD-3** (P1) Remixer : remplacer, mixer (ducking) ou supprimer une piste d'une vidéo.
- **EF-AUD-4** (P1) Bibliothèque de clips audio réutilisables.
- **EF-AUD-5** (P2) Voix off premium avec accent africain francophone (rail payant).

### 9.7 Design graphique

- **EF-DSG-1** (P1) Générer des images (providers gratuits par défaut, premium en option).
- **EF-DSG-2** (P1) Composer des visuels par templates (citation, chiffre-clé, résumé, produit, +).
- **EF-DSG-3** (P1) Décliner un visuel en plusieurs formats (recadrage intelligent, règle des tiers).
- **EF-DSG-4** (P1) Retrait de fond, overlays (logo, texte, filtres), coins arrondis, dégradés.
- **EF-DSG-5** (P1) Filigrane appliqué selon le rôle (voir §13).
- **EF-DSG-6** (P2) Bannières display multi-tailles, carrousels, formats print (A4).

### 9.8 Super-agent (campagne)

- **EF-AGT-1** (P1) À partir d'une intention + document, planifier une **campagne mixte** (vidéo + images + audio).
- **EF-AGT-2** (P1) Plan **éditable** avant exécution (retirer/ajouter/modifier une étape).
- **EF-AGT-3** (P1) Exécution **tolérante aux échecs partiels** (statut « partiel » + erreurs listées).
- **EF-AGT-4** (P1) Respecter la charte du client sur tous les livrables d'une campagne.
- **EF-AGT-5** (P2) Toute nouvelle capacité bas niveau devient automatiquement plannable par l'agent.

### 9.9 Charte de marque

- **EF-CHT-1** (P1) Importer une charte fournie (couleurs, logo, police, ton, filigrane).
- **EF-CHT-2** (P1) **Proposer 2-3 pistes de charte après clarification** si le client n'en a pas.
- **EF-CHT-3** (P1) Propager la charte retenue dans design **et** storyboard.
- **EF-CHT-4** (P2) Chartes strictes par pôle interne.

### 9.10 Vérification qualité (QC)

- **EF-QC-1** (P1) Détecter texte tronqué/débordant, cadre quasi-vide, contraste insuffisant.
- **EF-QC-2** (P1) Détecter incohérence de données (chiffre absurde, champ vide, placeholder resté).
- **EF-QC-3** (P1) Vérifier présence de piste audio sur les vidéos (anti-Reel muet).
- **EF-QC-4** (P1) Vérifier durée/résolution/ratio.
- **EF-QC-5** (P1) Vérifier présence du filigrane sur tout livrable gratuit (sécurité).
- **EF-QC-6** (P2) Régénérer automatiquement un livrable sous le seuil de qualité.

### 9.11 Review humaine

- **EF-REV-1** (P1) Inbox globale des livrables en attente, traversant toutes les campagnes.
- **EF-REV-2** (P1) Trois actions : **approuver**, **demander une modification** (recommandation en langage naturel → régénération), **rejeter**.
- **EF-REV-3** (P2) Les drapeaux QC pré-remplissent des recommandations.
- **EF-REV-4** (P2) Historique des versions d'un livrable.

### 9.12 Empaquetage & remise à Griot

- **EF-PKG-1** (P1) Produire un **manifeste de publication** par plateforme (chemins des fichiers formatés, copy suggéré, hashtags candidats, moment conseillé).
- **EF-PKG-2** (P1) Exposer ce manifeste via **webhook** consommable par Griot.
- **EF-PKG-3** (P2) Recevoir en retour les métriques de performance depuis Griot.

### 9.13 Mesure & optimisation *(pilier 360° n°6-7 — dépend de Griot)*

- **EF-MES-1** (P2) Stocker et agréger les métriques par campagne, client, période.
- **EF-MES-2** (P2) Tableau de bord de performance par client.
- **EF-MES-3** (P3) **Boucle d'apprentissage** : identifier ce qui performe et le réinjecter dans la stratégie et le copy.

---

## 10. Innovations & différenciateurs IA

Ce qui doit faire de KORA la référence du 21ᵉ siècle — au-delà du simple assemblage.

1. **Équipe créative multi-agents.** Des agents spécialisés (Stratège, Copywriter, Directeur Artistique, Monteur, Contrôleur Qualité) qui collaborent et se critiquent, plutôt qu'un prompt unique. Chaque agent est remplaçable/améliorable indépendamment.
2. **Brand Brain — mémoire de marque persistante.** Pour chaque client, KORA accumule voix, codes visuels, préférences validées et ce qui a performé. La marque devient de plus en plus « elle-même » au fil du temps. Actif défendable majeur.
3. **Boucle de performance auto-apprenante.** Les résultats réels (via Griot) réorientent automatiquement les futures campagnes vers les formats/angles gagnants — bandit d'optimisation, A/B systématique.
4. **Planification consciente du coût.** L'agent optimise la qualité **sous contrainte de budget** : il choisit gratuit vs premium en fonction du tier, et sait dire « voici le meilleur possible pour ce budget ».
5. **Localisation culturelle, pas seulement traduction.** Adaptation des références, de l'humour, des accents (français d'Afrique de l'Ouest), des codes visuels — pas un simple `translate()`.
6. **Mode basse bande passante / offline-first.** Rendu côté serveur, livrables légers, tolérance aux connexions instables (Cotonou et au-delà) — pensé comme une **fonctionnalité**, pas une contrainte subie.
7. **Provenance & confiance.** Traçabilité de chaque livrable (quel agent, quel provider, quel coût) et perspective **Content Credentials (C2PA)** pour marquer l'origine IA de façon vérifiable — anticipe la régulation.
8. **Génération pilotée par gabarit déterministe + IA.** Le contenu factuel (texte, chiffres, cases réelles) est rendu **fidèlement** par gabarit ; l'IA générative ne sert qu'au décor. Zéro hallucination sur les données du client.
9. **Recommandations de modification en langage naturel.** La review n'est pas binaire : « agrandis le titre », « le fond trop clair » → régénération ciblée. L'humain dirige comme un directeur de création.
10. **Une intention → une campagne complète.** Le vrai saut : passer d'« un outil par tâche » à « un agent par objectif ».

---

## 11. Exigences non-fonctionnelles (ENF)

- **ENF-PERF-1** (P1) Le rendu vidéo tourne côté serveur (VPS), jamais sur la machine de l'opérateur.
- **ENF-PERF-2** (P2) Mode **batch** (produire 20-30 livrables d'un coup), traitement nocturne pour lisser la charge.
- **ENF-PERF-3** (P2) Cible volume de départ : < 20 vidéos/semaine, 1 worker suffisant ; architecture prête à scaler (file de tâches) au palier ~50/semaine.
- **ENF-COUT-1** (P1) Cœur **100 % gratuit** obligatoire (aucun coût fixe sur le tier free).
- **ENF-COUT-2** (P1) Tout appel à un provider payant est **tracé** (coût par job, par client) et **répercuté** (pay-as-you-serve).
- **ENF-COUT-3** (P1) Un job `free` ne peut **techniquement pas** invoquer un provider payant (garde-fou au registre).
- **ENF-SEC-1** (P1) Rôles et entitlements vérifiés à chaque job (voir §13).
- **ENF-SEC-2** (P1) Filigrane appliqué **côté service** (rendu/composer), non contournable par l'UI.
- **ENF-SEC-3** (P2) Données client (PDF, rushes) potentiellement sensibles → politique de rétention et purge ; chiffrement au repos en production.
- **ENF-FIA-1** (P1) Dégradation gracieuse : indisponibilité d'un provider → repli gratuit, jamais d'échec global d'une campagne.
- **ENF-FIA-2** (P2) Persistance : documents, briefs, campagnes, assets, jobs, comptes survivent à un redémarrage.
- **ENF-I18N-1** (P1) FR & EN nativement (voix + sous-titres).
- **ENF-I18N-2** (P2) Fon & Yoruba : sous-titres et/ou voix humaine enregistrée *(pas de TTS fiable à ce jour — voir §18)*.
- **ENF-ACC-1** (P2) Sous-titres lisibles (contraste, taille), respect des bonnes pratiques d'accessibilité.
- **ENF-MAINT-1** (P1) Architecture modulaire à providers branchables (ajouter un moteur = un fichier + enregistrement).
- **ENF-OBS-1** (P2) Journalisation des jobs, coûts et échecs pour audit et tableau de bord.

---

## 12. Architecture technique

**Principe :** un **moteur modulaire** où chaque capacité est un module à providers branchables, coiffé par un **super-agent orchestrateur**.

```
        SOURCES                    MOTEUR KORA                      SORTIES
   ┌──────────────┐        ┌────────────────────────┐        ┌──────────────┐
   │ PDF / BD     │        │ Ingestion (+cases BD)  │        │ MP4 (Reels)  │
   │ Brief        │  ───▶  │ Clarification → Brief  │  ───▶  │ PNG (visuels)│
   │ Charte       │        │ Stratégie              │        │ Audio / stems│
   │ Rushes       │        │ Copywriting            │        │ Manifeste    │
   └──────────────┘        │ Storyboard → Rendu     │        │   de publi.  │
                           │ Audio / Design         │        └──────┬───────┘
                           │ QC + Review            │               │ webhook
                           │ ┌──────────────────┐   │               ▼
                           │ │  SUPER-AGENT     │   │        ┌──────────────┐
                           │ │  (campagne 360°) │   │        │    GRIOT     │
                           │ └──────────────────┘   │  ◀──── │  (SMM/diffu. │
                           └────────────────────────┘  perf │   + écoute)  │
                                                             └──────────────┘
```

**Stack cible :**

| Couche | Cœur (gratuit) | Premium (à l'usage) |
|---|---|---|
| Compréhension / stratégie / copy | LLM (avec repli déterministe) | LLM premium |
| Rendu vidéo | Remotion + FFmpeg | + effets |
| Voix off | eSpeak / Kokoro | ElevenLabs |
| Sous-titres | Génération déterministe (sans ASR) | idem |
| Séparation audio | Demucs | idem |
| Génération d'image | Pollinations (gratuit) | fal / Runway |
| Retrait de fond | rembg | idem |
| Orchestration écosystème | n8n (KORA ↔ Griot) | idem |
| Persistance | SQLite + file de tâches | Postgres au scale |

**Décisions d'architecture structurantes :**
- Champ **`tier`** (free/premium) et **compteur de coût** portés par chaque job.
- **Garde-fou providers** : refus d'un provider payant sur un job free.
- **Fidélité au document** : contenu factuel par gabarit déterministe, génératif réservé au décor.
- **Frontière Griot** nette via le manifeste de publication (webhook).

---

## 13. Rôles, filigrane & entitlements

Deux axes distincts : le **rôle** (droits & limites) et le **tier de coût** (providers). Le rôle **contraint** le tier.

| Rôle | Filigrane blvckUnlimited | Limites | Providers |
|---|---|---|---|
| **admin** (toi) | Retirable (commandes freelance) | Aucune | Tous |
| **premium** | Retirable / remplaçable par sa charte *(contrôles à définir)* | Élevées | Free + premium |
| **free** | **Forcé, non-retirable** | Quota (générations/jour), pas de batch, résolution plafonnée | Gratuits uniquement |

**Règles :**
- **EF-ROLE-1** (P1) Le filigrane est appliqué **côté rendu** ; un rôle `free` ne peut produire aucun livrable sans filigrane, même en trafiquant la requête.
- **EF-ROLE-2** (P1) Un objet **Entitlements** `{watermark_removable, daily_quota, max_resolution, batch_allowed, allowed_tier}` est dérivé du rôle et vérifié à chaque job.
- **EF-ROLE-3** (P2) Contrôles premium à préciser : retrait du filigrane, filigrane personnalisé (logo client), file prioritaire, formats HD, accès providers premium facturés.

> **À toi (voir Annexe B) :** valeurs exactes des quotas gratuits et liste finale des contrôles premium.

---

## 14. Vérification qualité & review

Deux filets successifs : **la machine attrape les ratés, l'humain valide le fond.**

1. **QC automatique** (§9.10) — score + drapeaux ; sous le seuil → « à revoir » + régénération possible.
2. **Review humaine** (§9.11) — inbox globale ; approuver / demander une modif (langage naturel → régénération) / rejeter.

> La boucle **recommandation → régénération** est le vrai levier qualité. Le QC ne *crée* pas la qualité : il attrape l'échec flagrant ; la finition des gabarits reste un chantier continu.

---

## 15. Modèle économique

**Structure à deux tiers + rôles :**

- **Gratuit (acquisition)** — cœur open-source, filigrane forcé, quotas. Convertit vers le premium.
- **Premium (valeur)** — à la vidéo ou par abonnement ; providers premium **répercutés** (pay-as-you-serve) ; filigrane retirable/custom ; HD, priorité.
- **Commandes freelance (admin)** — toi, sans limite ni filigrane, sur ComeUp et au-delà.
- **Interne (pôles)** — coût interne, chartes strictes.

**Principes :**
- Budget fixe blvckUnlimited de départ = **0 $** ; aucun coût récurrent tant qu'aucun client ne paie.
- Chaque appel premium est mesuré → **facturation reflète l'usage réel**.
- Grille tarifaire (montants) à fixer par la direction *(hors périmètre technique)*.

*Note : la stratégie de prix chiffrée et le go-to-market détaillé relèvent d'un document business séparé.*

---

## 16. Interconnexion écosystème

KORA n'est pas seul : il est le **moteur créatif** d'un écosystème.

- **KORA ↔ Griot** — KORA produit et empaquette (manifeste de publication) ; Griot diffuse, gère la communauté, écoute les performances et les renvoie à KORA. **Responsabilités nettes, boucle fermée.**
- **KORA ↔ Pôles** (BlvckStore, BlvckForge, BlvckArt, BlvckPrince) — chartes dédiées, contenu régulier.
- **KORA ↔ Unlimited Academy** — capsules pédagogiques.

**Contrat d'interconnexion (technique) :** manifeste JSON standard + webhooks, orchestrés via n8n. KORA et Griot restent **découplés** — chacun évolue sans casser l'autre.

---

## 17. Roadmap & piliers 360°

*(État : ✅ livré · 🟡 en cours · ⏳ à venir)*

| Slice | Pilier 360° | État |
|---|---|---|
| 1–3 Ingestion · Storyboard · Rendu | Production | ✅ |
| Audio toolkit · Design · Super-agent | Production | ✅ |
| 4 Voix off + sous-titres + musique | Production | ✅ |
| **5 Identité : rôles + filigrane + chartes** | Cross-cutting | 🟡 |
| 6 **Copywriting** (par plateforme, A/B) | Pilier 2 | ⏳ |
| 7 **Stratégie** (objectif→persona→angle→canaux) | Pilier 1 | ⏳ |
| 8 Vérification qualité (QC) | Confiance | ⏳ |
| 9 Persistance + file | Opérationnel | ⏳ |
| 10 Review + recommandations | Confiance | ⏳ |
| 11 Distribution : contrat Griot | Pilier 4 | ⏳ |
| 12 **Mesure & optimisation** | Piliers 6-7 | ⏳ |
| Média payant | Pilier 5 | ⏳ optionnel |

**Ordre recommandé : 5 → 6 → 7**, puis consolidation (8-10), puis la boucle 360° (11-12).

---

## 18. Risques & mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| **Course technologique** (les labs surpassent nos briques) | Élevé | Ne pas parier sur « le meilleur générateur » ; miser sur orchestration + localisation + écosystème. Providers branchables → adopter le meilleur du moment. |
| **Qualité perçue insuffisante** | Élevé | QC automatique + review humaine + finition continue des gabarits. |
| **Dépendance à un provider payant** | Moyen | Cœur gratuit toujours fonctionnel ; premium en repli optionnel. |
| **Fon/Yoruba sans TTS fiable** | Moyen | Sous-titres ou voix humaine ; ne pas promettre la synthèse. |
| **Perte de données / crash** | Moyen | Persistance (Slice 9) + sauvegardes. |
| **Conformité plateformes (label IA, shadowban)** | Moyen | Respecter le label AI-generated ; maximiser le rendu humain sans dissimuler. |
| **Bande passante Cotonou** | Moyen | Rendu serveur, livrables légers, mode offline-first. |
| **Frontière KORA/Griot floue** | Faible | Manifeste + webhooks ; responsabilités écrites (§6, §16). |

---

## 19. Conformité, éthique & légal

- **Label « AI-generated »** — respecté quand les plateformes l'imposent ; qualité, pas dissimulation.
- **Deepfakes** — pas d'avatar IA d'une personne réelle sans consentement ; visuels non-humains ou image propre privilégiés.
- **Droits musicaux** — uniquement musique licenciée/libre ; jamais de piste non licenciée.
- **Clauses IA au contrat client** — transparence, cession de droits sur le livrable, limite de responsabilité.
- **Verticaux sensibles** (santé, finance, politique) — écartés au démarrage.
- **Données personnelles** — rétention limitée, purge, chiffrement (posture RGPD-like).
- **Process en cas d'échec qualité** — régénération gratuite → refonte manuelle → remboursement en dernier recours (CGV).

---

## 20. KPIs & critères d'acceptation

**Critères d'acceptation produit (extraits) :**
- Une intention + un PDF produit une campagne mixte cohérente à la charte, en un seul flux.
- Aucun livrable gratuit ne sort sans filigrane (test de contournement échoue).
- Un job free n'invoque jamais un provider payant (test échoue proprement).
- Un Reel sort avec voix + sous-titres synchronisés.
- Un échec de provider ne fait pas échouer la campagne entière (statut partiel).

**KPIs de succès (business/produit) :**
- Temps brief → campagne (cible : minutes).
- Taux d'approbation au premier passage (qualité).
- Coût moyen par livrable (proche de 0 sur le tier free).
- Rétention client premium (effet Brand Brain).
- Part des livrables régénérés après recommandation (levier qualité).
- Une fois Griot branché : performance des contenus (vues, engagement, conversions).

---

## 21. Glossaire

- **KORA** — nom produit proposé ; le moteur créatif (ce système).
- **Griot** — agent SMM/distribution de l'écosystème (publication, community management, écoute des performances).
- **Brief** — objet typé résumant l'intention de production.
- **Storyboard** — plan de tournage multi-format consommé par le rendu.
- **Super-agent** — orchestrateur qui transforme une intention en campagne multi-modale.
- **Tier** — niveau de coût d'un job (free / premium).
- **Rôle** — droits & limites d'un utilisateur (admin / premium / free).
- **Entitlements** — droits dérivés du rôle, vérifiés à chaque job.
- **Brand Brain** — mémoire de marque persistante par client.
- **Manifeste de publication** — paquet standard remis à Griot pour diffusion.
- **Motion comic** — animation d'une BD case par case.
- **Pay-as-you-serve** — coût premium répercuté au client qui le demande.

---

## 22. Annexes

### Annexe A — Naming

**Nom proposé : KORA.**

La *kora* est la harpe-luth à 21 cordes des griots d'Afrique de l'Ouest. Métaphore d'écosystème parfaite : **KORA compose, Griot raconte et diffuse** — l'instrument et le conteur. Court (4 lettres), prononçable mondialement, ancré culturellement, cohérent avec l'univers blvck.

**Alternatives :**

| Nom | Sens | Note |
|---|---|---|
| **KORA** *(recommandé)* | Instrument du griot | Interconnexion évidente avec Griot |
| **MANSA** | « Roi des rois » (Mansa Musa), richesse, puissance | Fort, court, évoque le créateur-roi |
| **SANKOFA** | « Retourne le chercher » (apprendre du passé) | Colle à la boucle d'apprentissage 360° |
| **DJELI / JELI** | Le griot lui-même | Trop proche de « Griot » |

*Le nom retenu se substituera à « KORA » dans tout le document.*

### Annexe B — Hypothèses & questions ouvertes (à trancher par la direction)

1. **Quotas du tier gratuit** — nombre exact de générations/jour ou /mois, plafond de résolution, batch autorisé ou non.
2. **Contrôles premium** — liste définitive (retrait filigrane, filigrane custom, HD, file prioritaire, providers premium…).
3. **Frontière KORA/Griot sur l'analyse** — confirmé : Griot collecte la donnée brute, KORA porte l'intelligence d'optimisation. À valider.
4. **Média payant** — appartient-il à Griot, à un module dédié, ou hors périmètre écosystème ? À trancher.
5. **Grille tarifaire** — montants (document business séparé).
6. **Nom définitif** — KORA ou alternative.

---

*Fin du cahier des charges — KORA v1.0. Document de travail interne blvckUnlimited.*
