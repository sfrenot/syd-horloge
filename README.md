# Temps et causalité : horloges de Lamport, vectorielles et matricielles

Dans un système réparti, il n'y a **ni mémoire commune ni horloge commune**. Pourtant, beaucoup de problèmes exigent de savoir « qui est passé avant qui » :

- une banque qui applique un dépôt puis un retrait sur deux répliques ;
- un chat de groupe où une réponse ne doit pas s'afficher avant sa question ;
- un débogueur qui reconstitue une exécution à partir des journaux de plusieurs machines.

Ce TD cherche à répondre à trois questions :

1. Que veut-on vraiment ordonner, et pourquoi l'heure des machines ne suffit-elle pas ?
2. Que garantit l'horloge de Lamport, et surtout, **que ne garantit-elle pas** ?
3. Comment les horloges vectorielles, puis matricielles, lèvent-elles ces limites, et à quel prix ?

| Fichier | Rôle |
|---|---|
| `horloges.py` | Les quatre horloges (physique, Lamport, vectorielle, matricielle), avec la même interface |
| `reseau.py` | Des processus qui s'échangent des messages UDP. Un observateur omniscient compare les estampilles à la causalité réelle |
| `scenario.py` | Calcule les estampilles d'un scénario écrit à la main et dessine son diagramme espace-temps (SVG) |
| `exercices/` | Scénarios et diagrammes des exercices |

Prérequis : Python ≥ 3.10, aucune bibliothèque externe.

---

## Introduction : processus, messages et événements

### Le modèle

Un système réparti est un ensemble de **processus** P1, P2…, Pn : des programmes qui s'exécutent sur des machines différentes (ou, dans ce TD, dans des threads différents d'une même machine). Chaque processus :

