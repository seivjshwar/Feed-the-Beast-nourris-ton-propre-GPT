"""Précision du filtre de langue, mesurée sur l'échantillon annoté à la main.

    python -m pipeline.langid_eval

Remplis d'abord la colonne « vrai_francais (1/0) » de pipeline/annotation_langue.csv :
1 si l'extrait est bien du français, 0 sinon.
"""

import csv

PATH = "pipeline/annotation_langue.csv"
COL = "vrai_francais (1/0)"


def main():
    rows = [r for r in csv.DictReader(open(PATH, encoding="utf-8")) if r[COL].strip() in ("0", "1")]
    tp = sum(r["garde_par_le_filtre"] == "1" and r[COL] == "1" for r in rows)
    fp = sum(r["garde_par_le_filtre"] == "1" and r[COL] == "0" for r in rows)
    fn = sum(r["garde_par_le_filtre"] == "0" and r[COL] == "1" for r in rows)
    tn = sum(r["garde_par_le_filtre"] == "0" and r[COL] == "0" for r in rows)
    print(f"{len(rows)} documents annotés")
    print(f"vrais positifs {tp} | faux positifs {fp} | faux négatifs {fn} | vrais négatifs {tn}")
    if tp + fp:
        print(f"précision (gardés qui sont bien du français) : {tp / (tp + fp):.1%}")
    if tp + fn:
        print(f"rappel (français effectivement gardé)        : {tp / (tp + fn):.1%}")
    print("Attention : l'échantillon est stratifié (60 gardés, 40 rejetés), le rappel est indicatif.")


if __name__ == "__main__":
    main()
