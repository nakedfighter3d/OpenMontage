"""Deterministic cross-artifact checks for Narrative Movie Production.

Creative judgment remains in stage skills and the agent reviewer. This module only
checks referential integrity between already-authored structured artifacts so a broken
handoff fails before paid generation.
"""

from __future__ import annotations

from typing import Any

from schemas.artifacts import validate_artifact


class NarrativeContractError(ValueError):
    """Raised when narrative artifacts are individually valid but disagree."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise NarrativeContractError(message)


def validate_planning_bundle(
    scene_intent: dict[str, Any],
    continuity_bible: dict[str, Any],
    shot_plan: dict[str, Any],
    continuity_report: dict[str, Any],
    prompt_package: dict[str, Any] | None = None,
) -> None:
    """Validate the dry-run handoff chain through optional prompt compilation."""

    artifacts = {
        "scene_intent": scene_intent,
        "continuity_bible": continuity_bible,
        "shot_plan": shot_plan,
        "continuity_report": continuity_report,
    }
    if prompt_package is not None:
        artifacts["prompt_package"] = prompt_package
    for name, artifact in artifacts.items():
        validate_artifact(name, artifact)

    scene_id = scene_intent["id"]
    bible_id = continuity_bible["id"]
    shot_plan_id = shot_plan["id"]

    _require(
        continuity_bible["scene_intent_id"] == scene_id,
        "continuity_bible.scene_intent_id does not match scene_intent.id",
    )
    _require(
        shot_plan["scene_intent_id"] == scene_id,
        "shot_plan.scene_intent_id does not match scene_intent.id",
    )
    _require(
        shot_plan["continuity_bible_id"] == bible_id,
        "shot_plan.continuity_bible_id does not match continuity_bible.id",
    )
    _require(
        continuity_report["shot_plan_id"] == shot_plan_id,
        "continuity_report.shot_plan_id does not match shot_plan.id",
    )

    character_ids = {character["id"] for character in scene_intent["characters"]}
    bible_character_ids = {
        character["character_id"] for character in continuity_bible["characters"]
    }
    _require(
        bible_character_ids <= character_ids,
        "continuity_bible contains character IDs absent from scene_intent",
    )

    beat_ids = {beat["id"] for beat in scene_intent["beats"]}
    shots = sorted(shot_plan["shots"], key=lambda shot: shot["order"])
    shot_ids = [shot["id"] for shot in shots]
    _require(len(shot_ids) == len(set(shot_ids)), "shot IDs must be unique")
    _require(
        [shot["order"] for shot in shots] == list(range(1, len(shots) + 1)),
        "shot order must be contiguous and start at 1",
    )
    for shot in shots:
        _require(
            set(shot["beat_ids"]) <= beat_ids,
            f"shot {shot['id']} references an unknown dramatic beat",
        )
        _require(
            set(shot["subjects"]) <= character_ids,
            f"shot {shot['id']} references an unknown character",
        )
        for line in shot.get("dialogue", []):
            _require(
                line["speaker_id"] in character_ids,
                f"shot {shot['id']} dialogue references an unknown speaker",
            )

    expected_pairs = list(zip(shot_ids, shot_ids[1:]))
    actual_pairs = [
        (boundary["from_shot_id"], boundary["to_shot_id"])
        for boundary in shot_plan["edit_boundaries"]
    ]
    _require(
        actual_pairs == expected_pairs,
        "edit_boundaries must cover every adjacent shot pair exactly once and in order",
    )

    for finding in continuity_report["findings"]:
        _require(
            set(finding["shot_ids"]) <= set(shot_ids),
            "continuity_report references an unknown shot",
        )
    if continuity_report["approved_for_generation"]:
        _require(
            continuity_report["status"] != "revise",
            "a continuity report marked revise cannot approve generation",
        )

    if prompt_package is None:
        return
    _require(
        prompt_package["shot_plan_id"] == shot_plan_id,
        "prompt_package.shot_plan_id does not match shot_plan.id",
    )
    _require(
        prompt_package["continuity_report_id"] == continuity_report["id"],
        "prompt_package.continuity_report_id does not match continuity_report.id",
    )
    compiled_ids = [item["shot_id"] for item in prompt_package["compiled_shots"]]
    _require(
        compiled_ids == shot_ids,
        "prompt_package must contain one compiled entry per shot, in shot order",
    )


def validate_take_qa(
    shot_plan: dict[str, Any],
    take_qa_report: dict[str, Any],
) -> None:
    """Validate that selected takes refer to planned shots and are not rejected."""

    validate_artifact("shot_plan", shot_plan)
    validate_artifact("take_qa_report", take_qa_report)
    _require(
        take_qa_report["shot_plan_id"] == shot_plan["id"],
        "take_qa_report.shot_plan_id does not match shot_plan.id",
    )
    shot_ids = {shot["id"] for shot in shot_plan["shots"]}
    takes = {take["take_id"]: take for take in take_qa_report["takes"]}
    for take in takes.values():
        _require(take["shot_id"] in shot_ids, f"take {take['take_id']} has unknown shot_id")
    for take_id in take_qa_report["selected_take_ids"]:
        _require(take_id in takes, f"selected take {take_id} is absent from takes")
        _require(
            takes[take_id]["verdict"] != "reject",
            f"selected take {take_id} is marked reject",
        )
