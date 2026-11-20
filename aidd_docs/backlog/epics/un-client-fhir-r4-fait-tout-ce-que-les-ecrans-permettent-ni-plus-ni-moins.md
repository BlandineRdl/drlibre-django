---
type: epic
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§15, §2 API client, 17.13)
goal: aidd_docs/memory/project-brief.md
depends_on: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
---
# Epic: Un client FHIR R4 fait tout ce que les écrans permettent, ni plus ni moins
Un client tiers lit le référentiel et les créneaux libres sans jeton, puis, avec le jeton d'un utilisateur, réserve, déplace, annule et suit les RDV en FHIR R4, sous exactement les mêmes règles que les écrans.

## Context and Value
- Audience : client API (§2), agissant avec les droits d'un seul utilisateur.
- Besoin : chaque concept du produit doit aussi être disponible en FHIR (§1). La spec en fait une autre porte sur le même produit (§15.1).
- Valeur : interopérabilité avec l'écosystème santé ; c'est aussi le différenciateur du portfolio, une façade FHIR posée sur les mêmes cas d'usage (INSTALL.md).

## Boundaries
- Includes:
  - Conventions : R4 4.0.1, `application/fhir+json`, base `/fhir`, `CapabilityStatement` complet, erreurs en `OperationOutcome` avec les statuts HTTP de §4, Bundles `searchset` paginés (`_count` jusqu'à 100, `_sort`), `meta.versionId`, `If-Match` avec 412 sur une version périmée, id du produit comme id logique (§15.1).
  - Correspondance de chaque concept avec sa ressource : Organization, Location, HealthcareService, CodeSystem / ValueSet, Practitioner, PractitionerRole, Schedule, Slot, Patient, Appointment, AppointmentResponse, Communication, AuditEvent (§15.2).
  - Correspondance des statuts de RDV et de liste d'attente ; une entrée acceptée devient la ressource du RDV réservé ; notes cliniques réservées au praticien du RDV (§15.3).
  - Interactions et droits par ressource ; accès sans jeton en lecture seule ; jeton bearer qui porte exactement les droits d'un utilisateur (§15.4).
  - Paramètres de recherche et `_include` listés au §15.5.
  - Réservation, déplacement, annulation, changements de statut, liste d'attente et acceptation d'offre via FHIR, avec placement, règles, audit et notifications identiques aux écrans (§15.6).
- Excludes:
  - Réservation sans compte via FHIR (§15.4).
  - Exposition des sessions (§15.2).
  - Schéma de jetons standard de type SMART on FHIR (laissé ouvert par 17.13).
  - Statut `CONFIRMED` (supprimé, §17).

## Success Evidence
- Les tests de contrat FHIR R4 sont verts : `CapabilityStatement` conforme à ce qui est servi, Bundles, `OperationOutcome`, correspondance des statuts (testing.md).
- Pour chaque écriture FHIR, un scénario montre le même refus que l'écran ou l'API applicative dans le même cas (`rule_violation`, `conflict`, `forbidden`, etc.).
- Un client sans jeton trouve un `Slot` libre ; avec le jeton du patient de démo, il le réserve (réponse `booked` avec praticien et salle attribués), puis l'annule ; l'audit et la notification sont identiques à ceux de l'écran.
- Un client qui utilise le jeton d'un patient ne voit ni les RDV ni la ressource Patient d'un autre patient.

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Tous les cas d'usage, y compris la réservation par l'admin | dependency | `depends_on` Epic 7, et par transitivité les Epics précédents |
| Émission des jetons : une commande d'administration et la seed (un jeton de démo par rôle), sans écran (non spécifié) | assumption | acceptée |
| §15.3 fait correspondre `BOOKED` à `booked` sans extension, puisque `CONFIRMED` est supprimé | decision | découle de la décision de l'Epic 4 |
