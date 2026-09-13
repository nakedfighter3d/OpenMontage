# Prompt Compiler — Narrative Movie Pipeline

Compile the approved provider-independent shot plan into `prompt_package`. This stage translates intent; it does not direct the scene again.

## Contract

- One compiled entry per shot.
- Preserve narrative purpose, blocking, performance, camera, state, direction, handles, and boundary needs.
- Put provider/model/mode, API parameters, negative-prompt support, and reference bindings only in the compiled entry.
- Bind each reference to one narrow role and state unwanted transfer where relevant.
- Read the selected OpenMontage provider skill before compiling.
- Treat `video-prompting-skill` as research material, not a parallel runtime router. Prefer OpenMontage's existing `seedance-2-5` and `minimax-h3` skills; do not use the Wan 2.2 guide as authority for WAN3.
- If the selected provider cannot express a required shot property, record the loss or split/repair strategy in `compile_notes`; never silently delete the intent.

The user-facing gate presents the complete shot count, provider/model, reference requirements, parameters, and estimated total generation cost. The foundational dry run ends here.

