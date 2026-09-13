"""Agent-mediated image generation through Codex's built-in image tool.

Python cannot call the host application's native image generator. This provider
therefore exposes a two-phase contract: prepare an action for the orchestrating
Codex agent, then register the generated local file as a normal OpenMontage asset.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class CodexImage(BaseTool):
    name = "codex_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "codex"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.HYBRID
    dependencies = []
    agent_skills = ["codex-imagegen"]
    capabilities = ["text_to_image", "image_edit", "agent_mediated_generation"]
    supports = {
        "text_to_image": True,
        "image_edit": True,
        "reference_image": True,
        "multiple_reference_images": True,
        "agent_mediated": True,
        "api_key_required": False,
    }
    best_for = [
        "default image generation when Codex is orchestrating OpenMontage",
        "API-key-free project images produced with Codex's built-in image generator",
        "image-to-video first frames and visual development",
    ]
    not_good_for = [
        "unattended Python-only runs without a Codex host",
        "workflows that require deterministic seeds or direct model parameters",
    ]
    install_instructions = "Run OpenMontage through Codex; no image API key is required."
    fallback = "comfyui_image"
    fallback_tools = ["comfyui_image"]
    resource_profile = ResourceProfile(network_required=False)
    side_effects = ["copies a Codex-generated image to output_path during register"]
    user_visible_verification = ["Inspect the generated image before registering it"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "operation": {
                "type": "string",
                "enum": ["prepare", "register"],
                "default": "prepare",
            },
            "generation_mode": {"type": "string", "enum": ["generate", "edit"]},
            "image_path": {"type": "string"},
            "image_paths": {"type": "array", "items": {"type": "string"}},
            "aspect_ratio": {"type": "string"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "output_path": {
                "type": "string",
                "description": "Required project destination for the registered final image.",
            },
            "generated_image_path": {
                "type": "string",
                "description": "Local file returned by Codex's built-in image generator.",
            },
        },
    }

    def get_status(self) -> ToolStatus:
        # This is an agent capability, not a subprocess dependency. The execute
        # result explicitly requests agent action when no generated file exists.
        return ToolStatus.AVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 120.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        operation = inputs.get("operation", "prepare")
        output_path = inputs.get("output_path")
        if operation != "register":
            return ToolResult(
                success=False,
                error=(
                    "Codex agent action required: invoke the built-in image_gen tool, "
                    "copy the selected result into the project, then call codex_image "
                    "with operation='register' and generated_image_path."
                ),
                data={
                    "provider": "codex",
                    "status": "agent_action_required",
                    "action": "invoke_builtin_image_gen",
                    "prompt": inputs["prompt"],
                    "generation_mode": inputs.get("generation_mode", "generate"),
                    "reference_image_paths": inputs.get("image_paths")
                    or ([inputs["image_path"]] if inputs.get("image_path") else []),
                    "requested_output_path": output_path,
                    "no_api_key_required": True,
                    "required_agent_skills": ["imagegen", "codex-imagegen"],
                },
            )

        source_value = inputs.get("generated_image_path")
        if not source_value or not output_path:
            return ToolResult(
                success=False,
                error="register requires generated_image_path and output_path",
            )
        source = Path(source_value).resolve()
        destination = Path(output_path).resolve()
        if not source.is_file():
            return ToolResult(success=False, error=f"Generated image not found: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and source != destination:
            return ToolResult(
                success=False,
                error=f"Refusing to overwrite existing image: {destination}",
            )
        if source != destination:
            shutil.copy2(source, destination)
        return ToolResult(
            success=True,
            data={
                "provider": "codex",
                "model": "Codex built-in image generation",
                "prompt": inputs["prompt"],
                "output": str(destination),
                "registered_from": str(source),
                "no_api_key_required": True,
            },
            artifacts=[str(destination)],
            cost_usd=0.0,
            model="Codex built-in image generation",
        )
