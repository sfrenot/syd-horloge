# Éléments de correction : horloges logiques

> Réservé à l'enseignant. Les valeurs numériques ont été vérifiées avec `scenario.py`. Les diagrammes annotés sont dans `exercices/correction/`.

## Introduction

- **« Connaître l'ordre » au sens de quoi ?** Au sens de l'**ordre d'exécution local** : le processus sait quel événement a suivi quel autre, parce qu'il les a exécutés lui-même, l'un après l'autre. Il n'a besoin d'aucune heure pour cela : il suffit de numéroter ses événements 1, 2, 3… Cet ordre est **total** sur les événements du processus, mais ne dit rien de leur date réelle ni de leur position par rapport aux événements des autres. C'est exactement le compteur que l'horloge de Lamport étend ensuite aux messages. Nuance à signaler : l'hypothèse suppose un processus séquentiel. Dans `reseau.py`, chaque processus a deux threads (émission et réception), d'où le verrou qui garantit que les événements restent totalement ordonnés.
- **Pourquoi a-t-on eu besoin de connaître l'heure ?** Réponse ouverte ; on attend quelques jalons et surtout la distinction entre **dater** et **ordonner / coordonner** :
  - **Agriculture et calendriers** (Égypte, crue du Nil) : prévoir les saisons, un temps cyclique lu dans le ciel.
  - **Vie religieuse et communautaire** (heures canoniales, cloches, horloges mécaniques des XIIIe–XIVe siècles) : se **coordonner** à plusieurs sur un même signal.
  - **Navigation** (XVIIIe siècle) : la longitude se déduit de l'écart entre l'heure locale et l'heure du port de départ. D'où le *Longitude Act* (1714) et le chronomètre de Harrison : une horloge qui **dérive** peu en mer.
  - **Chemins de fer et télégraphe** (XIXe siècle) : chaque ville avait son heure solaire ; il faut une heure commune pour les horaires et pour éviter que deux trains s'engagent sur la même voie unique. D'où l'heure des chemins de fer, puis les fuseaux horaires (conférence de Washington, 1884). C'est un problème d'**ordre et d'exclusion mutuelle** autant que de date.
  - **Aujourd'hui** : GPS (la position se calcule à partir de la synchronisation d'horloges atomiques), horodatage des ordres en finance, bases de données réparties.

  Morale pour le TD : dans la plupart de ces cas, l'heure sert surtout à **ordonner et coordonner** des acteurs éloignés, ce que les horloges logiques font sans heure physique.

- **I1.** Oui pour les deux. a (envoi de m1) précède e sur P2 ; e précède g, envoi de m3 ; m3 est reçu en i. L'information part donc de a et atteint P3 par la chaîne a → e → g → i. De même, d → e → g → i. Attention : « pouvoir savoir » signifie que l'information a pu circuler, pas que le message m3 la contient forcément.
- **I2.** Non. Aucune chaîne de messages ne relie h à b, dans un sens comme dans l'autre : P3 n'envoie rien à P1. Les deux événements sont concurrents (notion formalisée en partie 1), et la position sur le dessin ne signifie rien.
- **I3.** Par exemple `P2: a>m1 b>m2` et `P3: c<m2 d<m1` : les flèches m1 et m2 se croisent. C'est possible car les canaux ne sont pas FIFO (UDP, routes différentes, retransmissions).

## Partie 0

1. Ce n'est pas un bug. Chaque horloge a son propre décalage et sa propre dérive. Si l'horloge de l'émetteur est en avance sur celle du récepteur d'un écart supérieur à la latence du message, la réception porte une date antérieure à l'envoi.
2. Non. Avec une précision ε (quelques ms), deux événements séparés de moins de 2ε ne peuvent pas être ordonnés. Pour un envoi et sa réception, l'ordre n'est garanti que si l'erreur des horloges reste inférieure au délai **minimal** de transmission : c'est la condition de Lamport sur les horloges physiques (*physical clock condition*). Or ce délai est souvent quasi nul sur un réseau local.
3. On n'a pas besoin de la date, mais d'un **ordre** : les deux répliques doivent appliquer les opérations dans le même ordre, et cet ordre doit respecter la causalité (un retrait émis après avoir vu le dépôt).

## Partie 1

