"""Test execution evidence report generator."""

from pathlib import Path
import pytest
from tools.generate_execution_evidence import EvidenceBuilder

_root = Path(__file__).resolve().parent.parent


def test_generate_execution_evidence_builds_valid_report():
    builder = EvidenceBuilder(allow_cloud=False)
    report = builder.build_report()

    assert len(report.splitlines()) >= 200
    assert len(report.splitlines()) <= 500
    assert "DEBUGLEAF - QPIAI QUANTUM & OPT EXECUTION EVIDENCE REPORT" in report
    assert "SECTION 1: ENVIRONMENT AND PROVENANCE" in report
    assert "SECTION 2: REAL CLASSICAL GBDT INFERENCE" in report
    assert "SECTION 3: FOUR-FEATURE QUANTUM FEATURE MAP" in report
    assert "SECTION 4: CUSTOM QUANTUM CIRCUIT EXECUTION" in report
    assert "SECTION 5: HYBRID ETA CALCULATION" in report
    assert "SECTION 6: DISPATCH-RISK 2-QUBIT DECISION VQC" in report
    assert "SECTION 7: QPIAI OPT COMBINATORIAL QUBO" in report
    assert "SECTION 8: QAOA EXECUTION VIA QPIAI OPT" in report
    assert "SECTION 9: LIVE FASTAPI DISPATCH -> QPIAI OPT EXECUTION TRACE" in report
    assert "SECTION 10: SDK INTEGRATION AND QCLOUD PROVENANCE" in report
    assert "SECTION 11: FINAL VERIFICATION SUMMARY" in report
    assert "Overall Evaluation Verdict:  [PASS]" in report

    # Verify output file generation
    out_file = _root / "evidence" / "DEBUGLEAF_QPIAI_EXECUTION.txt"
    assert out_file.is_file()


def test_generate_live_execution_trace():
    builder = EvidenceBuilder(allow_cloud=False)
    live_report = builder.build_live_report()

    num_lines = len(live_report.splitlines())
    assert 20 <= num_lines <= 35, f"Live report line count {num_lines} not in [20, 35]"
    assert "DEBUGLEAF HYBRID QUANTUM FLEET DISPATCH - LIVE EXECUTION" in live_report
    assert "[DEBUGLEAF API]" in live_report
    assert "[DEBUGLEAF ETA]" in live_report
    assert "[QPIAI OPT]" in live_report
    assert "[QPIAI QUANTUM]" in live_report
    assert "[SOLVER]" in live_report
    assert "[VALIDATOR]" in live_report
    assert "[RESULT]" in live_report
    assert "QUBO constraint penalties applied" in live_report
    assert "Computed Dispatch Plan" in live_report
    assert "FastAPI TestClient" in live_report
    assert "Exhaustive Feasible Optimum" in live_report
    assert "STATUS: SUCCESS" in live_report

    out_file = _root / "evidence" / "DEBUGLEAF_LIVE_EXECUTION.txt"
    assert out_file.is_file()


def test_no_obsolete_judge_terminology_in_evidence_reports():
    q_file = _root / "evidence" / "DEBUGLEAF_QPIAI_EXECUTION.txt"
    l_file = _root / "evidence" / "DEBUGLEAF_LIVE_EXECUTION.txt"

    assert q_file.is_file()
    assert l_file.is_file()

    q_text = q_file.read_text(encoding="utf-8").lower()
    l_text = l_file.read_text(encoding="utf-8").lower()

    assert "judge" not in q_text, "Found 'judge' in DEBUGLEAF_QPIAI_EXECUTION.txt"
    assert "judge" not in l_text, "Found 'judge' in DEBUGLEAF_LIVE_EXECUTION.txt"
