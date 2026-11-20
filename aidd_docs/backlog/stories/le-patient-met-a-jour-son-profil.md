---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§8 Profile, §4)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
---

# Story: Le patient met à jour son profil
**As** patient connecté, avec ou sans mot de passe
**I want** modifier mon téléphone et ma date de naissance
**So that** mes coordonnées restent justes

## Acceptance
- Le nom et l'email sont affichés, non modifiables.
- Le téléphone accepte 7 à 20 caractères parmi chiffres, espaces et `+ ( ) -` ; la date de naissance est une date réelle, pas dans le futur ; un champ vide efface la valeur ; une valeur invalide donne `invalid_input` avec le message du champ.
- La modification laisse une entrée d'audit avec le nom des champs changés, jamais leurs valeurs.
- Un patient qui a un mot de passe accède au changement de mot de passe ; un patient sans mot de passe ne le voit pas.
