"""Étape 2 : nettoyage. Réparation de l'encodage, identification de la langue, boilerplate."""

import os
import re
import sys

import ftfy

from pipeline import config as C

# --- Encodage -----------------------------------------------------------------------------------
def fix_encoding(text):
    # uncurl_quotes=False : on garde les apostrophes typographiques (’), présentes dans la validation
    return ftfy.fix_text(text, uncurl_quotes=False)


# --- Langue ------------------------------------------------------------------------------------
FR_STOPWORDS = {"le", "la", "les", "de", "des", "du", "et", "est", "un", "une", "que", "qui", "dans",
                "pour", "pas", "sur", "au", "avec", "il", "elle", "nous", "vous", "ce", "se", "ne",
                "par", "plus", "sont", "mais", "ou", "son", "sa", "ses", "leur", "aux", "été"}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


class LangID:
    """fastText lid.176 (Joulin et al.) ; repli sur un détecteur par mots-outils si fastText manque."""

    URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"

    def __init__(self, path="data/downloads/lid.176.bin"):
        self.model = None
        try:
            import fasttext
            if not os.path.exists(path):
                import requests
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(requests.get(self.URL, timeout=600).content)
            fasttext.FastText.eprint = lambda *a, **k: None
            self.model = fasttext.load_model(path)
            self.name = "fasttext-lid176"
        except Exception as e:  # noqa: BLE001
            print("[langue] fastText indisponible, repli sur les mots-outils :", repr(e)[:150], file=sys.stderr)
            self.name = "mots-outils"

    def predict(self, text):
        """-> (langue, probabilité)"""
        t = " ".join(text.split())[:3000]
        if not t:
            return "?", 0.0
        if self.model is not None:
            try:
                labels, probs = self.model.predict(t, k=1)
                return labels[0].replace("__label__", ""), float(probs[0])
            except ValueError:   # fasttext 0.9.2 + numpy 2 : on appelle la fonction interne
                prob, label = self.model.f.predict(t, 1, 0.0, "strict")[0]
                return label.replace("__label__", ""), float(prob)
        words = [w.lower() for w in WORD.findall(t)[:500]]
        if not words:
            return "?", 0.0
        ratio = sum(w in FR_STOPWORDS for w in words) / len(words)
        return ("fr", min(1.0, ratio * 3)) if ratio > 0.15 else ("autre", 1 - ratio)

    def is_french(self, text):
        lang, p = self.predict(text)
        return lang == "fr" and p >= C.LANG_MIN_PROB


# --- Boilerplate du web ----------------------------------------------------------------------
BOILER = re.compile(
    r"cookie|javascript|tous droits réservés|all rights reserved|politique de confidentialité|"
    r"mentions légales|conditions générales|abonnez-vous|newsletter|cliquez ici|lire aussi|"
    r"partager sur|se connecter|mot de passe|inscrivez-vous|accepter et fermer|©|"
    r"publicité|votre navigateur|contenu sponsorisé|commentaires? \(\d+\)",
    re.IGNORECASE)
TERMINAL = tuple(".!?»…:;\"”)")


def strip_boilerplate(text):
    """Supprime, ligne par ligne : menus (lignes courtes sans ponctuation finale), mentions de cookies,
    liens de partage, lignes répétées. Inspiré des règles de C4 (Raffel et al. 2019) et de CCNet."""
    out, seen = [], set()
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            out.append("")
            continue
        if BOILER.search(s) and len(s) < 250:
            continue
        if len(s.split()) < 4 and not s.endswith(TERMINAL):
            continue
        if s in seen and len(s) < 200:      # ligne répétée (menu, pied de page)
            continue
        seen.add(s)
        out.append(s)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# --- Gutenberg : en-têtes de licence et retours à la ligne --------------------------------
START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.IGNORECASE)
END = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", re.IGNORECASE)
END_OLD = re.compile(r"End of (the )?Project Gutenberg", re.IGNORECASE)


def strip_gutenberg(text):
    m = START.search(text)
    if m:
        text = text[m.end():]
    m = END.search(text) or END_OLD.search(text)
    if m:
        text = text[:m.start()]
    lines = [l for l in text.split("\n")
             if not re.match(r"\s*(Produced by|This file was produced|\[Illustration)", l, re.IGNORECASE)]
    return "\n".join(lines).strip()


def reflow(text):
    """Les livres Gutenberg sont coupés à ~70 caractères par ligne. On recolle chaque paragraphe
    sur une seule ligne, comme dans la validation : sinon le modèle apprend des « \\n » parasites."""
    paras = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    out = []
    for p in paras:
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        if not lines:
            continue
        out.append(" ".join(lines))
    return "\n\n".join(out)


def clean_doc(doc, langid, stats):
    """Renvoie le document nettoyé, ou None s'il est rejeté (la raison est comptée dans stats)."""
    src = doc["source"]
    t = fix_encoding(doc["text"])
    if t != doc["text"]:
        stats["encodage_repare"] = stats.get("encodage_repare", 0) + 1
    if src == "gutenberg":
        t = reflow(strip_gutenberg(t))
    if src in C.WEB_SOURCES:
        t = strip_boilerplate(t)
    if len(t) < 200:
        stats["trop_court"] = stats.get("trop_court", 0) + 1
        return None
    if src in C.LANG_SOURCES and not langid.is_french(t):
        stats["pas_francais"] = stats.get("pas_francais", 0) + 1
        return None
    return {**doc, "text": t}
