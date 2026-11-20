import json
import urllib.parse
import urllib.request
from typing import Any


def find_messages(api_url: str, subject: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"query": f'subject:"{subject}"'})
    with urllib.request.urlopen(f"{api_url}/search?{query}", timeout=5) as response:  # noqa: S310
        return json.load(response)["messages"]
