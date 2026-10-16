"""README template of every export (contract §9).

``README.md`` is the generic part. A platform adds ``platforms/<platform id>.md``; that section
is versioned together with its extractor.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent


def render_readme(platform_id: str | None) -> str:
    template = (HERE / "README.md").read_text(encoding="utf-8")
    section = ""
    if platform_id:
        p = HERE / "platforms" / f"{platform_id}.md"
        if p.is_file():
            section = "\n" + p.read_text(encoding="utf-8").rstrip("\n") + "\n"
    return template.replace("{platform_section}\n", section).rstrip("\n") + "\n"
