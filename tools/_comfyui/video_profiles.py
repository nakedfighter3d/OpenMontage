"""Named, patchable ComfyUI video workflows used by OpenMontage.

Profiles deliberately sit above arbitrary ``workflow_path`` execution: they expose a
stable media/prompt contract while allowing the user's saved graph to remain the
source of model and sampler settings.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools._comfyui.client import ComfyUIClient, ComfyUIError


DEFAULT_WORKFLOW_DIR = Path(
    r"C:\!AI\ComfyUI-Easy-Install\ComfyUI-Easy-Install\ComfyUI\user\default\workflows"
)


@dataclass(frozen=True)
class VideoWorkflowProfile:
    name: str
    filename: str
    operations: tuple[str, ...]
    model: str
    hosted: bool
    required_nodes: tuple[str, ...]
    min_duration: int
    max_duration: int
    default_duration: int = 5
    resolution: str = "480p"
    aspect_ratio: str = "16:9"


PROFILES: dict[str, VideoWorkflowProfile] = {
    "OpenMontage_WAN3_fl2va": VideoWorkflowProfile(
        name="OpenMontage_WAN3_fl2va",
        filename="OpenMontage_WAN3_fl2va.json",
        operations=("image_to_video",),
        model="wan-3-0-image-to-video",
        hosted=True,
        required_nodes=("VeniceWANImageToVideo", "SaveVideo", "LoadImage"),
        min_duration=2,
        max_duration=30,
    ),
    "OpenMontage_WAN3_ref2va": VideoWorkflowProfile(
        name="OpenMontage_WAN3_ref2va",
        filename="OpenMontage_WAN3_ref2va.json",
        operations=("reference_to_video",),
        model="wan-3-0-reference-to-video",
        hosted=True,
        required_nodes=(
            "VeniceWANReferenceToVideo", "SaveVideo", "LoadImage", "LoadVideo", "LoadAudio"
        ),
        min_duration=2,
        max_duration=30,
    ),
    "OpenMontage_MiniMaxH3_fl2va": VideoWorkflowProfile(
        name="OpenMontage_MiniMaxH3_fl2va",
        filename="OpenMontage_MiniMaxH3_fl2va.json",
        operations=("text_to_video", "image_to_video"),
        model="MiniMax-H3 FL2VA (local)",
        hosted=False,
        required_nodes=("MiniMaxH3ImageToVideo", "SaveVideo"),
        min_duration=3,
        max_duration=10,
    ),
}


def workflow_dir() -> Path:
    return Path(os.environ.get("COMFYUI_WORKFLOW_DIR", DEFAULT_WORKFLOW_DIR))


def profile_path(profile: VideoWorkflowProfile) -> Path:
    return workflow_dir() / profile.filename


def get_profile(name: str) -> VideoWorkflowProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ComfyUIError(
            f"Unknown ComfyUI workflow profile {name!r}. Available: {', '.join(PROFILES)}"
        ) from exc


def default_profile_for(operation: str) -> str:
    from lib.config_model import OpenMontageConfig

    cfg = OpenMontageConfig.load().generation.video
    return {
        "image_to_video": cfg.image_to_video_workflow,
        "reference_to_video": cfg.reference_to_video_workflow,
        "text_to_video": cfg.text_to_video_workflow,
    }.get(operation, cfg.image_to_video_workflow)


def profile_ready(client: ComfyUIClient, name: str) -> bool:
    profile = get_profile(name)
    if not profile_path(profile).is_file():
        return False
    if not client.is_available():
        return client.can_auto_start()
    return all(client.has_node(node) for node in profile.required_nodes)


def _duration(inputs: dict[str, Any], profile: VideoWorkflowProfile) -> int:
    raw = inputs.get("duration", profile.default_duration)
    try:
        duration = int(str(raw).rstrip("s"))
    except (TypeError, ValueError) as exc:
        raise ComfyUIError(f"duration must be whole seconds, got {raw!r}") from exc
    if not profile.min_duration <= duration <= profile.max_duration:
        raise ComfyUIError(
            f"{profile.name} supports {profile.min_duration}-{profile.max_duration}s; got {duration}s"
        )
    return duration


def _input_path(inputs: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = inputs.get(key)
        if value:
            return str(value)
    return None


def _upload(client: ComfyUIClient, path: str, prefix: str) -> str:
    source = Path(path)
    return client.upload_file(source, f"om_{prefix}_{source.name}")


def _save_node(video_link: list[Any], output_path: Path) -> dict[str, Any]:
    return {
        "class_type": "SaveVideo",
        "inputs": {
            "video": video_link,
            "filename_prefix": f"video/{output_path.stem}",
            "format": "auto",
            "format.codec": "auto",
            "codec": "auto",
        },
    }


def _build_wan_fl(
    client: ComfyUIClient,
    inputs: dict[str, Any],
    output_path: Path,
    seed: int,
    profile: VideoWorkflowProfile,
) -> tuple[dict[str, Any], str]:
    first = _input_path(inputs, "first_image_path", "reference_image_path", "image_path")
    if not first:
        raise ComfyUIError(f"{profile.name} requires first_image_path/reference_image_path")
    workflow: dict[str, Any] = {
        "2": {"class_type": "LoadImage", "inputs": {"image": _upload(client, first, "first")}},
        "1": {
            "class_type": "VeniceWANImageToVideo",
            "inputs": {
                "model": profile.model,
                "model.prompt": inputs["prompt"],
                "model.duration": f"{_duration(inputs, profile)}s",
                "model.resolution": inputs.get("resolution", profile.resolution),
                "model.aspect_ratio": inputs.get("aspect_ratio", profile.aspect_ratio),
                "model.audio": bool(inputs.get("generate_audio", True)),
                "image": ["2", 0],
                "generation_id": seed,
                "resume_job": "",
            },
        },
        "3": _save_node(["1", 0], output_path),
    }
    last = _input_path(inputs, "last_image_path")
    if last:
        workflow["4"] = {
            "class_type": "LoadImage",
            "inputs": {"image": _upload(client, last, "last")},
        }
        workflow["1"]["inputs"]["last_frame"] = ["4", 0]
    return workflow, "3"


def _list_inputs(inputs: dict[str, Any], plural: str, singular: str) -> list[str]:
    values = list(inputs.get(plural) or [])
    one = inputs.get(singular)
    if one and one not in values:
        values.insert(0, str(one))
    return [str(value) for value in values]


def _build_wan_ref(
    client: ComfyUIClient,
    inputs: dict[str, Any],
    output_path: Path,
    seed: int,
    profile: VideoWorkflowProfile,
) -> tuple[dict[str, Any], str]:
    groups = [
        ("reference_image_paths", "reference_image_path", "LoadImage", "image", "reference_images.image"),
        ("reference_video_paths", "reference_video_path", "LoadVideo", "file", "reference_videos.video"),
        ("reference_audio_paths", "reference_audio_path", "LoadAudio", "audio", "reference_audios.audio"),
    ]
    workflow: dict[str, Any] = {}
    model_inputs: dict[str, Any] = {
        "model": profile.model,
        "model.prompt": inputs["prompt"],
        "model.duration": f"{_duration(inputs, profile)}s",
        "model.resolution": inputs.get("resolution", profile.resolution),
        "model.aspect_ratio": inputs.get("aspect_ratio", profile.aspect_ratio),
        "model.audio": bool(inputs.get("generate_audio", True)),
        "generation_id": seed,
        "resume_job": "",
    }
    next_id = 10
    media_count = 0
    for plural, singular, node_class, input_name, dynamic_prefix in groups:
        for index, path in enumerate(_list_inputs(inputs, plural, singular), 1):
            node_id = str(next_id)
            next_id += 1
            workflow[node_id] = {
                "class_type": node_class,
                "inputs": {input_name: _upload(client, path, f"ref_{media_count}")},
            }
            model_inputs[f"{dynamic_prefix}{index}"] = [node_id, 0]
            media_count += 1
    if not media_count:
        raise ComfyUIError(f"{profile.name} requires at least one reference image, video, or audio")
    workflow["4"] = {"class_type": "VeniceWANReferenceToVideo", "inputs": model_inputs}
    workflow["3"] = _save_node(["4", 0], output_path)
    return workflow, "3"


_WIDGET_INPUTS: dict[str, tuple[str, ...]] = {
    "KSamplerSelect": ("sampler_name",),
    "PrimitiveFloat": ("value",),
    "VAELoader": ("vae_name",),
    "CLIPLoader": ("clip_name", "type", "device"),
    "ComfyMathExpression": ("expression",),
    "RandomNoise": ("noise_seed",),
    "OTUNetLoaderW8A8": ("unet_name", "weight_dtype", "model_type", "on_the_fly_quantization", "enable_convrot", "lora_mode"),
    "PathchSageAttentionKJ": ("sage_attention", "allow_compile"),
    "ImageResizeKJv2": ("width", "height", "upscale_method", "keep_proportion", "pad_color", "crop_position", "divisible_by", "device"),
    "CreateVideo": ("fps", "bit_depth", "color_space"),
    "MiniMaxH3SigmaShift": ("shift_video", "shift_audio"),
    "LoraLoaderModelOnly": ("lora_name", "strength_model"),
    "BasicScheduler": ("scheduler", "steps", "denoise"),
    "SpectrumApplyMiniMaxH3": (
        "enabled", "blend_weight", "degree", "ridge_lambda", "window_size", "flex_window",
        "warmup_steps", "tail_actual_steps", "max_history", "debug", "history_storage",
        "bootstrap_first_forecast", "anchor_residual_feedback", "selective_rollback_correction",
        "offline_smoothing_replay", "audio_blend_weight", "offline_archive_storage",
        "model_aware_mode", "model_aware_risk_threshold", "model_aware_trust_shrinkage",
        "model_aware_replay_generic_correction", "generic_correction_mode",
        "generic_correction_limiter", "generic_correction_limit",
        "generic_correction_attenuation", "sa_pece_forecast_policy",
    ),
}


def _build_minimax(
    client: ComfyUIClient,
    inputs: dict[str, Any],
    output_path: Path,
    seed: int,
    profile: VideoWorkflowProfile,
) -> tuple[dict[str, Any], str]:
    source_path = profile_path(profile)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    subgraph = source["definitions"]["subgraphs"][0]
    outer = next(node for node in source["nodes"] if node["type"] == subgraph["id"])
    outer_values = list(outer.get("widgets_values") or [])
    width = int(inputs.get("width", outer_values[1]))
    height = int(inputs.get("height", outer_values[2]))
    external: dict[int, Any] = {
        2: inputs["prompt"], 3: width, 4: height,
        5: float(_duration(inputs, profile)), 6: seed,
        7: outer_values[5], 8: outer_values[6], 9: outer_values[7], 10: outer_values[8],
    }
    first = _input_path(inputs, "first_image_path", "reference_image_path", "image_path")
    last = _input_path(inputs, "last_image_path")
    if first:
        external[0] = ["901", 0]
    if last:
        external[1] = ["902", 0]

    links = {int(link["id"]): link for link in subgraph["links"]}
    inactive = set()
    if not first:
        inactive.add(125)
    if not last:
        inactive.add(126)
    workflow: dict[str, Any] = {}
    for node in subgraph["nodes"]:
        node_id = int(node["id"])
        if node_id in inactive:
            continue
        values = list(node.get("widgets_values") or [])
        widget_names = _WIDGET_INPUTS.get(node["type"], ())
        api_inputs = {name: values[i] for i, name in enumerate(widget_names) if i < len(values)}
        for slot, item in enumerate(node.get("inputs") or []):
            link_id = item.get("link")
            if link_id is None:
                continue
            link = links[int(link_id)]
            origin = int(link["origin_id"])
            if origin == -10:
                value = external.get(int(link["origin_slot"]))
                if value is not None:
                    api_inputs[item["name"]] = value
            elif origin not in inactive:
                api_inputs[item["name"]] = [str(origin), int(link["origin_slot"])]
        workflow[str(node_id)] = {"class_type": node["type"], "inputs": api_inputs}
    if first:
        workflow["901"] = {"class_type": "LoadImage", "inputs": {"image": _upload(client, first, "first")}}
    if last:
        workflow["902"] = {"class_type": "LoadImage", "inputs": {"image": _upload(client, last, "last")}}
    workflow["92"] = _save_node(["91", 0], output_path)
    return workflow, "92"


def build_profile_workflow(
    client: ComfyUIClient,
    name: str,
    inputs: dict[str, Any],
    output_path: Path,
    seed: int,
) -> tuple[dict[str, Any], str, VideoWorkflowProfile]:
    profile = get_profile(name)
    operation = str(inputs.get("operation", "image_to_video"))
    if operation not in profile.operations:
        raise ComfyUIError(f"{profile.name} does not support {operation}; supports {profile.operations}")
    if not profile_path(profile).is_file():
        raise ComfyUIError(
            f"Workflow profile file not found: {profile_path(profile)}. "
            "Set COMFYUI_WORKFLOW_DIR if the ComfyUI user workflow folder moved."
        )
    if name == "OpenMontage_WAN3_fl2va":
        workflow, output_node = _build_wan_fl(client, inputs, output_path, seed, profile)
    elif name == "OpenMontage_WAN3_ref2va":
        workflow, output_node = _build_wan_ref(client, inputs, output_path, seed, profile)
    else:
        workflow, output_node = _build_minimax(client, inputs, output_path, seed, profile)
    return workflow, output_node, profile
