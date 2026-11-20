---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§7.1, §7.2, §5.2, §7.6, §7.7, §12.2, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/le-visiteur-consulte-les-pages-publiques-des-praticiens-hopitaux-et-specialites.md
---

# Story: Un visiteur réserve un créneau en validant un code reçu par email
**As** visiteur
**I want** réserver le créneau d'un praticien nommé en validant un code reçu par email, sans mot de passe
**So that** j'obtienne un RDV et un compte patient en une seule démarche

## Acceptance
- Un créneau d'un résultat ou d'une page publique ouvre la réservation en un clic ; le parcours enchaîne type de RDV, praticien puis créneau.
- Le visiteur saisit nom complet, date de naissance, email, téléphone facultatif, motif facultatif, et accepte les conditions et la notice de confidentialité.
- L'envoi de ces informations crée une réservation provisoire de 10 minutes sur le créneau et envoie par email un code à 6 chiffres.
- Avec le bon code, le RDV est créé en `BOOKED`, source `ONLINE`, fin égale au début plus la durée du type, et la réservation provisoire disparaît.
- Si le type exige une salle, le RDV reçoit la salle par défaut du praticien si elle est libre, sinon la première salle active libre du département par ordre de code ; un type sans salle n'en reçoit pas.
- Un email inconnu crée un patient sans mot de passe, avec le nom, la date de naissance et le téléphone saisis, et l'email marqué vérifié.
- Le bon code ouvre une session de 24 h, jamais prolongée.
- La page de confirmation montre le RDV, propose son fichier `.ics` et un lien vers les RDV du patient.
- La réservation envoie un seul email, la confirmation : heure, hôpital et praticien, sans motif ; comme l'email du code, il ne contient aucun lien qui connecte, seulement un lien vers la page de connexion.
- Les emails partent une fois la réservation enregistrée, avec nouvelles tentatives ; un échec d'envoi n'annule ni la réservation provisoire ni le RDV, et le visiteur peut redemander un code.
- Sont audités avec le domaine de l'email seulement : réservation provisoire créée, compte patient créé, RDV pris ; l'acteur est vide avant la vérification, puis c'est le patient.
- `POST /booking/holds` et `POST /booking/holds/{id}/verify` offrent le même parcours sans session.
- Sur la seed de charge, la réservation répond sous 200 ms au p95 du scénario Locust.
