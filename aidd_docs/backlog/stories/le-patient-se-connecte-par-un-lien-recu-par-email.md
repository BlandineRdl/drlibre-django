---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§7.3, §7.6, §7.7, §12.1, §12.2, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
---

# Story: Le patient se connecte par un lien reçu par email
**As** patient
**I want** recevoir un lien de connexion par email, sans mot de passe
**So that** je retrouve mon espace patient après ma réservation

## Acceptance
- Sur la page de connexion, le patient saisit son email et demande un lien ; la page affiche le même message que l'adresse ait un compte ou non.
- Le lien n'est envoyé qu'à un patient actif ; un email inconnu, d'admin, de praticien ou d'utilisateur inactif ne reçoit rien et ne crée rien.
- Le lien vaut 15 minutes et sert une fois ; en demander un nouveau annule les précédents ; au plus 3 liens par heure et par email, et 20 demandes par heure et par adresse réseau.
- Ouvrir le lien affiche un bouton « Continuer » ; le lien n'est consommé qu'au clic, puis le patient arrive dans son espace sur une adresse sans le jeton.
- La session dure 24 h et n'est jamais prolongée, que le patient ait un mot de passe ou non.
- Un lien expiré, déjà utilisé ou annulé ne connecte pas.
- L'email du lien est le seul email qui contient un lien qui connecte ; le jeton n'apparaît jamais dans les journaux.
- Lien demandé, lien utilisé et lien refusé sont audités avec le domaine de l'email seulement.
- `POST /auth/link` répond toujours de la même façon ; `POST /auth/link/verify` échange le jeton contre la session.
