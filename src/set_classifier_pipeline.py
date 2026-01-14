from set_classifier import classify_sets, SetClassifierConfig, get_top_sets_summary

import pandas as pd
from pathlib import Path

def enrich_and_summarize_sets(training: pd.DataFrame, out_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clasifica y enriquece los sets de entrenamiento, y genera resumen por ejercicio/día.
    Guarda los resultados en CSVs en el directorio de salida.
    """
    # Clasificación automática de sets
    config = SetClassifierConfig()
    # Si falta 'load', crearla a partir de 'weight'
    if 'load' not in training.columns and 'weight' in training.columns:
        training = training.copy()
        training['load'] = training['weight']
    classified = classify_sets(training, config)

    # Añadir columnas booleanas y métricas agregadas
    classified['is_top_set'] = classified['set_role'] == 'TOP'
    classified['is_backoff'] = classified['set_role'] == 'BACKOFF'

    # Para cada (date, exercise), obtener top set info
    top_sets = classified[classified['is_top_set']].copy()
    top_info = top_sets.groupby(['date', 'exercise']).agg(
        top_set_load = ('load', 'max'),
        top_set_reps = ('reps', 'max'),
        top_set_rir = ('rir', 'min'),
        top_set_rpe = ('rpe', 'max'),
    ).reset_index()

    # Merge info de top set a todos los sets de ese ejercicio/día
    classified = classified.merge(top_info, on=['date', 'exercise'], how='left')

    # Backoff count y mean load pct
    def backoff_stats(g):
        n_backoff = g['is_backoff'].sum()
        mean_load_pct = (g.loc[g['is_backoff'], 'load'] / g['top_set_load']).mean() if n_backoff > 0 else None
        return pd.Series({'backoff_count': n_backoff, 'backoff_mean_load_pct': mean_load_pct})
    backoff_df = classified.groupby(['date', 'exercise']).apply(backoff_stats).reset_index()
    classified = classified.merge(backoff_df, on=['date', 'exercise'], how='left')

    # Guardar sets enriquecidos
    sets_out = Path(out_dir) / 'sets_processed.csv'
    classified.to_csv(sets_out, index=False)

    # Resumen por ejercicio/día
    summary = get_top_sets_summary(classified)
    # Añadir volumen y métricas de backoff
    def exercise_day_summary(g):
        backoff = g[g['set_role'] == 'BACKOFF']
        return pd.Series({
            'backoff_volume': (backoff['load'] * backoff['reps']).sum(),
            'backoff_mean_load': backoff['load'].mean(),
            'backoff_mean_rir': backoff['rir'].mean(),
            'n_sets_total': len(g),
            'n_sets_hard': ((g['rir'] <= 2) | (g['rpe'] >= 8)).sum()
        })
    summary_extra = classified.groupby(['date', 'exercise']).apply(exercise_day_summary).reset_index()
    summary = summary.merge(summary_extra, on=['date', 'exercise'], how='left')
    # Guardar resumen
    summary_out = Path(out_dir) / 'exercise_day_summary.csv'
    summary.to_csv(summary_out, index=False)

    return classified, summary
