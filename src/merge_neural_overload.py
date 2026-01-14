import pandas as pd
from pathlib import Path

def merge_neural_overload_with_daily(
    daily_path: str,
    overload_path: str,
    out_path: str = None
):
    """
    Merge daily.csv with neural_overload_daily.csv by date, adding overload_score, overload_flags, overload_lifts.
    If overload file does not exist, fill with defaults.
    """
    daily = pd.read_csv(daily_path)
    if Path(overload_path).exists():
        overload = pd.read_csv(overload_path)
        merged = pd.merge(daily, overload, on='date', how='left')
        merged['overload_score'] = merged['overload_score'].fillna(0)
        merged['overload_flags'] = merged['overload_flags'].fillna('NONE')
        merged['overload_lifts'] = merged['overload_lifts'].fillna('')
    else:
        merged = daily.copy()
        merged['overload_score'] = 0
        merged['overload_flags'] = 'NONE'
        merged['overload_lifts'] = ''
    out_path = out_path or daily_path.replace('.csv', '_enriched.csv')
    merged.to_csv(out_path, index=False)
    print(f"Merged and saved: {out_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Merge neural overload with daily.csv")
    parser.add_argument('--daily', required=True, help='Path to daily.csv')
    parser.add_argument('--overload', required=True, help='Path to neural_overload_daily.csv')
    parser.add_argument('--out', required=False, help='Output path (default: daily_enriched.csv)')
    args = parser.parse_args()
    merge_neural_overload_with_daily(args.daily, args.overload, args.out)
