import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class OverloadV2Config:
    window_sessions: int = 6
    min_sessions_advanced: int = 12
    cv_advanced: float = 0.05
    load_tolerance_kg: float = 2.5
    near_failure_rir: float = 1.0
    near_failure_rpe: float = 9.0
    near_failure_prop: float = 0.66
    near_failure_k: int = 3
    drift_rep_drop: int = 1
    drift_rir_drop: float = 1.0
    drift_e1rm_drop_pct: float = 0.03
    volatility_rep_range: int = 2
    volatility_e1rm_cv: float = 0.04
    plateau_rir_diff: float = 0.7
    plateau_load_change: float = 0.03
    max_intent_var_rir: float = 1.0
    max_intent_var_rpe: float = 9.0
    max_intent_var_prop: float = 0.5
    max_intent_var_cv: float = 0.06
    cns_cost_rising_rpe_delta: float = 0.7
    cns_cost_rising_rir_delta: float = -0.7
    cns_cost_rising_window: int = 4
    # Severities
    weight_sustained_failure: int = 25
    weight_fixed_load_drift: int = 20
    weight_high_volatility: int = 10
    weight_plateau_effort: int = 15
    weight_max_intent_var: int = 18
    weight_cns_cost_rising: int = 22
    # Cap
    overload_score_cap: int = 100

@dataclass
class AdvancedV2Config(OverloadV2Config):
    window_sessions: int = 4
    near_failure_prop: float = 0.5
    drift_e1rm_drop_pct: float = 0.015
    volatility_e1rm_cv: float = 0.03
    max_intent_var_cv: float = 0.045
    cns_cost_rising_window: int = 3


def classify_advanced_lifts_v2(df: pd.DataFrame, min_sessions: int, cv_threshold: float) -> Dict[str, bool]:
    result = {}
    for exercise in df["exercise"].unique():
        df_ex = df[df["exercise"] == exercise]
        n_sessions = len(df_ex)
        if n_sessions < 6:
            result[exercise] = False
            continue
        if n_sessions < min_sessions:
            result[exercise] = False
            continue
        cv = df_ex["top_e1rm"].std() / df_ex["top_e1rm"].mean() if df_ex["top_e1rm"].mean() else 0
        result[exercise] = cv < cv_threshold
    return result


