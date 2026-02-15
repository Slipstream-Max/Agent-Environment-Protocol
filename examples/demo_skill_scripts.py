"""
Demo: add a skill that contains Python files under scripts/ and run it.

Run:
    uv run python examples/demo_skill_scripts.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from aep import AEP, EnvManager


def run_and_print(session, command: str) -> None:
    print(f"\n>>> {command}")
    result = session.exec(command)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print("[stderr]")
        print(result.stderr.strip())


def main() -> None:
    skill_source = Path(__file__).resolve().parent / "skills" / "script-runner"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_dir = root / "config"
        workspace = root / "workspace"
        workspace.mkdir()

        config = EnvManager(config_dir)
        config.add_skill(skill_source)
        config.index()

        aep = AEP.attach(workspace=workspace, config=config)
        session = aep.create_session()

        run_and_print(session, "skills list")
        run_and_print(session, "skills info script-runner")
        run_and_print(session, "skills run script-runner/scripts/hello.py AEP")


if __name__ == "__main__":
    main()
