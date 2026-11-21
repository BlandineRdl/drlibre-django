# Questions ouvertes des Stories
Points où la spec et les Epics sont muets, relevés en écrivant les Stories (2026-11-20). À trancher au plus tard au plan de l'Epic concerné ; une réponse change l'Acceptance de la Story visée.

## E2 Disponibilités et créneaux
Tranchées au plan E2 (`aidd_docs/tasks/2026_11/2026_11_20_e2-disponibilites-creneaux/plan.md`, Decisions).
- Que deviennent les RDV futurs quand la plage qui les contient est modifiée ou supprimée ? → Rien : modifier ou supprimer une plage, comme une absence, ne touche jamais les RDV existants.
- Modifier une plage remet-il sa date de début de validité à aujourd'hui ? → Non, elle garde sa date ; seule une nouvelle plage vaut à partir d'aujourd'hui.
- Que renvoie `GET /slots` au-delà de l'horizon de 90 jours de la table `slot` ? → Rien d'autre : les créneaux au-delà sont simplement absents.
- Que renvoie `GET /slots` pour un type d'un autre département, un type inactif ou un praticien inactif ? → `not_found` pour un type inconnu ou inactif, ou un praticien inconnu, inactif ou hors du département du type.
- Quel code pour une plage qui en chevauche une autre ou une absence en double : `invalid_input` ou `conflict` ? → `invalid_input` sur le champ, message nommant le conflit ; `conflict` reste réservé aux chevauchements de RDV.
- Que montrent le résumé hebdomadaire et le calendrier admin, et le calendrier se navigue-t-il ? → Résumé : jour et plages HH:MM–HH:MM par praticien. Calendrier : grille 07:00–19:00 par 30 minutes avec plages et absences, liens semaine précédente, cette semaine, suivante.

## E3 Recherche et réservation sans compte
Tranchées au plan E3 (`aidd_docs/tasks/2026_11/2026_11_21_e3-reservation-sans-compte/plan.md`, Decisions).
- La disponibilité et les règles de §5.3 sont-elles vérifiées dès la réservation provisoire, ou au code seulement ? → Dès la provisoire : créneau, délai, type réservable en ligne, disponibilité ; les contrôles liés au patient seulement au code, puis tout le placement rejoué.
- Une deuxième réservation provisoire pour le même email est-elle refusée ou remplace-t-elle la première ? → Elle remplace la première, libérée avec son code.
- Un renvoi de code annule-t-il le précédent, remet-il les 5 essais à zéro, prolonge-t-il la réservation provisoire ? → Il annule le précédent, donne un code neuf de 10 minutes avec 5 essais, ne prolonge pas la réservation.
- Après 5 essais manqués, la réservation provisoire est-elle libérée ? → Non : le code est mort, la réservation reste jusqu'à son expiration, un nouveau code peut être demandé.
- Le refus générique (email du personnel ou inactif) arrive-t-il à la réservation provisoire ou au code, et un code est-il envoyé ? → Au code : même flux et même email, puis un seul `forbidden` générique, réservation libérée, aucun compte créé.
- Code correct mais placement en échec : la réservation provisoire est-elle supprimée ? → Oui : compte créé, session ouverte, réservation retirée, échec affiché avec les créneaux rafraîchis.
- Quelle réponse au dépassement d'une limite de débit (aucun code ni 429 au §4) ? → `rule_violation` de règle `too_many_requests` ; une demande de lien au-delà de sa limite renvoie la réponse habituelle sans rien envoyer.
- Où vont les hôpitaux sans coordonnées dans le tri par distance ? → Après ceux qui en ont, puis par nom, puis par id.
- Les créneaux à 12:00 et 17:00 pile sont-ils « après-midi » ou « soir » ? → Intervalles semi-ouverts dans le fuseau de l'hôpital : matin [00:00, 12:00), après-midi [12:00, 17:00), soir [17:00, 24:00).
- En « premier disponible », le visiteur voit-il le praticien choisi avant de saisir le code ? → Oui : la page du code nomme le praticien choisi à la création de la réservation.
- Page praticien : quelle semaine par défaut, navigation au-delà de 90 jours ? → Semaine courante dans le fuseau de l'hôpital, `?week=`, navigation limitée à l'horizon de 90 jours. Page hôpital : prochains créneaux du plus court type en ligne actif de chaque département.

