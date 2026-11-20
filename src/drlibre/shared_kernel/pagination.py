from dataclasses import dataclass

PAGE_SIZE = 20


@dataclass(frozen=True, slots=True)
class PageRequest:
    number: int = 1
    search: str = ""

    @classmethod
    def from_query(cls, *, page: str | None, search: str | None) -> "PageRequest":
        number = int(page) if page and page.isdigit() and int(page) >= 1 else 1
        return cls(number=number, search=(search or "").strip()[:100])

    @property
    def offset(self) -> int:
        return (self.number - 1) * PAGE_SIZE


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: tuple[T, ...]
    total: int
    number: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // PAGE_SIZE))

    @property
    def has_previous(self) -> bool:
        return self.number > 1

    @property
    def has_next(self) -> bool:
        return self.number < self.pages