4. `b → l` : oui, par la chaîne b → h (m1), h → i, i → j (m2), j → k → l. `c → i` : non, c ‖ i. `a ‖ f` : oui.
5. C'est un ordre **partiel strict**, irréflexif et transitif. Il n'est pas total, puisque des paires sont incomparables (a ‖ f).
6. Non. La concurrence signifie qu'**aucune information** n'a pu circuler de l'un à l'autre, ce qui correspond au « cône de lumière » en relativité. Physiquement, a peut avoir eu lieu une heure avant f.
7. Non : les événements d'un même processus sont totalement ordonnés.

## Partie 2

8. On vérifie la condition sur les deux types d'arcs. Sur un même processus, L croît strictement à chaque événement (règles 1 à 3). Pour un message, la réception prend `max(L, t) + 1 > t = L(envoi)`. La relation `<` est transitive, et `→` est la fermeture transitive de ces arcs, donc `a → b ⇒ L(a) < L(b)`.
9. Elle compte les paires **concurrentes** auxquelles l'horloge attribue un ordre strict. Avec Lamport, ce sont presque toutes les paires concurrentes : seules les estampilles égales y échappent.
10. Garantir que la réception est postérieure à l'envoi. Sans le `max`, un processus « lent » donnerait à la réception une valeur inférieure à celle de l'envoi, ce qui violerait la cohérence.

### Exercice 1

1. Estampilles de Lamport (voir `correction/exo1-lamport.svg`) :

   | P1 | a=1 | b=2 | c=3 | d=7 | e=8 |
   |---|---|---|---|---|---|
   | **P2** | f=1 | g=2 | h=3 | i=4 | |
   | **P3** | j=5 | k=6 | l=7 | | |

   d = max(3, 6) + 1 = 7 (la valeur « saute » à la réception de m3) ; h = max(2, 2) + 1 = 3.
2. Non. Il y a 13 paires concurrentes : a‖f, a‖g, b‖f, c‖f, b‖g, c‖g, c‖h, c‖i, c‖j, c‖k, c‖l, d‖l et e‖l. Les **9** pièges sont celles dont les estampilles diffèrent : a‖g, b‖f, c‖f, c‖g, c‖i, c‖j, c‖k, c‖l, e‖l.
3. Des estampilles égales impliquent des événements concurrents. En effet, si `a → b`, alors `L(a) < L(b)` ; par contraposée, `L(a) = L(b) ⇒ ¬(a → b) ∧ ¬(b → a)`.
4. Ordre total : a(1,P1) f(1,P2) b(2,P1) g(2,P2) c(3,P1) h(3,P2) i(4) j(5) k(6) d(7,P1) l(7,P3) e(8).
   - Il respecte la causalité, car c'est une extension linéaire de `→`.
   - Il ne reflète **pas** l'ordre physique des événements concurrents : placer c avant h est un choix arbitraire.

### Exercice 2 (voir `correction/exo2-lamport.svg`)

1. Sans correction : P1 = 6, 12, 18, 24, 30 ; P2 = 8, 16, 24, 32, 40 ; P3 = 10, 20, 30, 40. Le message m3 part à 40 (n) et arrive à 24 (d) : il semble reçu avant d'être parti.
2. Avec la règle `max(C + pas, t + 1)` :
   - g = max(16, 7) = 16 : pas de correction ;
   - m = max(30, 25) = 30 : pas de correction ;
   - **d = max(24, 41) = 41**, donc e = 47 ;
   - m4 part alors avec 47, d'où **j = max(40, 48) = 48**.

   La correction se **propage** : P1 avance son horloge, donc tout ce qu'il envoie ensuite porte une valeur plus grande et peut forcer une correction chez le récepteur.

### Limites

11. Une estampille plus petite ne désigne pas une cause possible. Le débogueur ne peut rien écarter : il doit examiner tous les événements d'estampille inférieure, dont la plupart sont concurrents et sans rapport avec l'erreur.
12. Non. L'écart 5 → 12 mêle des événements de tous les processus, sans dire lesquels. L'horloge ne détecte ni un message perdu ni un message en retard.
13. Non. Seuls les messages **internes au système** créent de la causalité observable. Le lien passe ici par un canal externe (le téléphone), invisible pour les horloges. C'est le scénario de la question E10.
14. Dans l'exclusion mutuelle de Lamport (ou dans tout ordonnancement par estampille), P1 gagne toutes les égalités. Il n'y a pas de famine, car les estampilles croissent, mais il y a un biais systématique. On peut le corriger par un tirage ou une rotation de la priorité.

