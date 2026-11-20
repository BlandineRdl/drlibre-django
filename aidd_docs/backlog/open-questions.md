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
- La disponibilité et les règles de §5.3 sont-elles vérifiées dès la réservation provisoire, ou au code seulement ?
- Une deuxième réservation provisoire pour le même email est-elle refusée ou remplace-t-elle la première ?
- Un renvoi de code annule-t-il le précédent, remet-il les 5 essais à zéro, prolonge-t-il la réservation provisoire ?
- Après 5 essais manqués, la réservation provisoire est-elle libérée ?
- Le refus générique (email du personnel ou inactif) arrive-t-il à la réservation provisoire ou au code, et un code est-il envoyé ?
- Code correct mais placement en échec : la réservation provisoire est-elle supprimée ?
- Quelle réponse au dépassement d'une limite de débit (aucun code ni 429 au §4) ?
- Où vont les hôpitaux sans coordonnées dans le tri par distance ?
- Les créneaux à 12:00 et 17:00 pile sont-ils « après-midi » ou « soir » ?
- En « premier disponible », le visiteur voit-il le praticien choisi avant de saisir le code ?
- Page praticien : quelle semaine par défaut, navigation au-delà de 90 jours ? Page hôpital : pour quel type calculer les prochains créneaux ?

## E4 Portail patient et notifications
- Le patient peut-il annuler un RDV `CHECKED_IN` ?
- `not_found` ou `forbidden` quand un patient vise le RDV ou l'entrée d'un autre patient ?
- Quel code pour le déplacement d'un RDV qui n'est pas `BOOKED` : `invalid_transition` ?
- Que contient le `.ics`, et le motif en est-il exclu ?
- `GET /appointments` pour le personnel est-il livré par E4 ou par E6 et E7 ?
- À quelle fréquence tourne le job de rappel ?

## E5 Liste d'attente
- Un patient peut-il s'inscrire pour un type non réservable en ligne ?
- Quelles règles pour la fenêtre (début avant fin, pas dans le passé, fin incluse) ?
- Le praticien préféré doit-il être du département du type ?
- Après un échec d'acceptation en `rule_violation`, l'entrée reste-t-elle `OFFERED` ou repasse-t-elle `WAITING` ?
- L'acceptation envoie-t-elle aussi la notification « RDV réservé », en plus de « Créneau réservé » ?
- Quel code pour accepter une entrée qui n'est pas `OFFERED` ?
- L'offre manuelle tient-elle compte du praticien préféré, et quel code sans créneau convenable ?
- Où l'admin accepte-t-il une offre dans la console ?
- Le patient est-il prévenu quand son offre repasse en `WAITING` ou que son entrée expire ?
- Le job d'expiration audite-t-il chaque entrée ou une seule fois avec le nombre ?
- L'offre automatique est-elle dans la transaction de l'annulation, et celui qui annule peut-il recevoir son propre créneau ?
- Quelles colonnes affiche la liste d'attente admin ?

## E6 Espace praticien
- « Prochain créneau libre » : pour quel type et à partir de quand ?
- Calendrier et frise des salles : navigation, et premier jour de la semaine ?
- Les RDV annulés apparaissent-ils dans la liste du jour ?
- Quels statuts occupent une salle dans la frise ?
- « Dernière » et « prochaine visite » : quels statuts comptent ?
- Le bandeau de déplacement change-t-il de semaine ?
- Arrivée et absence sont-elles permises avant l'heure du RDV ?
- Les notes d'un RDV terminé ou annulé restent-elles modifiables ?
- Le motif d'annulation a-t-il une longueur maximale ?

## E7 Supervision admin
- « Plus récents d'abord » : tri sur le début ou la création, et quelles colonnes ?
- Minutes disponibles de l'utilisation : dans le fuseau de l'hôpital de chaque praticien ?
- Égalités et moins de 5 praticiens dans le top 5 ?
- Dans quel fuseau afficher le journal d'audit ?
- La salle choisie par l'admin doit-elle être du département du praticien ?
- D'où l'admin lance-t-il arrivée, absence et annulation ?
- Le bouton de rappel affiche-t-il le nombre de rappels créés ?

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
