"""Tests for model-aware prompts over model-opaque ComfyUI workflows."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from lib.narrative_contracts import validate_planning_bundle
from lib.narrative_prompt_compilers import (
    PromptCompilationError,
    comfyui_inputs_for_compiled_shot,
    compile_prompt_package,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "narrative-dialogue-dry-run"


def _load(name: str) -> dict:
    return json.loads((EXAMPLE / f"{name}.json").read_text(encoding="utf-8"))


def _compile(dialect: str, contract: str, **kwargs) -> dict:
    return compile_prompt_package(
        _load("shot_plan"),
        _load("continuity_report"),
        prompt_dialect=dialect,
        workflow_contract=_load(contract),
        continuity_bible=_load("continuity_bible"),
        **kwargs,
    )


def test_h3_compiles_only_to_declared_comfyui_workflow_inputs():
    package = _compile("minimax-h3", "workflow_contract.minimax-h3")
    assert [shot["shot_id"] for shot in package["compiled_shots"]] == [
        "SH001", "SH002", "SH003", "SH004"
    ]
    first = package["compiled_shots"][0]
    assert first["provider"] == "comfyui"
    assert first["model"] == "workflow:local-h3-t2v"
    assert first["parameters"]["tool"] == "comfyui_video"
    assert first["parameters"]["operation"] == "custom_workflow"
    assert set(first["parameters"]["workflow_inputs"]) == {
        "prompt", "duration_seconds", "aspect_ratio", "generate_audio"
    }
    assert "<d>[English] It leaves at eleven.</d>" in first["prompt"]
    serialized = json.dumps(package).lower()
    assert "https://" not in serialized
    assert "/api/v1/video" not in serialized
    validate_planning_bundle(
        _load("scene_intent"), _load("continuity_bible"), _load("shot_plan"),
        _load("continuity_report"), package
    )


def test_compiled_shot_converts_to_comfyui_tool_inputs():
    compiled = _compile("wan3", "workflow_contract.wan3")["compiled_shots"][0]
    inputs = comfyui_inputs_for_compiled_shot(compiled, output_path="take-SH001.mp4")
    assert "tool" not in inputs
    assert inputs["prompt"] == compiled["prompt"]
    assert inputs["workflow_path"] == "local/workflows/wan3-t2v-api.json"
    assert inputs["output_node"] == "99"
    assert inputs["output_path"] == "take-SH001.mp4"


def test_wan3_uses_same_opaque_transport_with_different_prompt_dialect():
    package = _compile("wan3", "workflow_contract.wan3")
    first = package["compiled_shots"][0]
    assert first["provider"] == "comfyui"
    assert first["model"] == "workflow:local-wan3-t2v"
    assert first["negative_prompt"]
    assert first["parameters"]["workflow_inputs"]["negative_prompt"] == first["negative_prompt"]
    assert "venice" not in json.dumps(package).lower()
    assert "wan-3-0" not in json.dumps(package).lower()


def test_duration_is_adapted_only_from_workflow_declared_values():
    package = _compile("wan3", "workflow_contract.wan3")
    durations = [
        shot["parameters"]["workflow_inputs"]["duration_seconds"]
        for shot in package["compiled_shots"]
    ]
    assert durations == [10, 5, 5, 5]
    assert "workflow input uses 10s" in package["compiled_shots"][0]["compile_notes"][0]


def test_workflow_without_duration_preserves_edit_duration_as_note():
    contract = _load("workflow_contract.minimax-h3")
    contract["inputs"].pop("duration_seconds")
    package = compile_prompt_package(
        _load("shot_plan"), _load("continuity_report"),
        prompt_dialect="minimax-h3", workflow_contract=contract
    )
    assert "does not expose duration" in package["compiled_shots"][0]["compile_notes"][0]


def test_image_workflow_requires_reference_binding():
    contract = _load("workflow_contract.wan3")
    contract["mode"] = "image_to_video"
    with pytest.raises(PromptCompilationError, match="requires an image"):
        compile_prompt_package(
            _load("shot_plan"), _load("continuity_report"),
            prompt_dialect="wan3", workflow_contract=contract
        )


def test_image_workflow_accepts_contract_named_local_input_without_model_knowledge():
    contract = _load("workflow_contract.wan3")
    contract["mode"] = "image_to_video"
    contract["inputs"]["source_frame_file"] = {
        "node_id": "30", "input_name": "image", "required": True
    }
    references = {
        shot_id: [{"asset_id": f"start-{shot_id}", "role": "first_frame"}]
        for shot_id in ("SH001", "SH002", "SH003", "SH004")
    }
    values = {
        shot_id: {"source_frame_file": f"frames/{shot_id}.png"}
        for shot_id in references
    }
    package = compile_prompt_package(
        _load("shot_plan"), _load("continuity_report"),
        prompt_dialect="wan3", workflow_contract=contract,
        reference_bindings=references, shot_workflow_inputs=values
    )
    first = package["compiled_shots"][0]
    assert first["parameters"]["workflow_inputs"]["source_frame_file"] == (
        "frames/SH001.png"
    )
    assert first["parameters"]["workflow_input_bindings"]["source_frame_file"] == {
        "node_id": "30", "input_name": "image"
    }


def test_contract_must_expose_prompt():
    contract = _load("workflow_contract.wan3")
    contract["inputs"].pop("prompt")
    with pytest.raises(PromptCompilationError, match="must expose a prompt"):
        compile_prompt_package(
            _load("shot_plan"), _load("continuity_report"),
            prompt_dialect="wan3", workflow_contract=contract
        )


def test_compilation_does_not_mutate_inputs():
    plan = _load("shot_plan")
    report = _load("continuity_report")
    bible = _load("continuity_bible")
    contract = _load("workflow_contract.wan3")
    original = copy.deepcopy((plan, report, bible, contract))
    compile_prompt_package(
        plan, report, prompt_dialect="wan3", workflow_contract=contract,
        continuity_bible=bible
    )
    assert (plan, report, bible, contract) == original