def detect_flags_v2(df: pd.DataFrame, config: OverloadV2Config, advanced_map: Dict[str, bool]) -> List[dict]:
    flags = []
    for exercise in df["exercise"].unique():
        df_ex = df[df["exercise"] == exercise].sort_values("date")
        is_advanced = advanced_map.get(exercise, False)
        cfg = AdvancedV2Config() if is_advanced else config
        # Precalcular bandas de carga y rep range para comparabilidad
        df_ex = df_ex.copy()
        df_ex["load_band"] = (df_ex["top_load"] / cfg.load_tolerance_kg).round() * cfg.load_tolerance_kg
        df_ex["rep_band"] = pd.cut(df_ex["top_reps"], bins=[0,2,5,8,12,100], labels=["1-2","3-5","6-8","9-12","13+"])
        for i in range(cfg.window_sessions-1, len(df_ex)):
            window = df_ex.iloc[i-cfg.window_sessions+1:i+1]
            date = window.iloc[-1]["date"]
            # SUSTAINED_NEAR_FAILURE
            prop_nf = ((window["top_rir"] <= cfg.near_failure_rir) | (window["top_rpe"] >= cfg.near_failure_rpe)).mean()
            mean_rir = window["top_rir"].mean()
            if prop_nf >= cfg.near_failure_prop and mean_rir <= cfg.near_failure_rir:
                flags.append({
                    'date': date, 'exercise': exercise, 'flag_type': 'SUSTAINED_NEAR_FAILURE',
                    'severity': int(cfg.weight_sustained_failure),
                    'evidence_json': json.dumps({'prop_nf': float(prop_nf), 'mean_rir': float(mean_rir)}),
                    'recommendations': ["Evita RIR0 en top sets", "Reduce sets -20%"]
                })
            # FIXED_LOAD_DRIFT
            last = window.iloc[-1]
            comparable = window[(window['top_load'] - last['top_load']).abs() <= cfg.load_tolerance_kg]
            if not comparable.empty:
                baseline_reps = float(comparable['top_reps'].median())
                baseline_rir = float(comparable['top_rir'].median())
                baseline_e1rm = float(comparable['top_e1rm'].median())
                rep_drop = bool(last['top_reps'] <= baseline_reps - cfg.drift_rep_drop)
                rir_drop = bool(last['top_rir'] <= baseline_rir - cfg.drift_rir_drop)
                e1rm_drop = bool(last['top_e1rm'] < baseline_e1rm * (1 - cfg.drift_e1rm_drop_pct))
                if rep_drop or rir_drop or e1rm_drop:
                    flags.append({
                        'date': date, 'exercise': exercise, 'flag_type': 'FIXED_LOAD_DRIFT',
                        'severity': int(cfg.weight_fixed_load_drift),
                        'evidence_json': json.dumps({
                            'baseline_reps': baseline_reps, 'current_reps': float(last['top_reps']),
                            'baseline_rir': baseline_rir, 'current_rir': float(last['top_rir']),
                            'baseline_e1rm': baseline_e1rm, 'current_e1rm': float(last['top_e1rm']),
                            'drift_type': [k for k, v in zip(['reps','rir','e1rm'], [rep_drop, rir_drop, e1rm_drop]) if v]
                        }),
                        'recommendations': ["Micro-deload: -5% carga o +2 RIR", "No busques PR esta semana"]
                    })
            # HIGH_VOLATILITY
            rep_range = window['top_reps'].max() - window['top_reps'].min()
            e1rm_cv = window['top_e1rm'].std() / window['top_e1rm'].mean() if window['top_e1rm'].mean() else 0
            low_rir_share = (window['top_rir'] <= 1).mean()
            is_volatile = (rep_range >= cfg.volatility_rep_range) or (e1rm_cv > cfg.volatility_e1rm_cv)
            if is_volatile and low_rir_share >= 0.5:
                flags.append({
                    'date': date, 'exercise': exercise, 'flag_type': 'HIGH_VOLATILITY',
                    'severity': int(cfg.weight_high_volatility),
                    'evidence_json': json.dumps({'rep_range': float(rep_range), 'e1rm_cv': float(e1rm_cv), 'low_rir_share': float(low_rir_share)}),
                    'recommendations': ["Aumenta consistencia", "Controla fatiga"]
                })
            # PLATEAU_EFFORT_RISE
            half = window.shape[0] // 2
            if half > 0:
                load_first = float(window.iloc[:half]['top_load'].median())
                load_last = float(window.iloc[half:]['top_load'].median())
                is_plateau = abs(load_last - load_first) / load_first < cfg.plateau_load_change if load_first else False
                rir_first = float(window.iloc[:half]['top_rir'].mean())
                rir_second = float(window.iloc[half:]['top_rir'].mean())
                effort_rising = (rir_second - rir_first) < -cfg.plateau_rir_diff
                if is_plateau and effort_rising:
                    flags.append({
                        'date': date, 'exercise': exercise, 'flag_type': 'PLATEAU_EFFORT_RISE',
                        'severity': int(cfg.weight_plateau_effort),
                        'evidence_json': json.dumps({'load_change_pct': float((load_last - load_first) / load_first) if load_first else None, 'rir_first_half': rir_first, 'rir_second_half': rir_second}),
                        'recommendations': ["Cambio de estímulo necesario"]
                    })
            # MAX_INTENT_VARIABILITY (mejorado)
            last_band = window.iloc[-1]["load_band"]
            last_rep_band = window.iloc[-1]["rep_band"]
            comp = window[(window["load_band"] == last_band) & (window["rep_band"] == last_rep_band)]
            if len(comp) >= 3:
                intent_mask = (comp['top_rir'] <= cfg.max_intent_var_rir) | (comp['top_rpe'] >= cfg.max_intent_var_rpe)
                prop_intent = float(intent_mask.mean())
                e1rm_cv = float(comp['top_e1rm'].std() / comp['top_e1rm'].mean()) if comp['top_e1rm'].mean() else 0.0
                e1rm_trend = float(comp['top_e1rm'].iloc[-1] - comp['top_e1rm'].median()) if len(comp) > 2 else 0.0
                if prop_intent >= cfg.max_intent_var_prop and e1rm_cv > cfg.max_intent_var_cv and e1rm_trend <= 0:
                    flags.append({
                        'date': date, 'exercise': exercise, 'flag_type': 'MAX_INTENT_VARIABILITY',
                        'severity': int(cfg.weight_max_intent_var),
                        'evidence_json': json.dumps({'prop_intent': prop_intent, 'e1rm_cv': e1rm_cv, 'e1rm_trend': e1rm_trend, 'n_comp': int(len(comp))}),
                        'recommendations': ["Reduce la variabilidad de ejecución", "Estandariza técnica y descanso"]
                    })
            # CNS_COST_RISING (mejorado)
            # Buscar sets comparables en ventana anterior
            if i >= cfg.window_sessions + cfg.cns_cost_rising_window:
                curr = df_ex.iloc[i-cfg.window_sessions+1:i+1]
                base = df_ex.iloc[i-cfg.window_sessions-cfg.cns_cost_rising_window+1:i-cfg.window_sessions+1]
                # Solo comparar si hay sets comparables (misma load_band y rep_band)
                curr_comp = curr[(curr["load_band"] == last_band) & (curr["rep_band"] == last_rep_band)]
                base_comp = base[(base["load_band"] == last_band) & (base["rep_band"] == last_rep_band)]
                if not curr_comp.empty and not base_comp.empty:
                    base_rpe = float(base_comp['top_rpe'].median())
                    base_rir = float(base_comp['top_rir'].median())
                    curr_rpe = float(curr_comp['top_rpe'].median())
                    curr_rir = float(curr_comp['top_rir'].median())
                    rpe_delta = float(curr_rpe - base_rpe)
                    rir_delta = float(curr_rir - base_rir)
                    if rpe_delta > cfg.cns_cost_rising_rpe_delta or rir_delta < cfg.cns_cost_rising_rir_delta:
                        flags.append({
                            'date': date, 'exercise': exercise, 'flag_type': 'CNS_COST_RISING',
                            'severity': int(cfg.weight_cns_cost_rising),
                            'evidence_json': json.dumps({'base_rpe': base_rpe, 'curr_rpe': curr_rpe, 'base_rir': base_rir, 'curr_rir': curr_rir, 'rpe_delta': rpe_delta, 'rir_delta': rir_delta, 'n_base': int(len(base_comp)), 'n_curr': int(len(curr_comp))}),
                            'recommendations': ["Revisa recuperación y técnica", "Considera deload"]
                        })
    return flags


