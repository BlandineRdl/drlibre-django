---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §3.1, §4)
parent: aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md
---

# Story: Le praticien déclare ses absences
**As** praticien
**I want** lister, créer et supprimer mes absences
**So that** les périodes où je ne consulte pas soient connues

## Acceptance
- Une absence porte un début, une fin après le début et un motif facultatif de 200 caractères au plus.
- Début et fin sont saisis et affichés en heure locale de l'hôpital du praticien, et la page nomme ce fuseau.
- Une période identique à une absence déjà enregistrée est refusée.
- La suppression demande une confirmation.
- Une absence n'annule pas les RDV déjà pris pendant sa période.
- Le praticien ne voit et ne modifie que ses propres absences.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
