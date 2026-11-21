import hashlib
import hmac
import secrets

from drlibre.booking.application.ports.outbound import CodeIssuer, IssuedCode


class HmacCodeIssuer(CodeIssuer):
    """Six digits from `secrets`, kept as a keyed HMAC-SHA256 (a bare hash is reversible)."""

    def __init__(self, *, key: str) -> None:
        self._key = key.encode()

    def issue(self) -> IssuedCode:
        code = f"{secrets.randbelow(10**6):06d}"
        return IssuedCode(code, self._hash(code))

    def matches(self, code: str, code_hash: str) -> bool:
        return hmac.compare_digest(self._hash(code), code_hash)

    def _hash(self, code: str) -> str:
        return hmac.new(self._key, code.encode(), hashlib.sha256).hexdigest()
