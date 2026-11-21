---
status: pending
---

# Instruction: Recherche publique, filtres, tris, pages publiques
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── pyproject.toml                                         ✏️  import-linter: `drlibre.search` layers container; search core forbids other contexts
├── config/settings.py                                     ✏️  search app if it needs one (no models expected)
├── src/drlibre/search/
│   ├── __init__.py                                        ✅
│   ├── domain/criteria.py                                 ✅  SearchCriteria.parse: text, list, filters, sort, page, size (10/20/50), location; bad values fall back to defaults
│   ├── domain/results.py                                  ✅  ProviderResult, HospitalResult, SpecialtyResult, NextSlots, public details
│   ├── application/ports/{__init__,inbound,outbound}.py   ✅  inbound SearchDirectory, PublicPages ; outbound SearchQueries
│   ├── application/use_cases/search_directory.py          ✅  horizon now + 120 min → + 90 days, last page when out of range
│   ├── application/use_cases/public_pages.py              ✅  provider, hospital, specialty; `not_found` when absent or inactive
│   └── infrastructure/sql_queries.py                      ✅  one SQL per list: partial ILIKE on 6 fields, bookable only, next slots from `scheduling_slot` minus open holds, time of day in hospital zone, haversine distance, stable order, COUNT for total
├── src/drlibre/scheduling/
│   └── (unchanged)                                        ·  `GET /slots` public reuses FindFreeSlots
├── src/drlibre/interfaces/
│   ├── api/search.py                                      ✅  `GET /search/providers|hospitals|specialties`
│   ├── api/public.py                                      ✅  `GET /providers/{id}`, `/hospitals/{id}`, `/specialties/{id}`
│   ├── api/slots.py                                       ✏️  no session required
│   ├── api/__init__.py                                    ✏️  mount routers
│   └── web/
│       ├── views/search.py                                ✅  `/` search page, state in the query string
│       ├── views/public.py                                ✅  `/providers/<id>?type=&week=`, `/hospitals/<id>`, `/specialties/<id>`
│       ├── views/auth.py                                  ✏️  `home` no longer redirects; route moves to search
│       ├── presenters/search.py                           ✅  list ViewModels, pagination, « Aucune disponibilité dans les 90 prochains jours », zone named
│       ├── presenters/public.py                           ✅  week strip Monday–Sunday, previous / next within horizon
│       ├── templates/search/home.html                     ✅
│       ├── templates/public/{provider,hospital,specialty}.html ✅
│       ├── templates/_nav.html                            ✏️  public nav, « Mon espace » when signed in
│       └── urls.py                                        ✏️
├── static/drlibre-geo.js                                  ✅  « Trier par distance » fills lat/lon from the browser; button hidden without geolocation
├── config/settings.py                                     ✏️  CSP allows own script (`'self'`) if not already
└── tests/
    ├── features/search/
    │   ├── un_visiteur_cherche_un_praticien_un_hopital_ou_une_specialite.feature  ✅
    │   ├── chaque_resultat_montre_ses_prochaines_disponibilites.feature          ✅
    │   ├── le_visiteur_filtre_et_trie_les_resultats.feature                      ✅
    │   └── le_visiteur_consulte_les_pages_publiques_des_praticiens_hopitaux_et_specialites.feature ✅
    ├── integration/search/test_*.py                       ✅  pytest-bdd on PostgreSQL, one module per feature
    ├── contracts/test_search_slots_match_booking.py       ✅  next slots of search == FindFreeSlots on the same data, holds included
    ├── api/test_search_endpoints.py                       ✅  anonymous 200; unknown filter value falls back; detail 404 for inactive
    ├── api/test_slots_endpoint.py                         ✏️  anonymous now 200
    └── presenters/test_search_presenters.py, test_public_presenters.py ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | PostgreSQL with two hospitals (one without coordinates), specialties, clinicians with rules, one inactive clinician, one type not online, one open hold | slot table refreshed | system |
