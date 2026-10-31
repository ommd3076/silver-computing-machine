# Full system audit — bounded evidence snapshot

2026-10-29, Asia/Kolkata. Branch `audit/codebase-stabilization`, base `cfe1abb`. This is a bounded inspection, not a comprehensive penetration test or evidence of operational deployment. See [consolidation inventory](REPOSITORY_CONSOLIDATION_PLAN.md), [tracked-file hashes](CONSOLIDATION-FILE-MANIFEST.csv), and [deliverable matrix](HACKATHON_DELIVERABLE_MATRIX.md).

## Prioritized findings

| Severity | Finding and direct evidence | Impact / next action |
|---|---|---|
| P1 | The checked-out 4Q release circuit has Git `i/lf w/crlf` under `core.autocrlf=true`, while the release manifest pins LF byte size and SHA-256. `artifacts/run2_india/india_eta_vqc4_cpu_release_v1/circuit.py` is 30,294 bytes in this checkout vs manifest's 29,701. The release loader checks size and SHA before loading. | A normal Windows checkout can reject an otherwise unchanged release. A narrow `.gitattributes` rule was added and verified for future checkouts; it does not rewrite the existing working file. Use the intact ZIP for this checkout and coordinate with Lenovo before refreshing the extracted copy. Do not weaken integrity checks or rewrite frozen evidence. |
| P1 | `backend/india_eta/prediction.py` defaults to the JSON linear fixture; `backend/india_eta/api.py` routes requests to it. The separate 4Q release is not wired to this main-branch API. Dell's local v2 implementation is on a separate four-commit branch. | The presence of the model bundle does not establish an integrated trained ETA backend. Coordinate contract, artifact trust and ownership before merging or asserting end-to-end behavior. |
| P1 | `backend/india_eta/compatibility.py` rejects `whole_delivery_time` for road arcs and returns at most `scenario_only` because no trusted uncertainty registry is wired; `source_adapter.py` explicitly allows synthetic overlays. | Current data does not validate road-edge deployment or calibrated fleet risk. Maintain this boundary. |
| P1 (deployment boundary) | `backend/auth.py` defaults to unauthenticated `local`; token mode is an explicitly documented localhost prototype. | Do not expose the service to a network or claim production authorization. Token mode does not provide tenant isolation. |
| P2 | `docs/API-RUNTIME.md` says VQC rejects `hard_window` while the later `docs/TERRA-V1-REPORT.md` records support and targeted checks. | Conflicting documentation can mislead integration; verify implementation and tests with Dell before choosing the canonical contract. |
| P2 | The release loader calls `joblib.load` only after pinning and hash checks; resume training uses `torch.load(..., weights_only=False)`. | Hashes prove equality to pinned bytes, not that a maliciously substituted trusted release is safe. Only execute trusted provenance; do not accept uploaded/user-selected model files. |
| P2 | Legion environment report and lock record absolute Windows paths and one machine's environment. Bundled release has pinned NumPy, sklearn and joblib, while backend and SDK environments differ. | Paths are historical, not portable setup instructions; separate reproducible platform locks and verify installation before making claims. |
| P2 | Historical report `RUN2_INDIA_INDEPENDENT_ACCEPTANCE_REPORT.md` describes an earlier partial stage; `RUN2_INDIA_QML_FINAL_TRAINING_REPORT.md` describes a later completed 4Q release. | Label report chronology; don't silently replace historical evidence or treat earlier status as current. |

## STRIDE and trust boundaries

Client -> localhost HTTP API -> server-side validation/auth -> solver and SQLite -> independently validated plan; separate trusted filesystem -> hash-pinned release loader -> model. The boundary between food-delivery ETA and road routing is explicitly restricted.

| Category | Evidence / remaining risk |
|---|---|
| Spoofing | Default local auth is disabled. Optional token checks and role allowlists exist; identity and tenant controls remain prototype-level. |
| Tampering | Independent plan validator, server-bound model identity and release hashes exist. Hash trust roots and workspace permissions remain critical. |
| Repudiation | ETA controller records audit/version information in SQLite; tamper-evident external audit and production identity are not established. |
| Information disclosure | Errors use bounded messages; SQLite/model data and local paths are sensitive. A full secret scan and deployment security review were not completed. |
| Denial of service | Input and solver/job budgets exist; timeouts suppress publication but Python threads may continue. Production load behavior and multiprocess limits are unverified. |
| Elevation | Role policy and approval principal guard exist; local mode and lack of tenant filtering preclude production authorization claims. |

