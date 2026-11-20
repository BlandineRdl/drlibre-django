---
type: epic
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§5.2–5.5, §6, §7, §14 [new])
goal: aidd_docs/memory/project-brief.md
depends_on:
  - aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
  - aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md
---
# Epic: Un visiteur trouve et réserve un créneau sans compte
Un visiteur cherche un praticien, un hôpital ou une spécialité, choisit un créneau libre et le réserve en validant un code reçu par email, sans mot de passe ; il devient patient et reste connecté 24 h.

## Context and Value
- Audience : visiteur anonyme, patient sans mot de passe, patient déjà connecté.
- Besoin : aujourd'hui, seul un patient créé par un admin peut réserver. La recherche publique, la réservation sans compte et le multi-hôpitaux sont les ajouts [new] de la spec (§1, §6, §7).
- Valeur : c'est le parcours principal du produit (brief, Main journey). La vérification de l'email avant la réservation empêche d'accaparer les créneaux en anonyme (17.6).

## Boundaries
- Includes:
  - Recherche publique en page d'accueil : texte partiel sur 6 champs, trois listes (praticiens, hôpitaux, spécialités), données publiques réservables uniquement (§6.1).
  - Résultats avec prochaines disponibilités, horizon de 120 min à 90 jours, type le plus court par défaut, « aucune disponibilité » en fin de liste (§6.2).
  - Filtres combinés, tris stables (dont distance), pagination 10/20/50, état complet dans l'URL (§6.3–6.5).
  - Pages publiques praticien, hôpital et spécialité, avec bandeau de créneaux à la semaine et « premier disponible » (§6.6).
  - Placement commun à tous les chemins de réservation, règles de réservation, « premier disponible » en round robin pondéré (§5.2, §5.3, §5.5) ; un patient ne réserve que pour lui-même (§5.4).
  - Parcours sans compte : saisie des informations, réservation provisoire de 10 min (une par email), code à 6 chiffres (5 essais, 3 renvois par heure), création du patient sans mot de passe ou rattachement à un patient existant, refus générique pour les emails du personnel ou d'un compte inactif, session de 24 h (§7.1, §7.2).
  - Page de confirmation avec fichier `.ics` et lien vers les RDV du patient ; un patient déjà connecté saute les étapes 2 à 4 (§7.1).
  - Connexion par lien email : patients uniquement, 15 min, usage unique au clic sur « Continuer », réponse identique que le compte existe ou non, 3 liens par heure (§7.3).
  - Limites de débit par email et par adresse réseau ; rien n'est révélé avant la vérification du code (§7.5).
  - Emails de code, de lien de connexion et de confirmation, sans lien qui connecte, sauf l'email du lien de connexion lui-même (§7.6).
  - Audit des événements de §7.7, avec le domaine de l'email seulement.
  - API publique correspondante (§14 [new]).
  - Tri par distance à partir de la géolocalisation du navigateur seulement, sans service externe ; sans position, pas de tri par distance.
  - En « premier disponible », le praticien est choisi à la création de la réservation provisoire ; sa date de dernière attribution n'est mise à jour qu'à la réservation.
  - Un job Celery expire les réservations provisoires chaque minute et les audite ; le créneau redevient libre dès l'heure d'expiration, même avant le passage du job.
  - Code correct mais placement en échec : le compte est créé et la session ouverte, l'échec s'affiche avec les créneaux à jour.
  - Emails envoyés après la validation de la transaction, par une tâche Celery avec nouvelles tentatives ; un échec d'envoi n'annule rien, et le visiteur peut redemander un code.
  - Limite de 20 requêtes par heure et par adresse réseau, pour chaque type : réservation provisoire, code, lien.
  - Un seul email par réservation : l'email de confirmation.
  - API `POST /appointments` pour un patient connecté (§14).
  - Option « taille » du script de seed pour la charge (10 hôpitaux, 200 praticiens, 5k patients, 50k RDV), utilisée par le scénario Locust.
- Excludes:
  - Liste et gestion des RDV du patient (annuler, déplacer), notifications in-app, rappels, emails de déplacement, d'annulation, de rappel et d'offre (Epic portail patient).
  - Réservation par le personnel (Epics espace praticien et supervision admin).
  - Liste d'attente (Epic dédié).
  - Mot de passe pour un patient sans mot de passe, auto-inscription, SMS, SEO (hors périmètre).

## Success Evidence
- De bout en bout sur la seed de démo : recherche → créneau → informations → code lu dans Mailpit → RDV `BOOKED` en source `ONLINE` ou `ROUND_ROBIN`, patient créé, session de 24 h ouverte.
- Un créneau tenu par une réservation provisoire n'est proposé à personne d'autre ; une réservation provisoire expirée libère le créneau ; un code non saisi ne crée ni RDV ni compte.
- Une demande de lien avec un email inconnu renvoie la même réponse et n'envoie rien.
- Scénarios BDD verts pour §5.2, §5.3, §5.5, §7.1–7.3 et §7.5.
- Recherche et réservation sous 200 ms au p95, mesuré par un scénario Locust sur la seed (architecture.md, testing.md).
- Parcours conforme WCAG 2.2 AA, de 375 à 1440 px (§16).

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Référentiel et profils praticiens | dependency | `depends_on` Epic 1 |
| Calcul des créneaux libres | dependency | `depends_on` Epic 2 |
| Valeurs proposées (horizon 90 j, 3 créneaux par résultat, réservation provisoire 10 min, lien 15 min) retenues telles quelles | assumption | acceptée (17.14) |
| Contenu des conditions et de la notice de confidentialité à accepter | assumption | acceptée : texte fictif de démo |
| Géolocalisation, choix du praticien, expiration, échec après code, emails, limite réseau, seed de charge | decision | prises : décision du rapport de zones d'ombre (aidd_docs/backlog/epics-shadow-report.md) |
