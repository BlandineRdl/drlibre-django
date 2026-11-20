---
type: epic
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§4, §10, §12)
goal: aidd_docs/memory/project-brief.md
---
# Epic: Le personnel se connecte et gère le référentiel multi-hôpitaux
Un admin connecté par mot de passe gère hôpitaux, spécialités, départements, salles, types de RDV, utilisateurs et profils praticiens ; chaque rôle n'accède qu'à son espace.

## Context and Value
- Audience : admin global (17.2) ; praticien pour la connexion seulement.
- Besoin : l'application actuelle modélise une seule clinique. La recherche par hôpital exige un Hospital au-dessus de Department, avec son propre fuseau (17.1), et une liste de spécialités gérée (17.4).
- Valeur : socle de données et d'accès pour tous les autres Epics. Sans référentiel, ni créneaux, ni recherche, ni réservation.

## Boundaries
- Includes:
  - Connexion par mot de passe, verrouillage après 10 échecs en 15 min, sessions de 12 h (admin) ou 7 j (autres) avec prolongation, déconnexion, coupure immédiate à la désactivation (12.1, 12.2).
  - Règles d'accès : un espace par rôle, `forbidden` / `not_found`, contrôles côté serveur, refus des requêtes cross-origin (12.3).
  - Gestion avec recherche, 20 lignes par page, codes uniques, suppression confirmée et refusée avec ses dépendances : hôpitaux, spécialités, départements, salles, types de RDV (10).
  - Utilisateurs : création avec mot de passe temporaire, modification, interdiction de se désactiver soi-même (10).
  - Rattachement du profil praticien : département, spécialité, titre, bio, salle par défaut, poids round robin (10).
  - Règles de la section 4 sur ces écrans : validation, audit dans la même transaction, codes d'erreur, correlation id, fuseau de l'hôpital.
  - Changement de son propre mot de passe pour tout compte qui en a un (10 à 72 caractères), obligatoire à la première connexion après un mot de passe temporaire.
  - Désactivation d'un praticien refusée tant qu'il a des RDV actifs à venir ; le refus les liste.
  - API `POST /auth/login` et `POST /auth/logout` (§14).
- Excludes:
  - Connexion par lien email et sessions de 24 h (Epic réservation sans compte).
  - Résumé des disponibilités et calendrier hebdomadaire du praticien (Epic disponibilités).
  - Dashboard, liste des RDV, export CSV, consultation du journal d'audit, réglages (Epic supervision admin).
  - Liste d'attente côté admin (Epic liste d'attente).
  - Admins par hôpital, praticien sur plusieurs départements, auto-inscription (17.2, 17.3, hors périmètre).

## Success Evidence
- L'admin de démo enchaîne hôpital → département → salle → type → praticien → profil, puis voit une suppression refusée qui liste ses dépendances.
- Un praticien qui ouvre la console admin reçoit `forbidden` ; un visiteur sans session est renvoyé vers la connexion.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle ; si l'audit échoue, l'écriture est annulée.
- Scénarios BDD verts pour §12 et pour les refus de suppression de §10 ; écrans conformes WCAG 2.2 AA, de 375 à 1440 px (§16).

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Walking skeleton | dependency | Task à créer avant cet Epic |
| Écriture du journal d'audit livrée ici, consultation dans l'Epic supervision | assumption | acceptée |
| Seed de démo enrichie Epic par Epic ; ici référentiel + un compte par rôle | assumption | acceptée |
| BDD + qualités §16 comme preuves de succès de chaque Epic | assumption | acceptée |
| Changement de mot de passe pour le personnel, obligatoire après un mot de passe temporaire | decision | prise : décision du rapport de zones d'ombre (aidd_docs/backlog/epics-shadow-report.md) |
| Praticien avec RDV actifs à venir non désactivable | decision | prise : décision du rapport de zones d'ombre (aidd_docs/backlog/epics-shadow-report.md) |
