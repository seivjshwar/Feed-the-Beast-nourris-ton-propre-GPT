class Value:

    def __init__(self, data, _children=(), _op=''):
        self.data = data
        self.grad = 0.0
        self._prev = set(_children)
        self._op = _op
        self._backward = lambda: None

    def __repr__(self):
        return f"Value(data={self.data})"
    
    def __add__(self, other):
        out = Value(self.data + other.data, (self, other), '+')

        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward

        return out

    def __mul__(self, other):
        out= Value(self.data * other.data, (self, other), '*')
        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        
        return out

    def backward(self):
        topo = []
        visited = set()

        def build(v):
            if v not in visited:
                visited.add(v)
                for parent in v._prev:
                    build(parent)   # d'abord les parents
                topo.append(v)      # puis le nombre lui-même

        build(self)

        self.grad = 1.0             # le point de départ
        for v in reversed(topo):
            v._backward()           # appeler la fonction qui transmet le gradient

if __name__ == "__main__":
    a = Value(2.0)
    b = Value(-3.0)
    c = a * b + Value(10.0)
    c.backward()
    print("a.grad =", a.grad)   # attendu : -3.0
    print("b.grad =", b.grad)   # attendu :  2.0