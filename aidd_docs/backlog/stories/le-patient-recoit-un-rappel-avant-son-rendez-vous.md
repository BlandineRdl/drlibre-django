---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.7, §11, §7.6, §17)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
depends_on: aidd_docs/backlog/stories/le-patient-lit-ses-notifications-et-les-marque-comme-lues.md
---

# Story: Le patient reçoit un rappel avant son rendez-vous
**As** patient avec un RDV réservé
**I want** être rappelé dans les 24 h qui précèdent mon RDV
**So that** je ne le manque pas

## Acceptance
- Exécuté sur planning, sans action d'un admin, le job de rappel crée une notification « Rappel de RDV » pour chaque RDV `BOOKED` qui commence dans les 24 prochaines heures et n'a pas encore de rappel.
- Deux exécutions ne créent qu'un rappel par RDV ; un RDV d'un autre statut n'en reçoit aucun.
- Chaque rappel envoie un email après la validation de la transaction, avec l'heure, l'hôpital et le praticien, sans motif, qui ne renvoie qu'à la page de connexion.
- Une exécution qui crée des rappels laisse une entrée d'audit avec leur nombre ; une exécution qui n'en crée aucun n'en laisse pas.