| Happy path | search « card » | three lists, matched on partial words, providers with 3 next starts and type named | browser, api |
| Happy path | filters type + afternoon + within 3 days, sort name Z→A, size 10, page 2 | URL carries every value; slots in hospital zone | browser |
| Edge case | provider without online type, inactive hospital | not listed | api |
| Edge case | nothing free in 90 days | listed last with the text | api |
| Edge case | page 99, size 7, sort distance without location | last page, size 20, distance not offered | browser |
| Edge case | slot 12:00 and 17:00 | afternoon and evening respectively | system |
| Edge case | held slot | absent from search, pages and `GET /slots` until expiry | api |
| Teardown | rollback | baseline | system |

## Wireframe
```txt
┌──────────────────────────────────────────────┐
│ (1) Nav publique · Se connecter / Mon espace  │
├──────────────────────────────────────────────┤
│ (2) [ Rechercher un praticien, un lieu… ] [OK]│
├──────────────────────────────────────────────┤
│ (3) Praticiens (12) | Hôpitaux (3) | Spécialités (4) │
├────────────┬─────────────────────────────────┤
│ (4) Filtres│ (5) Tri [Disponibilité ▾] [Distance] │
│ spécialité │ ┌─────────────────────────────┐ │
│ hôpital    │ │ (6) Dr Nom · titre · spéc.  │ │
│ ville      │ │ hôpital · dép. · ville      │ │
│ type       │ │ Consultation 20 min         │ │
│ à partir du│ │ [lun 9:00][lun 9:20][mar…]  │ │
│ fenêtre    │ │ Tous les horaires →         │ │
│ moment     │ └─────────────────────────────┘ │
│ [Appliquer]│ (7) 1–20 sur 47 · page 1/3 [‹][›] │
│            │ Taille [20 ▾] · Fuseau : Europe/Paris │
└────────────┴─────────────────────────────────┘
```
1. Nav: search, sign-in or « Mon espace ».
2. Search box, labelled, state kept in the URL.
3. List switcher with counts.
4. Filters as a GET form; on 375 px they stack above the results.
5. Sort select; distance button only when geolocation is available.
6. Result card: public fields, next slots as booking links, all-times link; empty text when none.
7. Pagination, total, page size, time zone named.

```txt
┌──────────────────────────────────────────────┐
│ (1) Dr Nom · titre · spécialité               │
│     hôpital · département · bio               │
├──────────────────────────────────────────────┤
│ (2) Type [Consultation 20 min ▾]              │
│ (3) [‹ Semaine précédente] semaine du … [›]   │
├──────┬──────┬──────┬──────┬──────┬─────┬─────┤
│ (4) Lun│ Mar│ Mer  │ Jeu  │ Ven  │ Sam │ Dim │
│ 9:00 │ 9:00 │  —   │ …    │      │     │     │
└──────┴──────┴──────┴──────┴──────┴─────┴─────┘
```
1. Provider public fields only.
2. Online-bookable types of the department.
3. Week navigation by `?week=`, limited to the horizon.
4. Week strip, each slot a booking link; day without slot says so in text.

Hospital page: header (name, address, phone, description), departments and specialties, providers each with next slots, and « Premier disponible » per online type. Specialty page: the provider list of phase 5's search filtered on that specialty.

## Tasks to do
### `1)` Read side
> One SQL per list, p95-friendly.

1. Criteria parsing with fallbacks; use cases; SQL adapter with `EXPLAIN` checked on the load seed in phase 7.
2. Contract test search slots == `FindFreeSlots`.

### `2)` Interfaces
> Public pages and API without session.

1. API routers; `GET /slots` public.
2. Web views, presenters, templates, geolocation script; `/` becomes the search.
3. Features in French per acceptance bullet, run on PostgreSQL.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | every acceptance bullet of the four Stories has a passing scenario, the p95 bullet excepted (phase 7) |
| 2 | anonymous `GET /`, public pages and search endpoints answer 200; no clinician email, phone or birth date in any response |
