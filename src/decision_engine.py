import pandas as pd
import numpy as np
from pathlib import Path
import argparse


REQUIRED_DAILY_COLUMNS = [
    "date", "volume", "volume_7d", "volume_28d", "acwr_7_28",
    "rir_weighted", "effort_mean", "performance_index", "performance_7d_mean",
    "sleep_hours", "sleep_quality", "fatigue_flag"
]


def load_processed_daily(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_DAILY_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en daily.csv: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ----------------------------
# Scores robustos por tramos
# ----------------------------
def score_sleep_hours(hours: float) -> float:
    # Personalizable luego; por ahora: 6.0 -> 0, 7.5 -> 1
    if pd.isna(hours):
        return np.nan
    return float(np.clip((hours - 6.0) / (7.5 - 6.0), 0, 1))


def score_sleep_quality(q: float) -> float:
    if pd.isna(q):
        return np.nan
    return float(np.clip((q - 1) / 4, 0, 1))


def score_performance(pi: float) -> float:
    # 0.98 -> 0, 1.00 -> 0.5, 1.02 -> 1
    if pd.isna(pi):
        return np.nan
    return float(np.clip((pi - 0.98) / (1.02 - 0.98), 0, 1))


def score_trend(pi: float, pi7: float) -> float:
    # Mejora si hoy estás por encima de tu media 7d
    if pd.isna(pi) or pd.isna(pi7):
        return 0.5  # neutro si no hay histórico
    delta = pi - pi7
    # -0.01 -> 0, 0.0 -> 0.5, +0.01 -> 1
    return float(np.clip((delta + 0.01) / 0.02, 0, 1))


def score_acwr(x: float) -> float:
    # ACWR 7/28: por tramos (más realista)
    if pd.isna(x):
        return 0.5

    # Zona óptima
    if 0.8 <= x <= 1.3:
        return 1.0

    # Demasiado alto (pico de carga)
    if 1.3 < x <= 1.5:
        # baja 1.0 -> 0.6
        return float(1.0 - (x - 1.3) * (0.4 / 0.2))
    if x > 1.5:
        # baja 0.6 -> 0.0 hasta 2.0
        return float(np.clip(0.6 - (x - 1.5) * (0.6 / 0.5), 0, 0.6))

    # Demasiado bajo (posible falta de estímulo)
    if 0.6 <= x < 0.8:
        # baja 1.0 -> 0.7
        return float(0.7 + (x - 0.6) * (0.3 / 0.2))
    # <0.6
    return 0.6


def score_rir_for_fatigue(rir: float) -> float:
    """
    Este score refleja FATIGA (readiness), no estímulo.
    RIR muy bajo sostenido = más fatiga => peor score.
    RIR alto NO penaliza readiness (solo indica poco estímulo).
    """
    if pd.isna(rir):
        return 0.5

    # Fatiga alta si <= 0.5
    if rir <= 0.5:
        return 0.0

    # Zona “productiva” sin ir al límite: 1–3 => score alto
    if 1.0 <= rir <= 3.0:
        return 1.0

    # Entre 0.5 y 1.0: escala 0 -> 1
    if 0.5 < rir < 1.0:
        return float((rir - 0.5) / 0.5)

    # >3: no penaliza readiness (neutro-alto)
    return 0.8


def flag_understim(rir: float, effort: float) -> bool:
    # Poco estímulo si RIR alto y esfuerzo bajo/moderado
    if pd.isna(rir) or pd.isna(effort):
        return False
    return (rir >= 4.0) and (effort <= 6.5)


def flag_high_strain_day(rir: float, effort: float) -> bool:
    # Día muy exigente: cerca del fallo + esfuerzo alto
    if pd.isna(rir) or pd.isna(effort):
        return False
    return (rir <= 1.0) and (effort >= 8.5)


# ----------------------------
# Cálculo principal
# ----------------------------
def compute_component_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["sleep_hours_score"] = out["sleep_hours"].apply(score_sleep_hours)
    out["sleep_quality_score"] = out["sleep_quality"].apply(score_sleep_quality)

    out["perf_score"] = out["performance_index"].apply(score_performance)
    out["trend_score"] = out.apply(lambda r: score_trend(r["performance_index"], r["performance_7d_mean"]), axis=1)

    out["acwr_score"] = out["acwr_7_28"].apply(score_acwr)
    out["rir_fatigue_score"] = out["rir_weighted"].apply(score_rir_for_fatigue)

    out["flag_understim"] = out.apply(lambda r: flag_understim(r["rir_weighted"], r["effort_mean"]), axis=1)
    out["flag_high_strain_day"] = out.apply(lambda r: flag_high_strain_day(r["rir_weighted"], r["effort_mean"]), axis=1)

    return out


def compute_readiness(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Readiness base (0–1)
    # Sueño 40% (25 + 15), performance 25%, trend 10%, acwr 15%, fatiga por RIR 10%
    out["readiness_0_1"] = (
        0.25 * out["sleep_hours_score"] +
        0.15 * out["sleep_quality_score"] +
        0.25 * out["perf_score"] +
        0.10 * out["trend_score"] +
        0.15 * out["acwr_score"] +
        0.10 * out["rir_fatigue_score"]
    )

    # Si falta sueño o perf, no inventamos
    out.loc[out["sleep_hours_score"].isna() | out["perf_score"].isna(), "readiness_0_1"] = np.nan

    out["readiness_score"] = (out["readiness_0_1"] * 100).round()

    # Overrides (caps)
    out.loc[out["fatigue_flag"] == True, "readiness_score"] = np.minimum(out["readiness_score"], 60)
    out.loc[out["sleep_hours"] < 6.0, "readiness_score"] = np.minimum(out["readiness_score"], 55)
    out.loc[(out["performance_index"] < 0.98) & (out["effort_mean"] >= 8.5), "readiness_score"] = np.minimum(out["readiness_score"], 50)

    # Clamp final
    out["readiness_score"] = out["readiness_score"].clip(lower=0, upper=100)

    return out


def generate_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def rec(row):
        rs = row["readiness_score"]
        if pd.isna(rs):
            return "Need data", "Log sleep + session", "MISSING_DATA"

        # Reglas inteligentes: distinguimos fatiga vs poco estímulo
        if rs >= 80:
            if row["flag_understim"]:
                return "Push day", "+1 set (key lift) OR target RIR 1–2", "UNDERSTIM|HIGH_READINESS"
            return "Push day", "+2.5% load (key lift) if PI>=1.01 else +1 set", "HIGH_READINESS"

        if 65 <= rs < 80:
            if row["acwr_7_28"] > 1.3:
                return "Normal", "Maintain load, -10% volume", "MOD_READINESS|ELEVATED_ACWR"
            return "Normal", "Maintain (target RIR 1–2)", "MOD_READINESS"

        if 50 <= rs < 65:
            # Reduce volumen, no hace falta bajar todo el peso si PI está ok
            if row["performance_index"] >= 1.00:
                return "Reduce", "-15% volume, keep technique, target RIR 2–3", "LOW_READINESS|VOLUME_CUT"
            return "Reduce", "-20% volume, avoid RIR<=1", "LOW_READINESS|PERF_SOFT"

        # < 50
        if row["sleep_hours"] < 6.0:
            return "Deload / Rest", "-40% volume, target RIR 3–5 OR rest", "VERY_LOW_READINESS|LOW_SLEEP"
        return "Deload / Rest", "-30–50% volume, target RIR 3–5", "VERY_LOW_READINESS"

    tmp = out.apply(lambda r: pd.Series(rec(r)), axis=1)
    tmp.columns = ["recommendation", "action_intensity", "primary_reason"]
    out = pd.concat([out, tmp], axis=1)

    # reason_codes explicativos
    def reason_codes(row):
        codes = []
        if pd.notna(row.get("sleep_hours")) and row["sleep_hours"] < 6.5:
            codes.append("LOW_SLEEP")
        if pd.notna(row.get("acwr_7_28")) and row["acwr_7_28"] > 1.5:
            codes.append("HIGH_ACWR")
        if pd.notna(row.get("performance_index")) and row["performance_index"] < 0.98:
            codes.append("PERF_DROP")
        if pd.notna(row.get("effort_mean")) and row["effort_mean"] >= 8.5:
            codes.append("HIGH_EFFORT")
        if bool(row.get("fatigue_flag")):
            codes.append("FATIGUE")
        if bool(row.get("flag_high_strain_day")):
            codes.append("HIGH_STRAIN_DAY")
        if bool(row.get("flag_understim")):
            codes.append("UNDERSTIM")
        return "|".join(codes) if codes else "NONE"

    out["reason_codes"] = out.apply(reason_codes, axis=1)

    # explicación humana breve
    out["explanation"] = out.apply(
        lambda r: (
            f"Readiness {int(r['readiness_score']) if pd.notna(r['readiness_score']) else 'NA'}: "
            f"{r['recommendation']} — {r['action_intensity']} (reasons: {r['reason_codes']})."
        ),
        axis=1
    )

    return out


def export_outputs(df: pd.DataFrame, out_dir: str) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Recomendaciones
    df.to_csv(out_path / "recommendations_daily.csv", index=False)

    # Flags/diagnóstico (útil para debug + LinkedIn)
    flags_cols = [
        "date", "readiness_score", "recommendation", "action_intensity",
        "reason_codes", "sleep_hours", "sleep_quality", "acwr_7_28",
        "performance_index", "performance_7d_mean", "rir_weighted", "effort_mean",
        "fatigue_flag", "flag_high_strain_day", "flag_understim"
    ]
    existing = [c for c in flags_cols if c in df.columns]
    df[existing].to_csv(out_path / "flags_daily.csv", index=False)


def main(daily_path: str, out_dir: str) -> None:
    df = load_processed_daily(daily_path)
    df = compute_component_scores(df)
    df = compute_readiness(df)
    df = generate_recommendations(df)
    export_outputs(df, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decision Engine: readiness + recomendaciones diarias.")
    parser.add_argument("--daily", required=True, help="Ruta a data/processed/daily.csv")
    parser.add_argument("--out", required=True, help="Directorio de salida (ej: data/processed)")
    args = parser.parse_args()

    main(args.daily, args.out)
