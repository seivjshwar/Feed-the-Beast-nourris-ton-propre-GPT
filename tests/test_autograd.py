import torch
from minigpt.autograd import Value

def test_gradients_comme_pytorch():
    # --- avec ta classe Value ---
    x1, x2 = Value(2.0), Value(0.0)
    w1, w2 = Value(-3.0), Value(1.0)
    b = Value(6.88)
    o = (x1*w1 + x2*w2 + b).tanh()
    o.backward()

    # --- le même calcul avec PyTorch ---
    tx1 = torch.tensor(2.0, dtype=torch.float64, requires_grad=True)
    tx2 = torch.tensor(0.0, dtype=torch.float64, requires_grad=True)
    tw1 = torch.tensor(-3.0, dtype=torch.float64, requires_grad=True)
    tw2 = torch.tensor(1.0, dtype=torch.float64, requires_grad=True)
    tb  = torch.tensor(6.88, dtype=torch.float64, requires_grad=True)
    to = torch.tanh(tx1*tw1 + tx2*tw2 + tb)
    to.backward()

    # --- comparaison ---
    assert abs(o.data - to.item()) < 1e-6
    for mien, ref in [(x1, tx1), (x2, tx2), (w1, tw1), (w2, tw2), (b, tb)]:
        assert abs(mien.grad - ref.grad.item()) < 1e-6