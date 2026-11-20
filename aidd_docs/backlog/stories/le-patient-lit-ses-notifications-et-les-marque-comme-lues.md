---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§11, §8 Notifications, §7.6, §4)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
---

# Story: Le patient lit ses notifications et les marque comme lues
**As** patient connecté, avec ou sans mot de passe
**I want** lire mes notifications et les marquer comme lues
**So that** je sache ce qui a changé sur mes RDV

## Acceptance
- Une réservation crée la notification « RDV réservé » (type « Changement de planning ») dans la même transaction que le RDV ; elle n'envoie que l'email de confirmation de l'Epic 3, aucun second email.
- Le texte d'une notification ne porte que l'heure du RDV : ni nom, ni motif, ni email.
- La liste montre les notifications du patient, des plus récentes aux plus anciennes, et seulement les siennes.
- « Marquer comme lu » fait passer la notification en lue ; l'écriture laisse une entrée d'audit sans donnée personnelle.
