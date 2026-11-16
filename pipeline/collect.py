"""Étape 1 : collecte. Chaque source est écrite telle quelle dans data/raw/<source>.jsonl.gz.

Sources :
  cc            Common Crawl brut (fichiers WET d'un crawl de décembre 2024, toutes langues)
  wikipedia     Wikipédia FR (dump Hugging Face wikimedia/wikipedia 20231101.fr)
  gutenberg     Projet Gutenberg, livres en français (Hugging Face manu/project_gutenberg, sinon gutenberg.org)
  an            Assemblée nationale, comptes rendus des séances (data.assemblee-nationale.fr)
  fineweb_news  FineWeb-2 fra_Latn, documents des domaines de presse
  fineweb       FineWeb-2 fra_Latn, web général
  moliere       corpus Molière du kit
"""

import csv
import gzip
import io
import random
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from urllib.parse import urlparse

from pipeline import config as C
from pipeline.docio import nbytes, write_docs


def log(*a):
    print("[collecte]", *a, file=sys.stderr, flush=True)


def take(docs, mb):
    """Garde les documents jusqu'à `mb` Mo de texte."""
    budget, got = int(mb * 1e6), 0
    for d in docs:
        if not d.get("text"):
            continue
        yield d
        got += nbytes(d["text"])
        if got >= budget:
            break


# --- Wikipédia -------------------------------------------------------------------------------
def wikipedia():
    from datasets import load_dataset
    ds = load_dataset("wikimedia/wikipedia", "20231101.fr", split="train", streaming=True)
    ds = ds.shuffle(seed=C.SEED, buffer_size=20_000)   # sinon on n'aurait que les premiers articles
    rows = ({"source": "wikipedia", "id": r.get("id"), "url": r.get("url"), "text": r["text"]} for r in ds)
    return write_docs(C.RAW / "wikipedia.jsonl.gz", take(rows, C.COLLECT_MB["wikipedia"]))


# --- FineWeb-2 : presse et web général ---------------------------------------------------------
def is_news(url):
    host = urlparse(url or "").netloc.lower()
    return any(host == d or host.endswith("." + d) for d in C.NEWS_DOMAINS)


def fineweb():
    from datasets import load_dataset
    ds = load_dataset("HuggingFaceFW/fineweb-2", name="fra_Latn", split="train", streaming=True)
    news, web = [], []
    b_news = b_web = scanned = 0
    for r in ds:
        t = r["text"]
        n = nbytes(t)
        scanned += n
        d = {"source": None, "url": r.get("url"), "date": r.get("date"), "text": t}
        if is_news(r.get("url")):
            if b_news < C.COLLECT_MB["fineweb_news"] * 1e6:
                d["source"] = "fineweb_news"
                news.append(d)
                b_news += n
        elif b_web < C.COLLECT_MB["fineweb"] * 1e6:
            d["source"] = "fineweb"
            web.append(d)
            b_web += n
        if len(news) % 2000 == 1 and b_news:
            print(f"\r  presse {b_news/1e6:.0f} Mo | web {b_web/1e6:.0f} Mo | lu {scanned/1e6:.0f} Mo",
                  end="", file=sys.stderr)
        if (b_news >= C.COLLECT_MB["fineweb_news"] * 1e6 and b_web >= C.COLLECT_MB["fineweb"] * 1e6) \
                or scanned >= C.FINEWEB_SCAN_MB * 1e6:
            break
    print(file=sys.stderr)
    write_docs(C.RAW / "fineweb_news.jsonl.gz", news)
    write_docs(C.RAW / "fineweb.jsonl.gz", web)
    return len(news) + len(web)


# --- Gutenberg ---------------------------------------------------------------------------------
def gutenberg():
    def cap(t):
        return t[:C.GUTENBERG_MAX_BOOK_BYTES]
    try:
        from datasets import load_dataset
        ds = load_dataset("manu/project_gutenberg", split="fr", streaming=True)
        rows = ({"source": "gutenberg", "id": r.get("id"), "text": cap(r["text"])} for r in ds)
        n = write_docs(C.RAW / "gutenberg.jsonl.gz", take(rows, C.COLLECT_MB["gutenberg"]))
        if n > 50:
            return n
        log("manu/project_gutenberg presque vide, on passe par gutenberg.org")
    except Exception as e:  # noqa: BLE001
        log("manu/project_gutenberg indisponible :", repr(e)[:200], "-> gutenberg.org")
    return gutenberg_direct(cap)


