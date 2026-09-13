# Upstream Synchronization

The derivative uses two remotes:

```text
origin   https://github.com/nakedfighter3d/OpenMontage.git
upstream https://github.com/calesthio/OpenMontage.git
```

Verify them before syncing:

```bash
git remote -v
git fetch origin
git fetch upstream
```

Integrate upstream through a review branch rather than force-pushing shared history:

```bash
git switch main
git pull --ff-only origin main
git switch -c chore/sync-upstream-YYYY-MM-DD
git merge --no-ff upstream/main
```

Resolve conflicts by preserving upstream behavior and reapplying the smallest
narrative extension. Then run the contract suite, inspect the diff, push the sync
branch, and merge it through a pull request:

```bash
python -m pytest tests/contracts/ -q
git diff --check upstream/main...HEAD
git push -u origin chore/sync-upstream-YYYY-MM-DD
```

Pay particular attention to the intentional extension seams:

- `pipeline_defs/narrative-movie.yaml`
- `skills/pipelines/narrative-movie/`
- the six narrative schemas in `schemas/artifacts/`
- `lib/narrative_contracts.py`
- narrative entries in `lib/checkpoint.py` and `schemas/artifacts/__init__.py`

Do not rebase or force-push `main`. Keep external knowledge repositories separate;
update their pinned or documented versions independently of upstream merges.
