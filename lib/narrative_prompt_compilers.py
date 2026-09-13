"""Deterministic prompt dialects for opaque ComfyUI video workflows.

The shot plan remains the creative source of truth. A workflow contract declares
only the inputs exposed by a user's premade ComfyUI API workflow and its video output
node. OpenMontage does not inspect or route to the service/model inside that graph.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from schemas.artifacts import validate_artifact


COMPILER_VERSION = "narrative-comfyui-prompt-compilers/0.2.0"
PROMPT_DIALECTS = ("minimax-h3", "wan3")
class PromptCompilationError(ValueError):
    """Raised when intent cannot be bound safely to a workflow contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PromptCompilationError(message)


def validate_workflow_contract(contract: Mapping[str, Any]) -> None:
    """Validate the small, model-agnostic contract beside a premade workflow."""

    required = {"version", "id", "workflow_path", "output_node", "mode", "inputs"}
    missing = required - set(contract)
    _require(not missing, f"workflow contract missing: {', '.join(sorted(missing))}")
    _require(contract["version"] == "1.0", "workflow contract version must be 1.0")
    _require(
        contract["mode"] in {"text_to_video", "image_to_video", "reference_to_video"},
        "workflow contract has unsupported mode",
    )
    _require(
        isinstance(contract["inputs"], dict),
        "workflow contract inputs must be an object",
    )
    _require("prompt" in contract["inputs"], "workflow contract must expose a prompt input")
    for semantic, binding in contract["inputs"].items():
        _require(isinstance(semantic, str) and bool(semantic), "workflow input names must be non-empty")
        _require(isinstance(binding, dict), f"binding {semantic!r} must be an object")
        _require(
            "node_id" in binding and "input_name" in binding,
            f"binding {semantic!r} requires node_id and input_name",
        )
        if "accepted_values" in binding:
            _require(
                isinstance(binding["accepted_values"], list),
                f"binding {semantic!r}.accepted_values must be an array",
            )


def _format_map(values: Mapping[str, str]) -> str:
    return "; ".join(f"{key}: {value}" for key, value in sorted(values.items()))


def _format_state(state: Mapping[str, Any]) -> str:
    return "; ".join(
        (
            f"positions ({_format_map(state['character_positions'])})",
            f"body orientation ({_format_map(state['body_orientation'])})",
            f"eyelines ({_format_map(state['eyelines'])})",
            f"movement ({_format_map(state['movement_direction'])})",
            f"action ({state['current_action']})",
            f"props ({_format_map(state['prop_states'])})",
            f"emotion ({_format_map(state['emotional_state'])})",
            f"camera side ({state['camera_side']})",
        )
    )


def _camera_text(camera: Mapping[str, str]) -> str:
    keys = (
        "shot_size",
        "position",
        "height",
        "angle",
        "movement",
        "field_of_view",
        "focus",
        "composition",
    )
    return "; ".join(
        f"{key.replace('_', ' ')}: {camera[key]}" for key in keys if camera.get(key)
    )


def _global_context(continuity_bible: Mapping[str, Any] | None) -> tuple[str, str]:
    if not continuity_bible:
        return "", ""
    characters = []
    for character in continuity_bible.get("characters", []):
        characters.append(
            f"{character['character_id']} — identity: "
            f"{', '.join(character.get('identity_traits', []))}; wardrobe: "
            f"{', '.join(character.get('wardrobe', []))}"
        )
    environment = continuity_bible.get("environment", {})
    keep = "; ".join(continuity_bible.get("global_must_keep", []))
    avoid = "; ".join(continuity_bible.get("global_must_avoid", []))
    context = "; ".join(
        item
        for item in (
            continuity_bible.get("visual_direction", ""),
            environment.get("description", ""),
            environment.get("time_of_day", ""),
            environment.get("lighting_state", ""),
            environment.get("weather_or_atmosphere", ""),
            " | ".join(characters),
            f"Must keep: {keep}" if keep else "",
        )
        if item
    )
    return context, avoid


