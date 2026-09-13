"""Contract tests for the Narrative Movie Production foundation."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from lib.narrative_contracts import NarrativeContractError, validate_planning_bundle
from lib.pipeline_loader import get_stage_order, load_pipeline
from scripts import install_screenwriting_skills as screenwriting_installer


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "narrative-dialogue-dry-run"


def _load(name: str) -> dict:
    return json.loads((EXAMPLE / f"{name}.json").read_text(encoding="utf-8"))


def test_narrative_pipeline_stage_separation():
    manifest = load_pipeline("narrative-movie")
    stages = get_stage_order(manifest)
    assert stages == [
        "proposal",
        "dramaturgy",
        "scene_design",
        "coverage",
        "continuity",
        "prompt_compile",
        "assets",
        "take_qa",
        "edit",
        "compose",
        "publish",
    ]
    assert stages.index("continuity") < stages.index("assets")
    assert stages.index("prompt_compile") < stages.index("assets")
    assert stages.index("take_qa") < stages.index("edit")
    assets = next(stage for stage in manifest["stages"] if stage["name"] == "assets")
    assert assets["required_tools"] == ["comfyui_video"]
    assert "video_selector" not in assets["tools_available"]


def test_dialogue_scene_dry_run_bundle_is_valid():
    validate_planning_bundle(
        _load("scene_intent"),
        _load("continuity_bible"),
        _load("shot_plan"),
        _load("continuity_report"),
        _load("prompt_package"),
    )


def test_screenwriting_dependency_is_pinned_and_selective():
    profile = yaml.safe_load(
        (ROOT / "skills/pipelines/narrative-movie/external-skills.yaml").read_text(
            encoding="utf-8"
        )
    )
    dependency = next(item for item in profile["dependencies"] if item["role"] == "dramaturgy")
    assert dependency["status"] == "available-pinned-local-install"
    assert dependency["revision"] == screenwriting_installer.REVISION
    assert dependency["workflow_mode"] == "subordinate"
    assert dependency["license_notice"] == screenwriting_installer.LICENSE_NOTICE
    assert dependency["selected_skills"] == list(screenwriting_installer.SELECTED_SKILLS)


def test_dramaturgy_director_enforces_dependency_boundary():
    body = (
        ROOT / "skills/pipelines/narrative-movie/dramaturgy-director.md"
    ).read_text(encoding="utf-8")
    assert "install_screenwriting_skills.py --check" in body
    assert "subordinate" in body
    assert "Never install" in body
    assert "silent fallback" in body


def test_selective_installer_locks_and_detects_tampering(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "tools").mkdir(parents=True)
    (source / "LICENSE").write_text(
        f"{screenwriting_installer.LICENSE_NOTICE}\n", encoding="utf-8"
    )
    (source / "tools/validate_skills.py").write_text(
        "print('fixture valid')\n", encoding="utf-8"
    )
    for skill in screenwriting_installer.SELECTED_SKILLS:
        folder = source / "skills" / skill
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: fixture\n---\n\n# {skill}\n",
            encoding="utf-8",
        )
        (folder / "reference.md").write_text("fixture\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "OpenMontage Tests",
        "GIT_AUTHOR_EMAIL": "tests@openmontage.invalid",
        "GIT_COMMITTER_NAME": "OpenMontage Tests",
        "GIT_COMMITTER_EMAIL": "tests@openmontage.invalid",
    }
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=source, check=True, env=environment)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    destination = tmp_path / ".agents" / "skills"
    lock_file = tmp_path / "skills-lock.json"
    monkeypatch.setattr(screenwriting_installer, "REVISION", revision)
    screenwriting_installer.install(source, destination, lock_file, revision, force=False)
    screenwriting_installer.check(destination, lock_file)

    installed_names = sorted(path.name for path in destination.iterdir())
    assert installed_names == sorted(screenwriting_installer.SELECTED_SKILLS)
    (destination / "sw-dialogue" / "reference.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(screenwriting_installer.IntegrationError, match="content differs"):
        screenwriting_installer.check(destination, lock_file)


def test_missing_edit_boundary_fails_before_generation():
    shot_plan = _load("shot_plan")
    shot_plan["edit_boundaries"] = shot_plan["edit_boundaries"][:-1]
    with pytest.raises(NarrativeContractError, match="every adjacent shot pair"):
        validate_planning_bundle(
            _load("scene_intent"),
            _load("continuity_bible"),
            shot_plan,
            _load("continuity_report"),
        )


def test_prompt_package_cannot_silently_drop_a_shot():
    prompt_package = copy.deepcopy(_load("prompt_package"))
    prompt_package["compiled_shots"].pop()
    with pytest.raises(NarrativeContractError, match="one compiled entry per shot"):
        validate_planning_bundle(
            _load("scene_intent"),
            _load("continuity_bible"),
            _load("shot_plan"),
            _load("continuity_report"),
            prompt_package,
        )
