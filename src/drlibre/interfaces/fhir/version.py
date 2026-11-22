import hashlib
import re
from datetime import datetime

from drlibre.interfaces.fhir.schemas.common import Meta

_IF_MATCH = re.compile(r'\s*(?:W/)?"([^"]+)"\s*')


def version_id(*parts: object) -> str:
    """A short fingerprint of a resource's versioned state; any change gives another one."""
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12]


def meta(version: str, last_updated: datetime) -> Meta:
    return Meta(version_id=version, last_updated=last_updated)


def etag(version: str) -> str:
    return f'W/"{version}"'


def expected_version(if_match: str | None) -> str | None:
    """The version an If-Match header names, weak or strong, or None without the header."""
    if not if_match:
        return None
    found = _IF_MATCH.fullmatch(if_match)
    return found[1] if found else if_match.strip()
