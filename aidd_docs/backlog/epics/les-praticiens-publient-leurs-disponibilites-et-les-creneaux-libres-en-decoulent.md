---
type: epic
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.1, §9 Availability, §10 Clinicians)
goal: aidd_docs/memory/project-brief.md
depends_on: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
---
# Epic: Les praticiens publient leurs disponibilités et les créneaux libres en découlent
Un praticien définit ses plages hebdomadaires et ses absences ; le système en déduit des créneaux libres justes pour tout type de RDV de son département.

## Context and Value
- Audience : praticien (saisie), admin (contrôle), tous les parcours de réservation (consommation).
- Besoin : la recherche (3 prochains créneaux par praticien) et chaque réservation reposent sur le même calcul de créneaux (§5.1, §6).
- Valeur : sans créneaux fiables, aucun RDV ne peut être proposé ni placé.

## Boundaries
- Includes:
  - Plages hebdomadaires du praticien : liste, création, modification, suppression ; salle active de son département ; pas de chevauchement le même jour (contact autorisé) ; valable dès aujourd'hui, sans fin (§9).
  - Absences : liste, création, suppression ; une période identique ne peut pas être enregistrée deux fois ; une absence n'annule pas les RDV déjà pris (§9).
  - Calcul des créneaux libres : pas de la plage, durée du type, exclusion du passé, des absences et des RDV actifs prolongés par le buffer du type, dédoublonnage, tri, 31 jours maximum, union du département si aucun praticien n'est choisi (§5.1).
  - Plages en heure locale de l'hôpital, justes au changement d'heure (§4).
  - Côté admin : résumé hebdomadaire des disponibilités et calendrier de la semaine en lecture seule pour chaque praticien (§10).
  - Requête de créneaux réservée aux utilisateurs connectés (§14 `GET /slots`).
- Excludes:
  - Accès public aux créneaux, recherche, placement d'un RDV (Epic réservation sans compte).
  - Agenda du jour, calendrier praticien, statuts, notes, vue des salles (Epic espace praticien).
  - Rendre modifiables les constantes de la politique de réservation (non spécifié, §17).

## Success Evidence
- Scénarios BDD verts pour chaque règle de §5.1 (pas, buffer, absence, passé, plafond de 31 jours, union du département) et pour les contraintes de saisie de §9.
- La semaine du changement d'heure, une plage 09:00–12:00 donne toujours des créneaux à 09:00 heure locale.
- Le praticien de démo crée une plage puis une absence ; les créneaux renvoyés reflètent les deux immédiatement.

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Référentiel, profils praticiens, salles, types | dependency | `depends_on` Epic 1 |
| Calcul vérifié contre des RDV actifs injectés en test, avant que la réservation existe | assumption | acceptée |
