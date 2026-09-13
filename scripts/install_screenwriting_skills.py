#!/usr/bin/env python3
"""Install the pinned narrative dramaturgy skill subset for local use.

The upstream-derived package is intentionally not vendored into OpenMontage. This
installer copies only the approved skills into the local Agent Skills directory and
records exact content digests in the gitignored skills lock file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPOSITORY = "https://github.com/nakedfighter3d/screenwriting-skills-en-optimized"
REVISION = "0c641f19a9d4e97d4438ff763d89c35772a2dce6"
DEPENDENCY_ID = "screenwriting-skills-en-optimized"
LICENSE_NOTICE = "For personal study use."
SELECTED_SKILLS = (
    "sw-workflow",
    "sw-premise-theme",
    "sw-story-structure",
    "sw-character-conflict",
    "sw-scene-craft",
    "sw-dialogue",
)
ROOT = Path(__file__).resolve().parents[1]


class IntegrationError(RuntimeError):
    """Raised when a dependency install or integrity check is unsafe."""


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise IntegrationError(f"Command failed: {' '.join(command)}\n{detail}")
    return completed.stdout.strip()


def _directory_digest(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = item.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _skill_name(skill_file: Path) -> str | None:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def _validate_source(source: Path, revision: str) -> None:
    if not (source / ".git").exists():
        raise IntegrationError("--source must be a Git checkout so its revision can be verified")
    head = _run(["git", "rev-parse", "HEAD"], cwd=source)
    expected = _run(["git", "rev-parse", revision], cwd=source)
    if head != expected:
        raise IntegrationError(f"Source checkout is {head}; expected pinned revision {expected}")

    validator = source / "tools" / "validate_skills.py"
    if not validator.is_file():
        raise IntegrationError("Source repository does not contain tools/validate_skills.py")
    _run([sys.executable, str(validator)], cwd=source)

    license_file = source / "LICENSE"
    if not license_file.is_file() or LICENSE_NOTICE not in license_file.read_text(
        encoding="utf-8"
    ):
        raise IntegrationError("Pinned study-use license notice is missing or changed")

    for skill in SELECTED_SKILLS:
        skill_file = source / "skills" / skill / "SKILL.md"
        if not skill_file.is_file():
            raise IntegrationError(f"Selected skill is missing: {skill}")
        if _skill_name(skill_file) != skill:
            raise IntegrationError(f"Skill frontmatter name does not match directory: {skill}")


def _read_lock(lock_file: Path) -> dict[str, Any]:
    if not lock_file.exists():
        return {"version": 1, "external_skills": {}}
    try:
        data = json.loads(lock_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise IntegrationError(f"Cannot read {lock_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise IntegrationError(f"{lock_file} must contain a JSON object")
    data.setdefault("version", 1)
    data.setdefault("external_skills", {})
    if not isinstance(data["external_skills"], dict):
        raise IntegrationError(f"{lock_file} external_skills must be an object")
    return data


def _write_lock(lock_file: Path, data: dict[str, Any]) -> None:
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{lock_file.name}.", dir=lock_file.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary_name, lock_file)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def install(source: Path, destination: Path, lock_file: Path, revision: str, force: bool) -> None:
    _validate_source(source, revision)
    existing = [destination / skill for skill in SELECTED_SKILLS if (destination / skill).exists()]
    if existing and not force:
        names = ", ".join(path.name for path in existing)
        raise IntegrationError(
            f"Already installed: {names}. Use --force to replace this exact subset."
        )

    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="openmontage-screenwriting-") as staging_name:
        staging = Path(staging_name)
        for skill in SELECTED_SKILLS:
            shutil.copytree(source / "skills" / skill, staging / skill)
        for skill in SELECTED_SKILLS:
            target = destination / skill
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(staging / skill, target)

    digests = {skill: _directory_digest(destination / skill) for skill in SELECTED_SKILLS}
    lock = _read_lock(lock_file)
    lock["external_skills"][DEPENDENCY_ID] = {
        "source": REPOSITORY,
        "revision": revision,
        "license_notice": LICENSE_NOTICE,
        "selected_skills": list(SELECTED_SKILLS),
        "sha256": digests,
    }
    _write_lock(lock_file, lock)


def check(destination: Path, lock_file: Path) -> None:
    lock = _read_lock(lock_file)
    record = lock["external_skills"].get(DEPENDENCY_ID)
    if not isinstance(record, dict):
        raise IntegrationError(f"{DEPENDENCY_ID} is not recorded in {lock_file}")
    if record.get("source") != REPOSITORY or record.get("revision") != REVISION:
        raise IntegrationError(
            "Installed dependency does not match the approved source and revision"
        )
    if record.get("license_notice") != LICENSE_NOTICE:
        raise IntegrationError("Installed dependency is missing the approved license notice")
    if record.get("selected_skills") != list(SELECTED_SKILLS):
        raise IntegrationError("Installed skill selection does not match the narrative profile")
    expected_digests = record.get("sha256")
    if not isinstance(expected_digests, dict):
        raise IntegrationError("Installed dependency has no content digests")
    for skill in SELECTED_SKILLS:
        target = destination / skill
        if not (target / "SKILL.md").is_file():
            raise IntegrationError(f"Installed skill is missing: {skill}")
        if _skill_name(target / "SKILL.md") != skill:
            raise IntegrationError(f"Installed skill has invalid frontmatter: {skill}")
        if _directory_digest(target) != expected_digests.get(skill):
            raise IntegrationError(f"Installed skill content differs from its lock: {skill}")


def _clone_pinned(revision: str, parent: Path) -> Path:
    checkout = parent / DEPENDENCY_ID
    _run(["git", "clone", "--filter=blob:none", "--no-checkout", REPOSITORY, str(checkout)])
    _run(["git", "checkout", "--detach", revision], cwd=checkout)
    return checkout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Existing checkout at the pinned revision")
    parser.add_argument("--destination", type=Path, default=ROOT / ".agents" / "skills")
    parser.add_argument("--lock-file", type=Path, default=ROOT / "skills-lock.json")
    parser.add_argument(
        "--force", action="store_true", help="Replace only the selected skill folders"
    )
    parser.add_argument(
        "--check", action="store_true", help="Verify the local install without network access"
    )
    parser.add_argument(
        "--acknowledge-study-use",
        action="store_true",
        help=f"Acknowledge the upstream-derived '{LICENSE_NOTICE}' notice",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.check:
            check(args.destination, args.lock_file)
            print(f"Verified {len(SELECTED_SKILLS)} pinned screenwriting skills")
            return 0
        if not args.acknowledge_study_use:
            raise IntegrationError("Installation requires --acknowledge-study-use")
        if args.source:
            install(
                args.source.resolve(),
                args.destination,
                args.lock_file,
                REVISION,
                args.force,
            )
        else:
            with tempfile.TemporaryDirectory(
                prefix="openmontage-screenwriting-source-"
            ) as temp_name:
                source = _clone_pinned(REVISION, Path(temp_name))
                install(source, args.destination, args.lock_file, REVISION, args.force)
        check(args.destination, args.lock_file)
        print(f"Installed and verified {len(SELECTED_SKILLS)} pinned screenwriting skills")
        return 0
    except IntegrationError as exc:
        print(f"screenwriting skill integration error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
