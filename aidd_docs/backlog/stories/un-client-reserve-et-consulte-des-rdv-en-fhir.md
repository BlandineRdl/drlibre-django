---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.2, §15.3, §15.4, §15.5, §15.6, §5.2, §5.3, §5.4, §5.5)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-agit-avec-le-jeton-d-un-utilisateur-et-exactement-ses-droits.md
---

# Story: Un client réserve et consulte des RDV en FHIR
**As** client API agissant pour un patient, un praticien ou un admin
**I want** réserver un créneau et retrouver les RDV de mon utilisateur
**So that** mon application gère la prise de RDV sous les mêmes règles que les écrans

## Acceptance
- Créer un `Appointment` au statut `proposed` avec le patient, le `serviceType` et soit une référence `slot`, soit un début et un praticien, renvoie un `Appointment` `booked` avec le praticien et la salle attribués ; la fin est toujours calculée par le serveur.
- Sans praticien, un patient obtient le premier disponible (round robin, source `ROUND_ROBIN`) ; le personnel doit nommer un praticien.
- Les droits sont ceux du §5.4 : le patient pour lui-même et sans salle, le praticien dans son agenda pour un patient actif, l'admin pour tout patient actif ; source `ONLINE`, `ROUND_ROBIN` ou `STAFF` comme à l'écran.
- Les refus sont ceux des écrans dans les mêmes cas : `not_found`, `conflict` avec les ressources en cause, `rule_violation` avec les règles violées, `no_room_available`, `no_clinician_available`, en `OperationOutcome`.
- La réservation laisse la même entrée d'audit et envoie la même notification et le même email qu'à l'écran.
- Lecture et recherche `Appointment` sont limitées aux RDV du patient, à l'agenda du praticien ou à tout pour l'admin, avec `patient`, `practitioner`, `location`, `status`, `date`, `service-type` et `_include` `Appointment:patient`, `Appointment:practitioner`, `Appointment:location`.
- Les statuts suivent le §15.3 : `BOOKED` → `booked` sans extension, `CHECKED_IN` → `checked-in`, `COMPLETED` → `fulfilled`, `CANCELLED` → `cancelled` avec `cancelationReason`, `NO_SHOW` → `noshow` ; la source est une extension et le motif du patient est `reasonCode.text`.
- Les notes cliniques (`Appointment.comment`) ne sont renvoyées qu'au praticien du RDV.
- Une retenue de réservation apparaît en `Appointment` `pending` pour le personnel seulement.
