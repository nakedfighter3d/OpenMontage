# Narrative dialogue dry run

This zero-cost example exercises the new planning contracts through workflow-specific prompt compilation. It deliberately stops before `assets`, so the expensive part can be reviewed before any ComfyUI job. It includes the original historical Seedance fixture plus current MiniMax H3 and WAN 3 prompt packages for opaque, premade ComfyUI workflows.

The scene is a restrained two-character conversation in one diner booth. Four shots demonstrate a relationship master, shot/reverse-shot coverage, a story-critical insert, sequential entrance/exit state, and three explicit edit boundaries.

Install the pinned six-skill dramaturgy layer once, outside a production run:

```bash
python scripts/install_screenwriting_skills.py --acknowledge-study-use
python scripts/install_screenwriting_skills.py --check
```

The external skill folders and `skills-lock.json` remain local and untracked. The
checked-in `scene_intent.json` records the pinned revision and the skills used to
revalidate its dramatic handoff.

Validate it with:

```bash
python -c "import json; from pathlib import Path; from lib.narrative_contracts import validate_planning_bundle; p=Path('examples/narrative-dialogue-dry-run'); load=lambda n: json.loads((p/f'{n}.json').read_text()); validate_planning_bundle(load('scene_intent'), load('continuity_bible'), load('shot_plan'), load('continuity_report'), load('prompt_package')); print('valid')"
```

Rebuild an H3 or WAN fixture with `scripts/compile_narrative_prompts.py`; see
`docs/NARRATIVE_PROMPT_COMPILERS.md` for the commands and local acceptance gate.
