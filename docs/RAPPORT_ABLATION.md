# Rapport d'ablation : qu'est-ce qui compte vraiment dans mes données ?

Saifeddine Sayah · Piscine I Lab « Feed the Beast » · 16 novembre 2026

## 1. Protocole

Même modèle officiel (10,17M paramètres, 100M tokens, graine 1337, GPU T4), même mélange de
sources, trois traitements différents. Seul le traitement change, pour mesurer l'effet de chaque
étape. Chaque variante a son propre tokenizer de 8 192 tokens. Mesure : BPB sur la validation
publique (230 documents, 4 genres à parts égales).

| Variante | Traitement |
|---|---|
| **Brut** | données telles que collectées |
| **Nettoyé** | + encodage (ftfy), langue (fastText ≥ 0,65), boilerplate web, licences Gutenberg retirées et paragraphes recollés |
| **Complet** | + dédup exacte et MinHash (Jaccard ≥ 0,8), filtres Gopher sur le web, masquage des données personnelles |

**Pourquoi ce mélange (443 Mo, identique pour les 3 variantes).** La validation contient 4 genres
à parts égales, donc j'ai cherché une source dédiée pour chacun plutôt que du web générique :
Wikipédia (encyclopédique, 25 %), Gutenberg + Molière (littéraire, 22 %), comptes rendus de
l'Assemblée nationale (dialogue, 24 % : c'est exactement le type de débats de la validation),
FineWeb-2 limité à ~70 domaines de presse (presse, 15 %), plus 7 % de web et 5 % de Common Crawl.

## 2. Résultats

| Dataset | BPB | Dialogue | Encyclo. | Littéraire | Presse | Octets/token |
|---|---|---|---|---|---|---|
| Baseline du kit | 1,332 | 1,146 | 1,410 | 1,549 | 1,224 | 3,77 |
| Brut | 1,262 | 0,872 | 1,415 | 1,549 | 1,218 | 3,56 |
| Nettoyé | 1,234 | 0,859 | 1,406 | 1,478 | 1,197 | – |
| **Complet (soumis)** | **1,234** | 0,861 | 1,406 | 1,473 | 1,203 | 3,77 |

![Courbes de BPB et BPB par genre](ablation.png)

## 3. Analyse

**1. Les sources : −0,07.** C'est l'effet le plus fort, et presque tout vient du dialogue
(1,15 → 0,87) : aucune quantité de web ne remplace des débats parlementaires quand l'évaluation en
contient. Avec le recul, j'aurais dû analyser la validation genre par genre dès le début.

**2. Le nettoyage : −0,03**, presque entièrement sur la littérature (1,549 → 1,478). J'ai recollé
les paragraphes Gutenberg parce que les livres bruts sont coupés tous les 70 caractères alors que la
validation met un paragraphe par ligne : sinon le modèle apprend des retours à la ligne qui n'existent
pas dans l'évaluation. Le nettoyage améliore aussi la compression (3,56 → 3,77 octets/token) : le
modèle lit 6 % de texte en plus pour le même budget.

**3. Dédup, qualité, données personnelles : ≈ 0 (+0,0004, du bruit).** Mes grosses sources étaient
déjà propres ; là où la dédup agit (214 livres Gutenberg sur 550 en double), il restait assez de
livres pour remplir la part de Gutenberg. Je les garde : elles masquent ~1 400 emails et ~1 700
téléphones, et compteraient davantage avec plus de web brut. J'ai choisi le seuil MinHash de 0,8 sur
des 5-grammes de mots, celui de FineWeb et de Lee et al. (2021) : au-dessus, deux pages ne diffèrent
que par un menu ou une date.

## 4. Ce qui n'a pas marché, et ce que j'ai changé

| Problème | Ce que j'ai fait | Pourquoi |
|---|---|---|
| Common Crawl renvoyait une page d'erreur (limitation de débit) | Réessais avec attente croissante, User-Agent, crawl de repli | Le sujet exige un segment brut ; un échec réseau ne doit pas bloquer le pipeline |
| Seulement 7 Mo de français sur 400 Mo de Common Crawl (88 % d'autres langues) | Part limitée à 5 % du mélange | Il est répété ~3 fois ; au-delà, je répéterais des pages de faible qualité |
| Le filtre de langue garde des boutiques et des menus (précision 100 % sur 100 extraits annotés à la main, mais la langue n'est pas la qualité) | Ajout des filtres Gopher et du retrait du boilerplate ligne par ligne | Un filtre de langue ne juge pas la qualité ; il faut une deuxième étape |
| Le serveur de l'Assemblée coupait les téléchargements | Téléchargement avec reprise (en-tête HTTP Range) et vérification du zip | Sans cette source, le dialogue s'effondre ; le pipeline doit tourner en une commande |
| 4 débats de la validation à 11-15 % de 13-grammes communs | Exclusion des séances après le 1er septembre 2026 | Le recouvrement restant vient des formules de procédure (« La parole est à… ») |
| Mélange v2 non évalué (2 sessions Colab perdues, plus de GPU) | Préparé (`--mix v2` : +6 pts Gutenberg, +3 pts presse, Common Crawl à 2 %) | La littérature est mon genre le plus faible (1,47) : c'est là qu'il reste à gagner |

Limite : une seule graine par variante, donc un écart de ±0,005 n'est pas significatif.