## Partie 3

15. Pour k ≠ i, `Vi[k]` est le nombre d'événements de Pk qui sont dans le passé causal de l'événement courant. `Vi[i]` est le nombre d'événements de Pi lui-même.
16. Deux événements concurrents ont chacun « vu » un événement que l'autre n'a pas vu, donc leurs vecteurs sont incomparables. L'horloge ne leur attribue jamais d'ordre.

### Exercice 3 (voir `correction/exo3-vecteur.svg`)

1. Estampilles vectorielles :

   | P1 | a (1,0,0) | b (2,0,0) | c (3,0,0) | d (4,4,2) | e (5,4,2) |
   |---|---|---|---|---|---|
   | **P2** | f (0,1,0) | g (0,2,0) | h (2,3,0) | i (2,4,0) | |
   | **P3** | j (2,4,1) | k (2,4,2) | l (2,4,3) | | |

2. Relations déduites des vecteurs :
   - c (3,0,0) et i (2,4,0) : 3 > 2 mais 0 < 4, donc **c ‖ i** ;
   - d (4,4,2) et l (2,4,3) : **concurrents** ;
   - b (2,0,0) ≤ l (2,4,3), donc **b → l**.
3. En e (5,4,2), P1 connaît 4 événements de P2 (f, g, h, i) et 2 de P3 (j, k). Il ne connaît pas l.

## Partie 4

17. `min_k Mi[k][l]` est le nombre d'événements de Pl dont Pi **sait** que tous les processus les connaissent.
18. Pi peut purger l'entrée dès que `min_k Mi[k][l] ≥ t`. Chaque processus possède alors déjà l'entrée, et Pi le sait. Cette connaissance est conservatrice : elle peut arriver bien après la connaissance effective.
19. Une estampille compte N² entiers par message. C'est acceptable pour de petits groupes (réplication entre quelques sites) ou si l'on n'envoie que les lignes modifiées.

### Exercice 4 (voir `correction/exo4-vecteur.svg` et `scenario.py exercices/exo4.txt --matrices`)

1. Matrice de P3 après h (ligne k = ce que P3 sait du vecteur de Pk) :

   ```
   P1 (3, 2, 0)
   P2 (1, 2, 0)
   P3 (3, 2, 2)
   ```

2. Minimum par colonne : (1, 2, 0). Tout le monde connaît le 1er événement de P1 (a, envoi de m1) et les 2 premiers de P2 (d, et e, envoi de m2). Aucun événement de P3 n'est connu de tous.
3. Non : `M3[P2][P3] = 0`. P2 a bien reçu m4 (événement f), mais **aucun message de P2 postérieur à f** n'est parvenu à P3. La matrice ne contient que ce qui a été *communiqué*, jamais la réalité globale.
4. P3 ne peut pas purger g, car la colonne P3 a pour minimum 0. Il peut purger a (colonne P1 ≥ 1) ainsi que d et e (colonne P2 ≥ 2).

## Partie 5

20. Synthèse :

| | Physique | Lamport | Vectorielle | Matricielle |
|---|---|---|---|---|
| Taille d'une estampille | 1 | 1 | N | N² |
| `a → b ⇒ C(a) < C(b)` | non (sauf erreur < délai min) | oui | oui | oui |
| `C(a) < C(b) ⇒ a → b` | non | non | oui | oui (sur la ligne propre) |
| Détecte la concurrence | non | non (seulement si égalité) | oui | oui |
| Lien avec l'heure réelle | oui | non | non | non |
| Exemple d'utilisation | journaux, baux, TTL | exclusion mutuelle, ordre total, réplication | diffusion causale, vecteurs de versions, débogage | purge de journaux répliqués, stabilité |

21. **HLC** : l'estampille reste proche de l'heure physique, donc lisible et utilisable pour « lire l'état à 14 h 03 », tout en gardant la garantie de Lamport. Cela corrige l'absence de lien avec le temps réel. **Spanner** : TrueTime renvoie un intervalle [plus tôt, plus tard]. En attendant que `plus tôt > estampille` avant de valider (*commit wait*), Spanner garantit que si T1 est validée avant que T2 ne commence, alors ts(T1) < ts(T2), même vu depuis un autre datacenter. C'est la cohérence externe.

---

## Questions type d'examen

