import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "aidd_docs" / "backlog" / "stories"
FEATURES = Path(__file__).resolve().parent / "features"
QUALIFIER = re.compile(r"\s*\([^()]*\)$")


def forms(name: str) -> set[str]:
    """The name, then without each trailing qualifier, as a bullet may end with its own."""
    name = " ".join(name.split()).removesuffix(".").rstrip()
    found = {name}
    while (bare := QUALIFIER.sub("", name).removesuffix(".").rstrip()) != name:
        found.add(name := bare)
    return found


def acceptance(story: Path) -> tuple[str, list[str]]:
    title, bullets, inside = "", [], False
    for line in story.read_text().splitlines():
        if line.startswith("# Story:"):
            title = line.removeprefix("# Story:").strip()
        elif line.startswith("## "):
            inside = line.strip() == "## Acceptance"
        elif inside and line.startswith("- "):
            bullets.append(line[2:])
        elif inside and line.startswith("  ") and bullets:
            bullets[-1] += " " + line.strip()
    return title, bullets


def scenario_names() -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    for feature in FEATURES.rglob("*.feature"):
        text = feature.read_text()
        title = re.search(r"^\s*Feature:\s*(.+)$", text, re.M)
        if title:
            found = re.findall(r"^\s*Scenario(?: Outline)?:\s*(.+)$", text, re.M)
            names.setdefault(title[1].strip(), set()).update(*map(forms, found))
    return names


LOAD_RUN = ("scripts/load-run.sh", "loadtests/locustfile.py")

# Bullets no Gherkin scenario can prove, mapped to the tests that do.
PROVEN_ELSEWHERE: dict[tuple[str, str], tuple[str, ...]] = {
    (
        "chaque-resultat-montre-ses-prochaines-disponibilites",
        "Sur la seed de charge (option « taille » du script de seed : 10 hôpitaux, 200 praticiens,"
        " 5k patients, 50k RDV), la recherche répond sous 200 ms au p95 du scénario Locust.",
    ): LOAD_RUN,
    (
        "un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email",
        "Sur la seed de charge, la réservation répond sous 200 ms au p95 du scénario Locust.",
    ): LOAD_RUN,
    (
        "un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email",
        "Les emails partent une fois la réservation enregistrée, avec nouvelles tentatives ;"
        " un échec d'envoi n'annule ni la réservation provisoire ni le RDV, et le visiteur peut"
        " redemander un code.",
    ): ("tests/integration/test_email_delivery_failure.py",),
    (
        "un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email",
        "Un créneau d'un résultat ou d'une page publique ouvre la réservation en un clic ;"
        " le parcours enchaîne type de RDV, praticien puis créneau.",
    ): (
        "tests/e2e/test_visitor_books_without_account.py",
        "tests/presenters/test_search_presenters.py",
    ),
    (
        "un-visiteur-reserve-le-premier-praticien-disponible",
        "Au choix du praticien, le parcours propose « premier disponible » dans le département"
        " du type ; la page hôpital le propose pour chaque type de RDV.",
    ): (
        "tests/e2e/test_visitor_books_without_account.py",
        "tests/presenters/test_search_presenters.py",
        "tests/presenters/test_booking_presenters.py",
    ),
}

SCENARIOS = scenario_names()
DELIVERED = [s for s in sorted(STORIES.glob("*.md")) if acceptance(s)[0] in SCENARIOS]


@pytest.mark.parametrize("story", DELIVERED, ids=[s.stem for s in DELIVERED])
def test_every_acceptance_bullet_names_a_scenario(story: Path) -> None:
    """Rule 5-acceptance-test-names: every Acceptance bullet appears in a scenario name."""
    title, bullets = acceptance(story)
    elsewhere = {b for slug, b in PROVEN_ELSEWHERE if slug == story.stem}
    missing = [b for b in bullets if b not in elsewhere and not forms(b) & SCENARIOS[title]]
    assert not missing, f"{title}: bullets without a scenario:\n- " + "\n- ".join(missing)


@pytest.mark.parametrize(
    ("slug", "bullet"), list(PROVEN_ELSEWHERE), ids=[s for s, _ in PROVEN_ELSEWHERE]
)
def test_every_bullet_proven_elsewhere_still_exists_with_its_proof(slug: str, bullet: str) -> None:
    """Rule 5-acceptance-test-names: an excepted bullet stays in its Story and its proof exists."""
    assert bullet in acceptance(STORIES / f"{slug}.md")[1]
    for path in PROVEN_ELSEWHERE[slug, bullet]:
        assert (ROOT / path).is_file(), path