def _boundary_context(
    shot_id: str, boundaries: Sequence[Mapping[str, Any]]
) -> tuple[str, str, str]:
    incoming = next((b for b in boundaries if b["to_shot_id"] == shot_id), None)
    outgoing = next((b for b in boundaries if b["from_shot_id"] == shot_id), None)
    incoming_text = outgoing_text = sound = ""
    if incoming:
        incoming_text = (
            f"Enter from {incoming['from_shot_id']}: {incoming['incoming_action']}; "
            f"cut at {incoming['intended_cut_point']}; {incoming['required_handles']}"
        )
        sound = incoming.get("audio_bridge", "")
    if outgoing:
        outgoing_text = (
            f"Hand off to {outgoing['to_shot_id']}: {outgoing['outgoing_action']}; "
            f"cut at {outgoing['intended_cut_point']}; {outgoing['required_handles']}"
        )
        sound = sound or outgoing.get("audio_bridge", "")
    return incoming_text, outgoing_text, sound


def _base_shot_text(
    shot: Mapping[str, Any],
    boundaries: Sequence[Mapping[str, Any]],
    continuity_bible: Mapping[str, Any] | None,
) -> tuple[str, str, str]:
    global_context, avoid = _global_context(continuity_bible)
    incoming, outgoing, sound = _boundary_context(shot["id"], boundaries)
    pieces = [
        "Single continuous shot; do not introduce an internal edit.",
        f"Narrative function: {shot['narrative_purpose']}",
        f"Subjects: {', '.join(shot['subjects'])}.",
        f"Starting state: {_format_state(shot['entrance_state'])}.",
        f"Blocking: {shot['blocking']}",
        f"Observable action: {shot.get('action', shot['exit_state']['current_action'])}",
        f"Performance: {shot['performance_intent']}",
        f"Camera: {_camera_text(shot['camera'])}.",
        f"Direction and eyelines: {shot['screen_direction']}; {_format_map(shot['eyelines'])}.",
        f"Lighting: {shot.get('lighting_intent', 'preserve established lighting').rstrip('.')}.",
        f"Ending state: {_format_state(shot['exit_state'])}.",
        f"Editorial handles: {shot['edit_handles']['head_seconds']} seconds clean at the head; "
        f"{shot['edit_handles']['tail_seconds']} seconds clean at the tail.",
        f"Incoming boundary: {incoming}." if incoming else "",
        f"Outgoing boundary: {outgoing}." if outgoing else "",
        f"Global continuity: {global_context}." if global_context else "",
        f"Allowed tolerances: {'; '.join(shot.get('tolerances', []))}."
        if shot.get("tolerances")
        else "",
    ]
    return " ".join(piece for piece in pieces if piece), sound, avoid


def _h3_dialogue(dialogue: Sequence[Mapping[str, str]]) -> str:
    speakers: dict[str, str] = {}
    rendered = []
    for line in dialogue:
        speaker = line["speaker_id"]
        speakers.setdefault(speaker, f"S{len(speakers) + 1}")
        rendered.append(
            f"{speaker} ({speakers[speaker]}) says exactly "
            f"<d>[{line['language']}] {line['text']}</d>"
        )
    return " Exact dialogue: " + "; ".join(rendered) + "." if rendered else ""


def _plain_dialogue(dialogue: Sequence[Mapping[str, str]]) -> str:
    rendered = [
        f"{line['speaker_id']} says exactly in {line['language']}: {line['text']!r}"
        for line in dialogue
    ]
    return " Exact dialogue: " + "; ".join(rendered) + "." if rendered else ""


def _compile_prompt(
    dialect: str,
    base: str,
    sound: str,
    dialogue: Sequence[Mapping[str, str]],
) -> str:
    if dialect == "minimax-h3":
        soundscape = sound or (
            "Preserve natural location ambience and synchronized action sounds."
        )
        return (
            f"integrated_multimodal_description: [Shot 1] {base}"
            f"{_h3_dialogue(dialogue)}\n\n"
            f"overall_soundscape: {soundscape}\n\n"
            "non_diegetic_music: N/A"
        )
    return base + _plain_dialogue(dialogue)


