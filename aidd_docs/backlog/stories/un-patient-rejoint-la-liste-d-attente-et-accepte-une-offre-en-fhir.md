---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.2, §15.3, §15.4, §15.6, §5.8)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-reserve-et-consulte-des-rdv-en-fhir.md
---

# Story: Un patient rejoint la liste d'attente et accepte une offre en FHIR
**As** client API agissant pour un patient ou un admin
**I want** inscrire un patient sur la liste d'attente et accepter le créneau offert
**So that** mon application profite des créneaux libérés

## Acceptance
- Créer un `Appointment` au statut `waitlist` avec le `serviceType`, un `requestedPeriod` et éventuellement un praticien préféré inscrit le patient ; le patient s'inscrit lui-même, l'admin inscrit tout patient, un praticien reçoit `forbidden`.
- Un type inactif ou un praticien préféré inactif donne `not_found`.
- Les statuts suivent le §15.3 : `WAITING` → `waitlist`, `OFFERED` → `proposed` avec le début, la fin et le praticien offerts, `EXPIRED` → `cancelled`.
- Créer un `AppointmentResponse` au statut `accepted` sur une offre accepte celle-ci, pour le patient sur sa propre offre ou pour l'admin ; le placement, les règles et les refus sont ceux de l'écran, `conflict` compris si le créneau est déjà pris.
- Après acceptation, la même ressource devient le RDV `booked` : une seule ressource, pas deux.
- `AppointmentResponse` est lisible par le patient (les siennes) et par l'admin.
- L'audit, les notifications et les emails sont ceux des écrans.
