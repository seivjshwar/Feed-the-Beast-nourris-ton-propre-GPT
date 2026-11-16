"""Lecture / écriture des documents : un .jsonl.gz par source, un document par ligne."""

import gzip
import json
from pathlib import Path


def write_docs(path, docs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_docs(path):
    path = Path(path)
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def nbytes(text):
    return len(text.encode("utf-8"))
