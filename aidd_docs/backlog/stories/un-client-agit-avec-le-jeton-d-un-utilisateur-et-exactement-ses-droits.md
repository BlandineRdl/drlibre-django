---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.1, §15.2, §15.4, §15.5, §12.3, §16)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-sans-jeton-decouvre-le-referentiel-et-les-creneaux-libres.md
---

# Story: Un client agit avec le jeton d'un utilisateur et exactement ses droits
**As** client API
**I want** m'authentifier avec le jeton bearer d'un utilisateur
**So that** j'accède à ce que cet utilisateur voit à l'écran, ni plus ni moins

## Acceptance
- Une commande d'administration émet un jeton pour un utilisateur ; la seed fournit un jeton de démo par rôle (admin, praticien, patient).
- Un jeton invalide renvoie `unauthenticated` (401) ; un jeton valide donne exactement les droits de son utilisateur.
- Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins.
- `Patient` (nom, date de naissance, email, téléphone, actif) est lisible par le patient lui-même, par un praticien pour ses propres patients, et par l'admin ; une autre fiche existante donne `forbidden`.
- Les recherches `Patient` acceptent `name`, `email`, `phone` et `birthdate`, limitées à ce que l'utilisateur peut voir.
- Le patient met à jour son propre téléphone et sa date de naissance ; une mise à jour avec un `If-Match` périmé échoue en 412.
- Chaque écriture laisse la même entrée d'audit que l'écran correspondant.
