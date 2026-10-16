"""Stand-in for ``s7dump`` in tests: ``stub_s7dump.py <project> --out <file> …``.

The project folder names its fixture in ``s7dump.fixture`` (e.g. ``press_s7300``); the stub
copies ``tests/fixtures/s7dump/<name>.json`` to ``--out``. ``exit:<n>`` in that file makes it
exit with code n (2 = project cannot be opened).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main(argv: list[str]) -> int:
    project = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1])
    marker = project / "s7dump.fixture"
    if not marker.is_file():
        print(f"cannot open project: no fixture in {project}", file=sys.stderr)
        return 2
    name = marker.read_text(encoding="utf-8").strip()
    if name.startswith("exit:"):
        print("cannot open project: simulated", file=sys.stderr)
        return int(name.split(":", 1)[1])
    shutil.copyfile(HERE / f"{name}.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
