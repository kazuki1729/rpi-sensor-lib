"""Validate that a Git tag matches the package's single version source."""

import argparse
import re
from pathlib import Path


def package_version() -> str:
    source = Path(__file__).parents[1] / "rpi_sensors" / "_version.py"
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        source.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if match is None:
        raise RuntimeError("could not read __version__")
    return match.group(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="release tag, for example v0.2.0")
    args = parser.parse_args()
    expected_tag = f"v{package_version()}"
    if args.tag != expected_tag:
        raise SystemExit(f"release tag {args.tag!r} does not match {expected_tag!r}")
    print(f"release tag matches package version: {expected_tag}")


if __name__ == "__main__":
    main()
