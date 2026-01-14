
import sys
import os
import tempfile
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from neural_overload_detector_v2 import main

def run_detector(summary_path, out_dir):
    main(summary_path, out_dir)

def test_max_intent_variability_trigger():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 120},
        {"date": "2026-01-03", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 110},
        {"date": "2026-01-05", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 130},
        {"date": "2026-01-07", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 100},
        {"date": "2026-01-09", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 140},
        {"date": "2026-01-11", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 90},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_detector(path, tmpdir)
        lifts_path = os.path.join(tmpdir, "neural_overload_lifts.csv")
        print("lifts_path exists:", os.path.exists(lifts_path), "size:", os.path.getsize(lifts_path) if os.path.exists(lifts_path) else -1)
        with open(lifts_path, 'r') as f:
            print("lifts.csv raw (trigger):\n", f.read())
        lifts = pd.read_csv(lifts_path)
        if "MAX_INTENT_VARIABILITY" not in lifts["flag_type"].values:
            print("lifts.csv contents (trigger):\n", lifts)
        assert "MAX_INTENT_VARIABILITY" in lifts["flag_type"].values

def test_max_intent_variability_no_trigger():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 2, "top_rpe": 8, "top_e1rm": 120},
        {"date": "2026-01-03", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 2, "top_rpe": 8, "top_e1rm": 121},
        {"date": "2026-01-05", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 2, "top_rpe": 8, "top_e1rm": 122},
        {"date": "2026-01-07", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 2, "top_rpe": 8, "top_e1rm": 123},
        {"date": "2026-01-09", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 2, "top_rpe": 8, "top_e1rm": 124},
        {"date": "2026-01-11", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 2, "top_rpe": 8, "top_e1rm": 125},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_detector(path, tmpdir)
        lifts_path = os.path.join(tmpdir, "neural_overload_lifts.csv")
        if os.path.getsize(lifts_path) == 0 or os.path.getsize(lifts_path) <= 2:
            lifts = pd.DataFrame(columns=["date","exercise","flag_type","severity","evidence_json","recommendations"])
        else:
            lifts = pd.read_csv(lifts_path)
        if "MAX_INTENT_VARIABILITY" in lifts["flag_type"].values:
            print("lifts.csv contents (no trigger):\n", lifts)
        assert "MAX_INTENT_VARIABILITY" not in lifts["flag_type"].values

def test_cns_cost_rising_trigger():
    df = pd.DataFrame([
        # Base window (high RIR, low RPE)
        {"date": "2026-01-01", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 4, "top_rpe": 6, "top_e1rm": 100},
        {"date": "2026-01-02", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 4, "top_rpe": 6, "top_e1rm": 100},
        {"date": "2026-01-03", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 4, "top_rpe": 6, "top_e1rm": 100},
        {"date": "2026-01-04", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 4, "top_rpe": 6, "top_e1rm": 100},
        {"date": "2026-01-05", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 4, "top_rpe": 6, "top_e1rm": 100},
        {"date": "2026-01-06", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 4, "top_rpe": 6, "top_e1rm": 100},
        # Current window (low RIR, high RPE)
        {"date": "2026-01-07", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 0, "top_rpe": 10, "top_e1rm": 100},
        {"date": "2026-01-08", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 0, "top_rpe": 10, "top_e1rm": 100},
        {"date": "2026-01-09", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 0, "top_rpe": 10, "top_e1rm": 100},
        {"date": "2026-01-10", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 0, "top_rpe": 10, "top_e1rm": 100},
        {"date": "2026-01-11", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 0, "top_rpe": 10, "top_e1rm": 100},
        {"date": "2026-01-12", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 0, "top_rpe": 10, "top_e1rm": 100},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_detector(path, tmpdir)
        lifts_path = os.path.join(tmpdir, "neural_overload_lifts.csv")
        if os.path.getsize(lifts_path) == 0 or os.path.getsize(lifts_path) <= 2:
            lifts = pd.DataFrame(columns=["date","exercise","flag_type","severity","evidence_json","recommendations"])
        else:
            lifts = pd.read_csv(lifts_path)
        if "CNS_COST_RISING" not in lifts["flag_type"].values:
            print("lifts.csv contents (trigger):\n", lifts)
        assert "CNS_COST_RISING" in lifts["flag_type"].values

def test_cns_cost_rising_no_trigger():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 3, "top_rpe": 7, "top_e1rm": 100},
        {"date": "2026-01-03", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 3, "top_rpe": 7, "top_e1rm": 100},
        {"date": "2026-01-05", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 3, "top_rpe": 7, "top_e1rm": 100},
        {"date": "2026-01-07", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 3, "top_rpe": 7, "top_e1rm": 100},
        {"date": "2026-01-09", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 3, "top_rpe": 7, "top_e1rm": 100},
        {"date": "2026-01-11", "exercise": "Press Banca", "top_load": 80, "top_reps": 5, "top_rir": 3, "top_rpe": 7, "top_e1rm": 100},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_detector(path, tmpdir)
        lifts_path = os.path.join(tmpdir, "neural_overload_lifts.csv")
        if os.path.getsize(lifts_path) == 0 or os.path.getsize(lifts_path) <= 2:
            lifts = pd.DataFrame(columns=["date","exercise","flag_type","severity","evidence_json","recommendations"])
        else:
            lifts = pd.read_csv(lifts_path)
        if "CNS_COST_RISING" in lifts["flag_type"].values:
            print("lifts.csv contents (no trigger):\n", lifts)
        assert "CNS_COST_RISING" not in lifts["flag_type"].values

if __name__ == "__main__":
    test_max_intent_variability_trigger()
    test_max_intent_variability_no_trigger()
    test_cns_cost_rising_trigger()
    test_cns_cost_rising_no_trigger()
    print("All v2 flag tests passed.")
