---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.1, §15.3, §15.6, §5.3, §5.6, §5.8)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-reserve-et-consulte-des-rdv-en-fhir.md
---

# Story: Un client déplace, annule et change le statut d'un RDV en FHIR
**As** client API agissant pour un patient, un praticien ou un admin
**I want** mettre à jour un `Appointment` pour le déplacer, l'annuler ou faire avancer son statut
**So that** mon application suive le RDV jusqu'à sa clôture

## Acceptance
- Mettre à jour le début déplace le RDV avec les règles du §5.6 : RDV `booked` seulement, même praticien et même type, règles patient pour un patient, salle réattribuée en préférant la courante.
- Passer le statut à `cancelled` avec un `cancelationReason` annule le RDV ; sans motif, `invalid_input` ; un patient reste soumis à la fenêtre de 24 heures ; l'offre automatique de la liste d'attente est lancée.
- Passer le statut à `checked-in`, `fulfilled` ou `noshow` est réservé au praticien du RDV et à l'admin.
- Tout autre changement de statut est refusé en 409 avec `invalid_transition` et le statut courant.
- Une mise à jour avec un `If-Match` périmé échoue en 412.
- Les refus, l'audit, les notifications et les emails sont ceux des écrans dans les mêmes cas.
