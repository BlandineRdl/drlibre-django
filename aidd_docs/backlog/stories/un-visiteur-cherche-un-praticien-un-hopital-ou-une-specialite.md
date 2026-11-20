---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§6.1, §6.2, §6.5, §4, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
---

# Story: Un visiteur cherche un praticien, un hôpital ou une spécialité
**As** visiteur
**I want** chercher par texte depuis la page d'accueil, sans compte
**So that** je trouve à qui m'adresser

## Acceptance
- La page d'accueil est la recherche ; elle s'ouvre sans session.
- Le texte trouve, sans tenir compte de la casse et sur des mots partiels, le nom d'hôpital, la ville, le nom du praticien, la spécialité, le département et le type de RDV.
- Les résultats forment trois listes entre lesquelles le visiteur bascule : praticiens, hôpitaux, spécialités.
- Un praticien montre nom complet, titre, spécialité, hôpital, département et ville ; un hôpital, nom, adresse, ville, spécialités proposées et nombre de praticiens réservables ; une spécialité, nom, nombre de praticiens et nombre d'hôpitaux.
- Seules les données réservables apparaissent : hôpitaux, praticiens et spécialités actifs, types actifs réservables en ligne ; un praticien sans type réservable en ligne dans son département n'est pas listé.
- L'email, le téléphone et la date de naissance d'un praticien, et toute donnée de patient, ne sont jamais montrés.
- 20 résultats par page par défaut, 10 ou 50 au choix ; la page montre le total, la page courante et le nombre de pages ; une page hors limites montre la dernière.
- Texte, liste, taille et numéro de page vivent dans l'adresse : la recherche se partage, le bouton retour fonctionne, et une valeur inutilisable retombe sur sa valeur par défaut.
- `GET /search/providers`, `GET /search/hospitals` et `GET /search/specialties` servent les mêmes résultats sans session.