def aggregate_daily_flags_v2(flags: List[dict]) -> pd.DataFrame:
    daily = {}
    for flag in flags:
        date = pd.to_datetime(flag['date']).date()
        if date not in daily:
            daily[date] = {'overload_score': 0, 'overload_flags': set(), 'overload_lifts': set()}
        daily[date]['overload_score'] += flag['severity']
        daily[date]['overload_flags'].add(flag['flag_type'])
        daily[date]['overload_lifts'].add(flag['exercise'])
    # Cap score
    for v in daily.values():
        v['overload_score'] = min(v['overload_score'], 100)
    return pd.DataFrame([
        {'date': str(date),
         'overload_score': v['overload_score'],
         'overload_flags': '|'.join(sorted(v['overload_flags'])),
         'overload_lifts': '|'.join(sorted(v['overload_lifts']))}
        for date, v in daily.items()
    ])


def main(summary_path: str, out_dir: str):
    df = pd.read_csv(summary_path)
    df['date'] = pd.to_datetime(df['date'])
    config = OverloadV2Config()
    advanced_map = classify_advanced_lifts_v2(df, config.min_sessions_advanced, config.cv_advanced)
    flags = detect_flags_v2(df, config, advanced_map)
    daily_df = aggregate_daily_flags_v2(flags)
    lifts_df = pd.DataFrame(flags)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    daily_df.to_csv(Path(out_dir) / 'neural_overload_daily.csv', index=False)
    lifts_df.to_csv(Path(out_dir) / 'neural_overload_lifts.csv', index=False)
    print(f"Exported: {Path(out_dir) / 'neural_overload_daily.csv'}")
    print(f"Exported: {Path(out_dir) / 'neural_overload_lifts.csv'}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Neural Overload Detector v2 CLI")
    parser.add_argument('--summary', required=True, help='Path to exercise_day_summary.csv')
    parser.add_argument('--out', required=True, help='Output directory')
    args = parser.parse_args()
    main(args.summary, args.out)