def gutenberg_direct(cap):
    """Plan B : catalogue officiel, livres en français publiés avant 2026-06 (pas de recouvrement
    possible avec la validation, dont les livres sont mis en ligne à partir de juillet 2026)."""
    import requests
    cat = requests.get("https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv", timeout=120).text
    ids = [r["Text#"] for r in csv.DictReader(io.StringIO(cat))
           if r.get("Language") == "fr" and r.get("Type") == "Text" and r.get("Issued", "9999") < "2026-06-01"]
    random.Random(C.SEED).shuffle(ids)
    out, got = [], 0
    for i in ids:
        try:
            r = requests.get(f"https://www.gutenberg.org/cache/epub/{i}/pg{i}.txt", timeout=60)
            if r.status_code != 200:
                continue
            t = cap(r.content.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            continue
        out.append({"source": "gutenberg", "id": i, "text": t})
        got += nbytes(t)
        if len(out) % 20 == 0:
            print(f"\r  gutenberg.org : {len(out)} livres, {got/1e6:.0f} Mo", end="", file=sys.stderr)
        if got >= C.COLLECT_MB["gutenberg"] * 1e6:
            break
        time.sleep(0.3)   # politesse envers le serveur
    print(file=sys.stderr)
    return write_docs(C.RAW / "gutenberg.jsonl.gz", out)


# --- Assemblée nationale -----------------------------------------------------------------------
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_seance(xml_bytes):
    """Un compte rendu Syceron -> (date 'AAAA-MM-JJ', texte au format « Orateur : propos »)."""
    root = ET.fromstring(xml_bytes)
    date = ""
    for el in root.iter():
        if _local(el.tag) == "dateSeance" and el.text:
            d = el.text.strip()
            date = f"{d[:4]}-{d[4:6]}-{d[6:8]}" if d[:8].isdigit() else d[:10]
            break
    paras = []
    for el in root.iter():
        if _local(el.tag) != "paragraphe":
            continue
        nom = ""
        for o in el.iter():
            if _local(o.tag) == "orateur":
                for n in o.iter():
                    if _local(n.tag) == "nom" and n.text:
                        nom = n.text.strip()
                        break
                break
        texte = ""
        for c in el:
            if _local(c.tag) == "texte":
                texte = " ".join("".join(c.itertext()).split())
                break
        if texte:
            paras.append(f"{nom} : {texte}" if nom else texte)
    return date, paras


def zip_ok(path):
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except zipfile.BadZipFile:
        return False


def download_resume(url, path, tries=40):
    """Le serveur de l'Assemblée coupe souvent la connexion en cours de route : on reprend le
    téléchargement là où il s'est arrêté (en-tête HTTP Range) au lieu de tout recommencer."""
    import requests
    for k in range(tries):
        done = path.stat().st_size if path.exists() else 0
        headers = {"Range": f"bytes={done}-"} if done else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=120) as r:
                if r.status_code == 416:      # déjà complet
                    return
                r.raise_for_status()
                mode = "ab" if done and r.status_code == 206 else "wb"
                with open(path, mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if zip_ok(path):
                return
        except Exception as e:  # noqa: BLE001
            log(f"  coupure ({done/1e6:.0f} Mo reçus) : {repr(e)[:80]} -> reprise {k + 1}")
            time.sleep(3)
    raise RuntimeError(f"téléchargement impossible : {url}")


def an():
    import requests
    C.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    out, got, n_files, n_skip = [], 0, 0, 0
    for k, url in enumerate(C.AN_URLS):
        path = C.DOWNLOADS / f"an_{k}.zip"
        if not path.exists() or not zip_ok(path):
            log("téléchargement", url)
            download_resume(url, path)
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".xml"):
                    continue
                try:
                    date, paras = parse_seance(z.read(name))
                except ET.ParseError:
                    continue
                n_files += 1
                if not paras or (date and date >= C.AN_DATE_MAX):
                    n_skip += 1
                    continue
                # on découpe chaque séance en morceaux d'environ 20 000 caractères
                chunk, size = [], 0
                for p in paras:
                    chunk.append(p)
                    size += len(p)
                    if size > 20_000:
                        out.append({"source": "an", "id": name, "date": date, "text": "\n\n".join(chunk)})
                        got += nbytes(out[-1]["text"])
                        chunk, size = [], 0
                if chunk:
                    out.append({"source": "an", "id": name, "date": date, "text": "\n\n".join(chunk)})
                    got += nbytes(out[-1]["text"])
                if got >= C.COLLECT_MB["an"] * 1e6:
                    break
        log(f"AN : {n_files} séances lues, {n_skip} ignorées (vides ou trop récentes), {got/1e6:.0f} Mo")
        if got >= C.COLLECT_MB["an"] * 1e6:
            break
    return write_docs(C.RAW / "an.jsonl.gz", out)


