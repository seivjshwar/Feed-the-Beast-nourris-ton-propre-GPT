"""Étape 3 : déduplication exacte (hash) et quasi-doublons (MinHash + LSH)."""

import hashlib
import re
import sys

from pipeline import config as C

WORD = re.compile(r"\w+", re.UNICODE)


def norm_hash(text):
    """Hash du texte normalisé (minuscules, espaces réduits) : deux copies identiques au formatage
    près ont le même hash."""
    return hashlib.sha1(" ".join(text.lower().split()).encode("utf-8")).hexdigest()


def exact_dedup(docs, seen, stats):
    out = []
    for d in docs:
        h = norm_hash(d["text"])
        if h in seen:
            stats["doublon_exact"] = stats.get("doublon_exact", 0) + 1
            continue
        seen.add(h)
        out.append(d)
    return out


def shingles(text):
    w = WORD.findall(text.lower())[:C.MINHASH_MAX_WORDS]
    n = C.MINHASH_NGRAM
    return {" ".join(w[i:i + n]).encode("utf-8") for i in range(max(1, len(w) - n + 1))}


def minhash_dedup(docs, stats):
    """Jaccard estimé sur les 5-grammes de mots. Seuil 0,8 (comme FineWeb et Lee et al. 2021) :
    au-dessus, deux pages ne diffèrent que par le menu, la date ou quelques phrases."""
    from datasketch import MinHash, MinHashLSH
    lsh = MinHashLSH(threshold=C.MINHASH_THRESHOLD, num_perm=C.MINHASH_PERM)
    out = []
    for i, d in enumerate(docs):
        m = MinHash(num_perm=C.MINHASH_PERM, seed=1)
        m.update_batch(list(shingles(d["text"])))
        if lsh.query(m):
            stats["quasi_doublon"] = stats.get("quasi_doublon", 0) + 1
            continue
        lsh.insert(str(i), m)
        out.append(d)
        if i % 5000 == 0:
            print(f"\r  minhash {i:,}/{len(docs):,}", end="", file=sys.stderr)
    print(file=sys.stderr)
    return out
