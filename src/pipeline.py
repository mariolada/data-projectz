from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from set_classifier_pipeline import enrich_and_summarize_sets


# ----------------------------
# Validación / carga
# ----------------------------
def load_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {p.resolve()}")
    return pd.read_csv(p)


def require_columns(df: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[{name}] Faltan columnas obligatorias: {missing}")


def coerce_numeric(df: pd.DataFrame, cols: list[str], name: str) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if out[cols].isna().any().any():
        bad = out[out[cols].isna().any(axis=1)].head(5)
        raise ValueError(
            f"[{name}] Hay valores no numéricos o nulos tras convertir tipos en {cols}. "
            f"Ejemplos:\n{bad}"
        )
    return out


def normalize_dates(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    out = df.copy()
    out[col] = pd.to_datetime(out[col], errors="coerce")
    if out[col].isna().any():
        bad = out[out[col].isna()].head(5)
        raise ValueError(f"Fechas inválidas en columna '{col}'. Ejemplos:\n{bad}")
    return out.sort_values(col).reset_index(drop=True)


# ----------------------------
# Intensidad RPE/RIR
# ----------------------------
def validate_intensity(df: pd.DataFrame, tol: float = 0.75) -> pd.DataFrame:
    out = df.copy()
    out["rpe_from_rir"] = 10 - out["rir"]
    out["rpe_diff"] = (out["rpe"] - out["rpe_from_rir"]).abs()
    out["coherencia_rpe_rir"] = out["rpe_diff"] <= tol
    return out


# ----------------------------
# Métricas por fila
# ----------------------------
def compute_row_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["volume"] = out["sets"] * out["reps"] * out["weight"]

    # e1RM (Epley)
    out["e1rm"] = out["weight"] * (1.0 + out["reps"] / 30.0)

    # Esfuerzo (más alto = más cerca del fallo)
    # Si tienes RIR: effort = 10 - RIR (equivalente a RPE teórico)
    out["effort"] = 10 - out["rir"]

    return out


def add_weighted_rir_per_day(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def _wavg(g: pd.DataFrame) -> float:
        w = g["volume"].to_numpy()
        x = g["rir"].to_numpy()
        if np.all(w == 0):
            return float(np.mean(x))
        return float(np.average(x, weights=w))

    rir_w = out.groupby("date", group_keys=False).apply(_wavg, include_groups=False)
    out["rir_weighted_day"] = out["date"].map(rir_w)

    return out


# ----------------------------
# Agregaciones
# ----------------------------
def aggregate_daily_exercise(df: pd.DataFrame) -> pd.DataFrame:
    # Por día y ejercicio: volumen y mejor e1RM del día para ese ejercicio
    return (
        df.groupby(["date", "exercise"], as_index=False)
        .agg(
            volume=("volume", "sum"),
            e1rm_max=("e1rm", "max"),
            effort_mean=("effort", "mean"),
            rir_w=("rir_weighted_day", "first"),
        )
        .sort_values(["date", "exercise"])
        .reset_index(drop=True)
    )


def round_columns(df, decimals=3):
    """Redondea todas las columnas numéricas de un DataFrame a un número fijo de decimales."""
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns
    df[numeric_cols] = df[numeric_cols].round(decimals)
    return df


def aggregate_daily_total(df: pd.DataFrame, key_lifts: list[str]) -> pd.DataFrame:
    daily = (
        df.groupby("date", as_index=False)
        .agg(
            volume=("volume", "sum"),
            effort_mean=("effort", "mean"),
            rir_weighted=("rir_weighted_day", "first"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )

    # Performance Index basado en key lifts
    keylift_data = df[df["exercise"].str.lower().isin(key_lifts)].copy()
    baseline_e1rm = keylift_data.groupby("exercise")["e1rm"].transform("mean")
    keylift_data.loc[:, "keylift_index"] = keylift_data["e1rm"] / baseline_e1rm

    performance_index = (
        keylift_data.groupby("date")["keylift_index"].mean().rename("performance_index")
    )

    daily = daily.merge(performance_index, on="date", how="left")
    return daily


def add_rolling_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    out = daily.copy().sort_values("date").reset_index(drop=True)

    # Rolling sums (carga aguda/crónica)
    out["volume_7d"] = out["volume"].rolling(window=7, min_periods=3).sum()
    out["volume_28d"] = out["volume"].rolling(window=28, min_periods=10).sum()

    # ACWR clásico (7d / 28d)
    out["acwr_7_28"] = out["volume_7d"] / out["volume_28d"]

    # Tendencias simples basadas en Performance Index
    out["performance_7d_mean"] = out["performance_index"].rolling(window=7, min_periods=3).mean()
    out["volume_7d_mean"] = out["volume"].rolling(window=7, min_periods=3).mean()

    return out


def aggregate_weekly_from_daily(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy().sort_values("date").reset_index(drop=True)
    d["week_start"] = d["date"].dt.to_period("W").apply(lambda r: r.start_time)

    weekly_load = (
        d.groupby("week_start", as_index=False)
        .agg(
            days=("date", "count"),
            volume_week=("volume", "sum"),
            effort_week_mean=("effort_mean", "mean"),
            rir_week_mean=("rir_weighted", "mean"),
        )
        .sort_values("week_start")
        .reset_index(drop=True)
    )

    # Monotony y strain protegidos
    def _monotony(g: pd.DataFrame) -> float:
        if len(g) < 4:
            return np.nan
        mu = float(g["volume"].mean())
        sd = float(g["volume"].std(ddof=0))
        if sd == 0:
            return np.nan
        return mu / sd

    mono = d.groupby("week_start", group_keys=False).apply(_monotony)
    weekly_load["monotony"] = weekly_load["week_start"].map(mono)

    # Strain protegido
    weekly_load["strain"] = weekly_load["volume_week"] * weekly_load["monotony"]

    return round_columns(weekly_load)


# ----------------------------
# Sueño + flags
# ----------------------------
def merge_sleep(daily: pd.DataFrame, sleep: pd.DataFrame) -> pd.DataFrame:
    """
    Merge daily aggregations con sleep data.
    Si sleep.csv contiene 'perceived_readiness' (0-10), se incluye.
    Si no, se crea la columna con NaN (para rellenar luego manualmente o desde UI).
    """
    s = sleep.copy()
    s = normalize_dates(s, "date")

    out = daily.merge(s, on="date", how="left")
    
    # Si no existe perceived_readiness en sleep.csv, crear columna vacía
    if 'perceived_readiness' not in out.columns:
        out['perceived_readiness'] = np.nan

    # Flag fatiga robusto: volumen alto (P75) + sueño bajo (P25)
    # (se calcula sobre días con sueño disponible)
    tmp = out.dropna(subset=["sleep_hours"])
    if len(tmp) >= 8:
        p75_v = tmp["volume"].quantile(0.75)
        p25_s = tmp["sleep_hours"].quantile(0.25)
        out["fatigue_flag"] = (out["volume"] >= p75_v) & (out["sleep_hours"] <= p25_s)
    else:
        out["fatigue_flag"] = False

    return out


# ----------------------------
# Pipeline
# ----------------------------
def run_pipeline(
    training_path: str,
    sleep_path: str,
    out_dir: str,
    key_lifts: list[str],
) -> None:
    out_dir = str(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Load
    training = load_csv(training_path)
    sleep = load_csv(sleep_path)

    # Validate structure
    require_columns(training, ["date", "exercise", "sets", "reps", "weight", "rpe", "rir"], "training")
    require_columns(sleep, ["date", "sleep_hours", "sleep_quality"], "sleep")

    # Normalize
    training = normalize_dates(training, "date")
    sleep = normalize_dates(sleep, "date")

    # Types
    training = coerce_numeric(training, ["sets", "reps", "weight", "rpe", "rir"], "training")
    sleep = coerce_numeric(sleep, ["sleep_hours", "sleep_quality"], "sleep")

    # Basic sanity
    if not training["rir"].between(0, 10).all():
        raise ValueError("RIR fuera de rango (0–10) en training.")
    if not training["rpe"].between(1, 10).all():
        raise ValueError("RPE fuera de rango (1–10) en training.")

    # Enrich
    training = validate_intensity(training, tol=0.75)
    training = compute_row_metrics(training)
    training = add_weighted_rir_per_day(training)

    # === CLASIFICACIÓN AUTOMÁTICA DE SETS ===
    sets_processed, exercise_day_summary = enrich_and_summarize_sets(training, out_dir)

    # Aggregations
    daily_ex = aggregate_daily_exercise(training)
    daily = aggregate_daily_total(training, key_lifts)
    daily = add_rolling_metrics(daily)
    daily = merge_sleep(daily, sleep)
    weekly = aggregate_weekly_from_daily(daily)

    # Redondear resultados antes de guardar
    training = round_columns(training)
    daily_ex = round_columns(daily_ex)
    daily = round_columns(daily)
    weekly = round_columns(weekly)

    # Save outputs
    training.to_csv(Path(out_dir, "training_enriched.csv"), index=False)
    daily_ex.to_csv(Path(out_dir, "daily_exercise.csv"), index=False)
    daily.to_csv(Path(out_dir, "daily.csv"), index=False)
    weekly.to_csv(Path(out_dir, "weekly.csv"), index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Pipeline de análisis de rendimiento deportivo.")
    parser.add_argument("--training", required=True, help="Ruta al archivo training.csv")
    parser.add_argument("--sleep", required=True, help="Ruta al archivo sleep.csv")
    parser.add_argument("--out", required=True, help="Directorio de salida para los archivos procesados")
    parser.add_argument("--key_lifts", required=False, default="", help="Lista de ejercicios clave separados por comas")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("Verificando columnas en el archivo de entrenamiento...")
    training_df = pd.read_csv(args.training)
    print("Columnas detectadas en training.csv:", training_df.columns.tolist())

    key_lifts = [lift.strip().lower() for lift in args.key_lifts.split(",") if lift.strip()]

    run_pipeline(
        training_path=args.training,
        sleep_path=args.sleep,
        out_dir=args.out,
        key_lifts=key_lifts
    )

    if key_lifts:
        print(f"Ejercicios clave: {', '.join(key_lifts)}")
