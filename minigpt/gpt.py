import math
import torch
import torch.nn as nn
from torch.nn import functional as F

torch.manual_seed(1337)
device = "mps" if torch.backends.mps.is_available() else "cpu"

# --- Hyperparamètres (petit modèle : ~15 min d'entraînement sur un Mac) ---
block_size = 128     # contexte : combien de caractères le modèle voit en arrière
batch_size = 32      # nombre de séquences par pas
n_embd = 192         # taille des vecteurs
n_head = 6           # nombre de têtes d'attention
n_layer = 4          # nombre de blocs
max_iters = 3000
lr = 1e-3

# --- Données ---
train_text = open("corpus/moliere_train.txt", encoding="utf-8").read()
val_text = open("corpus/moliere_val.txt", encoding="utf-8").read()
chars = sorted(set(train_text) | set(val_text))
vocab_size = len(chars)
stoi = {c: i for i, c in enumerate(chars)}     # caractère -> numéro
itos = {i: c for i, c in enumerate(chars)}     # numéro -> caractère

def encode(s):
    return [stoi[c] for c in s]

def decode(ids):
    return "".join(itos[i] for i in ids)

train_data = torch.tensor(encode(train_text), dtype=torch.long)
val_data = torch.tensor(encode(val_text), dtype=torch.long)

def get_batch(split):
    data = train_data if split == "train" else val_data
    ix = torch.randint(len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix])
    y = torch.stack([data[ i + 1 :i + block_size + 1] for i in ix])
    return x.to(device), y.to(device)

if __name__ == "__main__":
    print("vocabulaire :", vocab_size, "caractères | device :", device)
    print(decode(encode("Bonjour Monsieur")))
    x, y = get_batch("train")
    print(x.shape, y.shape)
    print(repr(decode(x[0][:30].tolist())))
    print(repr(decode(y[0][:30].tolist())))