# Narrative Prompt Compilers and ComfyUI Workflow Contracts

Narrative Movie Production sends every video-generation job through a premade
ComfyUI API workflow. OpenMontage does not select, call, price, or inspect any model
service that may exist inside that workflow. It supplies only inputs explicitly
declared by the workflow owner and retrieves the workflow's declared video output.

The prompt compiler still needs a prompt dialect. `minimax-h3` and `wan3` describe
how filmmaking intent is worded; they are not execution providers. Both compile to
the same opaque `comfyui_video` transport.

Implementation: `lib/narrative_prompt_compilers.py`

Dry-run CLI: `scripts/compile_narrative_prompts.py`

## Workflow contract

Each premade workflow has a small sidecar JSON file:

```json
{
  "version": "1.0",
  "id": "my-video-workflow",
  "workflow_path": "local/workflows/video-api.json",
  "output_node": "99",
  "mode": "text_to_video",
  "inputs": {
    "prompt": {"node_id": "10", "input_name": "text"},
    "duration_seconds": {
      "node_id": "20",
      "input_name": "duration",
      "accepted_values": [5, 10]
    }
  }
}
```

The workflow remains the authority. If it exposes only `prompt`, OpenMontage changes
only that input. Standard values include `negative_prompt`, `duration_seconds`,
`aspect_ratio`, and `generate_audio`; contracts may declare any other semantic name
needed by the premade workflow. Per-shot values for those inputs are supplied through
`--workflow-values`. Unexposed graph settings remain untouched. Required values,
bindings to missing nodes, and missing input names fail before ComfyUI queues the job.

The contract records no API endpoint, remote model ID, pricing, checkpoint path, or
node implementation. `model` in the resulting prompt package is a workflow identity
(`workflow:<contract-id>`), not a claim about what runs inside it.

## Creative data boundary

The compiler reads narrative purpose, subjects, exact dialogue, blocking,
performance, camera intent, direction, eyelines, entrance/exit state, edit handles,
adjacent edit boundaries, and the optional global continuity bible. It never invents
or revises those decisions.

Dialogue is structured on the shot as `speaker_id`, `text`, and `language`, so the
compiler cannot recover or paraphrase a line from action prose. The H3 dialect emits
the three-field audiovisual structure and `<d>` dialogue tags. The WAN 3 dialect
emits a continuous-shot prompt and, when the workflow exposes it, a negative prompt.

Logical reference asset IDs stay in `reference_bindings`. Their resolved local paths
or other exact values go into named per-shot workflow values after the actual
workflow contract is registered; no model-specific reference field is hard-coded in
OpenMontage.

## Duration behavior

`duration_seconds` in the shot plan is the intended edit duration. A workflow
contract may omit duration entirely or declare its accepted values. When the nearest
valid generated duration is longer, compilation records the surplus as removable
edit-handle material. It never changes the planned cut length silently.

## Dry-run usage

```bash
python3 scripts/compile_narrative_prompts.py \
  --shot-plan examples/narrative-dialogue-dry-run/shot_plan.json \
  --continuity-report examples/narrative-dialogue-dry-run/continuity_report.json \
  --continuity-bible examples/narrative-dialogue-dry-run/continuity_bible.json \
  --prompt-dialect minimax-h3 \
  --workflow-contract examples/narrative-dialogue-dry-run/workflow_contract.minimax-h3.json
```

Use `--prompt-dialect wan3` with the appropriate WAN workflow contract. The checked-in
contracts are interface examples; replace their paths, node IDs, input names,
accepted values, and output node with the exact values from the premade API workflows
on the local system.

## Local acceptance gate

1. Export each premade workflow in ComfyUI API format.
2. Create its sidecar contract from the inputs that already exist in that workflow.
3. Run compilation and inspect the final patched workflow in a no-generation test.
4. Start ComfyUI and generate only `SH001` first.
5. Verify the returned video for identity, left/right geography, eyelines, prop state,
   audio, and edit handles before authorizing the remaining shots.
6. Record the result as a take and send it to take QA. A completed ComfyUI job is not
   automatically an editorially usable take.

This keeps the repository reproducible and leaves machine-specific workflow files,
custom nodes, credentials, and model/service choices under local ComfyUI control.
