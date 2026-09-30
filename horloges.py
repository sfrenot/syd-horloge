"""Quatre horloges pour systèmes répartis, avec la même interface.

    h = Lamport(pid, n)
    h.local()                   -> estampille d'un événement interne
    h.envoi()                   -> estampille à joindre au message envoyé
    h.reception(emetteur, e)    -> estampille de l'événement de réception

pid est le numéro du processus (0..n-1), n le nombre de processus.
"""
import random
import time


class Physique:
    """Horloge matérielle imparfaite : décalage initial et dérive (en ms)."""

    def __init__(self, pid, n, decalage=None, derive=None):
        self.pid = pid
        self.decalage = random.uniform(0, 60) if decalage is None else decalage
        self.derive = random.uniform(-0.05, 0.05) if derive is None else derive
        self.origine = time.monotonic()

    def lire(self):
        ecoule_ms = (time.monotonic() - self.origine) * 1000
        return round(self.decalage + ecoule_ms * (1 + self.derive))

    def local(self):
        return self.lire()

    def envoi(self):
        return self.lire()

    def reception(self, emetteur, estampille):
        return self.lire()  # l'estampille reçue est ignorée


class Lamport:
    """Horloge scalaire. pas > 1 simule une machine dont l'horloge avance plus vite."""

    def __init__(self, pid, n, pas=1):
        self.pid, self.pas, self.c = pid, pas, 0

    def local(self):
        self.c += self.pas
        return self.c

    def envoi(self):
        return self.local()

    def reception(self, emetteur, estampille):
        self.c = max(self.c + self.pas, estampille + 1)
        return self.c


class Vectorielle:
    """v[k] = nombre d'événements de P_k dont ce processus a connaissance."""

    def __init__(self, pid, n):
        self.pid, self.v = pid, [0] * n

    def local(self):
        self.v[self.pid] += 1
        return tuple(self.v)

    def envoi(self):
        return self.local()

    def reception(self, emetteur, estampille):
        self.v = [max(a, b) for a, b in zip(self.v, estampille)]
        return self.local()


class Matricielle:
    """m[pid] est le vecteur du processus ; m[k] ce qu'il sait du vecteur de P_k."""

    def __init__(self, pid, n):
        self.pid, self.n = pid, n
        self.m = [[0] * n for _ in range(n)]

    def _figer(self):
        return tuple(tuple(ligne) for ligne in self.m)

    def local(self):
        self.m[self.pid][self.pid] += 1
        return self._figer()

    def envoi(self):
        return self.local()

    def reception(self, emetteur, estampille):
        i, j = self.pid, emetteur
        for k in range(self.n):
            # ce que je sais : tout ce que l'émetteur savait...
            self.m[i][k] = max(self.m[i][k], estampille[j][k])
            # ... et ce qu'il savait de ce que savent les autres
            for l in range(self.n):
                self.m[k][l] = max(self.m[k][l], estampille[k][l])
        return self.local()

    def stables(self):
        """Pour chaque P_l : nombre de ses événements connus de tous les processus."""
        return [min(self.m[k][l] for k in range(self.n)) for l in range(self.n)]


HORLOGES = {"physique": Physique, "lamport": Lamport,
            "vectorielle": Vectorielle, "matricielle": Matricielle}


def vecteur(estampille, pid):
    """Partie vectorielle d'une estampille (la ligne propre pour une matrice)."""
    if isinstance(estampille[0], tuple):
        return estampille[pid]
    return estampille


def relation(a, b):
    """Relation entre deux estampilles vectorielles : '=', '->', '<-' ou '||'."""
    if a == b:
        return "="
    if all(x <= y for x, y in zip(a, b)):
        return "->"
    if all(x >= y for x, y in zip(a, b)):
        return "<-"
    return "||"
