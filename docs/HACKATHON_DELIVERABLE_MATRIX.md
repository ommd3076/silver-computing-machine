# Hackathon deliverable matrix

2026-10-29 snapshot, base `cfe1abb`. PASS applies only to the narrowly described evidence; PARTIAL indicates an implemented or historically tested slice with gaps. Historical reported runs are not runs performed by this audit. QML-01 requirements come from `sources/problem-extract.txt`.

| Requirement | Status | Evidence and limit |
|---|---|---|
| Vehicle-to-route assignment and ordered stops | PARTIAL | `backend/solver.py`, `backend/validator.py`; `docs/TERRA-V1-REPORT.md` reports tiny synthetic plans. No live fleet. |
| ETA and SLA risk | PARTIAL | `backend/india_eta/prediction.py` and `uncertainty.py` provide fixture inference and bounded uncertainty interfaces. Real source-domain calibrated SLA risk is not shown. |
| Financial exposure | PARTIAL | `backend/financial.py`, `docs/API-RUNTIME.md`: caller-supplied rates and local arithmetic only, not validated commercial rates. |
| Plan feasibility and complete coverage | PARTIAL | Independent recomputation in `backend/validator.py`; prior report describes small synthetic inputs, not real operations. |
| SLA violations | PARTIAL | Scenario replay in `backend/risk.py`; empirical supplied-world frequencies are not calibrated forecasts. |
| Prediction calibration | NOT VERIFIED | No validated India contractual-SLA calibration evidence found. |
| Solver quality and runtime | PARTIAL | Tiny exact-reference and synthetic benchmark evidence in `docs/TERRA-V1-REPORT.md`; no production-scale guarantee. |
| Classical versus quantum | PARTIAL | Prior matched synthetic comparisons and retrospective India ETA reports; no quantum advantage and no pristine 4Q holdout. |
| QpiAI Quantum local execution | PARTIAL | Prior SDK local statevector parity is documented in `RUN2_INDIA_QML_FINAL_TRAINING_REPORT.md`; this does not prove hardware use. |
| QpiAI Opt | PARTIAL | `docs/TERRA-V1-REPORT.md` reports local compilation and equivalence, not an authenticated Opt service solve. |
| QCloud | PARTIAL | In the earlier chat, a two-qubit illustrative VQC was saved and QCloud reported a local-browser 1,000-shot simulation. It is not connected to a validated dispatch decision and does not establish meaningful challenge integration, remote cloud simulation, or QPU execution. |
| Reproducible checkpoints | PARTIAL | Candidate, release and training artifacts are present; `PRETEST_FREEZE.json` and report record hashes. Windows line-ending conversion currently makes at least one packaged working-file hash differ from the manifest. |
| ETA-to-routing semantic compatibility | PARTIAL | `backend/india_eta/compatibility.py` rejects whole-delivery-to-road-arc mapping and `source_adapter.py` marks synthetic scenarios. No verified real-domain bridge. |

The 4Q release's validation-selected operational choice is **alpha=0**. Its candidate metrics are research evidence, not a deployed quantum improvement. The QpiAI product-use requirement asks for meaningful decision-connected invocation, not merely a circuit drawing or package import.
