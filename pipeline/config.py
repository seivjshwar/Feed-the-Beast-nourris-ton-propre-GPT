"""Paramètres du pipeline : volumes collectés, mélange final, seuils.

Tout est ici pour que les choix soient visibles (et justifiables en soutenance).
"""

from pathlib import Path

DATA = Path("data")
RAW = DATA / "raw"          # données collectées, telles quelles
CLEAN = DATA / "clean"      # après nettoyage (encodage, langue, boilerplate)
FULL = DATA / "full"        # après déduplication, filtrage qualité, masquage des données perso
MIX = DATA / "mix"          # les trois datasets d'ablation : brut / nettoye / complet
DOWNLOADS = DATA / "downloads"

# --- Collecte : volume visé par source (Mo de texte brut) ---------------------------------
COLLECT_MB = {
    "wikipedia": 170,       # encyclopédique
    "gutenberg": 220,       # littéraire
    "an": 400,              # dialogue (comptes rendus de l'Assemblée nationale), plafond
    "fineweb_news": 110,    # presse : FineWeb-2 restreint aux domaines de presse
    "fineweb": 80,          # web français général (déjà filtré par Hugging Face)
    "cc": 400,              # Common Crawl brut (fichiers WET, toutes langues)
}
FINEWEB_SCAN_MB = 2500      # volume max lu dans FineWeb-2 pour trouver la presse
CC_CRAWL = "CC-MAIN-2024-51"  # crawl de décembre 2024 : antérieur à la validation et au test
CC_N_FILES = 3
AN_DATE_MAX = "2026-09-01"  # on exclut les séances récentes (la validation date d'octobre 2026)
AN_URLS = [
    "https://data.assemblee-nationale.fr/static/openData/repository/17/vp/syceronbrut/syseron.xml.zip",
    "https://data.assemblee-nationale.fr/static/openData/repository/16/vp/syceronbrut/syseron.xml.zip",
]
GUTENBERG_MAX_BOOK_BYTES = 600_000

# Domaines de presse francophone (pour la part « presse » du mélange)
NEWS_DOMAINS = [
    "lemonde.fr", "lefigaro.fr", "liberation.fr", "francetvinfo.fr", "20minutes.fr", "ouest-france.fr",
    "lexpress.fr", "lepoint.fr", "rfi.fr", "france24.com", "la-croix.com", "huffingtonpost.fr",
    "bfmtv.com", "leparisien.fr", "sudouest.fr", "ladepeche.fr", "actu.fr", "lavoixdunord.fr",
    "nouvelobs.com", "letemps.ch", "rtbf.be", "lesoir.be", "radio-canada.ca", "ledevoir.com",
    "lapresse.ca", "latribune.fr", "lesechos.fr", "challenges.fr", "marianne.net",
    "courrierinternational.com", "radiofrance.fr", "francebleu.fr", "europe1.fr", "rtl.fr",
    "tf1info.fr", "lci.fr", "midilibre.fr", "letelegramme.fr", "ledauphine.com", "leprogres.fr",
    "estrepublicain.fr", "dna.fr", "lalsace.fr", "nicematin.com", "laprovence.com", "lindependant.fr",
    "republicain-lorrain.fr", "lamontagne.fr", "centrepresseaveyron.fr", "lejdd.fr", "valeursactuelles.com",
    "humanite.fr", "mediapart.fr", "slate.fr", "rts.ch", "tdg.ch", "24heures.ch", "lalibre.be",
    "dhnet.be", "journaldemontreal.com", "lesoleil.com", "tv5monde.com", "jeuneafrique.com",
    "linfo.re", "clicanoo.re", "lequipe.fr", "capital.fr", "usinenouvelle.com", "sciencesetavenir.fr",
]

# --- Mélange final : part de chaque source, en octets ---------------------------------------
# Le set de validation (et le test) contient 4 genres à parts égales : on vise ~25 % chacun.
MIX_SHARES = {
    "wikipedia": 0.25,      # encyclopédique
    "gutenberg": 0.21,      # littéraire
    "moliere": 0.03,        # littéraire (corpus du kit)
    "an": 0.24,             # dialogue
    "fineweb_news": 0.15,   # presse
    "fineweb": 0.07,        # web général
    "cc": 0.05,             # Common Crawl traité par notre pipeline
}
MIX_TARGET_MB = 450         # ~100M tokens avec un BPE de 8 192 (≈ 4,4 octets par token)
MAX_REPEAT = 4              # une source trop petite est répétée au plus 4 fois
TAIL_FRACTION = 0.10        # les derniers 10 % du flux : données les plus propres (fin d'entraînement)
TAIL_SOURCES = ["wikipedia", "gutenberg", "an", "fineweb_news"]
SEED = 0

# --- Seuils --------------------------------------------------------------------------------
LANG_MIN_PROB = 0.65        # proba minimale « fr » (fastText lid.176)
LANG_SOURCES = ["cc", "fineweb", "fineweb_news", "gutenberg"]   # Wikipédia, AN, Molière : déjà en français
MINHASH_THRESHOLD = 0.8     # Jaccard sur 5-grammes de mots (seuil de FineWeb et de Lee et al. 2021)
MINHASH_PERM = 128
MINHASH_NGRAM = 5
MINHASH_MAX_WORDS = 2000
WEB_SOURCES = ["cc", "fineweb", "fineweb_news"]   # sources où on applique les filtres de type Gopher
