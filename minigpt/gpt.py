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
class Head(nn.Module):
    """Une tête d'attention avec masque causal."""
    def __init__(self, head_size):
        super().__init__()
        self.key = nn.Linear(n_embd, head_size, bias=False)
        self.query = nn.Linear(n_embd, head_size, bias=False)
        self.value = nn.Linear(n_embd, head_size, bias=False)
        self.register_buffer("tril", torch.tril(torch.ones(block_size, block_size)))

    def forward(self, x):
        B, T, C = x.shape
        k = self.key(x)
        q = self.query(x)
        scores = q @ k.transpose(-2, -1) / math.sqrt(k.shape[-1])
        scores = scores.masked_fill(self.tril[:T, :T] == 0, float("-inf"))
        poids = F.softmax(scores, dim=-1)
        v = self.value(x)
        return poids @ v


class MultiHeadAttention(nn.Module):
    def __init__(self):
        super().__init__()
        head_size = n_embd // n_head
        self.heads = nn.ModuleList([Head(head_size) for _ in range(n_head)])
        self.proj = nn.Linear(n_embd, n_embd)

    def forward(self, x):
        out = torch.cat([h(x) for h in self.heads], dim=-1)
        return self.proj(out)


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(n_embd, 4 * n_embd), nn.GELU(), nn.Linear(4 * n_embd, n_embd))

    def forward(self, x):
        return self.net(x)


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = MultiHeadAttention()
        self.ln2 = nn.LayerNorm(n_embd)
        self.mlp = MLP()

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class GPT(nn.Module):
    def __init__(self):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.Sequential(*[Block() for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        x = self.tok_emb(idx) + self.pos_emb(torch.arange(T, device=idx.device))
        x = self.blocks(x)
        logits = self.head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(B * T, -1), targets.view(B * T))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, n):
        for _ in range(n):
            logits, _ = self(idx[:, -block_size:])
            probs = F.softmax(logits[:, -1, :], dim=-1)
            nxt = torch.multinomial(probs, 1)
            idx = torch.cat([idx, nxt], dim=1)
        return idx
if __name__ == "__main__":
    model = GPT().to(device)
    print(f"{sum(p.numel() for p in model.parameters())/1e6:.2f} M paramètres")
    x, y = get_batch("train")
    logits, loss = model(x, y)
    print(logits.shape, f"loss initiale : {loss.item():.3f} (attendu ≈ {math.log(vocab_size):.3f})")