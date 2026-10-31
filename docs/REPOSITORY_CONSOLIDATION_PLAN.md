# Repository consolidation inventory and plan

Snapshot: 2026-10-29, Asia/Kolkata. The working base is `origin/main` at `cfe1abbd09e006628f3116a552d3840361252eff` (PR #7), with audit work on `audit/codebase-stabilization`. Fetch completed before inspection. This is an inventory and recovery map, not a claim that another laptop was inspected or that backups exist off this machine.

## Preservation inventory

| Accessible checkout | Branch / HEAD | State observed before audit | Unique commits versus origin/main |
|---|---|---|---|
| `C:\ommd3076\Proejcts\nmit-hackathon` | main / `cfe1abb`; audit branch subsequently created at same commit | Clean tracked/untracked status | None |
| `C:\ommd3076\Proejcts\nmit-hackathon\.runtime\india-eta-implementation` | `codex/india-eta-integration` / `f50f9f7` | Clean | None; ancestor of main |
| `C:\ommd3076\Proejcts\nmit-hackathon\.runtime\india-eta-planning` | `codex/india-eta-integration-plan` / `819913e` | Clean | None; ancestor of main |

These are three worktrees of the same Git repository and use `https://github.com/ommd3076/silver-computing-machine.git`. A direct-child scan of `C:\ommd3076\Proejcts` found no other checkout with that remote. This is a bounded scan, not a claim that every disk or nested clone has been searched. Lenovo and Dell laptop local files, other users' worktrees, and editing activity are unavailable here.

The local branch `feat/india-eta-v2-real-backend` at `cc761b9` has four commits not in current main (`450194f`, `1f06ce0`, `93444f5`, `cc761b9`), including changes to Dell-owned `backend/india_eta/`. It is preserved and is not merged by this audit. `origin/feature/india-vqc4-run2` at `12ea0ac` is already an ancestor of main via PR #7. Open PR inventory is **unresolved**: `gh` is not installed and the GitHub public-page fetch was unavailable. Refreshed remote branches are visible with `git branch -a -vv`.

The accompanying [CONSOLIDATION-FILE-MANIFEST.csv](CONSOLIDATION-FILE-MANIFEST.csv) inventories SHA-256 and size for 711 tracked files present at the base (96,577,186 bytes), including tracked data, source, reports and artifacts. It is an integrity inventory, not a backup. Git commit `cfe1abb` and the retained local branch provide recovery for their tracked bytes; they do not back up ignored or uncommitted material. `_archive/`, `.runtime/`, environments, historical sources and other ignored paths remain untouched and are not comprehensively hashed. Ensure independent backups of unique laptop and ignored data before any consolidation or deletion. Working-file hashes can differ from Git blob bytes because `core.autocrlf=true`; see the audit's release blocker.

On each unavailable laptop, from each candidate checkout, run without exposing credentials:

```powershell
git rev-parse --show-toplevel
git remote -v
git branch -vv
git rev-parse HEAD
git worktree list --porcelain
git status --short --branch
git fetch origin --prune
git log --oneline origin/main..HEAD
Get-ChildItem artifacts -Recurse -File | Get-FileHash -Algorithm SHA256
```

Do not use `git clean`, reset, overwrite, move, or delete as part of inventory. Coordinate with active owners before touching their paths; this audit does not establish that an owner has stopped editing.

## Current map and ownership

| Area | Responsibility / owner boundary | Disposition |
|---|---|---|
| `frontend/` | Owner's frontend | Do not edit |
| `backend/`, `backend/india_eta/` | Dispatch/API and Dell's ETA integration | Active but divergent; coordinate with Dell before edits or merge |
| `experiments_india_vqc4/`, `artifacts/india_eta_vqc4_run2/` | Lenovo 4Q training, checkpoint and reproducibility evidence | Retain frozen; no retraining |
| `artifacts/run2_india/india_eta_vqc4_cpu_release_v1/` | Packaged 4Q CPU release with pinned manifest | Retain bytes and release provenance |
| `experiments_india_qml/`, `experiments_india_eta/` | Earlier training/recovery paths | Historical and reproducibility material; don't collapse |
| `data/`, `fixtures/`, `sources/`, `evidence/` | Data, deterministic fixtures and provenance | Preserve; split and leakage boundaries apply |
| `docs/`, `tests/`, `tools/`, `bootstrap/` | Contracts, verification and environment evidence | Audit separately; lockfiles may be machine-specific |

Recommend protected GitHub `main`, owner-assigned feature branches/worktrees and reviewed merges, versioned contracts, and one explicitly designated inference release after Dell and Lenovo agree on integration. Protection settings and owner agreement have not been verified. Current `main` ETA prediction defaults to a JSON fixture, not the 4Q release; these paths are not automatically interchangeable. Never substitute whole-delivery duration for road-arc travel time.

## Duplicate classification

The tracked-byte inventory found 23 SHA-256 duplicate groups with 76 total paths. Examples: 14 skill license files; 11 other skill license files; five preprocessing JSON copies; three copies each of baseline60, extended76, and the recovered GBDT. The groups are byte-identical in this working tree, not automatically redundant: release-bundle copies are necessary to make self-contained pinned packages and reproduced checkpoints are historical evidence. Other experiment folders and two-qubit versus four-qubit circuits are divergent implementations, not byte-identical duplicates. Generated outputs include plots, prediction tables, logs and archives; active source includes backend and experiment implementations. Classify each consumer and provenance before a removal proposal. No file was removed, moved or rewritten by this audit.

For recovery, keep the tracked commit, local ETA branch, tracked artifact manifest and existing ignored files. The CSV cannot restore contents: separately back up unique ignored files and other machines before any structural work. Prefer a versioned, hash-verified release bundle and documented authoritative pointer, but do not replace the existing releases or revise frozen manifests without Lenovo's review.
