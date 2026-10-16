"""Stand-in for ``tiadump`` in tests, like 004's ``stub_s7dump.py``.

``stub_tiadump.py probe <file> --out <json>`` and
``stub_tiadump.py project|library <file> --work <dir> --out <dir>``.

TIA sources are single files, so the source copy itself names its fixture: its text is
``fixture: <name>``. ``project``/``library`` copy the recorded dump tree
``tests/fixtures/tiadump/<name>/`` (``dump.json`` plus SD, SimaticML and alarm files) into
``--out``. ``exit:<n>`` instead of a name exits with code n (2 cannot open, 3 upgrade refused,
4 access denied, 5 locked).

``TIADUMP_STUB_INSTALLED`` (JSON ``[{"version": "V21 Upd1", "products":
["STEP 7 Safety"]}, …]``) makes the stub one or more TIA installations. ``--tia V20`` picks one,
else the newest. ``stub_tiadump.py installed --tia V21 --out <json>`` reports it. ``project``
then behaves as that installation: a second source line ``uses: A; B`` names products the
project needs, missing ones end in TIA's missing-products refusal (exit 2); ``partial: C`` names
products TIA opens it without, listed in ``missing_packages`` when not installed; the dump gets the
installation's version, the saved version from the file suffix, an upgrade when the source is
older, and ``used_products``. Without the variable the stub behaves as before.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
SUFFIX = re.compile(r"\.(z?ap|z?al|als)(\d\d)$", re.IGNORECASE)


def _lines(source: Path) -> list[str]:
    return source.read_text(encoding="utf-8", errors="replace").strip().splitlines() or [""]


def _fixture(source: Path) -> str:
    text = _lines(source)[0].strip()
    return text.split(":", 1)[1].strip() if text.startswith("fixture:") else text


def _listed(source: Path, key: str) -> list[str]:
    for line in _lines(source)[1:]:
        if line.startswith(f"{key}:"):
            return [x.strip() for x in line.split(":", 1)[1].split(";") if x.strip()]
    return []


def _uses(source: Path) -> list[str]:
    """Products without which TIA refuses to open the project."""
    return _listed(source, "uses")


def _partial(source: Path) -> list[str]:
    """Products TIA opens the project without, leaving their parts out (missing_packages)."""
    return _listed(source, "partial")


def _installation(argv: list[str]) -> dict[str, Any] | None:
    """The emulated TIA installation: by ``--tia`` major, else the newest."""
    raw = os.environ.get("TIADUMP_STUB_INSTALLED")
    if not raw:
        return None
    installs: list[dict[str, Any]] = json.loads(raw)
    major = lambda i: int(re.match(r"V?(\d+)", str(i["version"])).group(1))  # noqa: E731
    if "--tia" in argv:
        want = int(argv[argv.index("--tia") + 1].lstrip("Vv").split()[0])
        chosen = [i for i in installs if major(i) == want]
        return chosen[0] if chosen else {"version": f"V{want}", "products": [], "absent": True}
    return max(installs, key=major)


def _bare(name: str) -> str:
    return re.sub(r"\s+V\d+.*$", "", name).strip().casefold()


def _patch(dump: dict[str, Any], install: dict[str, Any], source: Path, uses: list[str]) -> None:
    """The dump as this installation would write it for this source."""
    major, _, update = str(install["version"]).partition(" ")
    saved = f"V{SUFFIX.search(source.name).group(2)}"  # type: ignore[union-attr]
    up = dump["tia"].get("upgrade")
    dump["tia"]["version"] = major
    dump["tia"]["update"] = update or None
    dump["tia"]["upgrade"] = (
        {"from": saved, "to": major, "messages": list((up or {}).get("messages") or [])[:2]}
        if int(saved[1:]) < int(major[1:]) else None
    )  # fmt: skip
    dump.setdefault("source", {})["saved_version"] = saved
    have = {_bare(p) for p in install.get("products") or []}
    left_out = [x for x in _partial(source) if _bare(x) not in have]
    dump["missing_packages"] = [{"name": f"{x} {major}", "objects": []} for x in left_out]
    uses = uses + _partial(source)  # UsedProducts lists them all, installed or not
    dump["used_products"] = sorted(
        [{"name": "STEP 7 Professional", "version": major}]
        + [{"name": u, "version": major} for u in uses],
        key=lambda r: r["name"],
    )


def main(argv: list[str]) -> int:
    if argv[:1] == ["--version"]:
        print("tiadump 0.0.0-stub")
        return 0
    if argv[:1] == ["installed"]:  # the emulated installation's software
        install = _installation(argv)
        if install is None or install.get("absent"):
            print("tiadump: TIA Portal Openness not found", file=sys.stderr)
            return 4
        major, _, update = str(install["version"]).partition(" ")
        rows = [{"name": "STEP 7 Professional", "version": major}] + [
            {"name": n, "version": major} for n in install.get("products") or []
        ]
        Path(argv[argv.index("--out") + 1]).write_text(
            json.dumps(
                {
                    "tool": {"name": "tiadump", "version": "0.0.0-stub", "openness": major},
                    "tia": {"version": major, "update": update or None},
                    "installed": sorted(rows, key=lambda r: r["name"]),
                }
            ),
            encoding="utf-8",
        )
        return 0
    command, source = argv[0], Path(argv[1])
    out = Path(argv[argv.index("--out") + 1])
    match = SUFFIX.search(source.name)
    if not match:
        print(f"tiadump: not a TIA project or library: {source}", file=sys.stderr)
        return 64
    if command == "probe":
        tag = match.group(1).lower()
        kind = "local_session" if tag == "als" else "library" if tag.endswith("al") else "project"
        out.write_text(
            json.dumps(
                {
                    "archive": tag.startswith("z"),
                    "kind": kind,
                    "saved_update": None,
                    "saved_version": f"V{match.group(2)}",
                }
            ),
            encoding="utf-8",
        )
        return 0
    # like the real tiadump: it only opens a copy inside its --work folder
    work = Path(argv[argv.index("--work") + 1]).resolve()
    if work not in source.resolve().parents:
        print("tiadump: the file must be a copy inside --work", file=sys.stderr)
        return 64
    name = _fixture(source)
    if name.startswith("missing:"):  # a TIA product the host lacks (exit 2, TIA's wording)
        print(
            "tiadump: missing software: Error when calling method 'Retrieve'. The project "
            f"cannot be opened without these products: {name.split(':', 1)[1].strip()}",
            file=sys.stderr,
        )
        return 2
    if name.startswith("exit:"):
        code = int(name.split(":", 1)[1])
        print(f"tiadump: simulated exit {code}", file=sys.stderr)
        return code
    tree = HERE / name
    if not (tree / "dump.json").is_file():
        print(f"tiadump: no recorded dump {name}", file=sys.stderr)
        return 2
    install = _installation(argv)
    uses = _uses(source)
    if install is not None and install.get("absent"):
        print("tiadump: TIA Portal Openness not found", file=sys.stderr)
        return 4
    if install is not None:
        have = {_bare(p) for p in install.get("products") or []}
        missing = [u for u in uses if _bare(u) not in have]
        if missing:
            major = str(install["version"]).split()[0]
            print(
                "tiadump: missing software: Error when calling method 'Open'. The project "
                "cannot be opened without these products: "
                + ", ".join(f"{m} {major}" for m in missing),
                file=sys.stderr,
            )
            return 2
    shutil.copytree(tree, out, dirs_exist_ok=True)
    if install is not None:
        dump_file = out / "dump.json"
        dump = json.loads(dump_file.read_text(encoding="utf-8"))
        _patch(dump, install, source, uses)
        dump_file.write_text(json.dumps(dump, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