## E3 suivi
Restée ouverte après la revue E3.
- Les créneaux de la recherche et de `GET /slots` ignorent les salles (§5.1), alors que §6.2 dit « les créneaux affichés sont exactement ceux que la réservation accepterait » : un créneau affiché peut échouer en `no_room_available` à la réservation (reproduction : un type avec salle, toutes les salles du département prises à cette heure, le créneau reste listé). Compter la capacité des salles dans les créneaux (lecture plus coûteuse, p95 à re-prouver) ou accepter l'écart et le documenter en §6.2 ?

## E4 Portail patient et notifications
Tranchées au plan E4 (`aidd_docs/tasks/2026_11/2026_11_21_e4-portail-patient-notifications/plan.md`, Decisions).
- Le patient peut-il annuler un RDV `CHECKED_IN` ? → Oui, comme `BOOKED`, règle des 24 h comprise ; `COMPLETED`, `CANCELLED`, `NO_SHOW` donnent `invalid_transition` avec le statut actuel.
- `not_found` ou `forbidden` quand un patient vise le RDV ou l'entrée d'un autre patient ? → `forbidden` ; un id inconnu donne `not_found`.
- Quel code pour le déplacement d'un RDV qui n'est pas `BOOKED` : `invalid_transition` ? → Oui, avec le statut actuel, vérifié avant les règles.
- Que contient le `.ics`, et le motif en est-il exclu ? → UID, début et fin UTC, type et praticien, hôpital et adresse ; jamais le motif.
- `GET /appointments` pour le personnel est-il livré par E4 ou par E6 et E7 ? → Par E6 et E7 : en E4, la liste, l'annulation et le déplacement servent le patient seul, le personnel reçoit `forbidden`.
- À quelle fréquence tourne le job de rappel ? → Toutes les 15 minutes : le rappel part entre 24 h et 23 h 45 avant le RDV, une seule fois par RDV.

## E5 Liste d'attente
Tranchées au plan E5 (`aidd_docs/tasks/2026_11/2026_11_21_e5-liste-d-attente/plan.md`, Decisions).
- Un patient peut-il s'inscrire pour un type non réservable en ligne ? → Non, `rule_violation` `type_not_bookable_online` ; l'admin inscrit pour tout type actif.
- Quelles règles pour la fenêtre (début avant fin, pas dans le passé, fin incluse) ? → Deux dates, fin incluse, dans le fuseau de l'hôpital du type ; fin avant début ou avant aujourd'hui donne `invalid_input` sur `to_date`.
- Le praticien préféré doit-il être du département du type ? → Oui, actif et du département du type, sinon `not_found`.
- Après un échec d'acceptation en `rule_violation`, l'entrée reste-t-elle `OFFERED` ou repasse-t-elle `WAITING` ? → Elle reste `OFFERED`, rien n'est écrit ; seul un `conflict` la repasse en `WAITING`.
- L'acceptation envoie-t-elle aussi la notification « RDV réservé », en plus de « Créneau réservé » ? → Non, « Créneau réservé » seule, ni « RDV réservé » ni email de confirmation.
- Quel code pour accepter une entrée qui n'est pas `OFFERED` ? → `invalid_transition` avec le statut actuel.
- L'offre manuelle tient-elle compte du praticien préféré, et quel code sans créneau convenable ? → Oui, même filtre que l'offre automatique ; sans RDV annulé à venir, libre et non offert, `not_found`.
- Où l'admin accepte-t-il une offre dans la console ? → Sur la ligne de la liste d'attente, « Accepter pour le patient » ; « Proposer un créneau » sur les lignes `WAITING`, inscription par `/console/waitlist/new`.
- Le patient est-il prévenu quand son offre repasse en `WAITING` ou que son entrée expire ? → Non, le statut se lit dans sa liste.
- Le job d'expiration audite-t-il chaque entrée ou une seule fois avec le nombre ? → Chaque entrée, acteur vide.
- L'offre automatique est-elle dans la transaction de l'annulation, et celui qui annule peut-il recevoir son propre créneau ? → Oui, dans la même transaction, après la mise à jour des créneaux ; les entrées de celui qui annule sont exclues.
- Quelles colonnes affiche la liste d'attente admin ? → Inscription, patient, type, praticien préféré, fenêtre, statut, heure proposée avec fuseau ; filtre `status`, plus anciennes d'abord, 20 par page avec le total.

