---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §3.1, §4, §10)
parent: aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md
---

# Story: Le praticien gère ses plages hebdomadaires
**As** praticien
**I want** lister, créer, modifier et supprimer mes plages hebdomadaires
**So that** mes disponibilités récurrentes soient publiées

## Acceptance
- Une plage porte un jour de la semaine, une heure de début et une heure de fin (HH:MM, fin après début), un pas de 5 à 240 minutes et une salle facultative.
- Les heures sont saisies et affichées en heure locale de l'hôpital du praticien, et la page nomme ce fuseau.
- La salle, si elle est donnée, est une salle active du département du praticien.
- Deux plages du même jour peuvent se toucher mais pas se chevaucher ; le refus le dit.
- Une nouvelle plage est valable dès aujourd'hui, sans date de fin.
- La suppression demande une confirmation.
- Le praticien ne voit et ne modifie que ses propres plages.
- Une salle utilisée par une plage ne peut pas être supprimée, et le refus le dit.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
