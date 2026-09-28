"""Calcule les estampilles d'un scénario écrit à la main et dessine son diagramme.

Usage : python3 scenario.py fichier.txt [--matrices] [--concurrents] [--svg sortie.svg [--avec lamport|vecteur]]

Format du scénario (une ligne par processus, événements dans l'ordre local) :

    # commentaire
    P1: a b>m1 c           a : événement interne
    P2: d<m1 e             b>m1 : envoi du message m1 ; d<m1 : sa réception
    P3[pas=5]: f           pas : incrément de l'horloge de Lamport de P3 (défaut 1)

Le résultat ne dépend que de la causalité, pas de l'entrelacement choisi.
"""
import argparse
import re
import sys

import horloges

LIGNE = re.compile(r"^\s*(\w+)\s*(?:\[pas=(\d+)\])?\s*:(.*)$")
EVENEMENT = re.compile(r"^(\w+)(?:([<>])(\w+))?$")


def lire(fichier):
    processus = []
    with open(fichier, encoding="utf-8") as f:
        for numero, ligne in enumerate(f, 1):
            ligne = ligne.split("#")[0].strip()
            if not ligne:
                continue
            m = LIGNE.match(ligne)
            if not m:
                sys.exit(f"{fichier}:{numero} : ligne illisible : {ligne}")
            evenements = []
            for jeton in m.group(3).split():
                e = EVENEMENT.match(jeton)
                if not e:
                    sys.exit(f"{fichier}:{numero} : événement illisible : {jeton}")
                nom, sens, msg = e.groups()
                type_ = {">": "envoi", "<": "reception", None: "local"}[sens]
                evenements.append({"nom": nom, "type": type_, "msg": msg})
            processus.append({"nom": m.group(1), "pas": int(m.group(2) or 1),
                              "evenements": evenements})
    return processus


def executer(processus):
    """Rejoue le scénario ; renvoie les événements dans un ordre d'exécution valide."""
    n = len(processus)
    for pid, p in enumerate(processus):
        p["horloges"] = (horloges.Lamport(pid, n, p["pas"]),
                         horloges.Vectorielle(pid, n), horloges.Matricielle(pid, n))
    emis, ordre = {}, []
    curseurs = [0] * n
    while any(c < len(p["evenements"]) for c, p in zip(curseurs, processus)):
        progres = False
        # un événement par processus par tour : le diagramme reste équilibré
        for pid, p in enumerate(processus):
            if curseurs[pid] == len(p["evenements"]):
                continue
            e = p["evenements"][curseurs[pid]]
            if e["type"] == "reception" and e["msg"] not in emis:
                continue  # le message n'est pas encore parti
            if e["type"] == "local":
                e["estampilles"] = [h.local() for h in p["horloges"]]
            elif e["type"] == "envoi":
                e["estampilles"] = [h.envoi() for h in p["horloges"]]
                emis[e["msg"]] = (pid, e)
            else:
                emetteur, envoi = emis[e["msg"]]
                e["estampilles"] = [h.reception(emetteur, s) for h, s
                                    in zip(p["horloges"], envoi["estampilles"])]
            e["pid"] = pid
            ordre.append(e)
            curseurs[pid] += 1
            progres = True
        if not progres:
            bloques = [p["evenements"][c]["msg"] for c, p in zip(curseurs, processus)
                       if c < len(p["evenements"])]
            sys.exit(f"Blocage : messages jamais envoyés (ou cycle) : {bloques}")
    return ordre


def afficher(processus, ordre, matrices, concurrents):
    print(f"{'événement':10} {'proc.':6} {'type':14} {'Lamport':>8}   vecteur")
    for p in processus:
        for e in p["evenements"]:
            detail = {"local": "interne", "envoi": f"envoi {e['msg']}",
                      "reception": f"récep. {e['msg']}"}[e["type"]]
            lamport, vect, matrice = e["estampilles"]
            print(f"{e['nom']:10} {p['nom']:6} {detail:14} {lamport:8}   {vect}")
            if matrices:
                for ligne, q in zip(matrice, processus):
                    print(f"{'':42}{q['nom']:>4} {ligne}")
        print()

    paires = [(a, b) for i, a in enumerate(ordre) for b in ordre[i + 1:]
              if horloges.relation(a["estampilles"][1], b["estampilles"][1]) == "||"]
    pieges = [(a, b) for a, b in paires if a["estampilles"][0] != b["estampilles"][0]]
    if concurrents:
        print("Événements concurrents :", " ".join(f"{a['nom']}‖{b['nom']}" for a, b in paires))
    print(f"{len(paires)} paires concurrentes, dont {len(pieges)} avec des estampilles "
          f"de Lamport différentes (l'horloge scalaire suggère un ordre qui n'existe pas).")

    if matrices:
        print()
        for p in processus:
            print(f"{p['nom']} final : connus de tous = {p['horloges'][2].stables()}")


