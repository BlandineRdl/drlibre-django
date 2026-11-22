"""Saves every kind of answer /fhir gives on the demo seed, for the HL7 validator."""

import json
import sys
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode, urlsplit

READERS = {
    "anonymous": None,
    "patient": "demo-patient-token",
    "clinician": "demo-clinician-token",
    "admin": "demo-admin-token",
}


def fetch(base: str, path: str, token: str | None) -> tuple[int, dict]:
    headers = {"Accept": "application/fhir+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Plain HTTP to the local stack only, never another scheme.
    connection = HTTPConnection(urlsplit(base).netloc, timeout=30)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, json.load(response)
    finally:
        connection.close()


def slot_query(base: str) -> str:
    _, services = fetch(base, "/fhir/HealthcareService?_count=1", None)
    start = datetime.now(UTC).replace(microsecond=0)
    return urlencode(
        [
            ("service-type", services["entry"][0]["resource"]["id"]),
            ("start", f"ge{start.isoformat()}"),
            ("start", f"lt{(start + timedelta(days=7)).isoformat()}"),
        ]
    )


def main(base: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    saved: dict[str, dict] = {}
    _, capability = fetch(base, "/fhir/metadata", None)
    saved["metadata"] = capability
    types = [r["type"] for r in capability["rest"][0]["resource"]]
    for reader, token in READERS.items():
        for kind in types:
            query = slot_query(base) if kind == "Slot" else "_count=100"
            status, bundle = fetch(base, f"/fhir/{kind}?{query}", token)
            saved[f"{reader}-{kind}-search-{status}"] = bundle
            for entry in bundle.get("entry", [])[:1]:
                _, resource = fetch(base, f"/fhir/{kind}/{entry['resource']['id']}", token)
                saved[f"{reader}-{kind}-read"] = resource
    saved["not-found"] = fetch(base, "/fhir/Patient/unknown", READERS["admin"])[1]
    saved["refused-parameter"] = fetch(base, "/fhir/Patient?nope=1", READERS["admin"])[1]
    for name, body in saved.items():
        (out / f"{name}.json").write_text(json.dumps(body, indent=2))
    print(f"{len(saved)} samples in {out}")


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/"), Path(sys.argv[2]))