- **E1.** Une horloge physique mesure le temps réel et dérive. Une horloge logique ne mesure que l'ordre causal. NTP laisse une incertitude de l'ordre de la milliseconde : les événements plus proches que cette incertitude ne peuvent pas être ordonnés (voir la question 2).
- **E2.** `a → b ⇒ C(a) < C(b)`. Lamport la respecte, mais pas la réciproque (exercice 1.2).
- **E3.**
  - **Problèmes :** Lamport ne donne pas la réciproque, ne détecte pas la concurrence et ne permet pas de repérer un message manquant.
  - **Solution :** les vecteurs caractérisent exactement la causalité.
  - **Prix :** N entiers par message, et un groupe de taille connue.
- **E4.** Voir la question 17. Application : purge d'un journal répliqué, détection des messages stables.
- **E5.** Réponses :
  - (a) **V**.
  - (b) **F**, contre-exemple c ‖ i dans l'exercice 1.
  - (c) **V**, par contraposée de (a).
  - (d) **V**.
  - (e) **F**, l'ordre entre concurrents est arbitraire.
  - (f) **F**.
- **E6.** On sait seulement que **B ne précède pas A**. Soit A → B, soit A ‖ B. Parmi les choix proposés dans le DS, la bonne réponse est « si A et B ont un lien de causalité, alors A est survenu avant B ».
- **E7.** Analyse de chaque ensemble :
  1. `(3,1,5,7) → (3,2,6,7)` ; `(2,1,6,8)` est concurrent des deux (1re composante plus petite, mais 3e ou 4e plus grande).
  2. Les trois sont **deux à deux concurrents**.
  3. Chaîne causale `(1,2,3,4) → (2,3,4,5) → (3,4,5,6)` : aucune concurrence.
  4. Chaîne `(1,3,2,2) → (1,4,5,7) → (1,5,6,7)` : aucune concurrence. Le piège est que les vecteurs sont donnés dans l'ordre décroissant.
- **E8.** Convention : les horloges avancent physiquement, le message porte l'heure de l'émetteur, et à la réception on applique `C ← max(C, t + 1)`.
  - A envoie m1 estampillé **10**.
  - B le reçoit à l'instant réel 4 : son horloge indique 4 < 11, donc elle passe à **11**.
  - Une unité plus tard, B indique 12 et envoie m2 estampillé **12**.
  - C le reçoit à l'instant réel 7 : son horloge indique 5 + 7 = 12, donc elle passe à **13**.

  Avec la convention « incrément avant chaque événement » (DS 2021), les valeurs changent légèrement : c'est acceptable si l'étudiant **énonce sa convention** et l'applique de façon cohérente.
- **E9.** Méthode de l'exercice 1. Pour générer un sujet et sa correction :

  ```bash
  python3 scenario.py sujet.txt --svg sujet.svg
  python3 scenario.py sujet.txt --svg corrige.svg --avec vecteur
  ```

- **E10.** Si B envoie m2 **après** avoir reçu m1 : m1 = 1, B passe à 2, m2 = 3, donc **C = 4**. Si B envoie m2 **avant** : m2 = 1, donc **C = 2**. La relation voulue par les utilisateurs, passée par le téléphone, n'est garantie que dans le premier cas.
- **E11.** L'inégalité stricte sur toutes les composantes est fausse. Contre-exemple : P1 envoie à P2, qui reçoit ; on a bien `(1,0) → (1,1)`, mais la première composante n'est pas strictement plus grande. Il faut « ≤ partout et ≠ ».
- **E12.** Diffusion causale. Chaque message porte un vecteur de diffusions `W` (`W[j]` = nombre de messages de Pj délivrés par l'émetteur, le sien compris). Pi délivre un message de Pj si `W[j] = Vi[j] + 1` (message suivant de Pj) et `W[k] ≤ Vi[k]` pour tout k ≠ j (Pi a déjà vu tout ce que l'émetteur avait vu) ; sinon il le met en attente, et réexamine la file à chaque délivrance. Coût : N entiers par message et une file d'attente par récepteur. Avec une horloge de Lamport, il faudrait attendre des nouvelles de tous les processus.
- **E13.** Les versions sont concurrentes : conflit à réconcilier : le système garde les deux versions (*siblings*) et l'application les fusionne, par exemple en faisant l'union des paniers dans Dynamo. Une estampille de Lamport imposerait un ordre arbitraire et la dernière écriture écraserait l'autre (*last-writer-wins*) : une mise à jour serait **silencieusement perdue**.
