"""Le pipeline complet, en une commande :

    python -m pipeline.run_pipeline                      # tout : collecte -> nettoyage -> traitement -> mélanges
    python -m pipeline.run_pipeline --steps clean,full,mix   # sans re-télécharger
    python -m pipeline.run_pipeline --scale 0.05         # essai rapide (5 % des volumes)
    python -m pipeline.run_pipeline --mix all            # + le mélange v2 (data/mix/complet_v2.jsonl)

Sorties :
    data/raw/      collecte brute, une source par fichier
    data/clean/    après nettoyage (encodage, langue, boilerplate)
    data/full/     après déduplication, filtres qualité et masquage des données personnelles
    data/mix/brut.jsonl, nettoye.jsonl, complet.jsonl   les trois datasets du rapport d'ablation
    pipeline/STATS.md, data/stats.json                  volumes et rejets à chaque étape
    pipeline/annotation_langue.csv                      échantillon à annoter à la main (filtre de langue)
"""

import argparse
import csv
import json
import random
import sys
import time

from pipeline import config as C
from pipeline.clean import LangID, clean_doc, fix_encoding, strip_boilerplate
from pipeline.collect import COLLECTORS
from pipeline.dedup import exact_dedup, minhash_dedup
from pipeline.docio import nbytes, read_docs, write_docs
from pipeline.quality import gopher_reason, mask_pii

SOURCES = ["moliere", "wikipedia", "gutenberg", "an", "fineweb_news", "fineweb", "cc"]


def log(*a):
    print("[pipeline]", *a, file=sys.stderr, flush=True)


def size(docs):
    return {"documents": len(docs), "mo": round(sum(nbytes(d["text"]) for d in docs) / 1e6, 2)}


# --- Étapes ----------------------------------------------------------------------------------
def step_collect(sources, stats):
    for name, fn in COLLECTORS.items():
        if name not in sources and not (name == "fineweb" and "fineweb_news" in sources):
            continue
        t0 = time.time()
        log("collecte :", name)
        try:
            fn()
        except Exception as e:  # noqa: BLE001  une source en panne ne bloque pas les autres
            log(f"ÉCHEC de la collecte {name} : {e!r}"[:300])
            stats.setdefault("echecs_collecte", {})[name] = repr(e)[:300]
        log(f"  {name} : {time.time() - t0:.0f} s")


def step_clean(sources, stats):
    langid = LangID()
    stats["identification_langue"] = langid.name
    for s in sources:
        docs = read_docs(C.RAW / f"{s}.jsonl.gz")
        if not docs:
            continue
        st = {}
        if s == "cc":
            langid_sample(docs, langid)
        out = [d2 for d in docs if (d2 := clean_doc(d, langid, st)) is not None]
        write_docs(C.CLEAN / f"{s}.jsonl.gz", out)
        stats.setdefault("brut", {})[s] = size(docs)
        stats.setdefault("nettoye", {})[s] = size(out)
        stats.setdefault("rejets_nettoyage", {})[s] = st
        log(f"nettoyage {s}: {len(docs)} -> {len(out)} documents {st}")


def step_full(sources, stats):
    seen = set()   # hash exacts, partagés entre sources (un même texte dans deux sources = doublon)
    for s in sources:
        docs = read_docs(C.CLEAN / f"{s}.jsonl.gz")
        if not docs:
            continue
        st = {}
        docs = exact_dedup(docs, seen, st)
        if s in C.WEB_SOURCES or s == "gutenberg":
            docs = minhash_dedup(docs, st)
        kept = []
        for d in docs:
            if s in C.WEB_SOURCES:
                r = gopher_reason(d["text"])
                if r:
                    st["qualite_" + r] = st.get("qualite_" + r, 0) + 1
                    continue
            kept.append({**d, "text": mask_pii(d["text"], st)})
        write_docs(C.FULL / f"{s}.jsonl.gz", kept)
        stats.setdefault("complet", {})[s] = size(kept)
        stats.setdefault("rejets_traitement", {})[s] = st
        log(f"traitement {s}: {len(docs)} -> {len(kept)} documents {st}")


def sample_source(docs, quota, rng):
    """Tire des documents (dans un ordre aléatoire) jusqu'à `quota` octets ; une source trop petite
    est relue, au plus MAX_REPEAT fois."""
    if not docs:
        return []
    out, got = [], 0
    for _ in range(C.MAX_REPEAT):
        order = docs[:]
        rng.shuffle(order)
        for d in order:
            out.append(d)
            got += nbytes(d["text"])
            if got >= quota:
                return out
    return out


