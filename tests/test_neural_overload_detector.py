import os
import tempfile
import pandas as pd
from src.neural_overload_detector_cli import run_neural_overload_detector

def test_sustained_near_failure():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 120},
        {"date": "2026-01-03", "exercise": "Sentadilla", "top_load": 102, "top_reps": 4, "top_rir": 1, "top_rpe": 9, "top_e1rm": 121},
        {"date": "2026-01-05", "exercise": "Sentadilla", "top_load": 104, "top_reps": 3, "top_rir": 1, "top_rpe": 9, "top_e1rm": 122},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_neural_overload_detector(path, tmpdir, window_sessions=3)
        daily = pd.read_csv(os.path.join(tmpdir, "neural_overload_daily.csv"))
        assert "SUSTAINED_NEAR_FAILURE" in daily["overload_flags"].iloc[-1]
        assert daily["overload_score"].iloc[-1] >= 25

def test_fixed_load_drift():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Press Banca", "top_load": 80, "top_reps": 8, "top_rir": 2, "top_rpe": 8, "top_e1rm": 95},
        {"date": "2026-01-03", "exercise": "Press Banca", "top_load": 80, "top_reps": 7, "top_rir": 2, "top_rpe": 8, "top_e1rm": 94},
        {"date": "2026-01-05", "exercise": "Press Banca", "top_load": 80, "top_reps": 6, "top_rir": 1, "top_rpe": 9, "top_e1rm": 92},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_neural_overload_detector(path, tmpdir, window_sessions=3)
        daily = pd.read_csv(os.path.join(tmpdir, "neural_overload_daily.csv"))
        assert "FIXED_LOAD_DRIFT" in daily["overload_flags"].iloc[-1]

def test_high_volatility():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Peso Muerto", "top_load": 150, "top_reps": 6, "top_rir": 2, "top_rpe": 8, "top_e1rm": 180},
        {"date": "2026-01-03", "exercise": "Peso Muerto", "top_load": 150, "top_reps": 4, "top_rir": 1, "top_rpe": 9, "top_e1rm": 175},
        {"date": "2026-01-05", "exercise": "Peso Muerto", "top_load": 150, "top_reps": 8, "top_rir": 2, "top_rpe": 8, "top_e1rm": 185},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_neural_overload_detector(path, tmpdir, window_sessions=3)
        daily = pd.read_csv(os.path.join(tmpdir, "neural_overload_daily.csv"))
        assert "HIGH_VOLATILITY" in daily["overload_flags"].iloc[-1]

def test_plateau_effort_rise():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Press Militar", "top_load": 75, "top_reps": 3, "top_rir": 3, "top_rpe": 7, "top_e1rm": 90},
        {"date": "2026-01-03", "exercise": "Press Militar", "top_load": 75, "top_reps": 3, "top_rir": 2, "top_rpe": 8, "top_e1rm": 90},
        {"date": "2026-01-05", "exercise": "Press Militar", "top_load": 75, "top_reps": 3, "top_rir": 1, "top_rpe": 9, "top_e1rm": 90},
        {"date": "2026-01-08", "exercise": "Press Militar", "top_load": 75, "top_reps": 3, "top_rir": 0, "top_rpe": 10, "top_e1rm": 90},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_neural_overload_detector(path, tmpdir, window_sessions=4)
        daily = pd.read_csv(os.path.join(tmpdir, "neural_overload_daily.csv"))
        assert "PLATEAU_EFFORT_RISE" in daily["overload_flags"].iloc[-1]

def test_aggregation_daily():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Sentadilla", "top_load": 100, "top_reps": 5, "top_rir": 1, "top_rpe": 9, "top_e1rm": 120},
        {"date": "2026-01-01", "exercise": "Press Banca", "top_load": 80, "top_reps": 8, "top_rir": 2, "top_rpe": 8, "top_e1rm": 95},
        {"date": "2026-01-03", "exercise": "Sentadilla", "top_load": 102, "top_reps": 4, "top_rir": 1, "top_rpe": 9, "top_e1rm": 121},
        {"date": "2026-01-03", "exercise": "Press Banca", "top_load": 80, "top_reps": 7, "top_rir": 2, "top_rpe": 8, "top_e1rm": 94},
        {"date": "2026-01-05", "exercise": "Sentadilla", "top_load": 104, "top_reps": 3, "top_rir": 1, "top_rpe": 9, "top_e1rm": 122},
        {"date": "2026-01-05", "exercise": "Press Banca", "top_load": 80, "top_reps": 6, "top_rir": 1, "top_rpe": 9, "top_e1rm": 92},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        run_neural_overload_detector(path, tmpdir, window_sessions=3)
        daily = pd.read_csv(os.path.join(tmpdir, "neural_overload_daily.csv"))
        # El 2026-01-05 debe tener score = suma de flags
        score = daily[daily['date'] == '2026-01-05']['overload_score'].iloc[0]
        assert score > 25

def test_advanced_sensitivity():
    df = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Press Militar", "top_load": 75, "top_reps": 3, "top_rir": 1, "top_rpe": 9, "top_e1rm": 90},
        {"date": "2026-01-03", "exercise": "Press Militar", "top_load": 75, "top_reps": 3, "top_rir": 1, "top_rpe": 9, "top_e1rm": 90},
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "exercise_day_summary.csv")
        df.to_csv(path, index=False)
        # Forzar advanced
        run_neural_overload_detector(path, tmpdir, window_sessions=2, min_sessions_advanced=2)
        daily = pd.read_csv(os.path.join(tmpdir, "neural_overload_daily.csv"))
        assert "SUSTAINED_NEAR_FAILURE" in daily["overload_flags"].iloc[-1]

if __name__ == "__main__":
    test_sustained_near_failure()
    test_fixed_load_drift()
    test_high_volatility()
    test_plateau_effort_rise()
    test_aggregation_daily()
    test_advanced_sensitivity()
    print("All tests passed.")
