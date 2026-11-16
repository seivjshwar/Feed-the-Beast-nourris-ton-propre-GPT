# Datasheet : dataset « complet » de la soumission Feed the Beast

Sur le modèle de *Datasheets for Datasets* (Gebru et al. 2018).
Empreinte du flux de tokens : `fe396987c0c6bdc6000381baf6d63c39c51d3b722e720a49db9760a0f0940682`
Tokenizer : `87d7c302f441bf6e66aaa27dd5bffcfbd338d61ec444d8de62d5307c0c37a832`

## Motivation
- **Pourquoi ce dataset ?** Pour le pré-entraînement d'un petit modèle de langue français
  (10M paramètres, 100M tokens) évalué sur 4 genres : encyclopédique, littéraire, presse, dialogue.
- **Qui l'a créé ?** Saifeddine Sayah, dans le cadre de la piscine I Lab de l'ECE Paris.
- **Financement** : aucun.

## Composition
- **Contenu** : 67 266 documents texte en français, 442,8 Mo, 117,5M tokens.
- **Répartition (octets)** :

| Source | Genre visé | Mo | Part |
|---|---|---|---|
| Wikipédia FR (2023) | encyclopédique | 112,5 | 25 % |
| Projet Gutenberg (livres FR) | littéraire | 94,6 | 21 % |
| Molière (corpus du kit) | littéraire | 6,1 | 1,4 % |
| Assemblée nationale, comptes rendus | dialogue | 108,0 | 24 % |
| FineWeb-2, domaines de presse | presse | 67,5 | 15 % |
| FineWeb-2, web général | divers | 31,5 | 7 % |
| Common Crawl (traité par ce pipeline) | divers | 22,5 | 5 % |

- **Répétitions** : le Common Crawl français (7 Mo uniques) est répété ~3 fois, Molière 4 fois.
  Les autres sources ne sont pas répétées. Le modèle voit 85 % du flux (100M tokens sur 117,5M).
- **Ordre** : mélange aléatoire (graine 0), sauf les ~10 % finaux, réservés aux sources les plus
  propres (Wikipédia, Gutenberg, Assemblée, presse).
- **Étiquettes** : chaque document garde sa source (champ `source`).
- **Données personnelles** : emails, numéros de téléphone français, IBAN et adresses IP masqués
  (`[EMAIL]`, `[TÉLÉPHONE]`, `[IBAN]`, `[IP]`). Les noms de personnes ne sont **pas** masqués :
  surtout des personnes publiques (députés en séance, personnalités de Wikipédia, auteurs).
- **Contenu sensible** : débats politiques, articles de presse sur des sujets sensibles, œuvres
  anciennes reflétant les préjugés de leur époque.
- **Recouvrement avec l'évaluation** : contrôle 13-grammes contre la validation publique, 4 documents
  sur 230 au-dessus de 10 % (débats parlementaires, 11 à 15 %, formules de procédure).

## Collecte
- **Méthode** : téléchargement automatisé, `python -m pipeline.run_pipeline` (voir
  `pipeline/SOURCES.md` pour la fiche de chaque source).
- **Période couverte** : œuvres anciennes (Gutenberg) ; Wikipédia au 1er novembre 2023 ; presse
  et web 2013-2024 ; Common Crawl de décembre 2024 ; débats de juin 2022 à août 2026. Rien après
  le 1er septembre 2026.
- **Échantillonnage** : Wikipédia tirée au hasard ; presse sélectionnée par domaine
  (~70 médias francophones) ; Common Crawl : 2 fichiers WET du crawl `CC-MAIN-2024-51`.
- **Consentement** : données publiques sous licence ouverte ou domaine public ; pas de collecte
  auprès de personnes.

## Traitement
Pipeline reproductible en une commande. Volumes à chaque étape dans `pipeline/STATS.md`.

1. **Encodage** : ftfy (apostrophes typographiques conservées) ; 8 100 documents réparés.
2. **Langue** : fastText lid.176, français avec probabilité ≥ 0,65, sur le web et Gutenberg ;
   41 454 pages Common Crawl rejetées (88 %). Mesure sur 100 extraits de Common Crawl
   (60 gardés, 40 rejetés), annotés à la main. Résultat :
   **précision 100 % (60/60), rappel 100 %** (aucun français parmi les 40 rejetés). Limite :
   la langue est juste, mais beaucoup de pages gardées sont des fiches produits ou des menus,
   d'où les filtres qualité de l'étape 5.
3. **Boilerplate** : suppression des lignes de menu, cookies, partage, mentions légales et
   lignes répétées (web) ; licences Gutenberg retirées et paragraphes recollés (livres).
4. **Déduplication** : exacte (SHA-1 du texte normalisé, entre toutes les sources) et
   quasi-doublons (MinHash 128 permutations sur 5-grammes de mots, LSH, Jaccard ≥ 0,8, seuil de
   FineWeb et de Lee et al. 2021) ; 221 doublons exacts et 19 quasi-doublons retirés.
5. **Qualité** : règles de Gopher (Rae et al. 2021) sur le web : nombre et longueur des mots,
   symboles, puces, lignes en « … », lignes répétées, mots alphabétiques, mots-outils français ;
   1 266 pages rejetées.
6. **Données personnelles** : expressions régulières ; 1 419 emails, 1 663 téléphones, 213 IP.

Données brutes et intermédiaires conservées localement (`data/raw`, `data/clean`), non publiées.

## Usages
- **Prévu** : pré-entraînement de petits modèles de langue français, recherche et enseignement.
- **À éviter** : usage commercial sans vérifier les droits de chaque source (presse, web) ;
  inférences sur des personnes.
- **Biais connus** : sur-représentation du registre parlementaire et de la littérature ancienne ;
  français de France majoritaire.

## Distribution et maintenance
- **Distribution** : non redistribué ; reconstructible avec le pipeline. Licences d'origine :
  CC BY-SA 4.0 (Wikipédia), domaine public (Gutenberg, Molière), Licence Ouverte (Assemblée),
  ODC-By (FineWeb-2), conditions de Common Crawl.
- **Maintenance** : aucune prévue après la piscine. Contact : saifeddine.sayah@edu.ece.fr.
