# Statistiques du pipeline

Généré par `python -m pipeline.run_pipeline`.

## Volumes à chaque étape (Mo de texte / documents)

| Source | Brut | Nettoyé | Complet |
|---|---|---|---|
| moliere | 1.54 Mo / 25 | 1.54 Mo / 25 | 1.54 Mo / 25 |
| wikipedia | 170.0 Mo / 41,578 | 169.86 Mo / 40,639 | 169.86 Mo / 40,639 |
| gutenberg | 220.12 Mo / 561 | 206.61 Mo / 550 | 125.71 Mo / 335 |
| an | 243.38 Mo / 11,702 | 243.38 Mo / 11,681 | 243.38 Mo / 11,681 |
| fineweb_news | 110.0 Mo / 35,982 | 108.58 Mo / 35,953 | 108.05 Mo / 35,467 |
| fineweb | 80.05 Mo / 20,673 | 77.49 Mo / 20,558 | 77.11 Mo / 20,057 |
| cc | 400.01 Mo / 47,083 | 8.14 Mo / 1,764 | 6.96 Mo / 1,460 |

## Rejets du nettoyage

```
{
 "moliere": {},
 "wikipedia": {
  "trop_court": 939,
  "encodage_repare": 47
 },
 "gutenberg": {
  "encodage_repare": 149,
  "pas_francais": 11
 },
 "an": {
  "trop_court": 21
 },
 "fineweb_news": {
  "trop_court": 20,
  "pas_francais": 9,
  "encodage_repare": 3
 },
 "fineweb": {
  "pas_francais": 69,
  "encodage_repare": 35,
  "trop_court": 46
 },
 "cc": {
  "pas_francais": 41454,
  "encodage_repare": 7875,
  "trop_court": 3865
 }
}
```

## Rejets du traitement (dédup, qualité, données perso)

```
{
 "moliere": {},
 "wikipedia": {
  "pii_email": 4,
  "pii_ip": 40,
  "pii_telephone": 11
 },
 "gutenberg": {
  "doublon_exact": 214,
  "quasi_doublon": 1,
  "pii_ip": 5
 },
 "an": {
  "pii_telephone": 1
 },
 "fineweb_news": {
  "quasi_doublon": 2,
  "pii_telephone": 645,
  "pii_email": 325,
  "qualite_points_suspension": 200,
  "qualite_nb_mots": 279,
  "pii_ip": 20,
  "qualite_symboles": 1,
  "qualite_puces": 4
 },
 "fineweb": {
  "quasi_doublon": 1,
  "qualite_points_suspension": 164,
  "qualite_nb_mots": 322,
  "pii_telephone": 594,
  "pii_email": 904,
  "qualite_puces": 11,
  "pii_ip": 117,
  "qualite_pas_de_mots_outils": 2,
  "qualite_symboles": 1
 },
 "cc": {
  "doublon_exact": 7,
  "quasi_doublon": 15,
  "qualite_peu_de_mots": 199,
  "pii_email": 186,
  "qualite_nb_mots": 35,
  "pii_telephone": 412,
  "qualite_points_suspension": 26,
  "qualite_symboles": 8,
  "qualite_pas_de_mots_outils": 6,
  "qualite_lignes_repetees": 3,
  "pii_ip": 31,
  "qualite_longueur_mots": 5
 }
}
```

## Mélanges d'ablation

- **brut** : 442.89 Mo, 66,410 documents — wikipedia 112.5 Mo, gutenberg 94.72 Mo, moliere 6.14 Mo, an 108.02 Mo, fineweb_news 67.5 Mo, fineweb 31.51 Mo, cc 22.5 Mo
- **nettoye** : 442.84 Mo, 67,925 documents — wikipedia 112.5 Mo, gutenberg 94.66 Mo, moliere 6.14 Mo, an 108.01 Mo, fineweb_news 67.5 Mo, fineweb 31.5 Mo, cc 22.52 Mo
- **complet** : 442.76 Mo, 67,266 documents — wikipedia 112.5 Mo, gutenberg 94.58 Mo, moliere 6.14 Mo, an 108.0 Mo, fineweb_news 67.5 Mo, fineweb 31.5 Mo, cc 22.53 Mo
