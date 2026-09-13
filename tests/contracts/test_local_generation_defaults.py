from pathlib import Path

from lib.config_model import OpenMontageConfig
from tools._comfyui import video_profiles
from tools._comfyui.client import ComfyUIClient
from tools.graphics.codex_image import CodexImage
from tools.graphics.image_selector import ImageSelector
from tools.video.comfyui_video import ComfyUIVideo
from tools.video.video_selector import VideoSelector
from tools.base_tool import BaseTool, ToolResult, ToolStatus


def test_config_defaults_to_codex_images_and_comfyui_i2v():
    cfg = OpenMontageConfig.load()
    assert cfg.generation.image.preferred_provider == "codex"
    assert cfg.generation.video.preferred_provider == "comfyui"
    assert cfg.generation.video.preferred_operation == "image_to_video"
    assert cfg.generation.video.image_to_video_workflow == "OpenMontage_WAN3_fl2va"


def test_codex_image_is_available_and_returns_agent_handoff(tmp_path):
    tool = CodexImage()
    result = tool.execute({"prompt": "a frame", "output_path": str(tmp_path / "frame.png")})
    assert tool.get_status().value == "available"
    assert result.success is False
    assert result.data["status"] == "agent_action_required"
    assert result.data["action"] == "invoke_builtin_image_gen"
    assert result.data["no_api_key_required"] is True


def test_codex_image_registers_generated_asset(tmp_path):
    source = tmp_path / "native.png"
    source.write_bytes(b"image")
    destination = tmp_path / "project" / "frame.png"
    result = CodexImage().execute({
        "prompt": "a frame",
        "operation": "register",
        "generated_image_path": str(source),
        "output_path": str(destination),
    })
    assert result.success is True
    assert destination.read_bytes() == b"image"
    assert result.artifacts == [str(destination.resolve())]


def test_image_selector_uses_codex_default(monkeypatch, tmp_path):
    monkeypatch.setattr(ImageSelector, "_providers", lambda self: [CodexImage()])
    result = ImageSelector().execute({
        "prompt": "a frame",
        "output_path": str(tmp_path / "frame.png"),
    })
    assert result.data["selected_tool"] == "codex_image"
    assert result.data["selected_provider"] == "codex"
    assert result.data["status"] == "agent_action_required"


def test_video_selector_schema_prefers_image_to_video():
    assert VideoSelector.input_schema["properties"]["operation"]["default"] == "image_to_video"


def test_video_selector_uses_configured_comfyui_default(monkeypatch):
    class FakeVideo(BaseTool):
        capability = "video_generation"
        supports = {"image_to_video": True}
        input_schema = {"type": "object", "properties": {"reference_image_path": {}}}

        def __init__(self, name, provider):
            self.name = name
            self.provider = provider

        def get_status(self):
            return ToolStatus.AVAILABLE

        def execute(self, inputs):
            return ToolResult(success=True, data={})

    other = FakeVideo("other_video", "other")
    comfy = FakeVideo("comfyui_video", "comfyui")
    monkeypatch.setattr(VideoSelector, "_providers", lambda self: [other, comfy])
    result = VideoSelector().execute({"prompt": "move", "reference_image_path": "frame.png"})
    assert result.success is True
    assert result.data["selected_tool"] == "comfyui_video"
    assert result.data["selected_provider"] == "comfyui"


def test_named_wan_profile_builds_patchable_api_graph(monkeypatch, tmp_path):
    (tmp_path / "OpenMontage_WAN3_fl2va.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("COMFYUI_WORKFLOW_DIR", str(tmp_path))
    client = ComfyUIClient()
    monkeypatch.setattr(client, "upload_file", lambda path, name=None: name or Path(path).name)
    workflow, output_node, profile = video_profiles.build_profile_workflow(
        client,
        "OpenMontage_WAN3_fl2va",
        {
            "prompt": "camera pushes in",
            "operation": "image_to_video",
            "reference_image_path": "first.png",
            "last_image_path": "last.png",
            "duration": 5,
        },
        tmp_path / "clip.mp4",
        42,
    )
    assert output_node == "3"
    assert profile.name == "OpenMontage_WAN3_fl2va"
    assert workflow["1"]["inputs"]["model.prompt"] == "camera pushes in"
    assert workflow["1"]["inputs"]["model.duration"] == "5s"
    assert workflow["1"]["inputs"]["model.resolution"] == "480p"
    assert workflow["1"]["inputs"]["last_frame"] == ["4", 0]


def test_comfyui_video_contract_exposes_all_named_profiles():
    info = ComfyUIVideo.input_schema["properties"]["workflow_profile"]
    assert set(info["enum"]) == set(video_profiles.PROFILES)
    assert "reference_to_video" in ComfyUIVideo.capabilities
