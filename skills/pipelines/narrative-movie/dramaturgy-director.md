# Dramaturgy Director — Narrative Movie Pipeline

Produce `scene_intent` using `schemas/artifacts/scene_intent.schema.json`.

When installed, load only the relevant skills selected under the `dramaturgy` dependency in `external-skills.yaml`. Preserve that repository's independent ownership and record invoked skill names in `skill_provenance`.

## Responsibility

Answer what happens and why:

- scene purpose and thematic pressure;
- each character's objective, opposition, stakes, and emotional change;
- beats, value changes, required information, setup/payoff, dialogue, action, and subtext.

Do not select shot sizes, lenses, camera moves, generation providers, or provider syntax. A visual action belongs here only when it changes the drama or must be visible for story comprehension.

## Gate

Every beat must change action, information, relationship, or value. Dialogue must be playable action rather than exposition detached from objectives. If the external dramaturgy package is not ready, mark that limitation in metadata and keep this first slice deliberately small.

