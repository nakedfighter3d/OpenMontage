---
name: codex-imagegen
description: Use OpenMontage's codex_image provider to generate or edit project bitmap assets with Codex's built-in image generator, without an image API key.
---

# Codex-native images for OpenMontage

`codex_image` is agent-mediated because Python tools cannot invoke Codex host tools.

1. Call `image_selector` normally. When it selects `codex_image`, expect a structured
   `agent_action_required` result; this is a handoff, not a provider failure.
2. Read the built-in `imagegen` skill and invoke the built-in `image_gen` tool. Do not
   use its CLI/API fallback unless the user explicitly requests that route.
3. Inspect the result. For project assets, copy the selected image from Codex's
   generated-images directory to the requested `projects/<id>/assets/images/` path.
4. Call `codex_image` with the original prompt, `operation: register`,
   `generated_image_path`, and `output_path`. Only the register result completes the
   asset and may be written into `asset_manifest` or a completed checkpoint.

Do not silently fall back to "no image" or report the prepare phase as a generated
artifact. If built-in generation is unavailable, surface that blocker and ask before
switching to an API-backed image provider.