## E6 Espace praticien
Tranchées au plan E6 (`aidd_docs/tasks/2026_11/2026_11_21_e6-praticien-agenda/plan.md`, Decisions).
- « Prochain créneau libre » : pour quel type et à partir de quand ? → Tout type : le plus tôt des créneaux stockés du praticien, non retenus, à partir de `max(maintenant, début du jour affiché)` ; « — » sinon.
- Calendrier et frise des salles : navigation, et premier jour de la semaine ? → Semaine du lundi, `?week=` précédente / courante / suivante ; Aujourd'hui et Salles en `?day=` ; une valeur inutilisable revient à aujourd'hui.
- Les RDV annulés apparaissent-ils dans la liste du jour ? → Oui, annulés et absents, avec leur statut et sans action ; les annulés comptés à part.
- Quels statuts occupent une salle dans la frise ? → Les RDV actifs : `BOOKED`, `CHECKED_IN`, `COMPLETED`.
- « Dernière » et « prochaine visite » : quels statuts comptent ? → Dernière : `COMPLETED` le plus récent avant maintenant ; prochaine : `BOOKED` ou `CHECKED_IN` le plus proche après maintenant.
- Le bandeau de déplacement change-t-il de semaine ? → Oui, `?week=` dans l'horizon de 90 jours, sans le délai patient de 120 min.
- Arrivée et absence sont-elles permises avant l'heure du RDV ? → Oui, aucune règle d'heure.
- Les notes d'un RDV terminé ou annulé restent-elles modifiables ? → Oui, dans tous les statuts.
- Le motif d'annulation a-t-il une longueur maximale ? → 500 caractères, la limite E4.
- Quand le praticien annule, son patient peut-il recevoir l'offre du créneau libéré ? → Non, comme en E5 : les entrées du patient du RDV annulé sont exclues, qui que soit celui qui annule.

## E7 Supervision admin
Tranchées au plan E7 (`aidd_docs/tasks/2026_11/2026_11_21_e7-supervision-admin/plan.md`, Decisions).
- « Plus récents d'abord » : tri sur le début ou la création, et quelles colonnes ? → `start` décroissant puis `id` (pas de `created_at`) ; début dans le fuseau nommé de l'hôpital, patient, praticien, département, type, statut, source, salle.
- Minutes disponibles de l'utilisation : dans le fuseau de l'hôpital de chaque praticien ? → Oui ; les jours sont aujourd'hui local de chaque hôpital et les n−1 précédents.
- Égalités et moins de 5 praticiens dans le top 5 ? → RDV non annulés décroissants puis nom ; seulement les praticiens ayant un RDV, « Aucun RDV sur la période » sinon.
- Dans quel fuseau afficher le journal d'audit ? → `settings.TIME_ZONE`, nommé sur la page ; filtre acteur par email, résolu dans la vue.
- La salle choisie par l'admin doit-elle être du département du praticien ? → Du département du type, active (`not_found`) puis libre (`conflict`).
- D'où l'admin lance-t-il arrivée, absence et annulation ? → De la fiche `/console/appointments/<id>`, liée depuis chaque ligne ; son historique montre les actions du praticien en « Personnel ».
- Le bouton de rappel affiche-t-il le nombre de rappels créés ? → Oui, « N rappels envoyés » ; `POST /jobs/reminders` renvoie `{count}`.

## E8 FHIR R4
- Quels champs de `PractitionerRole` sont publics sans jeton ?
- Quels codes pour nommer un autre patient ou praticien, une salle par un patient, un déplacement qui change de praticien ou de type, une écriture sur un champ non autorisé, une interaction non supportée ?
- Un `_count` au-delà de 100 est-il ramené à 100 ou refusé ?
- Le jeton d'un utilisateur désactivé cesse-t-il aussitôt, expire-t-il, se révoque-t-il ?
- L'offre manuelle de l'admin passe-t-elle par FHIR ?
- Un praticien voit-il les entrées qui le désignent comme praticien préféré ?
- Le praticien écrit-il ses notes (`Appointment.comment`) par FHIR ?
- Créer un hôpital (`Organization` + `Location`) se fait-il en une ou deux requêtes, et un `Practitioner` ou `Patient` FHIR exige-t-il un mot de passe temporaire ?
- Un client peut-il fixer le `planningHorizon` d'un `Schedule` ?
