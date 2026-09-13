#!/usr/bin/env python3
"""Compile a narrative shot plan for an opaque premade ComfyUI workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.narrative_prompt_compilers import PROMPT_DIALECTS, compile_prompt_package


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shot-plan", type=Path, required=True)
    parser.add_argument("--continuity-report", type=Path, required=True)
    parser.add_argument("--continuity-bible", type=Path)
    parser.add_argument("--workflow-contract", type=Path, required=True)
    parser.add_argument("--prompt-dialect", choices=PROMPT_DIALECTS, required=True)
    parser.add_argument(
        "--reference-bindings",
        type=Path,
        help="Optional JSON map from shot ID to logical reference bindings",
    )
    parser.add_argument(
        "--workflow-values",
        type=Path,
        help="Optional JSON map from shot ID to values for other exposed workflow inputs",
    )
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    package = compile_prompt_package(
        _load(args.shot_plan),
        _load(args.continuity_report),
        prompt_dialect=args.prompt_dialect,
        workflow_contract=_load(args.workflow_contract),
        continuity_bible=_load(args.continuity_bible) if args.continuity_bible else None,
        reference_bindings=(
            _load(args.reference_bindings) if args.reference_bindings else None
        ),
        shot_workflow_inputs=(
            _load(args.workflow_values) if args.workflow_values else None
        ),
        aspect_ratio=args.aspect_ratio,
        audio=not args.no_audio,
    )
    rendered = json.dumps(package, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
