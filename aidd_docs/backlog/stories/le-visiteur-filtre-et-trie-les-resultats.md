---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§6.3, §6.4, §6.5, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/chaque-resultat-montre-ses-prochaines-disponibilites.md
---

# Story: Le visiteur filtre et trie les résultats
**As** visiteur
**I want** filtrer et trier les résultats de ma recherche
**So that** je trouve le créneau qui me convient

## Acceptance
- Filtres facultatifs, combinés en ET : spécialité, hôpital, ville, type de RDV, date au plus tôt, fenêtre (toutes, aujourd'hui, sous 3 jours, sous 7 jours), moment de la journée (matin avant 12:00, après-midi de 12:00 à 17:00, soir après 17:00, dans le fuseau de l'hôpital).
- Avec un filtre de type, les créneaux sont calculés pour ce type.
- Un filtre de temps change à la fois les résultats listés et les créneaux montrés.
- Tris : disponibilité la plus proche (par défaut), nom de A à Z, nom de Z à A, distance la plus courte.
- Le tri porte sur tout l'ensemble des résultats, pas sur la page ; les égalités se départagent par nom puis par id.
- Le tri par distance part de la position donnée par le navigateur, sans service externe, et des coordonnées des hôpitaux ; sans position, il n'est pas proposé.
- Filtres et tri vivent dans l'adresse de la page, et les trois `GET /search/providers`, `/search/hospitals`, `/search/specialties` les acceptent.
