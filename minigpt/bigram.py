import math
import random
from collections import defaultdict

train = open("corpus/moliere_train.txt", encoding="utf-8").read()
val = open("corpus/moliere_val.txt", encoding="utf-8").read()

# 1. Compter les paires (caractère, caractère suivant)
counts = defaultdict(lambda: defaultdict(int))
for a, b in zip(train, train[1:]):
    counts[a][b] += 1

vocab = sorted(set(train) | set(val))
V = len(vocab)

# 2. Probabilité de b sachant a, avec lissage (+1) pour ne jamais avoir 0 (Lissage de Laplace)
def prob(a, b):
    total = sum(counts[a].values())
    return (counts[a][b] + 1) / (total + V)

# 3. Loss moyenne sur la validation (en nats) et BPB
nll = 0.0
for a, b in zip(val, val[1:]):
    nll += -math.log(prob(a, b))
n = len(val) - 1
loss = nll / n
bpb = nll / (math.log(2) * len(val[1:].encode("utf-8")))
print(f"loss validation : {loss:.4f} | BPB : {bpb:.4f}")

# 4. Générer 300 caractères
random.seed(0)
c = "\n"
out = []
for _ in range(300):
    suivants = list(counts[c].keys())
    poids = list(counts[c].values())
    c = random.choices(suivants, weights=poids)[0]
    out.append(c)
print("".join(out))