- est **séquentiel** : il fait une chose après l'autre, dans un ordre qu'il connaît parfaitement (question : au sens de quoi ? Que signifie « connaître l'ordre » sans horloge ?) ;
- a sa **propre mémoire**, que les autres ne peuvent pas lire ;
- a sa **propre horloge**, qui n'a aucune raison d'indiquer la même heure que celle des voisins. Historiquement, pourquoi a-t-on eu besoin de connaître l'heure ? Autrement dit, à quel moment de l'histoire de l'humanité le temps est-il devenu important ?

Le seul moyen pour un processus d'apprendre quelque chose sur un autre est de recevoir un **message** de sa part. Un message met un temps inconnu et variable à arriver : on sait seulement qu'il finit par arriver. Deux messages envoyés dans un certain ordre peuvent même arriver dans l'ordre inverse.

La vie d'un processus est une suite d'**événements**, de trois types :

| Type | Exemple | Ce qui se passe |
|---|---|---|
| **Interne** | écrire dans un fichier, faire un calcul | le processus change son état, sans communiquer |
| **Envoi** | `sendto(m1, P2)` | un message part vers un autre processus |
| **Réception** | `recvfrom()` reçoit m1 | un message arrive ; son contenu devient connu du processus |

À chaque message correspondent exactement deux événements : son envoi par l'émetteur, et sa réception par le destinataire.

### Le diagramme espace-temps

On représente une exécution par un **diagramme espace-temps** :

![Diagramme d'introduction](exercices/intro.svg)

- chaque processus est une ligne horizontale, et son temps local s'écoule de gauche à droite ;
- chaque point est un événement ;
- chaque flèche est un message, qui va de l'événement d'envoi à l'événement de réception. Elle est inclinée, parce que le transport prend du temps.

Dans cet exemple, P1 envoie m1 à P2 (événement a), fait un calcul interne (b), puis reçoit m2 (c). P2 a un événement interne (d), reçoit m1 (e), puis envoie m2 à P1 (f) et m3 à P3 (g). P3 a un événement interne (h), puis reçoit m3 (i).

**Attention** : seule la position d'un événement **sur sa propre ligne** a un sens. Comparer des positions horizontales entre deux lignes n'a pas de sens : h est dessiné à gauche de b, mais rien ne dit que h a eu lieu avant b. Personne, dans le système, ne peut d'ailleurs le savoir, puisqu'aucun message ne relie ces deux événements.

**Dans le code** : dans `reseau.py`, un processus est un thread muni d'une socket UDP, et un message est un datagramme. Dans `scenario.py`, un processus est une ligne de texte qui liste ses événements dans l'ordre local. Le diagramme ci-dessus est produit à partir de `exercices/intro.txt` :

```
P1: a>m1 b c<m2        a>m1 : envoi de m1 ;  c<m2 : réception de m2
P2: d e<m1 f>m2 g>m3   b, d, h : événements internes
P3: h i<m3
```

```bash
python3 scenario.py exercices/intro.txt --svg intro.svg
```

**Questions**

- **I1.** Dans le diagramme, P3 peut-il savoir que l'événement a a eu lieu ? Et l'événement d ? Justifiez en suivant les flèches.
- **I2.** P1 peut-il savoir si h a eu lieu avant ou après b ?
- **I3.** Dessinez à la main une exécution possible de trois processus où P2 envoie deux messages à P3, et où P3 les reçoit dans l'ordre inverse de leur envoi.

---

## Partie 0 : pourquoi pas l'heure des machines ?

```bash
python3 reseau.py physique -k 2 --paires
```

Chaque processus estampille ses événements avec sa propre horloge, qui a une avance de 0 à 60 ms sur l'heure de référence et une dérive de ±5 %. Chacun des 3 processus fait 2 actions (option `-k`), soit une dizaine d'événements, nommés `P<i>.<rang>` (rang dans l'ordre local du processus). L'option `--paires` liste les paires causales et concurrentes réelles, et marque d'un ✗ celles sur lesquelles l'horloge se trompe. Les messages mettent entre 0 et 50 ms à arriver. Le journal est ensuite trié par estampille, et le symbole ⚠ signale une réception placée **avant** l'envoi du même message.

**Questions**

1. Relancez plusieurs fois. Pourquoi voit-on des réceptions avant leur envoi ? Est-ce un défaut de programmation ?
2. On synchronise les machines avec NTP, dont la précision est de l'ordre de la milliseconde sur un réseau local. Est-ce suffisant pour ordonner correctement deux événements séparés de 100 µs sur deux machines ? Que faudrait-il connaître pour garantir l'ordre ?
3. Dans le problème de la banque, a-t-on besoin de **la date** des opérations ? De quoi a-t-on besoin exactement ?

---

## Partie 1 : la causalité

On reprend le modèle de l'introduction : des processus P1…Pn, dont les événements sont internes, des envois ou des réceptions. On définit la relation **« s'est produit avant »**, notée `→` :

- si a et b ont lieu sur le même processus et que a précède b, alors `a → b` ;
- si a est l'envoi d'un message et b sa réception, alors `a → b` ;
- la relation est transitive : si `a → b` et `b → c`, alors `a → c`.

Deux événements a et b sont **concurrents**, noté `a ‖ b`, si ni `a → b` ni `b → a`.

![Diagramme de l'exercice 1](exercices/exo1.svg)

**Questions**

4. Sur le diagramme ci-dessus, a-t-on `b → l` ? `c → i` ? `a ‖ f` ?
5. `→` est-elle un ordre total ou partiel ? Justifiez.
6. `a ‖ f` signifie-t-il que a et f ont eu lieu « en même temps » ? Que signifie la concurrence physiquement ?
7. Deux événements d'un même processus peuvent-ils être concurrents ?

**Objectif d'une horloge logique** : associer à chaque événement une estampille `C(e)` calculable **localement**, uniquement à partir des messages reçus, telle que :

> **Condition de cohérence** : si `a → b`, alors `C(a) < C(b)`.

---

## Partie 2 : l'horloge de Lamport (1978)

Chaque processus Pi possède un compteur entier `Li`, initialisé à 0.

1. **Événement interne** : `Li ← Li + 1`.
2. **Envoi** : `Li ← Li + 1`, puis on joint `Li` au message.
3. **Réception** d'un message portant `t` : `Li ← max(Li, t) + 1`.

Lisez la classe `Lamport` dans `horloges.py` (ou écrivez-la avant de la lire), puis :

```bash
python3 reseau.py lamport
python3 reseau.py lamport -k 2 --paires   # journal court, avec la liste des paires
```

**Questions sur le mécanisme**

8. Démontrez que l'horloge de Lamport vérifie la condition de cohérence.
9. Dans la sortie de `reseau.py`, la ligne « paires causales » vaut 100 %. Que mesure la ligne « fausse causalité » ?
10. Quel est l'objectif de la règle 3 ? Que se passerait-il sans le `max` ?

### Exercice 1 : calculer, puis interpréter

À partir du diagramme de la partie 1 (`exercices/exo1.txt`) :

1. Déterminez l'estampille de Lamport de chaque événement.
2. On a `L(c) < L(i)`. Peut-on en conclure `c → i` ? Trouvez toutes les paires d'événements pour lesquelles l'horloge « suggère » un ordre qui n'existe pas.
3. c et h ont la même estampille, tout comme d et l. Que peut-on dire de deux événements de même estampille ? Démontrez-le.
4. Pour obtenir un **ordre total**, on compare les couples `(L(e), numéro du processus)`. Écrivez la suite totalement ordonnée des événements. Cet ordre respecte-t-il la causalité ? Reflète-t-il l'ordre physique des événements concurrents ?

Vous pouvez vérifier vos calculs avec `python3 scenario.py exercices/exo1.txt`.

### Exercice 2 : horloges qui avancent à des vitesses différentes

Dans la version d'origine de l'article de Lamport, les horloges sont des compteurs physiques qui avancent de 6, 8 et 10 unités à chaque événement de P1, P2, P3 (`exercices/exo2.txt`).

![Diagramme de l'exercice 2](exercices/exo2.svg)

1. Calculez les valeurs des horloges **sans** la règle de réception. Quel message semble arriver avant d'être parti ?
2. Appliquez la règle de Lamport, `C ← max(C + pas, t + 1)`. Quelles horloges sont corrigées ? Pourquoi la correction de d en entraîne-t-elle une autre sur P2 ?

### Les limites de l'horloge de Lamport

11. L'implication réciproque (`L(a) < L(b) ⇒ a → b`) est fausse. Quelle conséquence cela a-t-il pour un débogueur qui cherche la cause d'une erreur dans des journaux estampillés ?
12. Un processus qui reçoit un message estampillé 12 alors que son horloge vaut 5 peut-il savoir combien d'événements ont eu lieu ailleurs ? Peut-il détecter qu'un message lui manque ?
13. A envoie m1 à B, puis **téléphone** à l'utilisateur de B pour lui demander d'envoyer m2 à C. Les horloges de Lamport rendent-elles compte du lien entre m1 et m2 ? Qu'est-ce que cela dit de la causalité « observable » par un système ?
14. L'ordre total `(L, pid)` favorise systématiquement P1 en cas d'égalité. Dans quel algorithme cela peut-il poser un problème d'équité ?

---

## Partie 3 : les horloges vectorielles (Fidge, Mattern, 1988)

On veut désormais l'**équivalence** : `a → b ⇔ C(a) < C(b)`. Chaque processus Pi maintient un vecteur `Vi` de n entiers, tous à 0 au départ.

1. **Événement interne ou envoi** : `Vi[i] ← Vi[i] + 1`. En cas d'envoi, on joint `Vi` au message.
2. **Réception** d'un message portant `W` : `Vi[k] ← max(Vi[k], W[k])` pour tout k, puis `Vi[i] ← Vi[i] + 1`.

On compare deux vecteurs ainsi :

- `V ≤ W` si et seulement si `V[k] ≤ W[k]` pour **tout** k ;
- `V < W` si et seulement si `V ≤ W` et `V ≠ W` ;
- `V ‖ W` si ni `V ≤ W` ni `W ≤ V`.

```bash
python3 reseau.py vectorielle
python3 reseau.py vectorielle -k 2 --paires   # journal court, avec la liste des paires
```

**Questions**

15. Que représente `Vi[k]` pour k ≠ i ? Et `Vi[i]` ?
16. Comparez la ligne « fausse causalité » avec celle de la partie 2. Pourquoi vaut-elle maintenant 0 ?

### Exercice 3 : vecteurs sur le même diagramme

1. Reprenez l'exercice 1 et calculez les horloges vectorielles.
2. Déterminez, **à partir des vecteurs uniquement**, la relation entre c et i, entre d et l, et entre b et l.
3. Au moment de e, combien d'événements de P2 et de P3 le processus P1 connaît-il ? Quels sont ces événements ?

---

## Partie 4 : les horloges matricielles

Un vecteur indique ce que **je** sais des autres. Une matrice indique en plus ce que je sais de **ce que les autres savent**. Pi maintient une matrice `Mi` de taille n×n :

- la ligne `Mi[i]` est le vecteur de Pi ;
- la ligne `Mi[k]` est ce que Pi sait du vecteur de Pk ;
- `Mi[k][l]` se lit : « Pi sait que Pk connaît au moins `Mi[k][l]` événements de Pl ».

1. **Événement interne ou envoi** : `Mi[i][i] ← Mi[i][i] + 1`. En cas d'envoi, on joint `Mi` au message.
2. **Réception** d'une matrice `M` venant de Pj :
   - `Mi[i][k] ← max(Mi[i][k], M[j][k])` pour tout k ;
   - `Mi[k][l] ← max(Mi[k][l], M[k][l])` pour tous k et l ;
   - enfin, `Mi[i][i] ← Mi[i][i] + 1`.

```bash
python3 reseau.py matricielle
python3 reseau.py matricielle -k 2 --paires   # journal court, avec la liste des paires
```

**Questions**

17. Interprétez `min_k Mi[k][l]`, affiché comme « événements connus de tous ».
18. Quel est le coût d'une estampille matricielle ? Dans quels cas ce coût est-il acceptable ?

### Exercice 4 : messages stables

![Diagramme de l'exercice 4](exercices/exo4.svg)

1. Calculez la matrice de P3 après l'événement h.
2. D'après cette matrice, quels événements P3 sait-il connus de tous les processus ?
3. P3 sait-il que P2 a reçu m4 ? Pourtant, P2 l'a bien reçu. Expliquez cet écart.

Vérification : `python3 scenario.py exercices/exo4.txt --matrices`.
