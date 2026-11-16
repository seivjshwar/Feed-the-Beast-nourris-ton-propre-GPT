# Fiches des sources

Volumes réels après chaque étape : voir `pipeline/STATS.md` (généré par le pipeline).
Règle commune : aucune donnée publiée après le 1er septembre 2026, pour ne recouvrir ni la
validation (octobre 2026) ni le test (publié après le début de la piscine). Le contrôle
`ftb.contamination` est lancé sur le dataset final.

## 1. Common Crawl (segment brut) : `cc`
- **Origine** : fichiers WET (texte extrait) du crawl `CC-MAIN-2024-51`, 3 fichiers pris à
  intervalles réguliers dans la liste `wet.paths.gz`. https://commoncrawl.org
- **Licence** : conditions d'utilisation de Common Crawl ; chaque page reste soumise aux droits de
  son auteur. Usage ici : recherche et éducation, non redistribué tel quel.
- **Volume collecté** : ~400 Mo de texte brut, toutes langues confondues.
- **Période** : pages crawlées en décembre 2024.
- **Risques** : majorité de pages non françaises, menus et boilerplate, spam, doublons, données
  personnelles (emails, téléphones). C'est la source qui justifie tout le pipeline.

## 2. Wikipédia FR : `wikipedia` (genre encyclopédique)
- **Origine** : dump Hugging Face `wikimedia/wikipedia`, configuration `20231101.fr`, articles
  tirés au hasard (mélange en flux, graine 0).
- **Licence** : CC BY-SA 4.0 (attribution : historique de chaque article).
- **Volume collecté** : ~170 Mo.
- **Période** : état de Wikipédia au 1er novembre 2023.
- **Risques** : faibles. Listes et ébauches peu informatives ; biais de couverture (sujets
  européens, masculins).

## 3. Projet Gutenberg, livres en français : `gutenberg` (genre littéraire)
- **Origine** : Hugging Face `manu/project_gutenberg` (split `fr`) ; plan B : catalogue
  officiel `pg_catalog.csv`, livres en français publiés avant juin 2026.
- **Licence** : domaine public (aux États-Unis) ; en-têtes et pieds de licence Gutenberg retirés.
- **Volume collecté** : ~220 Mo (600 Ko maximum par livre, pour la variété).
- **Période** : œuvres du XVIIe au début du XXe siècle, numérisées avant 2024.
- **Risques** : orthographe ancienne, retours à la ligne tous les 70 caractères (recollés par le
  pipeline), éditions en double (quasi-doublons MinHash), quelques livres bilingues.

## 4. Assemblée nationale, comptes rendus des séances : `an` (genre dialogue)
- **Origine** : open data de l'Assemblée nationale, comptes rendus « Syceron » des XVIe et XVIIe
  législatures. https://data.assemblee-nationale.fr
- **Licence** : Licence Ouverte / Open Licence (Etalab).
- **Volume collecté** : jusqu'à 400 Mo, découpé en extraits d'environ 20 000 caractères au format
  « Orateur : propos », comme la validation.
- **Période** : juin 2022 à août 2026 (séances à partir du 1er septembre 2026 exclues).
- **Risques** : noms de personnes (élus, personnes publiques dans l'exercice de leur mandat) ;
  registre très particulier (procédure parlementaire) ; propos polémiques.

## 5. FineWeb-2 français : `fineweb_news` (presse) et `fineweb` (web général)
- **Origine** : Hugging Face `HuggingFaceFW/fineweb-2`, configuration `fra_Latn`. La part
  « presse » ne garde que les pages d'environ 70 domaines de presse francophone
  (`pipeline/config.py`).
- **Licence** : ODC-By 1.0 ; chaque page reste soumise aux droits de son auteur.
- **Volume collecté** : ~110 Mo de presse, ~80 Mo de web général.
- **Période** : crawls Common Crawl de 2013 à 2024.
- **Risques** : déjà filtré par Hugging Face, mais il reste des doublons, du boilerplate,
  quelques données personnelles ; articles de presse soumis au droit d'auteur.

## 6. Molière (corpus du kit) : `moliere`
- **Origine** : `corpus/moliere_train.txt` du kit (édition Chasles 1888, Projet Gutenberg).
- **Licence** : domaine public.
- **Volume** : 1,5 Mo (25 pièces), répété pour atteindre 3 % du mélange.
- **Risques** : orthographe du XVIIe siècle, vers.
