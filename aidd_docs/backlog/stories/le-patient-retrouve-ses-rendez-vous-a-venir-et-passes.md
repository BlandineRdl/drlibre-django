---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§7.4, §8 Appointments, §14, §4)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
---

# Story: Le patient retrouve ses rendez-vous à venir et passés
**As** patient connecté, avec ou sans mot de passe
**I want** voir tous mes RDV, à venir et passés
**So that** je sache avec qui, quand et où j'ai rendez-vous

## Acceptance
- À venir : RDV `BOOKED` ou `CHECKED_IN` pas encore commencés, du plus proche au plus lointain. Passés : tous les autres, du plus récent au plus ancien.
- Chaque RDV montre le praticien (nom, titre, spécialité), la date, l'heure de début et de fin dans le fuseau de l'hôpital, qui est nommé, l'hôpital (nom, adresse), le département, la salle quand elle est attribuée, le type, le statut et le motif.
- Un RDV réservé par le parcours sans compte apparaît dès la session ouverte.
- `GET /appointments` filtre par praticien, statut et période, et ne renvoie au patient que ses propres RDV, même s'il nomme un autre patient.
