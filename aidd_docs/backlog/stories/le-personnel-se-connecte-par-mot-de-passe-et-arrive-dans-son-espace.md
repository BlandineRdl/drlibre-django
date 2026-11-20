---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§12.1, §12.2)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
---

# Story: Le personnel se connecte par mot de passe et arrive dans son espace
**As** membre du personnel (admin ou praticien)
**I want** me connecter avec mon email et mon mot de passe
**So that** j'accède à mon espace de travail

## Acceptance
- Une connexion réussie mène l'admin à la console admin, le praticien à son espace, et le patient avec mot de passe à la page d'accueil du portail, encore vide jusqu'à l'Epic portail patient.
- Un email inconnu et un mauvais mot de passe donnent le même message, dans le même temps de réponse.
- Un utilisateur inactif ne peut pas se connecter.
- La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié.
- La déconnexion supprime la session.
- La connexion et la déconnexion sont aussi disponibles par l'API `POST /auth/login` et `POST /auth/logout` (§14).
- La réussite et l'échec sont audités avec seulement le domaine de l'email.
