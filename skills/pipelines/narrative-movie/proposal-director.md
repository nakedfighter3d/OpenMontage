# Proposal Director — Narrative Movie Pipeline

Create the normal `proposal_packet` and append-only `decision_log`, reusing OpenMontage's capability, budget, provider-selection, render-runtime, and approval rules.

Make these narrative-specific decisions explicit:

- scene or film scope, target duration, aspect ratio, language, and sound assumptions;
- whether the run stops at the dry-run `prompt_compile` stage;
- whether motion is required;
- candidate video providers without committing filmmaking intent to any one provider;
- sample size, take count, and estimated cost before any batch;
- picture-composition runtime and mode, presented according to the standard runtime-choice contract.

When both runtimes are available, **Present both** Remotion and HyperFrames
(`hyperframes`) before
recording `render_runtime_selection`. Recommend one with reasons, but never silently
choose it. Remotion is usually the direct fit for conventional clip-led narrative
editing; HyperFrames remains a valid option when its HTML-native motion, titles, or
shader transitions materially serve the film. Record availability, fit, tradeoff,
and the user's choice in the proposal packet.

This gate authorizes planning only. It does not authorize later paid generation.
