<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# record-index

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

Une structure de données SQLite+FTS5 gérée, indexant un ensemble d’enregistrements décisionnels au format Markdown, afin qu’une session puisse **interroger** l’enregistrement plutôt que de le lire, puis afficher les quarante lignes auxquelles la requête fait référence, au lieu des six cents lignes qu’elle aurait parcourues.

**[Page d’accueil et manuel →](https://mcp-tool-shop-org.github.io/record-index/)**

Le format Markdown reste le format de référence. L’index est dérivé et régénéré à chaque modification, avec une validation basée sur quatre critères `verify`, et il est **par définition incorrect dès qu’il est modifié manuellement**.

## Statut : extrait, testé, pas encore disponible sur PyPI

*(Cette section affichait « SEULMENT UN MODÈLE — aucun code d’outil n’est présent dans ce dépôt pour le moment » jusqu’au 11 août 2026, ce que l’extraction a contredit. Correction effectuée.)*

**L’extraction a été réalisée.** Le paquet est disponible sur `main`, avec une validation basée sur l’identité des octets lors de son ajout, en comparaison avec la version intégrée à facet (19/19), et **aucune différence au niveau des lignes** dans le même corpus. Deux consommateurs l’utilisent : [facet](https://github.com/mcp-tool-shop-org/facet), dont les ~2 462 lignes intégrées sont devenues une déclaration ainsi qu’un adaptateur avec ~140 de ses tests, qui utilisent le paquet, et [armature](https://github.com/mcp-tool-shop-org/armature), dont l’index a permis d’obtenir 15 résultats sur 15, avec 47 règles.

**Le paquet contient sa propre suite de tests : 455 tests** pour les dix modules, exécutés en CI sur Python 3.11 et 3.13, basés sur deux référentiels d’enregistrements qui présentent des divergences sur tous les axes déclarables (marqueurs, racines du corpus, règles d’arc, vocabulaire de vérification, formats d’en-tête), afin qu’une implémentation incorrecte puisse être détectée. **Dépendances : aucune.** Uniquement la bibliothèque standard (`sqlite3` + `re` + `json`), et il s’agit d’une propriété déclarée, pas d’un hasard.

**Quatre défauts sont connus, reproduits et enregistrés dans le code en tant que tests `xfail(strict=True)`**, plutôt que cachés : `verify()` double ses décomptes de diagnostics (les critères de validation ne sont pas affectés) ; le modèle d’arc de revendication suppose des arcs numérotés `E` ; le localisateur de sous-règle n’est pas dérivé du format d’en-tête déclaré ; et quatre champs de déclaration ne peuvent pas être déclarés comme étant honnêtement vides. Aucun de ces défauts n’affecte les deux consommateurs actuels ; les quatre sont mis en file d’attente pour la prochaine version.

**Pas encore disponible sur PyPI.** `release.yml` publie via OIDC Trusted Publishing lorsqu’une nouvelle version est créée sur GitHub ; rien n’est publié lors d’un commit.

## Origine de ce projet

Il s’agit d’une extraction de l’index des enregistrements, créé et amélioré dans [`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet), où toutes les conventions ci-dessous ont été définies. Il extrait plutôt que de créer une branche, car le recueil de règles de facet contient cinq copies manuelles d’une même fonction, réparties sous quatre noms différents, invisibles pour une recherche basée sur le nom pendant des mois ; créer une deuxième branche avec des milliers de lignes serait cette erreur multipliée par trois.

La condition d’extraction a été définie à l’avance et validée par une mesure : *l’index est extrait lorsqu’un deuxième dépôt adopte les conventions*. [`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) est ce dépôt.

## La conception, en un paragraphe

Un dépôt d’enregistrements déclare **ce que ses documents signifient** : quels fichiers contiennent des règles, quels formats d’en-tête les ouvrent, quel est son vocabulaire de vérification et quels corpus il contient. L’outil fournit **le fonctionnement de la recherche** : analyse syntaxique, classement, déterminisme, critères de validation, avec des valeurs de réglage qui contiennent le corpus et la date à laquelle ils ont été calibrés. Les conventions constituent une **déclaration complète** (un dépôt déclare sa propre signification ; il n’hérite jamais de l’historique d’un autre dépôt par omission). Le mécanisme est basé sur **des valeurs par défaut avec des remplacements**.

Chaque vocabulaire indique ce qu’il **n’a pas reconnu**. Une table vide et une table qui a supprimé silencieusement six artefacts sont indiscernables au niveau de l’appel, et un seul d’entre eux est correct.

## Le blocage qui existait auparavant et comment il s’est terminé

*(Jusqu’au 11 août 2026, cette section bloquait la compilation en cas de collision mesurée. Le blocage était réel, la règle a été définie et la compilation a repris ; elle est conservée ici comme trace plutôt que supprimée.)*

L’étape de classification avait mesuré que la dérivation d’un arc de document à partir de son préfixe `E\d\d` **entraînait une collision sur 7 clés primaires** avec facet (`E10-ruling.md` et `E10-offsurface-ruling.md` deviennent tous deux l’arc `E10`). L’exécuteur a détecté cette erreur par rapport à un test dont le nom enregistre la même défaillance, la règle conjointe a été retirée et redérivée, et l’extraction a pu se poursuivre. La trace (preuves, les réponses annulées et la règle qui les a remplacées) est disponible dans `armature/docs/dispatches/` (l’arc S02).

## Licence

MIT : voir [LICENSE](LICENSE).
