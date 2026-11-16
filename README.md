# Feed the Beast : nourris ton propre GPT

Piscine I Lab (Intelligence Lab, ECE Paris), novembre 2026 · **Saifeddine Sayah**

Un mini-GPT codé de zéro, puis un pipeline qui transforme du web brut en données d'entraînement
françaises, évalué dans une compétition où seul le dataset change.

## Résultats en bref

| | Résultat |
|---|---|
| Autograd (`Value`) | gradients identiques à PyTorch (`tests/test_autograd.py`) |
| Bigramme sur Molière | BPB validation **3,31** |
| Mini-GPT sur Molière, caractères | BPB validation **1,82** (1,84M paramètres) |
| Mini-GPT sur Molière, mon BPE (512 tokens) | BPB validation **1,85** (2,00M paramètres ; surapprentissage après ~1 750 pas) |
| Compétition, baseline du kit | BPB validation 1,332 |
| **Compétition, mon dataset** | **BPB validation 1,234** (−0,098) |

## Structure

```
minigpt/      bloc 1 : mon mini-GPT, codé de zéro
  autograd.py   classe Value : +, ×, tanh, backward() par tri topologique
  bigram.py     modèle bigramme par comptage (lissage de Laplace)
  bpe.py        tokenizer BPE sur les octets : train, encode, decode
  gpt.py        transformer décodeur : attention multi-têtes à masque causal, LayerNorm,
                MLP, connexions résiduelles ; entraînement, BPB, échantillons
tests/test_autograd.py   vérification de l'autograd contre PyTorch
pipeline/     bloc 2 : le pipeline de données (une commande)
  collect.py    collecte : Common Crawl (WET), Wikipédia, Gutenberg, Assemblée nationale,
                FineWeb-2 (presse et web), Molière
  clean.py      encodage (ftfy), langue (fastText), boilerplate, mise en forme Gutenberg
  dedup.py      déduplication exacte et MinHash + LSH
  quality.py    filtres de type Gopher, masquage des données personnelles
  run_pipeline.py   orchestration ; produit les 3 datasets d'ablation
  langid_eval.py    précision du filtre de langue sur l'échantillon annoté à la main
  SOURCES.md    fiche de chaque source (origine, licence, volume, période, risques)
  STATS.md      volumes et rejets à chaque étape
docs/         RAPPORT_ABLATION.md, DATASHEET.md
resultats/    journaux d'entraînement et échantillons des 3 runs d'ablation
submissions/  soumissions au leaderboard
ftb/, config/, corpus/, data/   kit de départ officiel
```

## Reproduire

```bash
pip install -r requirements.txt -r pipeline/requirements.txt

# Bloc 1 (CPU / Mac)
python -m pytest tests/test_autograd.py -q
python minigpt/bigram.py
python minigpt/bpe.py
python minigpt/gpt.py            # TOKENIZER = "char" ou "bpe" en haut du fichier

# Bloc 2 : pipeline complet (~35 min), puis les 3 datasets d'ablation dans data/mix/
python -m pipeline.run_pipeline
python -m pipeline.langid_eval

# Bloc 3 : entraînement officiel (GPU T4, ~12 min) et soumission
python -m ftb.tokenizer train --inputs data/mix/complet.jsonl --out tok.json --max-docs 300000
python -m ftb.prepare --inputs data/mix/complet.jsonl --tokenizer tok.json --out prepared/
python -m ftb.train --data prepared/ --tokenizer tok.json --out runs/complet
python -m ftb.submit --run runs/complet --participant "Saifeddine Sayah"
```

Sur Colab : `notebooks/pipeline_colab.ipynb` enchaîne pipeline, 3 entraînements et soumission.

## Mini-GPT : caractères ou BPE ?

Même architecture (4 blocs, 6 têtes, d_model 192, contexte 128), 3 000 pas, 3 minutes sur Mac.

| Tokenizer | Vocabulaire | BPB validation | Meilleure loss val | Remarque |
|---|---|---|---|---|
| Caractères | 100 | **1,82** | 1,29 au pas 3 000 | apprend encore à la fin |
| Mon BPE | 512 | 1,85 | 2,66 au pas 1 750 | surapprend ensuite |

Avec le BPE, chaque token couvre ~2,5 caractères : les 128 tokens de contexte voient ~300
caractères au lieu de 128, et les échantillons contiennent davantage de vrais mots. Mais le
corpus d'entraînement ne fait plus que ~600 000 tokens : le modèle le mémorise et la loss de
validation remonte après 1 750 pas, d'où un BPB final légèrement moins bon. Un arrêt anticipé
ou du dropout corrigerait ce point.

## Ce que j'ai appris

Voir `docs/RAPPORT_ABLATION.md`. En une phrase : **choisir des sources alignées sur l'évaluation**
(ici les débats parlementaires pour le dialogue) apporte plus que tous les filtres réunis ;
le nettoyage aide surtout sur les livres ; la déduplication et les filtres qualité n'ont pas
d'effet mesurable à cette échelle, mais restent nécessaires pour les données personnelles et
la mémorisation.
