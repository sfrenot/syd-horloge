"""Processus qui échangent des messages UDP, chacun équipé d'une horloge.

Usage : python3 reseau.py physique|lamport|vectorielle|matricielle [-n 3] [-k 6] [--graine 1]

Un observateur omniscient (qui n'existe pas dans un vrai système réparti !) note
l'ordre réel de tous les événements, puis compare ce que les horloges affirment
à la causalité réelle.
"""
import argparse
import json
import random
import socket
import threading
import time

import horloges

PORT = 7100
LATENCE_MAX = 0.05  # secondes


class Journal:
    """L'observateur omniscient : ordre réel des événements."""

    def __init__(self):
        self.evenements, self.verrou = [], threading.Lock()

    def noter(self, pid, type_, msg, estampille):
        with self.verrou:
            self.evenements.append({"pid": pid, "type": type_, "msg": msg,
                                    "estampille": estampille})


def figer(valeur):
    """JSON renvoie des listes ; les estampilles sont manipulées en tuples."""
    return tuple(figer(v) for v in valeur) if isinstance(valeur, list) else valeur


class Processus(threading.Thread):
    def __init__(self, pid, n, horloge, k, journal, graine):
        super().__init__()
        self.pid, self.n, self.k = pid, n, k
        self.horloge, self.journal = horloge, journal
        self.alea = random.Random(graine)
        self.verrou = threading.Lock()  # l'horloge est partagée par deux threads
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", PORT + pid))
        self.sock.settimeout(0.1)
        self.actif = True
        self.recepteur = threading.Thread(target=self.recevoir)

    def run(self):
        self.recepteur.start()
        for i in range(1, self.k + 1):
            time.sleep(self.alea.uniform(0, 0.02))
            if self.alea.random() < 0.3:
                with self.verrou:
                    self.journal.noter(self.pid, "local", None, self.horloge.local())
                continue
            dest = self.alea.choice([p for p in range(self.n) if p != self.pid])
            msg = f"m{self.pid + 1}.{i}"
            with self.verrou:
                estampille = self.horloge.envoi()
                self.journal.noter(self.pid, f"envoi→P{dest + 1}", msg, estampille)
            donnees = json.dumps({"de": self.pid, "msg": msg, "estampille": estampille})
            latence = self.alea.uniform(0, LATENCE_MAX)
            threading.Timer(latence, self.sock.sendto,
                            (donnees.encode(), ("127.0.0.1", PORT + dest))).start()

    def recevoir(self):
        while self.actif:
            try:
                donnees, _ = self.sock.recvfrom(65536)
            except socket.timeout:
                continue
            m = json.loads(donnees)
            with self.verrou:
                estampille = self.horloge.reception(m["de"], figer(m["estampille"]))
                self.journal.noter(self.pid, f"récep←P{m['de'] + 1}", m["msg"], estampille)

    def arreter(self):
        self.actif = False
        self.recepteur.join()
        self.sock.close()


def causalite_reelle(evenements):
    """descendants[i] = événements b tels que i -> b (ordre réel du journal)."""
    successeurs = {i: [] for i in range(len(evenements))}
    dernier, envoi = {}, {}
    for i, e in enumerate(evenements):
        if e["pid"] in dernier:
            successeurs[dernier[e["pid"]]].append(i)
        dernier[e["pid"]] = i
        if e["type"].startswith("envoi"):
            envoi[e["msg"]] = i
        elif e["type"].startswith("récep"):
            successeurs[envoi[e["msg"]]].append(i)
    descendants = {}
    for i in reversed(range(len(evenements))):
        descendants[i] = set()
        for s in successeurs[i]:
            descendants[i] |= {s} | descendants[s]
    return descendants


def cle_de_tri(nom, e):
    if nom in ("physique", "lamport"):
        return (e["estampille"], e["pid"])
    return (sum(horloges.vecteur(e["estampille"], e["pid"])), e["pid"])


def affirme_avant(nom, a, b):
    """L'horloge permet-elle de conclure que a précède b ?"""
    if nom in ("physique", "lamport"):
        return a["estampille"] < b["estampille"]
    va = horloges.vecteur(a["estampille"], a["pid"])
    vb = horloges.vecteur(b["estampille"], b["pid"])
    return horloges.relation(va, vb) == "->"


def analyser(nom, evenements, processus):
    descendants = causalite_reelle(evenements)
    n = len(evenements)
    causales = [(a, b) for a in range(n) for b in descendants[a]]
    concurrentes = [(a, b) for a in range(n) for b in range(a + 1, n)
                    if b not in descendants[a] and a not in descendants[b]]
    coherentes = sum(affirme_avant(nom, evenements[a], evenements[b]) for a, b in causales)
    fausses = sum(affirme_avant(nom, evenements[a], evenements[b])
                  or affirme_avant(nom, evenements[b], evenements[a])
                  for a, b in concurrentes)

    print(f"\nJournal trié selon l'horloge « {nom} » (⚠ = réception placée avant son envoi)")
    vus = set()
    for e in sorted(evenements, key=lambda e: cle_de_tri(nom, e)):
        alerte = "⚠" if e["type"].startswith("récep") and e["msg"] not in vus else " "
        if e["type"].startswith("envoi"):
            vus.add(e["msg"])
        print(f" {alerte} P{e['pid'] + 1}  {e['type']:9} {e['msg'] or '':6} {e['estampille']}")

    print(f"\n{n} événements.")
    print(f"Paires causales réelles (a → b)        : {len(causales):5}")
    print(f"  dont l'horloge affirme a avant b      : {coherentes:5}"
          f"   ({100 * coherentes / max(1, len(causales)):.0f} %, doit valoir 100 %)")
    print(f"Paires concurrentes réelles (a ‖ b)    : {len(concurrentes):5}")
    print(f"  dont l'horloge affirme un ordre       : {fausses:5}   (fausse causalité)")

    if nom == "matricielle":
        for p in processus:
            print(f"\nP{p.pid + 1} : matrice {p.horloge.m}")
            print(f"     événements connus de tous : {p.horloge.stables()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("horloge", choices=horloges.HORLOGES)
    parser.add_argument("-n", type=int, default=3, help="nombre de processus")
    parser.add_argument("-k", type=int, default=6, help="actions par processus")
    parser.add_argument("--graine", type=int, default=None)
    args = parser.parse_args()

    random.seed(args.graine)
    journal = Journal()
    processus = [Processus(pid, args.n, horloges.HORLOGES[args.horloge](pid, args.n),
                           args.k, journal, random.random())
                 for pid in range(args.n)]
    for p in processus:
        p.start()
    for p in processus:
        p.join()
    time.sleep(LATENCE_MAX + 0.1)  # laisser arriver les messages en vol
    for p in processus:
        p.arreter()

    analyser(args.horloge, journal.evenements, processus)


if __name__ == "__main__":
    main()
