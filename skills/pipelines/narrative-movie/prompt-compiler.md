# Prompt Compiler — Narrative Movie Pipeline

Compile the approved provider-independent shot plan into `prompt_package`. This stage translates intent; it does not direct the scene again.

## Contract

- One compiled entry per shot.
- Preserve narrative purpose, blocking, performance, camera, state, direction, handles, and boundary needs.
- Put prompt dialect, ComfyUI workflow identity, exposed workflow inputs, and reference bindings only in the compiled entry.
- Bind each reference to one narrow role and state unwanted transfer where relevant.
- Read the selected prompt-dialect skill before compiling. The execution target remains an opaque premade ComfyUI workflow.
- Treat `video-prompting-skill` as research material, not a runtime router. Do not use its Wan 2.2 guide as authority for WAN 3.
- If the selected workflow does not expose a required shot property, record the loss or split/repair strategy in `compile_notes`; never silently delete the intent.
- Use `lib/narrative_prompt_compilers.py` for MiniMax H3 and WAN 3 prompt dialects. Both emit only `comfyui_video` workflow inputs; creative rewriting remains upstream.
- Store exact dialogue on the shot as structured `speaker_id`, `text`, and `language`; never recover or paraphrase lines from general action prose.
- Treat `duration_seconds` as intended edit duration and workflow duration as generated material. Record any adaptation as removable handles.
- Never embed API endpoints, remote model IDs, pricing, or provider routing in a narrative prompt package.

The user-facing gate presents the complete shot count, prompt dialect, workflow contract, exposed inputs, output binding, and reference requirements. The foundational dry run ends here.
