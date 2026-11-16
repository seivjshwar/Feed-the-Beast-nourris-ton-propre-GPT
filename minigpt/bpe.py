class BPE:
    def __init__(self):
        self.merges = {}                                  # (a, b) -> nouveau numéro, dans l'ordre d'apprentissage
        self.vocab = {i: bytes([i]) for i in range(256)}  # numéro -> octets qu'il représente

    @staticmethod
    def get_stats(ids):
        """Compte chaque paire de voisins : [1, 2, 3, 1, 2] -> {(1,2): 2, (2,3): 1, (3,1): 1}"""
        counts = {}
        for pair in zip(ids, ids[1:]):
            counts[pair] = counts.get(pair, 0) + 1      
        return counts

    @staticmethod
    def merge(ids, pair, idx):
        """Remplace chaque occurrence de `pair` par le numéro `idx`."""
        out, i = [], 0
        while i < len(ids):
            if i < len(ids) - 1 and (ids[i], ids[i + 1]) == pair:
                out.append(idx)                           # le nouveau numéro
                i += 2
            else:
                out.append(ids[i])
                i += 1                                  
        return out

    def train(self, text, vocab_size, verbose=False):
        ids = list(text.encode("utf-8"))
        for k in range(vocab_size - 256):
            stats = self.get_stats(ids)
            pair = max(stats, key=stats.get)              # la paire la plus fréquente
            idx = 256 + k
            ids = self.merge(ids, pair, idx)
            self.merges[pair] = idx
            self.vocab[idx] = self.vocab[pair[0]] + self.vocab[pair[1]]   # les octets du nouveau token
            if verbose and k % 50 == 0:
                print(k, repr(self.vocab[idx].decode("utf-8", "replace")))

    def encode(self, text):
        ids = list(text.encode("utf-8"))
        while len(ids) >= 2:
            stats = self.get_stats(ids)
            # la paire apprise le plus tôt (plus petit numéro) passe en premier
            pair = min(stats, key=lambda p: self.merges.get(p, float("inf")))
            if pair not in self.merges:
                break                                     # plus aucune fusion possible
            ids = self.merge(ids, pair, self.merges[pair])
        return ids

    def decode(self, ids):
        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")


if __name__ == "__main__":
    text = open("corpus/moliere_train.txt", encoding="utf-8").read()[:200_000]
    bpe = BPE()
    bpe.train(text, 512, verbose=True)
    s = "Monsieur, je vous demande pardon."
    ids = bpe.encode(s)
    print(ids, len(s.encode("utf-8")), "octets ->", len(ids), "tokens")
    assert bpe.decode(ids) == s, "decode(encode(s)) doit redonner s"
    print("aller-retour OK")