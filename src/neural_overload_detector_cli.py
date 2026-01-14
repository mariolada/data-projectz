import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from src.neural_overload_detector import (
    OverloadConfig, AdvancedConfig, extract_top_sets, classify_advanced_lifts
)

def run_neural_overload_detector(
    summary_path: str,
    out_dir: str,
    window_sessions: int = 6,
    min_sessions_advanced: int = 12,
    cv_advanced: float = 0.05
):
    """
    Ejecuta el detector de sobrecarga neural sobre exercise_day_summary.csv
    y exporta los resultados requeridos.
    """
    df = pd.read_csv(summary_path)
    df['date'] = pd.to_datetime(df['date'])
    df['exercise'] = df['exercise'].astype(str)
    df = df.sort_values(['exercise', 'date'])

    # Normalizar nombres
    df['exercise_norm'] = df['exercise'].str.lower().str.strip()

    # Clasificación avanzada por ejercicio
    advanced_map = classify_advanced_lifts(df, min_sessions=min_sessions_advanced, cv_threshold=cv_advanced)

    # Salidas
    daily_records = {}
    lift_records = []

    for exercise in df['exercise_norm'].unique():
        df_ex = df[df['exercise_norm'] == exercise].sort_values('date')
        is_advanced = advanced_map.get(exercise, False)
        config = AdvancedConfig() if is_advanced else OverloadConfig()
        for i in range(window_sessions-1, len(df_ex)):
            window = df_ex.iloc[i-window_sessions+1:i+1]
            date = window.iloc[-1]['date']
            flags = []
            # SUSTAINED_NEAR_FAILURE
            prop_nf = ((window['top_rir'] <= config.near_failure_rir_threshold) | (window['top_rpe'] >= config.near_failure_rpe_threshold)).mean()
            mean_rir = window['top_rir'].mean()
            if prop_nf >= config.near_failure_proportion and mean_rir <= config.near_failure_rir_threshold:
                flags.append({
                    'flag_type': 'SUSTAINED_NEAR_FAILURE',
                    'severity': config.weight_sustained_failure,
                    'evidence': {'prop_nf': prop_nf, 'mean_rir': mean_rir},
                    'recommendations': [
                        f"Evita RIR0 en {exercise} durante 7 días",
                        f"Top set a RIR2 + 2 backoff sets",
                        f"Reduce sets -20%"
                    ]
                })
            # FIXED_LOAD_DRIFT
            last = window.iloc[-1]
            comparable = window[(window['top_load'] - last['top_load']).abs() <= config.load_tolerance_kg]
            if not comparable.empty:
                baseline_reps = comparable['top_reps'].median()
                baseline_rir = comparable['top_rir'].median()
                baseline_e1rm = comparable['top_e1rm'].median()
                rep_drop = last['top_reps'] <= baseline_reps - config.drift_rep_drop
                rir_drop = last['top_rir'] <= baseline_rir - config.drift_rir_drop
                e1rm_drop = last['top_e1rm'] < baseline_e1rm * (1 - config.drift_e1rm_drop_pct)
                if rep_drop or rir_drop or e1rm_drop:
                    flags.append({
                        'flag_type': 'FIXED_LOAD_DRIFT',
                        'severity': config.weight_fixed_load_drift,
                        'evidence': {
                            'baseline_reps': baseline_reps,
                            'current_reps': last['top_reps'],
                            'drift_type': [k for k, v in zip(['reps','rir','e1rm'], [rep_drop, rir_drop, e1rm_drop]) if v]
                        },
                        'recommendations': [
                            f"Micro-deload: -5% carga o +2 RIR por 1 semana",
                            f"Cambia estímulo: pausas, tempo, rep range 6-8",
                            f"No busques PR esta semana"
                        ]
                    })
            # HIGH_VOLATILITY
            rep_range = window['top_reps'].max() - window['top_reps'].min()
            e1rm_cv = window['top_e1rm'].std() / window['top_e1rm'].mean() if window['top_e1rm'].mean() else 0
            low_rir_share = (window['top_rir'] <= 1).mean()
            is_volatile = (rep_range >= config.volatility_rep_range) or (e1rm_cv > config.volatility_e1rm_cv)
            if is_volatile and low_rir_share >= 0.5:
                flags.append({
                    'flag_type': 'HIGH_VOLATILITY',
                    'severity': config.weight_high_volatility,
                    'evidence': {
                        'rep_range': rep_range,
                        'e1rm_cv': e1rm_cv,
                        'low_rir_share': low_rir_share
                    },
                    'recommendations': [
                        f"Aumenta consistencia: misma estructura y descanso",
                        f"Controla fatiga: máx 1 top set pesado por sesión",
                        f"Máx 1 set @RIR0/semana; usa top set @RIR1 + backoffs"
                    ]
                })
            # PLATEAU_EFFORT_RISE
            half = window.shape[0] // 2
            if half > 0:
                load_first = window.iloc[:half]['top_load'].median()
                load_last = window.iloc[half:]['top_load'].median()
                is_plateau = abs(load_last - load_first) / load_first < 0.03 if load_first else False
                rir_first = window.iloc[:half]['top_rir'].mean()
                rir_second = window.iloc[half:]['top_rir'].mean()
                effort_rising = (rir_second - rir_first) < -0.7
                if is_plateau and effort_rising:
                    flags.append({
                        'flag_type': 'PLATEAU_EFFORT_RISE',
                        'severity': config.weight_plateau_effort,
                        'evidence': {
                            'load_change_pct': (load_last - load_first) / load_first if load_first else None,
                            'rir_first_half': rir_first,
                            'rir_second_half': rir_second
                        },
                        'recommendations': [
                            f"Cambio de estímulo necesario",
                            f"Varía rep ranges, tempo, o variantes del ejercicio",
                            f"Considera deload de 1 semana"
                        ]
                    })
            # Guardar flags por ejercicio/día
            for flag in flags:
                lift_records.append({
                    'date': str(date.date()),
                    'exercise': exercise,
                    'flag_type': flag['flag_type'],
                    'severity': flag['severity'],
                    'evidence_json': json.dumps(flag['evidence']),
                    'recommendations': json.dumps(flag['recommendations'])
                })
            # Agregado diario
            if len(flags) > 0:
                if date not in daily_records:
                    daily_records[date] = {'overload_score': 0, 'overload_flags': [], 'overload_lifts': []}
                daily_records[date]['overload_score'] += sum(f['severity'] for f in flags)
                daily_records[date]['overload_flags'].extend(f['flag_type'] for f in flags)
                daily_records[date]['overload_lifts'].extend([exercise]*len(flags))
    # Exportar daily
    daily_out = Path(out_dir) / 'neural_overload_daily.csv'
    daily_df = pd.DataFrame([
        {'date': str(date.date()),
         'overload_score': v['overload_score'],
         'overload_flags': '|'.join(v['overload_flags']),
         'overload_lifts': '|'.join(v['overload_lifts'])}
        for date, v in daily_records.items()
    ])
    daily_df.to_csv(daily_out, index=False)
    # Exportar lifts
    lifts_out = Path(out_dir) / 'neural_overload_lifts.csv'
    lifts_df = pd.DataFrame(lift_records)
    lifts_df.to_csv(lifts_out, index=False)
    print(f"Exported: {daily_out}")
    print(f"Exported: {lifts_out}")
    return daily_df, lifts_df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Neural Overload Detector CLI")
    parser.add_argument('--summary', required=True, help='Path to exercise_day_summary.csv')
    parser.add_argument('--out', required=True, help='Output directory')
    parser.add_argument('--window', type=int, default=6, help='Sessions window (default=6)')
    args = parser.parse_args()
    run_neural_overload_detector(args.summary, args.out, window_sessions=args.window)
