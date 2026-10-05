# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

TD « Temps et causalité » du cours SYD (INSA Lyon) : horloges physique, de Lamport, vectorielle et matricielle. Tout le contenu (code, identifiants, commentaires, sujet) est en **français** ; garder ce style. Python ≥ 3.10, bibliothèque standard uniquement (pas de dépendances, pas de suite de tests, pas de build).

- `README.md` est le **sujet distribué aux étudiants** (questions I1–I3 de l'introduction, questions numérotées 1–24, exercices, questions d'examen E1–E13).
- `CORRECTION.md` est **réservé à l'enseignant** ; ses valeurs numériques sont vérifiées avec `scenario.py`. Ne pas en recopier de réponses dans `README.md`. Si une question du sujet est renumérotée ou modifiée, mettre à jour la correction en parallèle.

## Commandes

```bash
python3 reseau.py physique|lamport|vectorielle|matricielle [-n 3] [-k 6] [--graine 1] [--paires]
python3 scenario.py exercices/exo1.txt [--matrices] [--concurrents]
python3 scenario.py exercices/exo1.txt --svg exercices/exo1.svg                               # diagramme vierge (sujet)
python3 scenario.py exercices/exo1.txt --svg exercices/correction/exo1-lamport.svg --avec lamport   # diagramme annoté
```

Les SVG de `exercices/` et `exercices/correction/` sont générés par `scenario.py` : après modification d'un `exoN.txt`, les régénérer plutôt que les éditer à la main (le fichier `exo1.txt` sert aux exercices 1 et 3, d'où `exo3-vecteur.svg`). Chaque SVG a un PNG jumeau (pour diapos et documents), à régénérer ensuite ; `README.md` continue de référencer les SVG :

```bash
for f in exercices/*.svg exercices/correction/*.svg; do rsvg-convert -z 2 -b white "$f" -o "${f%.svg}.png"; done
```

## Architecture

- `horloges.py` : les quatre horloges partagent la même interface `local()`, `envoi()`, `reception(emetteur, estampille)`, toutes renvoyant l'estampille de l'événement. Les estampilles sont des valeurs immuables (int, tuple, tuple de tuples) ; `vecteur()` extrait la ligne propre d'une matrice pour que `relation()` (`=`, `->`, `<-`, `||`) fonctionne sur vectorielles comme matricielles. `HORLOGES` est le registre nom → classe utilisé par les deux scripts. `Lamport(pas=…)` simule une horloge qui avance plus vite.
- `reseau.py` : exécution réelle et non déterministe. Chaque processus est un thread avec une socket UDP sur `127.0.0.1:7100+pid` et un thread récepteur ; la latence est simulée par `threading.Timer` avant `sendto`. Un `Journal` global (« observateur omniscient ») enregistre l'ordre réel ; `analyser()` reconstruit la causalité réelle à partir de ce journal et la compare à ce qu'affirme l'horloge (paires causales / fausse causalité). Les estampilles transitent en JSON, d'où `figer()` pour reconvertir listes → tuples.
- `scenario.py` : rejoue de façon déterministe un scénario écrit à la main (format documenté dans la docstring : `P1: a b>m1 c`, `d<m1`, `P3[pas=5]:`). `executer()` fait avancer un événement par processus et par tour (bloquant les réceptions dont le message n'est pas encore émis), calcule simultanément Lamport, vectorielle et matricielle, et cet ordre fixe l'abscisse de chaque événement dans le SVG.
