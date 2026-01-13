import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Crear directorios si no existen
Path('data/raw').mkdir(parents=True, exist_ok=True)
Path('data/processed').mkdir(parents=True, exist_ok=True)

# Rango de fechas: últimos 35 días (para tener histórico suficiente)
today = datetime(2026, 1, 10)
start = today - timedelta(days=34)
dates = [start + timedelta(days=i) for i in range(35)]

# ===== TRAINING.CSV (raw) =====
training_data = []
for date in dates:
    for _ in range(np.random.randint(1, 4)):
        training_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'exercise': np.random.choice(['Press Banca', 'Press Militar', 'Peso Muerto', 'Sentadilla', 'Remo']),
            'sets': np.random.randint(3, 6),
            'reps': np.random.randint(6, 12),
            'weight': np.random.uniform(60, 120),
            'rpe': np.random.uniform(5, 9.5),
            'rir': np.random.uniform(0.5, 3.5)
        })

df_training = pd.DataFrame(training_data)
df_training.to_csv('data/raw/training.csv', index=False)
print('✓ training.csv')

# ===== SLEEP.CSV (raw) =====
sleep_data = []
for date in dates:
    # Simulación de sueño con variabilidad
    base_sleep = 7.5
    sleep_hours = np.clip(np.random.normal(base_sleep, 0.8), 5.0, 9.5)
    sleep_quality = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.15, 0.3, 0.35, 0.15])
    
    # PERCEPCIÓN PERSONAL: cómo te sientes (puede no correlacionar 100% con sueño)
    # A veces duermes poco pero te sientes bien (café, adrenalina, etc.)
    # A veces duermes bien pero te sientes mal (estrés, enfermo, etc.)
    perceived_base = 7.0  # Media neutral
    # Correlación parcial con sueño (~60%)
    sleep_influence = (sleep_hours - 6.5) * 0.6  # +/- 1.8 aprox
    quality_influence = (sleep_quality - 3) * 0.3  # +/- 0.6 aprox
    random_variation = np.random.normal(0, 1.2)  # Variación subjetiva
    
    perceived_readiness = np.clip(
        perceived_base + sleep_influence + quality_influence + random_variation,
        1, 10
    )
    perceived_readiness = round(perceived_readiness, 1)
    
    sleep_data.append({
        'date': date.strftime('%Y-%m-%d'),
        'sleep_hours': round(sleep_hours, 1),
        'sleep_quality': sleep_quality,
        'perceived_readiness': perceived_readiness
    })

df_sleep = pd.DataFrame(sleep_data)
df_sleep.to_csv('data/raw/sleep.csv', index=False)
print('✓ sleep.csv')

# ===== MOOD_DAILY.CSV (raw) =====
mood_data = [{
    'date': date.strftime('%Y-%m-%d'),
    'mood': np.random.randint(1, 6),
    'fatigue_flag': np.random.choice([0, 1], p=[0.7, 0.3])
} for date in dates]

df_mood = pd.DataFrame(mood_data)
df_mood.to_csv('data/raw/mood_daily.csv', index=False)
print('✓ mood_daily.csv')

# ===== DAILY.CSV (processed) =====
daily_data = []
for i, date in enumerate(dates):
    day_data = df_training[df_training['date'] == date.strftime('%Y-%m-%d')]
    volume = (day_data['sets'] * day_data['reps'] * day_data['weight']).sum() if len(day_data) > 0 else 0
    
    window_7 = df_training[df_training['date'].isin([
        (date - timedelta(days=j)).strftime('%Y-%m-%d') for j in range(7)
    ])]
    volume_7d = (window_7['sets'] * window_7['reps'] * window_7['weight']).sum() / 7 if len(window_7) > 0 else 0
    
    window_28 = df_training[df_training['date'].isin([
        (date - timedelta(days=j)).strftime('%Y-%m-%d') for j in range(28)
    ])]
    volume_28d = (window_28['sets'] * window_28['reps'] * window_28['weight']).sum() / 28 if len(window_28) > 0 else 0
    
    acwr_7_28 = volume_7d / volume_28d if volume_28d > 0 else 1.0
    
    daily_data.append({
        'date': date.strftime('%Y-%m-%d'),
        'volume': max(volume, 0),
        'volume_7d': max(volume_7d, 0),
        'volume_28d': max(volume_28d, 0),
        'acwr_7_28': min(acwr_7_28, 2.0) if volume_28d > 0 else 0,
        'rir_weighted': day_data['rir'].mean() if len(day_data) > 0 else 0,
        'effort_mean': (10 - day_data['rir']).mean() if len(day_data) > 0 else 0,
        'performance_index': np.random.uniform(0.95, 1.05),
        'performance_7d_mean': np.random.uniform(0.97, 1.03),
        'sleep_hours': df_sleep[df_sleep['date'] == date.strftime('%Y-%m-%d')]['sleep_hours'].values[0],
        'sleep_quality': df_sleep[df_sleep['date'] == date.strftime('%Y-%m-%d')]['sleep_quality'].values[0],
        'fatigue_flag': df_mood[df_mood['date'] == date.strftime('%Y-%m-%d')]['fatigue_flag'].values[0],
        'readiness_score': np.random.uniform(40, 100),
        'recommendation': np.random.choice(['REST', 'LIGHT', 'MODERATE', 'HIGH']),
        'action_intensity': np.random.choice(['-10% load', 'Maintain', '+2.5% load', 'Max effort']),
        'reason_codes': 'LOW_SLEEP|HIGH_ACWR' if np.random.rand() > 0.7 else '',
        'explanation': ''
    })

df_daily = pd.DataFrame(daily_data)
df_daily.to_csv('data/processed/daily.csv', index=False)
print('✓ daily.csv')

# ===== WEEKLY.CSV (processed) =====
weekly_data = []
for i in range(0, len(dates), 7):
    week_dates = dates[i:i+7]
    week_df = df_daily[df_daily['date'].isin([d.strftime('%Y-%m-%d') for d in week_dates])]
    
    if len(week_df) > 0:
        volumes = week_df['volume'].values
        volume_mean = volumes.mean()
        volume_std = volumes.std() if len(volumes) > 1 else 1.0
        monotony = volume_mean / volume_std if volume_std > 0 else 1.0
        
        effort_mean = week_df['effort_mean'].mean()
        strain = volume_mean * monotony
        
        weekly_data.append({
            'week_start': week_dates[0].strftime('%Y-%m-%d'),
            'days': len(week_df),
            'volume_week': week_df['volume'].sum(),
            'effort_week_mean': effort_mean,
            'rir_week_mean': week_df['rir_weighted'].mean(),
            'monotony': monotony,
            'strain': strain,
            'performance_index': week_df['performance_index'].mean(),
            'avg_sleep': week_df['sleep_hours'].mean(),
            'fatigue_days': week_df['fatigue_flag'].sum()
        })

df_weekly = pd.DataFrame(weekly_data)
df_weekly.to_csv('data/processed/weekly.csv', index=False)
print('✓ weekly.csv')

# ===== RECOMMENDATIONS_DAILY.CSV (processed) =====
recommendations_data = [{
    'date': date.strftime('%Y-%m-%d'),
    'readiness_score': np.random.uniform(40, 100),
    'recommendation': np.random.choice(['REST', 'LIGHT', 'MODERATE', 'HIGH']),
    'reason': np.random.choice(['High fatigue', 'Low sleep', 'Good recovery', 'Optimal state'])
} for date in dates]

df_recommendations = pd.DataFrame(recommendations_data)
df_recommendations.to_csv('data/processed/recommendations_daily.csv', index=False)
print('✓ recommendations_daily.csv')
