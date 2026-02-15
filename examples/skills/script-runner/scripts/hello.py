#!/usr/bin/env python3
"""Simple script skill entry under scripts/."""

import sys


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"[script-runner] Hello, {name}!")


if __name__ == "__main__":
    main()