def _negative_prompt(dialect: str, avoid: str) -> str | None:
    if dialect == "minimax-h3":
        return None
    generic = (
        "internal cuts, axis reversal, incorrect eyeline, reversed screen direction, "
        "identity drift, wardrobe drift, duplicate props, unwanted camera motion"
    )
    return f"{generic}; {avoid}" if avoid else generic


def _adapt_value(
    semantic: str,
    value: Any,
    binding: Mapping[str, Any],
    notes: list[str],
) -> Any:
    accepted = binding.get("accepted_values")
    if not accepted or value in accepted:
        return value
    if semantic == "duration_seconds":
        candidates = sorted(
            candidate
            for candidate in accepted
            if isinstance(candidate, (int, float)) and candidate >= value
        )
        _require(bool(candidates), f"workflow cannot represent a {value:g}s shot")
        chosen = candidates[0]
        notes.append(
            f"Planned edit duration is {value:g}s; workflow input uses {chosen:g}s and "
            "the difference is removable edit-handle material."
        )
        return chosen
    raise PromptCompilationError(
        f"workflow input {semantic!r} does not accept requested value {value!r}"
    )


def _workflow_values(
    contract: Mapping[str, Any],
    prompt: str,
    negative_prompt: str | None,
    planned_duration: float,
    aspect_ratio: str,
    audio: bool,
    overrides: Mapping[str, Any],
    notes: list[str],
) -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative_prompt or "",
        "duration_seconds": math.ceil(planned_duration),
        "aspect_ratio": aspect_ratio,
        "generate_audio": audio,
        **overrides,
    }
    unknown = set(overrides) - set(contract["inputs"])
    _require(
        not unknown,
        "shot workflow values are not exposed by the contract: "
        + ", ".join(sorted(unknown)),
    )
    values = {
        semantic: _adapt_value(semantic, candidates[semantic], binding, notes)
        for semantic, binding in contract["inputs"].items()
        if semantic in candidates
    }
    missing_required = {
        semantic
        for semantic, binding in contract["inputs"].items()
        if binding.get("required") and semantic not in values
    }
    _require(
        not missing_required,
        "required workflow values are missing: " + ", ".join(sorted(missing_required)),
    )
    if "duration_seconds" not in contract["inputs"]:
        notes.append(
            "Workflow does not expose duration; planned edit duration remains "
            f"{planned_duration:g}s."
        )
    return values


def _validate_bindings(mode: str, bindings: Sequence[Mapping[str, Any]]) -> None:
    roles = {binding["role"] for binding in bindings}
    if mode == "text_to_video":
        _require(not bindings, "text_to_video cannot contain reference bindings")
    elif mode == "image_to_video":
        _require(
            bool(roles & {"image", "first_frame"}),
            "image_to_video requires an image or first_frame binding",
        )
    elif mode == "reference_to_video":
        _require(bool(bindings), "reference_to_video requires at least one binding")


