# Rapport d'ablation : quelles étapes du pipeline comptent ?

**Saifeddine Sayah** · Piscine I Lab « Feed the Beast » · novembre 2026

## 1. Protocole

Le modèle officiel du kit (GPT de 10,17M paramètres) est entraîné à l'identique (mêmes
hyperparamètres, graine 1337, 100M tokens, GPU T4) sur trois versions du **même mélange** de
données. Seul le traitement appliqué change :

| Variante | Traitement appliqué |
|---|---|
| **Brut** | données collectées telles quelles |
| **Nettoyé** | + réparation de l'encodage (ftfy), identification de la langue (fastText lid.176, seuil 0,65), suppression du boilerplate web, retrait des licences Gutenberg et recollage des paragraphes |
| **Complet** | + déduplication exacte (SHA-1 du texte normalisé) et quasi-doublons (MinHash + LSH, seuil 0,8), filtres qualité de type Gopher sur le web, masquage des données personnelles, données les plus propres en fin de flux |

Les trois variantes font **443 Mo** avec les **mêmes proportions** par source : Wikipédia 25 %,
Gutenberg 21 %, Molière 1,4 %, Assemblée nationale 24 %, presse (FineWeb-2, domaines de presse)
15 %, web général 7 %, Common Crawl 5 %. Chaque variante a son propre tokenizer BPE de
8 192 tokens, entraîné sur ses données. Comme référence, on ajoute la **baseline du kit**
(FineWeb-2 70 %, Wikipédia 25 %, Molière 5 %, sans traitement).

Mesure : BPB sur le set de validation public (230 documents, 4 genres à parts égales).

## 2. Résultats

| Dataset | BPB | Dialogue | Encyclo. | Littéraire | Presse | Octets/token (données) |
|---|---|---|---|---|---|---|
| Baseline du kit | 1,332 | 1,146 | 1,410 | 1,549 | 1,224 | 3,77 |
| Brut | 1,262 | 0,872 | 1,415 | 1,549 | 1,218 | 3,56 |
| Nettoyé | **1,234** | 0,859 | 1,406 | 1,478 | 1,197 | – |
| Complet (soumis) | **1,234** | 0,861 | 1,406 | 1,473 | 1,203 | 3,77 |

![Courbes de BPB et BPB par genre](ablation.png)

## 3. Ce qui compte

**1. Le choix des sources (−0,070 BPB, baseline → brut).** C'est de loin l'effet le plus fort.
Le BPB du dialogue passe de 1,15 à 0,87 : la validation contient des débats parlementaires, et
aucune quantité de web ne remplace 108 Mo de comptes rendus de l'Assemblée. Aligner le mélange
sur les 4 genres de l'évaluation vaut plus que n'importe quel filtre.

**2. Le nettoyage (−0,028 BPB, brut → nettoyé).** Le gain est concentré sur la **littérature**
(1,549 → 1,478, soit −0,07). Les livres Gutenberg bruts contiennent la licence anglaise et des
retours à la ligne tous les 70 caractères ; la validation, elle, a un paragraphe par ligne.
Recoller les paragraphes enseigne au modèle la bonne mise en forme. Le nettoyage améliore aussi
la compression : les données brutes (dont 88 % du Common Crawl n'est pas en français) donnent
3,56 octets/token au lieu de 3,77, donc le modèle lit **6 % de texte en moins** pour le même
budget. La courbe du brut reste au-dessus des deux autres pendant tout l'entraînement.

**3. Déduplication, filtres qualité, données personnelles (+0,0004, nettoyé → complet) :
aucun effet mesurable.** L'écart est en dessous du bruit d'un entraînement à graine unique.
Explications :
- les sources qui pèsent le plus (Wikipédia, Assemblée, presse) sont déjà propres et uniques ;
  la dédup n'y retire presque rien (3 quasi-doublons sur 56 000 pages FineWeb-2) ;
- là où elle agit, son effet est compensé par la répétition : Gutenberg perd 214 doublons exacts
  sur 550 livres (39 %), mais il reste assez de livres pour remplir sa part ; le Common Crawl
  français (7 Mo) doit être répété ~3 fois ;
- les filtres Gopher ne retirent que ~1 300 pages web sur 58 000 ;
- le masquage des données personnelles ne touche que ~3 300 emails et téléphones.

Ces étapes ne sont donc **pas inutiles**, mais leur intérêt n'est pas le BPB à cette échelle :
elles évitent de mémoriser des doublons (Lee et al. 2021), retirent des données personnelles
(RGPD) et deviendraient décisives avec plus de web brut.

## 4. Limites et suite

- **Filtre de langue** : précision 100 % et rappel 100 % sur 100 extraits Common Crawl annotés
  à la main. Il ne juge pas la qualité : une majorité des pages françaises gardées sont des boutiques, menus ou annuaires.
- **Une seule graine par variante** : un écart de ±0,005 BPB n'est pas significatif.
- **Peu de Common Crawl** : 2 fichiers WET, soit 7 Mo de français après filtrage. Le pipeline est
  prêt pour en traiter davantage ; c'est là que la dédup et les filtres qualité devraient compter.
- **Contamination** : 4 documents de validation sur 230 dépassent 10 % de 13-grammes communs,
  tous des débats parlementaires (11 à 15 %), à cause des formules de procédure répétées
  (« La parole est à… », « L'amendement n'est pas adopté »). Les séances postérieures au
  1er septembre 2026 sont exclues à la collecte.
- **Pistes non testées** : augmenter la part de littérature (genre le plus difficile, BPB 1,47),
  plus de presse récente, répéter les meilleures sources plutôt que le Common Crawl.
