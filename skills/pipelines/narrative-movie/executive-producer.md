# Executive Producer — Narrative Movie Pipeline

Use this profile for dramatic scenes and short narrative films whose shots must form an editable scene, not merely a collection of attractive clips.

## Operating contract

1. Read `pipeline_defs/narrative-movie.yaml` and run the standard provider preflight.
2. Initialize the normal OpenMontage project workspace and preserve checkpoints, cost tracking, decision logs, and human gates.
3. Execute the manifest serially. Never merge dramaturgy, continuity validation, prompt compilation, take QA, and picture editing into one prose pass.
4. Treat `scene_intent`, `continuity_bible`, and `shot_plan` as provider-independent source truth.
5. Stop after `prompt_compile` by default for the first vertical slice. Paid generation requires the prompt-package gate plus explicit user approval.
6. If an external skill in `external-skills.yaml` is absent, report the missing layer. Do not replace it with a large improvised prompt or silently install an overlapping skill suite.

## Cross-stage gates

- Dramaturgy answers what happens and why; it does not choose lenses or providers.
- Scene design establishes identity, physical space, and the active axis before coverage.
- Coverage gives every shot an entrance state, exit state, edit handles, and a neighboring boundary.
- Continuity findings state the reason, risk, exception status, and repair options. Conventions are defaults, not laws.
- Prompt compilation may change expression for a provider but not the approved filmmaking intent.
- Take QA judges actual generated evidence and selects usable ranges; an API success is not a passed take.
- Picture editing is a new creative judgment based on available performances, not execution of the pre-edit plan by rote.

## Cost discipline

Never spend API credits during a plumbing or contract test. When generation is approved, announce the exact tool, provider, model, estimated unit cost, and whether it is a sample or batch. Begin with the smallest representative sample.

