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
    @torch.no_grad()
    def estimate_loss(model, iters=50):
        model.eval()
        out = {}
        for split in ("train", "val"):
            losses = [model(*get_batch(split))[1].item() for _ in range(iters)]
            out[split] = sum(losses) / len(losses)
        model.train()
        return out


    @torch.no_grad()
    def val_bpb(model):
        """BPB sur toute la validation : somme des -log p (en nats) / (ln 2 × nombre d'octets)."""
        model.eval()
        nll, n_tok = 0.0, 0
        for i in range(0, len(val_data) - 1, block_size):
            x = val_data[i : i + block_size].unsqueeze(0).to(device)
            y = val_data[i + 1 : i + block_size + 1].unsqueeze(0).to(device)
            x = x[:, : y.shape[1]]
            logits, _ = model(x)
            nll += F.cross_entropy(logits.view(-1, vocab_size), y.view(-1), reduction="sum").item()
            n_tok += y.numel()
        model.train()
        n_bytes = len(decode(val_data[1 : n_tok + 1].tolist()).encode("utf-8"))
        return nll / (math.log(2) * n_bytes)


    if __name__ == "__main__":
        import json, time
        model = GPT().to(device)
        print(f"{sum(p.numel() for p in model.parameters())/1e6:.2f} M paramètres")
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
        history = []
        t0 = time.time()
        for step in range(max_iters + 1):
            if step % 250 == 0:
                l = estimate_loss(model)
                history.append({"step": step, **l})
                print(f"pas {step:5d} | train {l['train']:.3f} | val {l['val']:.3f} | {time.time()-t0:.0f} s")
            x, y = get_batch("train")
            logits, loss = model(x, y)
            optimizer.zero_grad(set_to_none=True)   # 1. remettre les gradients à zéro
            loss.backward()                         # 2. rétropropagation (comme dans ton autograd !)
            optimizer.step()                        # 3. faire un pas d'optimisation

        bpb = val_bpb(model)
        print(f"BPB validation : {bpb:.4f}")
        torch.save(model.state_dict(), "minigpt/gpt_moliere.pt")

        # 5 échantillons
        with open("minigpt/echantillons.txt", "w", encoding="utf-8") as f:
            for k in range(5):
                torch.manual_seed(k)
                start = torch.tensor([encode("\n")], device=device)
                txt = decode(model.generate(start, 400)[0].tolist())
                print(f"\n=== Échantillon {k+1} ===\n{txt}")
                f.write(f"=== Échantillon {k+1} ===\n{txt}\n\n")

        # courbe de loss
        json.dump({"history": history, "bpb_val": bpb}, open("minigpt/gpt_moliere_log.json", "w"), indent=1)
        import matplotlib.pyplot as plt
        plt.plot([h["step"] for h in history], [h["train"] for h in history], label="train")
        plt.plot([h["step"] for h in history], [h["val"] for h in history], label="validation")
        plt.xlabel("pas"); plt.ylabel("loss (nats)"); plt.title("Mini-GPT sur Molière"); plt.legend()
        plt.savefig("minigpt/courbe_loss.png", dpi=120)
        print("courbe enregistrée : minigpt/courbe_loss.png")