# --- Common Crawl ------------------------------------------------------------------------------
CC_CRAWLS = ["CC-MAIN-2024-51", "CC-MAIN-2024-46", "CC-MAIN-2024-42", "CC-MAIN-2024-38", "CC-MAIN-2024-33"]
HEADERS = {"User-Agent": "feed-the-beast-piscine/1.0 (projet etudiant ECE Paris)"}


def cc_get(url, stream=False, tries=6):
    """Common Crawl limite le débit (réponses 503 / 403 « SlowDown ») : on réessaie en attendant."""
    import requests
    for k in range(tries):
        r = requests.get(url, headers=HEADERS, stream=stream, timeout=600)
        if r.status_code == 200:
            return r
        log(f"  {url[-60:]} -> HTTP {r.status_code}, nouvel essai dans {5 * 2 ** k} s")
        r.close()
        time.sleep(5 * 2 ** k)
    raise RuntimeError(f"Common Crawl inaccessible : {url} (HTTP {r.status_code})")


def cc():
    from warcio.archiveiterator import ArchiveIterator
    base = "https://data.commoncrawl.org/"
    paths, crawl = None, None
    for crawl in [C.CC_CRAWL] + [c for c in CC_CRAWLS if c != C.CC_CRAWL]:
        try:
            paths = gzip.decompress(cc_get(f"{base}crawl-data/{crawl}/wet.paths.gz", tries=3).content).decode().split()
            break
        except Exception as e:  # noqa: BLE001
            log(f"  {crawl} indisponible : {e!r}"[:200])
    if not paths:
        raise RuntimeError("aucun crawl Common Crawl accessible")
    log(f"crawl {crawl} : {len(paths)} fichiers WET")
    picks = [paths[i * (len(paths) // C.CC_N_FILES)] for i in range(C.CC_N_FILES)]   # étalés dans le crawl
    C.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    out, got = [], 0
    for k, p in enumerate(picks):
        local = C.DOWNLOADS / f"cc_{k}.warc.wet.gz"
        if not local.exists():
            log("WET", p)
            with cc_get(base + p, stream=True) as r, open(local, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        with open(local, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type != "conversion":
                    continue
                t = rec.content_stream().read().decode("utf-8", "replace")
                out.append({"source": "cc", "crawl": crawl,
                            "url": rec.rec_headers.get_header("WARC-Target-URI"),
                            "cc_lang": rec.rec_headers.get_header("WARC-Identified-Content-Language"),
                            "text": t})
                got += nbytes(t)
                if got >= C.COLLECT_MB["cc"] * 1e6:
                    break
        log(f"  Common Crawl : {len(out)} pages, {got/1e6:.0f} Mo")
        if got >= C.COLLECT_MB["cc"] * 1e6:
            break
    return write_docs(C.RAW / "cc.jsonl.gz", out)


# --- Molière (kit) -----------------------------------------------------------------------------
def moliere():
    plays = open("corpus/moliere_train.txt", encoding="utf-8").read().split("\n\n=====\n\n")
    return write_docs(C.RAW / "moliere.jsonl.gz", ({"source": "moliere", "text": p} for p in plays if p.strip()))


COLLECTORS = {"moliere": moliere, "wikipedia": wikipedia, "gutenberg": gutenberg, "an": an,
              "fineweb": fineweb, "cc": cc}
