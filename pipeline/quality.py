"""Étape 4 : filtrage qualité (heuristiques de Gopher, Rae et al. 2021) et masquage des données
personnelles."""

import re

from pipeline.clean import FR_STOPWORDS

WORD = re.compile(r"\S+")
ALPHA = re.compile(r"[^\W\d_]", re.UNICODE)


def gopher_reason(text):
    """Renvoie la règle qui rejette le document, ou None s'il passe."""
    words = WORD.findall(text)
    n = len(words)
    if n < 50 or n > 100_000:
        return "nb_mots"
    mean_len = sum(len(w) for w in words) / n
    if mean_len < 3 or mean_len > 10:
        return "longueur_mots"
    if (text.count("#") + text.count("...") + text.count("…")) / n > 0.1:
        return "symboles"
    lines = [l for l in text.split("\n") if l.strip()]
    if lines:
        if sum(l.lstrip().startswith(("•", "-", "*", "·")) for l in lines) / len(lines) > 0.9:
            return "puces"
        if sum(l.rstrip().endswith(("...", "…")) for l in lines) / len(lines) > 0.3:
            return "points_suspension"
        if len(set(lines)) / len(lines) < 0.7:
            return "lignes_repetees"
    if sum(bool(ALPHA.search(w)) for w in words) / n < 0.8:
        return "peu_de_mots"
    lw = {w.lower().strip(".,;:!?«»\"'()") for w in words[:2000]}
    if len(lw & FR_STOPWORDS) < 4:
        return "pas_de_mots_outils"
    return None


# --- Données personnelles ----------------------------------------------------------------
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+33\s?|0033\s?|0)[1-9](?:[\s.-]?\d{2}){4}(?!\d)")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IBAN = re.compile(r"\bFR\d{2}(?:\s?\w{4}){5}\s?\w{3}\b")


def mask_pii(text, stats):
    for name, pat, repl in (("email", EMAIL, "[EMAIL]"), ("telephone", PHONE, "[TÉLÉPHONE]"),
                            ("iban", IBAN, "[IBAN]"), ("ip", IPV4, "[IP]")):
        text, k = pat.subn(repl, text)
        if k:
            stats["pii_" + name] = stats.get("pii_" + name, 0) + k
    return text