Inspect `backend/jobs.py`, `backend/india_eta/controller.py`, `backend/india_eta/jobs.py`, `backend/india_eta/api.py` and `backend/india_eta/store.py` for cancellation, SQLite transactions, idempotency, approval, and replay guards. Prior integration evidence in `INDIA_ETA_INTEGRATION_REPORT.md` is historical; this audit did not independently re-execute its entire stress suite or establish correctness under concurrent multi-process deployment.

## RUN2 evidence and methodology

`RUN2_INDIA_QML_FINAL_TRAINING_REPORT.md`, the release manifest, `PRETEST_FREEZE.json`, training progress and checkpoints record 60- and 76-angle models, CPU training and independent reproduction. Manifest and source inspection confirm operational `alpha=0`; this is a GBDT-only fallback. Reported trained-checkpoint QpiAI parity is historical local-simulator evidence, not cloud/QPU. The 4Q test is explicitly retrospective: the test partition had been opened earlier. Historical metrics remain unchanged. Hashes and reports alone cannot prove training execution or independent reload in this environment.

The incoming bundle contains a pinned loader and data-only checkpoint files; `joblib` is executable deserialization and must remain trusted-only. The ZIP SHA matches the frozen value and all 12 manifest-listed ZIP payloads match; 11 of 12 manifest-listed directory payloads match. Only the directory `circuit.py` differs, and in-memory CRLF-to-LF conversion matches both the pinned hash and the Git blob. The ZIP itself is intact. Separate CPU and accelerator dependency environments and the reported Legion measurements do not establish performance on this host. No new training, held-out scoring, paid jobs, deployment or model promotion was performed.

## Checks executed in this audit

- Luna ran `.venv-sdk/Scripts/python.exe -m pytest tests/test_india_vqc4_circuit.py -q -rs -p no:cacheprovider`, with bytecode writes disabled: **6 passed, 2 skipped**, 13.83 s; the skips require Torch. This is local circuit test evidence, not a trained-model release acceptance.
- A combined circuit and release run in `.venv` yielded **5 passed, 3 skipped, 4 failed**, 3.60 s. Release tests failed on missing `joblib`; Torch and QpiAI cases skipped. The environment cannot establish release-loader success or failure. The report's `.runtime/run2` environment is absent here.
- The worker independently checked both candidate checkpoint hashes, release ZIP hash and all 12 ZIP payload hashes; it checked directory payload hashes and found the single LF issue described above. The alpha policy is 0.0.
- Luna added only `.gitattributes` for the release circuit with `text eol=lf`. `git check-attr` showed the rule applied. A temporary-index `git checkout-index` extraction with `core.autocrlf=true` produced 29,701 bytes and SHA-256 `801468f544e25ae913c26e1f2131cf5f88b384b8495172da62be9051d5a96ba0`, matching the frozen manifest. A clone-based verification was blocked by an MSYS `NtCreateDirectoryObject` access-denied error. Existing frozen files were not rewritten; their current directory remains affected.
- A bounded literal-pattern search for private-key headers and quoted high-entropy credential assignments in backend, 4Q code, tools, bootstrap, release directory and `.env.example` returned no paths. It excluded JSON, CSV, Parquet, notebooks and lockfiles; it is not a complete secret scan or assurance that no credential exists.
- The only performance results inspected were the historical CPU/GPU microprofile in `RUN2_INDIA_QML_FINAL_TRAINING_REPORT.md`; no new workload profile was run. No optimization or speedup claim is made.

## Scope and remaining checks

The tracked manifest is an inventory rather than an independent backup. Open PR discovery, cross-laptop inventory, broad secret and dependency vulnerability scanning, multi-process concurrency, full performance profiling and full current API smoke remain incomplete. Preserve all frozen experiments and coordinate Dell overlap before implementing a backend fix. No frontend changes or repository structure cleanup were made. Only one substantive failure/repair/recheck cycle was completed here; the three-cycle V1 target is not satisfied by this audit.
