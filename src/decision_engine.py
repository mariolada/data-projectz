import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import json
import sys

# Importar personalization engine
sys.path.insert(0, str(Path(__file__).parent))
from personalization_engine import (
    calculate_personal_baselines,
    analyze_sleep_responsiveness,
    detect_user_archetype,
    calculate_personal_adjustment_factors,
    create_user_profile
)

# Importar neural overload detector
from neural_overload_detector import (
    analyze_neuromuscular_overload,
    merge_overload_into_daily,
    apply_overload_caps,
    extract_top_sets,
    classify_advanced_lifts,
    OverloadConfig,
    AdvancedConfig
)


REQUIRED_DAILY_COLUMNS = [
    "date", "volume", "volume_7d", "volume_28d", "acwr_7_28",
    "rir_weighted", "effort_mean", "performance_index", "performance_7d_mean",
    "sleep_hours", "sleep_quality", "fatigue_flag"
]

# Columnas mínimas para sesiones de ejercicio (flexibles)
# Soporta tanto formato "top set" como formato agregado
EXERCISE_MIN_COLUMNS = [
    "date", "exercise"
]


def load_processed_daily(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_DAILY_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en daily.csv: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_exercise_sessions(path: Path) -> pd.DataFrame:
    """
    Carga sesiones por ejercicio. Soporta múltiples formatos:
    
    Formato 1 (agregado): date, exercise, volume, e1rm_max, effort_mean, rir_w
    Formato 2 (set-level): date, exercise, load_kg, reps, rir
    Formato 3 (top-set): date, exercise, load_top, reps_top, rir_top
    """
    if not path.exists():
        return None
    df = pd.read_csv(path)
    missing = [c for c in EXERCISE_MIN_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en {path.name}: {missing}")
    df["date"] = pd.to_datetime(df["date"])
    # Normalizar nombres de ejercicio
    df["exercise"] = df["exercise"].str.lower().str.strip()
    return df.sort_values("date").reset_index(drop=True)


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
    """
    Calcula readiness score basado en métricas objetivas y PERCEPCIÓN PERSONAL si está disponible.
    Si perceived_readiness (0-10) está presente, pesa 25%, reduciendo otros componentes proporcionalmente.
    """
    out = df.copy()

    # Rellenar scores faltantes con valores por defecto (0.5 = neutral/promedio)
    sleep_h_score = out["sleep_hours_score"].fillna(0.5)
    sleep_q_score = out["sleep_quality_score"].fillna(0.5)
    perf_score = out["perf_score"].fillna(0.5)
    trend_score = out["trend_score"].fillna(0.5)
    acwr_score = out["acwr_score"].fillna(0.5)
    rir_score = out["rir_fatigue_score"].fillna(0.5)
    
    # PERCEPCIÓN PERSONAL: si existe y es válida (0-10), usarla con peso 25%
    has_perceived = 'perceived_readiness' in out.columns
    if has_perceived:
        perceived_score = out['perceived_readiness'].fillna(np.nan) / 10.0
        # Solo aplicar peso si hay valor válido
        perceived_weight = 0.25 * perceived_score.where(perceived_score.notna(), 0)
        base_multiplier = perceived_score.notna().astype(float) * 0.75 + perceived_score.isna().astype(float) * 1.0
    else:
        perceived_weight = 0
        base_multiplier = 1.0

    # Readiness base (0–1)
    # Sueño 40% (25 + 15), performance 25%, trend 10%, acwr 15%, fatiga por RIR 10%
    # Si hay perceived, estos pesos se reducen proporcionalmente
    out["readiness_0_1"] = (
        perceived_weight +
        base_multiplier * (
            0.25 * sleep_h_score +
            0.15 * sleep_q_score +
            0.25 * perf_score +
            0.10 * trend_score +
            0.15 * acwr_score +
            0.10 * rir_score
        )
    )

    out["readiness_score"] = (out["readiness_0_1"] * 100).round()

    # Overrides (caps)
    out.loc[out["fatigue_flag"] == True, "readiness_score"] = np.minimum(out["readiness_score"], 60)
    out.loc[out["sleep_hours"] < 6.0, "readiness_score"] = np.minimum(out["readiness_score"], 55)
    out.loc[(out["performance_index"] < 0.98) & (out["effort_mean"] >= 8.5), "readiness_score"] = np.minimum(out["readiness_score"], 50)

    # Clamp final
    out["readiness_score"] = out["readiness_score"].clip(lower=0, upper=100)

    return out


def compute_readiness_with_personalisation(df: pd.DataFrame, adjustment_factors: dict = None) -> pd.DataFrame:
    """
    Calcula readiness CON factores de personalización.
    
    Si adjustment_factors es None, usa valores por defecto.
    Útil para aplicar ajustes personales calculados en el histórico.
    """
    out = df.copy()
    
    if adjustment_factors is None:
        adjustment_factors = {
            'sleep_weight': 0.25,
            'performance_weight': 0.25,
            'acwr_weight': 0.15,
            'fatigue_sensitivity': 1.0,
        }
    
    # Extraer factores
    sleep_w = adjustment_factors.get('sleep_weight', 0.25)
    perf_w = adjustment_factors.get('performance_weight', 0.25)
    acwr_w = adjustment_factors.get('acwr_weight', 0.15)
    fatigue_sens = adjustment_factors.get('fatigue_sensitivity', 1.0)
    
    # Otros pesos (derivados para mantener suma ~1.0)
    sleep_quality_w = 0.15
    trend_w = 0.10
    rir_w = 0.10
    
    # Normalizar si es necesario (mantener suma cercana a 1.0)
    total = sleep_w + sleep_quality_w + perf_w + trend_w + acwr_w + rir_w
    sleep_w = (sleep_w / total) * 0.95  # 95% para dejar margen
    perf_w = (perf_w / total) * 0.95
    acwr_w = (acwr_w / total) * 0.95
    rir_w = (rir_w / total) * 0.95 * fatigue_sens
    
    # Rellenar scores faltantes con valores por defecto (0.5 = neutral/promedio)
    sleep_h_score = out["sleep_hours_score"].fillna(0.5)
    sleep_q_score = out["sleep_quality_score"].fillna(0.5)
    perf_score = out["perf_score"].fillna(0.5)
    trend_score = out["trend_score"].fillna(0.5)
    acwr_score = out["acwr_score"].fillna(0.5)
    rir_score = out["rir_fatigue_score"].fillna(0.5)
    
    # Readiness personalizado
    out["readiness_0_1_personalized"] = (
        sleep_w * sleep_h_score +
        sleep_quality_w * sleep_q_score +
        perf_w * perf_score +
        trend_w * trend_score +
        acwr_w * acwr_score +
        rir_w * rir_score
    )
    
    out["readiness_score_personalized"] = (out["readiness_0_1_personalized"] * 100).round()
    
    # Aplicar overrides (igual que versión genérica)
    out.loc[out["fatigue_flag"] == True, "readiness_score_personalized"] = np.minimum(out["readiness_score_personalized"], 60)
    out.loc[out["sleep_hours"] < 6.0, "readiness_score_personalized"] = np.minimum(out["readiness_score_personalized"], 55)
    out.loc[(out["performance_index"] < 0.98) & (out["effort_mean"] >= 8.5), "readiness_score_personalized"] = np.minimum(out["readiness_score_personalized"], 50)
    
    out["readiness_score_personalized"] = out["readiness_score_personalized"].clip(lower=0, upper=100)
    
    return out


def generate_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def rec(row):
        rs = row["readiness_score"]
        if pd.isna(rs):
            return "Need data", "Log sleep + session", "MISSING_DATA"

        # Verificar si hay sobrecarga neuromuscular
        overload_score = row.get("overload_score", 0)
        has_overload = overload_score >= 30 if pd.notna(overload_score) else False

        # Reglas inteligentes: distinguimos fatiga vs poco estímulo
        if rs >= 80:
            if has_overload:
                return "Normal+", "Mantén carga, evita RIR0 en lifts afectados", "HIGH_READINESS|NEURAL_CAUTION"
            if row["flag_understim"]:
                return "Push day", "+1 set (key lift) OR target RIR 1–2", "UNDERSTIM|HIGH_READINESS"
            return "Push day", "+2.5% load (key lift) if PI>=1.01 else +1 set", "HIGH_READINESS"

        if 65 <= rs < 80:
            if has_overload:
                return "Normal", "Mantén volumen, RIR 2-3, no máximos", "MOD_READINESS|NEURAL_RECOVERY"
            if row["acwr_7_28"] > 1.3:
                return "Normal", "Maintain load, -10% volume", "MOD_READINESS|ELEVATED_ACWR"
            return "Normal", "Maintain (target RIR 1–2)", "MOD_READINESS"

        if 50 <= rs < 65:
            if has_overload:
                return "Reduce", "-20% vol en lifts afectados, RIR 3+", "LOW_READINESS|NEURAL_OVERLOAD"
            # Reduce volumen, no hace falta bajar todo el peso si PI está ok
            if row["performance_index"] >= 1.00:
                return "Reduce", "-15% volume, keep technique, target RIR 2–3", "LOW_READINESS|VOLUME_CUT"
            return "Reduce", "-20% volume, avoid RIR<=1", "LOW_READINESS|PERF_SOFT"

        # < 50
        if has_overload:
            return "Deload", "Deload obligatorio: -40% vol, evita lifts afectados", "VERY_LOW_READINESS|NEURAL_CRITICAL"
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
        
        # Añadir códigos de sobrecarga neuromuscular
        overload_flags = row.get("overload_flags", "")
        if overload_flags and isinstance(overload_flags, str) and overload_flags.strip():
            codes.append("NEURAL_OVERLOAD")
            
        return "|".join(codes) if codes else "NONE"

    out["reason_codes"] = out.apply(reason_codes, axis=1)

    # explicación humana breve
    def build_explanation(row):
        rs = row['readiness_score'] if pd.notna(row['readiness_score']) else 'NA'
        base = f"Readiness {int(rs) if isinstance(rs, (int, float)) else rs}: {row['recommendation']} — {row['action_intensity']}"
        
        # Añadir info de sobrecarga si existe
        overload_flags = row.get("overload_flags", "")
        if overload_flags and isinstance(overload_flags, str) and overload_flags.strip():
            flags_short = overload_flags.split("|")[:2]  # Máx 2 flags
            base += f" [Sobrecarga: {', '.join(flags_short)}]"
        
        base += f" (reasons: {row['reason_codes']})."
        return base

    out["explanation"] = out.apply(build_explanation, axis=1)

    return out


def export_outputs(df: pd.DataFrame, out_dir: str) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Recomendaciones (readiness + recomendaciones)
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


def export_ohp_flags(flags: list, out_dir: str) -> None:
    """Exporta flags/insights de OHP a JSON sencillo."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / "ohp_flags.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=2, ensure_ascii=False)
    print(f"✓ OHP flags guardados en {out_file} ({len(flags)} hallazgos)")


def _estimate_e1rm(load_kg: float, reps: float, rir: float) -> float:
    """Estimación rápida de e1RM (Epley) ajustando reps si hay RIR>0."""
    if pd.isna(load_kg) or pd.isna(reps):
        return np.nan
    reps_eff = reps + max(rir, 0) * 0.5 if not pd.isna(rir) else reps
    return float(load_kg * (1.0 + reps_eff / 30.0))


def detect_ohp_neuromuscular_patterns(ohp_df: pd.DataFrame, sleep_p50: float = None, stress_col: str = "stress") -> list:
    """
    Detecta patrones de fatiga/volatilidad en OHP (Overhead Press).
    Retorna lista de dicts con id, title, action y evidencia.
    Requiere columnas: date, load_top, reps_top, rir_top, exercise (normalizado a "ohp").
    Opcionales: sleep_hours, stress.
    """
    if ohp_df is None or ohp_df.empty:
        return []

    df = ohp_df.copy()
    df = df[df["exercise"].str.contains("ohp|overhead", na=False)]
    if df.empty:
        return []

    # Asegurar e1rm_top
    if "e1rm_top" not in df.columns:
        df["e1rm_top"] = df.apply(lambda r: _estimate_e1rm(r["load_top"], r["reps_top"], r.get("rir_top", np.nan)), axis=1)
    else:
        df["e1rm_top"] = df["e1rm_top"].fillna(df.apply(lambda r: _estimate_e1rm(r["load_top"], r["reps_top"], r.get("rir_top", np.nan)), axis=1))

    # Sleep p50 si no viene de fuera
    if sleep_p50 is None and "sleep_hours" in df.columns:
        sleep_p50 = df["sleep_hours"].median()
    if sleep_p50 is None:
        sleep_p50 = 7.0

    df = df.sort_values("date")
    recent = df.tail(10)  # últimas 10 sesiones de OHP
    if len(recent) < 4:
        return []

    flags = []
    tol_load = 2.5

    def same_load_mask(load_val: float):
        return recent["load_top"].sub(load_val).abs() <= tol_load

    e1rm_median = recent["e1rm_top"].median()
    rir_median = recent["rir_top"].median()
    last = recent.iloc[-1]

    # FLAG 1 — Drop con buen descanso
    if "sleep_hours" in recent.columns:
        good_rest = (recent["sleep_hours"] >= sleep_p50)
        if stress_col in recent.columns:
            good_rest &= (recent[stress_col] <= 6)
        if good_rest.any():
            ref = recent[good_rest].iloc[-1]
            mask_same = same_load_mask(ref["load_top"])
            median_reps_same = recent.loc[mask_same, "reps_top"].median()
            median_rir_same = recent.loc[mask_same, "rir_top"].median()
            rep_drop = ref["reps_top"] <= (median_reps_same - 1)
            rir_drop = ref["rir_top"] <= (median_rir_same - 1)
            e1rm_drop = ref["e1rm_top"] < e1rm_median * 0.99
            if rep_drop or rir_drop or e1rm_drop:
                flags.append({
                    "id": "ohp_drop_good_rest",
                    "title": "Fatiga neuromuscular en OHP",
                    "action": "Sube RIR objetivo +1–2 y recorta 10–20% sets de OHP.",
                    "evidence": {
                        "load": ref["load_top"],
                        "reps": ref["reps_top"],
                        "e1rm": ref["e1rm_top"],
                        "median_e1rm": e1rm_median
                    }
                })

    # FLAG 2 — Grinding trap
    if rir_median < 1.5 and e1rm_median <= recent.iloc[0]["e1rm_top"] * 1.005:
        flags.append({
            "id": "ohp_grinding",
            "title": "Grinding trap en OHP",
            "action": "1 semana OHP @RIR 2–3, volumen moderado o -20%.",
            "evidence": {
                "median_rir": rir_median,
                "median_e1rm": e1rm_median
            }
        })

    # FLAG 3 — Volatilidad alta
    ref_load = last["load_top"]
    comp = recent[same_load_mask(ref_load)]
    if len(comp) >= 3:
        rng = comp["reps_top"].max() - comp["reps_top"].min()
        std = comp["reps_top"].std()
        low_rir_share = (comp["rir_top"] <= 1).mean()
        if ((rng >= 2) or (std is not None and std >= 1)) and (low_rir_share >= 0.5):
            flags.append({
                "id": "ohp_volatility",
                "title": "Volatilidad alta en OHP",
                "action": "Máx 1 set @RIR0/semana; top set @RIR1 + backoffs.",
                "evidence": {
                    "range_reps": rng,
                    "std_reps": std,
                    "low_rir_share": low_rir_share
                }
            })

    # FLAG 4 — Degradación con mal sueño
    if "sleep_hours" in recent.columns and last["sleep_hours"] < sleep_p50:
        if last["e1rm_top"] < e1rm_median * 0.99:
            flags.append({
                "id": "ohp_sleep_related",
                "title": "Bajada de OHP alineada con sueño bajo",
                "action": "Reduce volumen y evita máximos hoy (causa: sueño bajo).",
                "evidence": {
                    "last_sleep": last["sleep_hours"],
                    "p50_sleep": sleep_p50,
                    "e1rm": last["e1rm_top"],
                    "median_e1rm": e1rm_median
                }
            })

    return flags


def export_user_profile(df_daily: pd.DataFrame, out_dir: str) -> None:
    """Crea y guarda el perfil personalizado del usuario como JSON."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Crear perfil
    profile = create_user_profile(df_daily)
    
    # Guardar como JSON para que Streamlit lo lea
    profile_path = out_path / "user_profile.json"
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    
    print(f"✓ User profile guardado: {profile_path}")
    print(f"  Archetype: {profile['archetype'].get('archetype', 'unknown')}")
    print(f"  Insights: {len(profile['insights'])} descubrimientos")


def main(daily_path: str, out_dir: str) -> None:
    df = load_processed_daily(daily_path)
    df = compute_component_scores(df)
    df = compute_readiness(df)
    
    # === NUEVO: Calcular factores personalizados ===
    adjustment_factors = calculate_personal_adjustment_factors(df)
    print(f"\n📊 Factores de ajuste calculados:")
    print(f"   Sleep weight: {adjustment_factors['sleep_weight']:.2f} (default: 0.25)")
    print(f"   Performance weight: {adjustment_factors['performance_weight']:.2f} (default: 0.25)")
    print(f"   ACWR weight: {adjustment_factors['acwr_weight']:.2f} (default: 0.15)")
    print(f"   Fatigue sensitivity: {adjustment_factors['fatigue_sensitivity']:.2f}x (default: 1.0)")
    
    # === NUEVO: Calcular readiness personalizado ===
    df = compute_readiness_with_personalisation(df, adjustment_factors)
    
    df = generate_recommendations(df)
    
    # === NUEVO: Análisis de sobrecarga neuromuscular ===
    exercise_path = Path(daily_path).parent / "daily_exercise.csv"
    training_path = Path(daily_path).parent.parent / "raw" / "training.csv"
    overload_result = None
    
    # Intentar cargar datos de ejercicios (preferir set-level si existe)
    exercise_df = None
    if training_path.exists():
        try:
            exercise_df = pd.read_csv(training_path)
            exercise_df["date"] = pd.to_datetime(exercise_df["date"])
            exercise_df["exercise"] = exercise_df["exercise"].str.lower().str.strip()
            # Renombrar columnas para compatibilidad
            if "weight" in exercise_df.columns and "load_kg" not in exercise_df.columns:
                exercise_df["load_kg"] = exercise_df["weight"]
            print(f"   Usando datos set-level de {training_path.name}")
        except Exception as e:
            print(f"   ⚠️ Error cargando training.csv: {e}")
            exercise_df = None
    
    if exercise_df is None and exercise_path.exists():
        try:
            exercise_df = load_exercise_sessions(exercise_path)
            print(f"   Usando datos agregados de {exercise_path.name}")
        except Exception as e:
            print(f"   ⚠️ Error cargando daily_exercise.csv: {e}")
    
    if exercise_df is not None and not exercise_df.empty:
        try:
            print(f"\n🧠 Analizando sobrecarga neuromuscular...")
            
            overload_result = analyze_neuromuscular_overload(
                df_exercise=exercise_df,
                df_daily=df,
                config=OverloadConfig()
            )
            
            # Mostrar resumen
            summary = overload_result["summary"]
            print(f"   Lifts clave analizados: {summary['n_key_lifts_analyzed']}")
            print(f"   Lifts avanzados: {summary['n_advanced_lifts']}")
            print(f"   Flags detectados: {summary['n_flags_detected']}")
            print(f"   Overload score total: {summary['total_overload_score']}")
            print(f"   Causa principal: {summary['primary_cause']}")
            
            if overload_result["flags"]:
                print(f"\n   ⚠️  Señales de sobrecarga detectadas:")
                for flag in overload_result["flags"]:
                    print(f"      - {flag.flag_type}: {flag.exercise}")
                    print(f"        Severidad: {flag.severity}, Recos: {flag.recommendations[0][:50]}...")
            
            # Integrar en DataFrame diario
            df = merge_overload_into_daily(df, overload_result["overload_df"])
            
            # Exportar flags detallados
            export_overload_flags(overload_result, out_dir)
            
        except Exception as exc:
            print(f"⚠️  Error en análisis de sobrecarga: {exc}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n⚠️  No se encontraron datos de ejercicios - análisis de sobrecarga omitido")
        df["overload_score"] = 0
        df["overload_flags"] = ""
        df["exercise_specific_recos"] = ""
    
    export_outputs(df, out_dir)
    
    # === NUEVO: Guardar perfil del usuario ===
    export_user_profile(df, out_dir)

    # === LEGACY: Detectar patrones OHP (mantener compatibilidad) ===
    ohp_flags = []
    try:
        exercise_df = load_exercise_sessions(exercise_path)
        if exercise_df is not None:
            sleep_p50 = df["sleep_hours"].median()
            ohp_flags = detect_ohp_neuromuscular_patterns(exercise_df, sleep_p50=sleep_p50, stress_col="stress")
            if ohp_flags:
                export_ohp_flags(ohp_flags, out_dir)
    except Exception as exc:
        pass  # Ya manejado arriba


def export_overload_flags(overload_result: dict, out_dir: str) -> None:
    """Exporta flags de sobrecarga neuromuscular a JSON."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Convertir flags a dict serializable
    flags_data = []
    for flag in overload_result["flags"]:
        flags_data.append({
            "flag_type": flag.flag_type,
            "exercise": flag.exercise,
            "severity": flag.severity,
            "evidence": flag.evidence,
            "recommendations": flag.recommendations,
            "date_detected": flag.date_detected
        })
    
    output = {
        "summary": overload_result["summary"],
        "flags": flags_data,
        "advanced_lifts": overload_result["advanced_map"]
    }
    
    out_file = out_path / "neural_overload_flags.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✓ Neural overload flags guardados en {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decision Engine: readiness + recomendaciones diarias + perfil personalizado.")
    parser.add_argument("--daily", required=True, help="Ruta a data/processed/daily.csv")
    parser.add_argument("--out", required=True, help="Directorio de salida (ej: data/processed)")
    args = parser.parse_args()

    main(args.daily, args.out)
