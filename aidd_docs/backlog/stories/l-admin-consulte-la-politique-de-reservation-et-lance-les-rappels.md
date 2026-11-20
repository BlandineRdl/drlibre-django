---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Settings, §5.3, §5.7, §14)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
---

# Story: L'admin consulte la politique de réservation et lance les rappels
**As** admin
**I want** voir les constantes de réservation et lancer le job de rappel à la demande
**So that** je sache quelles règles s'appliquent aux patients et que les rappels partent sans attendre le planning

## Acceptance
- La page de réglages montre en lecture seule le délai minimal de 120 minutes, la fenêtre d'annulation de 24 heures et la limite de 3 réservations en ligne ouvertes.
- Un bouton lance le job de rappel : un rappel pour chaque RDV `BOOKED` qui commence dans les 24 heures et n'en a pas encore.
- Deux lancements successifs ne rappellent personne deux fois.
- Le job laisse une entrée d'audit avec le nombre de rappels quand il en crée.
- `POST /jobs/reminders` lance le même job pour un admin ; tout autre rôle reçoit `forbidden`.
