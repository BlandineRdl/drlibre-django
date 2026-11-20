---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Audit log, §3.1, §4)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
---

# Story: L'admin consulte le journal d'audit
**As** admin
**I want** parcourir le journal d'audit
**So that** je retrouve qui a fait quoi, et sur quelle requête

## Acceptance
- Le journal est en lecture seule : aucune entrée ne peut être modifiée ni supprimée.
- Les entrées les plus récentes viennent en premier, 20 par page avec le nombre total.
- Les filtres portent sur l'acteur, le type d'entité et la période ; une valeur inutilisable dans l'adresse revient au défaut.
- Chaque entrée montre l'heure, l'acteur (vide pour un échec de connexion ou une étape avant vérification de l'email), l'action, l'entité et le correlation id.
