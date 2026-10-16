"""Route policy ``s7classic-policy.yaml``.

``{content_type: {direct_route: enabled|disabled}}``. The route comparison disables a content
type whose two exports differ in meaning on a reference project; the direct extractor then sends
every project with such content to the fallback. Nothing enables a type again by itself:
that is a decision of a person after the cause is fixed.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

CONTENT_TYPES = ("blocks", "symbols", "comments", "hardware")
STATES = ("enabled", "disabled")


class PolicyError(ValueError):
    pass


def load_policy(path: Path | None) -> dict[str, str]:
    """Content type -> ``enabled`` | ``disabled``; a missing file or path means all enabled."""
    if path is None or not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise PolicyError(f"{path}: expected a mapping of content types")
    policy: dict[str, str] = {}
    for content_type, entry in data.items():
        state = entry.get("direct_route") if isinstance(entry, dict) else None
        if content_type not in CONTENT_TYPES or state not in STATES:
            raise PolicyError(
                f"{path}: {content_type!r} must be one of {', '.join(CONTENT_TYPES)} "
                f"with direct_route: {' | '.join(STATES)}"
            )
        policy[content_type] = state
    return policy


def disabled_types(path: Path | None) -> list[str]:
    return [t for t in CONTENT_TYPES if load_policy(path).get(t) == "disabled"]


def disable(path: Path, content_types: Iterable[str]) -> list[str]:
    """Mark the given types as disabled for the direct route; returns the newly disabled ones."""
    policy = load_policy(path)
    new = [t for t in CONTENT_TYPES if t in set(content_types) and policy.get(t) != "disabled"]
    if not new:
        return []
    for t in new:
        policy[t] = "disabled"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {t: {"direct_route": policy[t]} for t in CONTENT_TYPES if t in policy}
    path.write_bytes(yaml.safe_dump(doc, sort_keys=False).encode("utf-8"))
    return new
