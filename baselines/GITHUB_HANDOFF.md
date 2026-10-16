# Vivaan's COMP1110 contribution: GitHub handoff

## Publication status

This contribution is prepared in an authenticated checkout of
`https://github.com/Yerasik/save-scumming.git` on
`vivaan/synthetic-data-rho` for review through the accompanying pull request.
The existing `main` checkout contains the team's two project-plan files, which
are preserved unchanged. No existing simulation loader is present to integrate
against; the supplied baseline loader and shared field contract are tested here.
A real Path of Exile snapshot remains pending H5.

## Files to copy

The supplied archive has only `data/synthetic/` and `baselines/`. Copy these
into the repository root, preserving the spelling `synthetic` (not `sythetic`).
If a path already contains a teammate's work, review the diff before replacing it.
Do not copy any `__pycache__/` directory or `.pyc` file. Folder-local `.gitignore`
files also exclude future caches.

## Finished changes

- Frozen existing JSON field names and kept all original session IDs.
- Corrected C to vary only E3's retry time (5/20/60/120 seconds).
- Regenerated 24 sessions, including an eight-event mixed known/Beta fixture.
- The Beta event uses `odds_type: "beta"`, `alpha: 1`, `beta: 49`, and no `p`.
- Added 40 explicitly fabricated `dummy_sessions.csv` rows and provenance metadata.
- Added `session_id` to all four rho CSVs without renaming previous columns.
- Added code explanations, loader guidance, and 16 regression checks.
- Made generated JSON use LF on Windows as well as Unix for byte-identical regeneration.
- No real PoE snapshot is claimed: that remains for H5 after source/league/date
  and currency units are agreed.

## Commands after copying into an authenticated clone

Run these in the repository root. `python` should refer to Python 3.10 or later.
The CLI and tests use only the standard library.

```bash
git switch -c vivaan/synthetic-data-rho
python -B data/synthetic/generate_synthetic.py
python -B -m unittest discover -s baselines -p 'test_*.py' -v
git status --short
git add data/synthetic baselines
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
```

Review that last listing: it must not contain `__pycache__` or `.pyc` files.
Then commit and push your feature branch (do not push directly to main):

```bash
git commit -m "Add synthetic sessions, plotting fixtures and rho baseline"
git push -u origin vivaan/synthetic-data-rho
```

Open a pull request against the repository's default branch using GitHub.
If your account cannot push, ask the owner for access or use your own fork;
the destination remote will differ for a fork. Do not paste tokens into chat.

## Suggested pull-request description

Title: Add synthetic sessions, plotting fixtures and rho baseline

Summary:

- Add reproducible toy/A/C/D/B inputs and one Beta-odds session (24 total).
- Change only E3 in Experiment C; preserve the shared JSON field contract.
- Add 40 fake plotting rows, clearly marked as not experimental findings.
- Add session identity to rho CSV outputs and explain the baseline assumptions.
- Include commented code and 16 passing tests; exclude Python caches.

Validation:

`python -B -m unittest discover -s baselines -p 'test_*.py' -v`

Integration note: Yusif's loader must branch on `odds_type` before accessing
`p`. Real PoE data and simulation findings are deliberately not included.
