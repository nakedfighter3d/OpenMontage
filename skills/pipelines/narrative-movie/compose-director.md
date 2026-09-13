# Compose Director — Narrative Movie Pipeline

Reuse OpenMontage's existing `video_compose`, `audio_mixer`, stitching, trimming, grading, render report, and final-review contracts.

Carry the approved `render_runtime` and composition mode forward unchanged. Route to
Remotion or HyperFrames exactly as recorded in `render_runtime_selection`; if the
chosen runtime is unavailable, stop and surface the constraint instead of silently
falling back. Composition realizes the picture edit; it does not rewrite shot order
or replace rejected takes. Validate duration, codec, frame rate, resolution, audio,
black frames, missing assets, and delivery-promise preservation before presenting
the film.
