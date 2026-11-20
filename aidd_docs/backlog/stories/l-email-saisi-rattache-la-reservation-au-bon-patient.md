---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§7.2, §7.5)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email.md
---

# Story: L'email saisi rattache la réservation au bon patient
**As** patient
**I want** que ma réservation sans connexion s'ajoute à mon compte existant
**So that** tous mes RDV restent au même endroit, sans que mon compte soit révélé à d'autres

## Acceptance
- Un email d'un patient actif, avec ou sans mot de passe, fait réserver pour ce patient ; les informations saisies ne changent pas son profil.
- Un email d'admin, de praticien ou d'utilisateur inactif fait refuser la réservation par un message générique qui n'en dit pas la raison.
- Aucune réponse ne révèle si un email a déjà un compte.
- Avant la vérification du code, rien n'est renvoyé sur le patient ni sur ses autres RDV.
