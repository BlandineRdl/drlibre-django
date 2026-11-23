from html.parser import HTMLParser


class _Finder(HTMLParser):
    def __init__(self, element_id: str) -> None:
        super().__init__()
        self.element_id = element_id
        self.found: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if self.found is None and values.get("id") == self.element_id:
            self.found = values


def attributes(html: str, element_id: str) -> dict[str, str]:
    """Attributes of the element with this id, in any order; a bare attribute maps to ''."""
    finder = _Finder(element_id)
    finder.feed(html)
    assert finder.found is not None, f"no element with id {element_id!r}"
    return finder.found


def described_by(html: str, element_id: str) -> list[str]:
    return attributes(html, element_id).get("aria-describedby", "").split()
