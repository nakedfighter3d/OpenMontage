# Asset Director — Narrative Movie Pipeline

Generate reference assets and video takes only from an approved `prompt_package`.

Route every narrative video take directly through `comfyui_video` with the approved premade workflow, workflow-input bindings, and output node. Do not select or call an API provider, and do not infer what model or service exists inside the graph. Image and audio helpers may still be used to prepare workflow inputs.

For each take, preserve traceability to scene, shot, compiled prompt, workflow contract, bound inputs, reference assets, seed when available, and output path. Start with one representative shot. A completed ComfyUI job moves a take to QA; it does not make the take editorially accepted.
