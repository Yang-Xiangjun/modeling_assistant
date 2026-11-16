"""Write the JSON Schema of every contract into schemas/.

uv run python tools/export_schemas.py           regenerate
uv run python tools/export_schemas.py --check   fail if schemas/ is stale
"""

import argparse
import json
import sys
from pathlib import Path

from drawgen.contracts.registry import ALL

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def render() -> dict[str, str]:
    """File name -> file content for every contract."""
    out: dict[str, str] = {}
    for name in sorted(ALL):
        schema = ALL[name].model_json_schema(by_alias=True)
        out[f"{name}.schema.json"] = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    return out


def stale(schema_dir: Path = SCHEMA_DIR) -> list[str]:
    """Names of files that are missing, different or unexpected in schema_dir."""
    expected = render()
    problems = [
        name
        for name, text in expected.items()
        if not (schema_dir / name).is_file() or (schema_dir / name).read_text() != text
    ]
    problems += [p.name for p in schema_dir.glob("*.schema.json") if p.name not in expected]
    return sorted(problems)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if stale")
    args = parser.parse_args(argv)
    if args.check:
        problems = stale()
        for name in problems:
            print(f"stale: schemas/{name}", file=sys.stderr)
        return 1 if problems else 0
    SCHEMA_DIR.mkdir(exist_ok=True)
    for old in SCHEMA_DIR.glob("*.schema.json"):
        old.unlink()
    for name, text in render().items():
        (SCHEMA_DIR / name).write_text(text)
    print(f"wrote {len(render())} schemas to {SCHEMA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