def svg(processus, ordre, fichier, avec):
    dx, dy, marge = 64, 90, 70
    x = {id(e): marge + 40 + i * dx for i, e in enumerate(ordre)}
    largeur = marge + 80 + len(ordre) * dx
    hauteur = 10 + len(processus) * dy
    y = lambda pid: 50 + pid * dy
    emis = {e["msg"]: e for e in ordre if e["type"] == "envoi"}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur}" height="{hauteur}" '
           f'viewBox="0 0 {largeur} {hauteur}" font-family="Helvetica, Arial, sans-serif">',
           '<style>text { paint-order: stroke; stroke: white; stroke-width: 4px; '
           'stroke-linejoin: round; }</style>',
           '<defs><marker id="fleche" viewBox="0 0 10 10" refX="10" refY="5" '
           'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           '<path d="M0,0 L10,5 L0,10 z" fill="#1f5fa8"/></marker></defs>',
           f'<rect width="{largeur}" height="{hauteur}" fill="white"/>']
    for pid, p in enumerate(processus):
        out.append(f'<text x="16" y="{y(pid) + 5}" font-size="16" font-weight="bold">{p["nom"]}</text>')
        out.append(f'<line x1="{marge}" y1="{y(pid)}" x2="{largeur - 20}" y2="{y(pid)}" '
                   'stroke="#333" stroke-width="1.5" marker-end="url(#fleche)"/>')
    for e in ordre:
        if e["type"] == "reception":
            s = emis[e["msg"]]
            x1, y1, x2, y2 = x[id(s)], y(s["pid"]), x[id(e)], y(e["pid"])
            longueur = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            ux, uy = (x2 - x1) / longueur, (y2 - y1) / longueur
            out.append(f'<line x1="{x1 + 6 * ux:.1f}" y1="{y1 + 6 * uy:.1f}" '
                       f'x2="{x2 - 8 * ux:.1f}" y2="{y2 - 8 * uy:.1f}" '
                       'stroke="#1f5fa8" stroke-width="1.3" marker-end="url(#fleche)"/>')
            out.append(f'<text x="{(x1 + x2) / 2 + 6}" y="{(y1 + y2) / 2}" font-size="12" '
                       f'fill="#1f5fa8" font-style="italic">{e["msg"]}</text>')
    for e in ordre:
        cx, cy = x[id(e)], y(e["pid"])
        out.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="#111"/>')
        out.append(f'<text x="{cx}" y="{cy - 10}" font-size="14" text-anchor="middle">{e["nom"]}</text>')
        if avec:
            valeur = e["estampilles"][0] if avec == "lamport" else \
                "(" + ",".join(map(str, e["estampilles"][1])) + ")"
            out.append(f'<text x="{cx}" y="{cy + 22}" font-size="12" text-anchor="middle" '
                       f'fill="#b3261e">{valeur}</text>')
    out.append("</svg>")
    with open(fichier, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"diagramme écrit dans {fichier}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fichier")
    parser.add_argument("--matrices", action="store_true", help="afficher les horloges matricielles")
    parser.add_argument("--concurrents", action="store_true", help="lister les paires concurrentes")
    parser.add_argument("--svg", help="écrire le diagramme espace-temps")
    parser.add_argument("--avec", choices=["lamport", "vecteur"], help="estampilles sur le diagramme")
    args = parser.parse_args()

    processus = lire(args.fichier)
    ordre = executer(processus)
    afficher(processus, ordre, args.matrices, args.concurrents)
    if args.svg:
        svg(processus, ordre, args.svg, args.avec)


if __name__ == "__main__":
    main()
