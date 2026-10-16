"""Copy a recorded ``tiadump`` output tree into the fixtures, with personal names replaced
.

``python tests/fixtures/tiadump/anonymize.py <dump dir> <fixture name> --person "Jane Doe" …``

Every text file (dump.json, .s7dcl, .s7res, SimaticML/HMI XML) is rewritten byte-for-byte
except the replaced names: BOM and CRLF stay as TIA wrote them, so the fixtures test the real
encoding. E-mail addresses become ``author@example.invalid``. Each ``--person`` becomes
``Author A``, ``Author B``, … in the given order. Binary
files (xlsx) are checked for the names and refused if they contain one.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
TEXT = {".json", ".s7dcl", ".s7res", ".xml", ".md", ".txt"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def anonymize(src: Path, name: str, persons: list[str]) -> list[str]:
    dst = HERE / name
    if dst.exists():
        shutil.rmtree(dst)
    replacements = [(p, f"Author {chr(ord('A') + i)}") for i, p in enumerate(persons)]
    problems: list[str] = []
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        target = dst / f.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = f.read_bytes()
        if f.suffix.lower() in TEXT:
            text = data.decode("utf-8")  # keeps a BOM as U+FEFF and CRLF as is
            for old, new in replacements:
                text = text.replace(old, new)
            text = EMAIL.sub("author@example.invalid", text)
            data = text.encode("utf-8")
        else:
            for old, _ in replacements:
                if old.encode("utf-8") in data:
                    problems.append(
                        f"{f.relative_to(src)} contains {old!r} (binary, not rewritten)"
                    )
        target.write_bytes(data)
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("name")
    ap.add_argument("--person", action="append", default=[])
    args = ap.parse_args(argv)
    problems = anonymize(args.src, args.name, args.person)
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
