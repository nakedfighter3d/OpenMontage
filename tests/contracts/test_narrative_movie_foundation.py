"""Contract tests for the Narrative Movie Production foundation."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from lib.narrative_contracts import NarrativeContractError, validate_planning_bundle
from lib.pipeline_loader import get_stage_order, load_pipeline


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


def test_dialogue_scene_dry_run_bundle_is_valid():
    validate_planning_bundle(
        _load("scene_intent"),
        _load("continuity_bible"),
        _load("shot_plan"),
        _load("continuity_report"),
        _load("prompt_package"),
    )


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

