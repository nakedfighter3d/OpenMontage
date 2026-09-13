# Dramaturgy Director — Narrative Movie Pipeline

Produce `scene_intent` using `schemas/artifacts/scene_intent.schema.json`.

Before creative work, run:

```bash
python scripts/install_screenwriting_skills.py --check
```

If the check fails, stop and provide the explicit installation command. Never install
or update an external dependency during a production run and never replace the
missing layer with improvised screenwriting theory.

Use `sw-workflow` in **subordinate** mode: OpenMontage owns routing, files, stage
state, approvals, and production decisions. Load only the relevant installed skills:

- `sw-premise-theme` for the governing premise, theme, and dramatic question;
- `sw-story-structure` when feature/sequence causality or a climax affects the scene;
- `sw-character-conflict` for objectives, opposition, stakes, and relationship pressure;
- `sw-scene-craft` for purpose, value turn, beats, visible information, and setup/payoff;
- `sw-dialogue` only when dialogue or subtext is part of the requested scene.

The external skills advise dramaturgy; `scene_intent.schema.json` remains the
authoritative host handoff. Translate their structured fields into `scene_intent`
rather than embedding their YAML/Markdown output as prose. Record every invoked skill
and the pinned dependency revision in `skill_provenance` and `metadata`.

## Responsibility

Answer what happens and why:

- scene purpose and thematic pressure;
- each character's objective, opposition, stakes, and emotional change;
- beats, value changes, required information, setup/payoff, dialogue, action, and subtext.

Do not select shot sizes, lenses, camera moves, generation providers, or provider
syntax. A visual action belongs here only when it changes the drama or must be
visible for story comprehension.

## Gate

Every beat must change action, information, relationship, or value. Dialogue must be
playable action rather than exposition detached from objectives. A missing or
integrity-failed dependency is a setup blocker, not permission to continue with a
silent fallback.