def build_mix(folder, variant, stats, scale, tail, shares=None):
    shares = shares or C.MIX_SHARES
    rng = random.Random(C.SEED)
    pools = {s: read_docs(folder / f"{s}.jsonl.gz") for s in shares}
    avail = {s: share for s, share in shares.items() if pools[s]}
    total_share = sum(avail.values())
    target = C.MIX_TARGET_MB * 1e6 * scale
    body, end, comp = [], [], {}
    for s, share in avail.items():
        picked = sample_source(pools[s], target * share / total_share, rng)
        comp[s] = size(picked)
        if tail and s in C.TAIL_SOURCES:
            k = int(len(picked) * C.TAIL_FRACTION * 2.5)   # ces 4 sources ≈ 40 % du flux -> ~10 % en fin
            end += picked[:k]
            body += picked[k:]
        else:
            body += picked
    rng.shuffle(body)
    rng.shuffle(end)
    docs = body + end
    C.MIX.mkdir(parents=True, exist_ok=True)
    with open(C.MIX / f"{variant}.jsonl", "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps({"source": d["source"], "text": d["text"]}, ensure_ascii=False) + "\n")
    stats.setdefault("melanges", {})[variant] = {"total": size(docs), "par_source": comp}
    log(f"mélange {variant}: {size(docs)}")


def step_mix(stats, scale, mix="v1"):
    if mix in ("v1", "all"):
        build_mix(C.RAW, "brut", stats, scale, tail=False)
        build_mix(C.CLEAN, "nettoye", stats, scale, tail=False)
        build_mix(C.FULL, "complet", stats, scale, tail=True)
    if mix in ("v2", "all"):
        build_mix(C.FULL, "complet_v2", stats, scale, tail=True, shares=C.MIX_SHARES_V2)


# --- Échantillon pour mesurer le filtre de langue -----------------------------------------
def langid_sample(docs, langid, path="pipeline/annotation_langue.csv", n_fr=60, n_other=40):
    import os
    if os.path.exists(path):
        return   # ne jamais écraser des annotations faites à la main
    rng = random.Random(C.SEED)
    order = docs[:]
    rng.shuffle(order)
    fr, other = [], []
    for d in order:
        t = strip_boilerplate(fix_encoding(d["text"]))
        if len(t) < 200:
            continue
        lang, p = langid.predict(t)
        row = {"id": d.get("url", ""), "prediction": lang, "proba": round(p, 3),
               "garde_par_le_filtre": int(lang == "fr" and p >= C.LANG_MIN_PROB),
               "extrait": " ".join(t.split())[:300], "vrai_francais (1/0)": ""}
        (fr if row["garde_par_le_filtre"] else other).append(row)
        if len(fr) >= n_fr and len(other) >= n_other:
            break
    rows = fr[:n_fr] + other[:n_other]
    rng.shuffle(rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log(f"{len(rows)} documents à annoter à la main dans {path}")


# --- Rapport --------------------------------------------------------------------------------
def write_stats(stats):
    C.DATA.mkdir(exist_ok=True)
    old = {}
    if (C.DATA / "stats.json").exists():
        old = json.loads((C.DATA / "stats.json").read_text())
    for k, v in stats.items():   # on fusionne avec les étapes déjà faites
        if isinstance(v, dict) and isinstance(old.get(k), dict):
            old[k].update(v)
        else:
            old[k] = v
    stats = old
    (C.DATA / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    lines = ["# Statistiques du pipeline", "", "Généré par `python -m pipeline.run_pipeline`.", "",
             "## Volumes à chaque étape (Mo de texte / documents)", "",
             "| Source | Brut | Nettoyé | Complet |", "|---|---|---|---|"]
    for s in SOURCES:
        cells = []
        for stage in ("brut", "nettoye", "complet"):
            v = stats.get(stage, {}).get(s)
            cells.append(f"{v['mo']} Mo / {v['documents']:,}" if v else "–")
        lines.append(f"| {s} | " + " | ".join(cells) + " |")
    lines += ["", "## Rejets du nettoyage", "", "```", json.dumps(stats.get("rejets_nettoyage", {}),
              indent=1, ensure_ascii=False), "```", "", "## Rejets du traitement (dédup, qualité, données perso)",
              "", "```", json.dumps(stats.get("rejets_traitement", {}), indent=1, ensure_ascii=False), "```",
              "", "## Mélanges d'ablation", ""]
    for v, m in stats.get("melanges", {}).items():
        lines.append(f"- **{v}** : {m['total']['mo']} Mo, {m['total']['documents']:,} documents — " +
                     ", ".join(f"{s} {x['mo']} Mo" for s, x in m["par_source"].items()))
    if stats.get("echecs_collecte"):
        lines += ["", "## Échecs de collecte", "", "```",
                  json.dumps(stats["echecs_collecte"], indent=1, ensure_ascii=False), "```"]
    open("pipeline/STATS.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--steps", default="collect,clean,full,mix")
    p.add_argument("--sources", default=",".join(SOURCES))
    p.add_argument("--scale", type=float, default=1.0, help="multiplie tous les volumes (essai rapide)")
    p.add_argument("--mix", default="v1", choices=["v1", "v2", "all"],
                   help="v1 : brut, nettoye, complet (ablation) ; v2 : complet_v2 ; all : les quatre")
    a = p.parse_args()
    if a.scale != 1.0:
        for k in C.COLLECT_MB:
            C.COLLECT_MB[k] *= a.scale
        C.FINEWEB_SCAN_MB *= a.scale
        C.CC_N_FILES = 1
    sources = a.sources.split(",")
    steps = a.steps.split(",")
    stats = {}
    t0 = time.time()
    if "collect" in steps:
        step_collect(sources, stats)
    if "clean" in steps:
        step_clean(sources, stats)
    if "full" in steps:
        step_full(sources, stats)
    if "mix" in steps:
        step_mix(stats, a.scale, a.mix)
    stats["duree_s"] = round(time.time() - t0)
    write_stats(stats)
    log(f"terminé en {time.time() - t0:.0f} s — voir pipeline/STATS.md")


if __name__ == "__main__":
    main()
