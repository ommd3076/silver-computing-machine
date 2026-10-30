#!/usr/bin/env python3
"""Run and inspect the Classical GBDT Delivery ETA Model (scikit-learn).

Loads the frozen operational model:
  artifacts/run2_india/india_eta_vqc4_cpu_release_v1/gbdt_model.joblib

Evaluates:
  1. Frozen estimator hyperparameters and structure (59 features).
  2. Inference across reference test delivery scenarios.
  3. Real-world scenario simulation (Bangalore evening dinner rush).
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

_root = Path(__file__).resolve().parent.parent

# Auto-route to .venv Python if invoked from global Python
_venv_py_win = _root / ".venv" / "Scripts" / "python.exe"
_venv_py_posix = _root / ".venv" / "bin" / "python"
_target_py = _venv_py_win if _venv_py_win.exists() else _venv_py_posix

if _target_py.exists() and Path(sys.executable).resolve() != _target_py.resolve():
    proc = subprocess.run([str(_target_py), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=str(_root))
    sys.exit(proc.returncode)

import joblib
import numpy as np


def main() -> None:
    release_dir = _root / "artifacts" / "run2_india" / "india_eta_vqc4_cpu_release_v1"
    gbdt_path = release_dir / "gbdt_model.joblib"
    fixture_path = release_dir / "reference_fixture.json"
    schema_path = release_dir / "feature_schema.json"

    print("=" * 72)
    print("  DebugLeaf — Classical GBDT Machine Learning Model Runner")
    print("=" * 72)
    print(f"  * Artifact Path: {gbdt_path.relative_to(_root)}")
    print(f"  * Status:        DEPLOYED OPERATIONAL (alpha = 0.0 policy)")
    print(f"  * Engine:        scikit-learn {joblib.__version__} / HistGradientBoostingRegressor")
    print("=" * 72)

    # 1. Load Model & Schema
    t0 = time.perf_counter()
    model = joblib.load(gbdt_path)
    t_load = (time.perf_counter() - t0) * 1000.0

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    feature_names = schema["feature_names"]

    print(f"\n[1] Model Architecture & Deserialization:")
    print(f"    - Deserialization Time:  {t_load:.2f} ms")
    print(f"    - Estimator Class:       {model.__class__.__name__}")
    print(f"    - Input Features:        {model.n_features_in_} tabular features")
    print(f"    - Max Trees (max_iter):  {model.max_iter}")
    print(f"    - Learning Rate:         {model.learning_rate}")
    print(f"    - L2 Regularization:     {model.l2_regularization}")
    print(f"    - Min Samples Leaf:      {model.min_samples_leaf}")

    # 2. Reference Benchmark Verification
    print(f"\n[2] Executing Benchmark Verification (reference_fixture.json):")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    rows = fixture["rows"]
    expected = fixture["expected_predictions_min"]["gbdt_only_min"]

    X_bench = np.array([[row[col] for col in feature_names] for row in rows], dtype=np.float64)

    t1 = time.perf_counter()
    preds = model.predict(X_bench)
    t_infer = (time.perf_counter() - t1) * 1000.0

    labels = [
        "Short Delivery (Off-Peak / Sunny)",
        "Congested Urban Delivery (Rush Hour / Traffic Jam)",
        "Adverse Weather / Multi-Drop Delivery",
    ]

    for i in range(len(rows)):
        diff = abs(preds[i] - expected[i])
        status = "EXACT MATCH (PASS)" if diff < 1e-7 else "DEVIATION"
        print(f"    Scenario {i+1} [{labels[i]}]:")
        print(f"      * Predicted Duration: {preds[i]:.4f} minutes")
        print(f"      * Expected Ground:   {expected[i]:.4f} minutes")
        print(f"      * Diff:              {diff:.2e} min -> [{status}]")

    print(f"    - Batch Inference Latency: {t_infer:.2f} ms for {len(rows)} samples ({t_infer / len(rows):.3f} ms/sample)")

    # 3. Custom Real-World Simulation
    print(f"\n[3] Real-World Delivery Scenario Simulation:")
    print("    Parameters: Bangalore (BANG), 4.2 km distance, Dinner Rush, High Traffic, Motorcycle")
    
    custom_sample = {name: 0.0 for name in feature_names}
    custom_sample["haversine_distance_km"] = 4.2
    custom_sample["departure_hour"] = 20.0  # 8 PM
    custom_sample["day_of_week"] = 4.0      # Friday
    custom_sample["is_weekend"] = 0.0
    custom_sample["is_rush_hour"] = 1.0
    custom_sample["is_dinner_rush"] = 1.0
    custom_sample["delivery_person_age_imp"] = 28.0
    custom_sample["delivery_person_ratings_imp"] = 4.8
    custom_sample["order_to_pickup_min_imp"] = 12.0
    custom_sample["vehicle_condition"] = 2.0
    custom_sample["multiple_deliveries_imp"] = 1.0
    custom_sample["traffic_density_ordinal_imp"] = 2.0  # High
    custom_sample["traffic_density_clean_High"] = 1.0
    custom_sample["weather_clean_imp_Sunny"] = 1.0
    custom_sample["type_of_vehicle_clean_motorcycle"] = 1.0
    custom_sample["city_type_clean_imp_Metropolitian"] = 1.0
    custom_sample["city_code_BANG"] = 1.0

    X_custom = np.array([[custom_sample[col] for col in feature_names]], dtype=np.float64)
    pred_custom = float(model.predict(X_custom)[0])

    print(f"    -----------------------------------------------------")
    print(f"    --> PREDICTED CLASSICAL ETA: {pred_custom:.1f} MINUTES ({pred_custom:.2f} min)")
    print(f"    -----------------------------------------------------")
    print(f"\n[OK] Classical model execution completed successfully.\n")


if __name__ == "__main__":
    main()