def compile_prompt_package(
    shot_plan: dict[str, Any],
    continuity_report: dict[str, Any],
    *,
    prompt_dialect: str,
    workflow_contract: dict[str, Any],
    continuity_bible: dict[str, Any] | None = None,
    reference_bindings: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    shot_workflow_inputs: Mapping[str, Mapping[str, Any]] | None = None,
    aspect_ratio: str = "16:9",
    audio: bool = True,
) -> dict[str, Any]:
    """Compile shots for one opaque, user-supplied ComfyUI workflow."""

    validate_artifact("shot_plan", shot_plan)
    validate_artifact("continuity_report", continuity_report)
    validate_workflow_contract(workflow_contract)
    _require(prompt_dialect in PROMPT_DIALECTS, f"unknown prompt dialect {prompt_dialect!r}")
    _require(
        continuity_report["shot_plan_id"] == shot_plan["id"],
        "continuity_report.shot_plan_id does not match shot_plan.id",
    )
    _require(
        continuity_report["approved_for_generation"],
        "continuity report has not approved generation",
    )
    if continuity_bible is not None:
        validate_artifact("continuity_bible", continuity_bible)
        _require(
            continuity_bible["id"] == shot_plan["continuity_bible_id"],
            "continuity_bible.id does not match shot_plan.continuity_bible_id",
        )

    binding_map = reference_bindings or {}
    input_map = shot_workflow_inputs or {}
    known_ids = {shot["id"] for shot in shot_plan["shots"]}
    _require(
        not (set(binding_map) - known_ids),
        "reference bindings contain unknown shots",
    )
    _require(
        not (set(input_map) - known_ids),
        "workflow input values contain unknown shots",
    )
    mode = workflow_contract["mode"]
    compiled = []
    for shot in sorted(shot_plan["shots"], key=lambda value: value["order"]):
        shot_id = shot["id"]
        references = [dict(item) for item in binding_map.get(shot_id, [])]
        _validate_bindings(mode, references)
        base, sound, avoid = _base_shot_text(
            shot, shot_plan["edit_boundaries"], continuity_bible
        )
        prompt = _compile_prompt(prompt_dialect, base, sound, shot.get("dialogue", []))
        negative = _negative_prompt(prompt_dialect, avoid)
        notes: list[str] = []
        workflow_values = _workflow_values(
            workflow_contract,
            prompt,
            negative,
            shot["duration_seconds"],
            aspect_ratio,
            audio,
            input_map.get(shot_id, {}),
            notes,
        )
        compiled.append(
            {
                "shot_id": shot_id,
                "provider": "comfyui",
                "model": f"workflow:{workflow_contract['id']}",
                "mode": mode,
                "prompt": prompt,
                "negative_prompt": negative,
                "parameters": {
                    "tool": "comfyui_video",
                    "operation": "custom_workflow",
                    "workflow_contract_id": workflow_contract["id"],
                    "workflow_path": workflow_contract["workflow_path"],
                    "output_node": str(workflow_contract["output_node"]),
                    "workflow_name": workflow_contract.get(
                        "name", workflow_contract["id"]
                    ),
                    "workflow_input_bindings": {
                        semantic: {
                            "node_id": str(binding["node_id"]),
                            "input_name": binding["input_name"],
                        }
                        for semantic, binding in workflow_contract["inputs"].items()
                    },
                    "workflow_inputs": workflow_values,
                },
                "reference_bindings": references,
                "compile_notes": notes,
            }
        )

    package = {
        "version": "1.0",
        "id": (
            f"prompts-{shot_plan['id']}-{prompt_dialect}-"
            f"{workflow_contract['id']}-v1"
        ),
        "shot_plan_id": shot_plan["id"],
        "continuity_report_id": continuity_report["id"],
        "compiler_version": COMPILER_VERSION,
        "compiled_shots": compiled,
        "metadata": {
            "dry_run": True,
            "generation_calls": 0,
            "transport": "comfyui-custom-workflow",
            "prompt_dialect": prompt_dialect,
        },
    }
    validate_artifact("prompt_package", package)
    return package


def comfyui_inputs_for_compiled_shot(
    compiled_shot: Mapping[str, Any], *, output_path: str | None = None
) -> dict[str, Any]:
    """Turn one compiled entry into inputs accepted by ``comfyui_video``."""

    _require(compiled_shot.get("provider") == "comfyui", "compiled shot is not ComfyUI")
    parameters = dict(compiled_shot["parameters"])
    _require(parameters.pop("tool", None) == "comfyui_video", "wrong compiled tool")
    parameters["prompt"] = compiled_shot["prompt"]
    if output_path is not None:
        parameters["output_path"] = output_path
    return parameters
