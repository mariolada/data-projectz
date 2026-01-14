import pandas as pd
import json
from pathlib import Path
import argparse

def load_neural_overload_daily(path):
    return pd.read_csv(path)

def load_neural_overload_lifts(path):
    return pd.read_csv(path)

def load_daily_metrics(path):
    return pd.read_csv(path)

def readiness_to_status(readiness, overload_score, acwr, sleep, perf):
    # Simplified rules, tune as needed
    if readiness >= 80 and overload_score < 30 and acwr < 1.3 and sleep >= 7:
        return "GO"
    if readiness >= 60 and overload_score < 60 and acwr < 1.5 and sleep >= 6:
        return "GO_WITH_CONSTRAINTS"
    if overload_score >= 80 or readiness < 40 or sleep < 5:
        return "RECOVER"
    return "REDIRECT"

def lift_flag_to_constraints(flag_type, recommendations):
    # Map flag_type to constraints (expand as needed)
    mapping = {
        "CNS_COST_RISING": ["NO_RIR0", "TOP_SET_RIR>=2", "SWAP_VARIANT"],
        "FIXED_LOAD_DRIFT": ["VOLUME_CAP_-20%", "NO_RIR0"],
        "SUSTAINED_NEAR_FAILURE": ["NO_RIR0", "BACKOFF_ONLY"],
        "MAX_INTENT_VARIABILITY": ["STANDARDIZE_TECHNIQUE", "NO_RIR0"],
        "HIGH_VOLATILITY": ["STANDARDIZE_TECHNIQUE"],
        "PLATEAU_EFFORT_RISE": ["SWAP_VARIANT", "VOLUME_CAP_-25%"]
    }
    base = mapping.get(flag_type, [])
    # Optionally parse recommendations for variants
    for rec in recommendations:
        if "pausado" in rec.lower():
            base.append("SWAP_VARIANT: Press militar pausado")
    return list(set(base))

def main(daily_path, overload_daily_path, overload_lifts_path, out_path):
    daily = load_daily_metrics(daily_path)
    overload_daily = load_neural_overload_daily(overload_daily_path)
    overload_lifts = load_neural_overload_lifts(overload_lifts_path)
    out_rows = []
    for idx, row in daily.iterrows():
        date = row["date"]
        # Readiness v3 assumed in daily.csv as 'readiness_v3' or fallback
        readiness = row.get("readiness_v3", row.get("readiness", 0))
        acwr = row.get("acwr", 1.0)
        sleep = row.get("sleep_h", 7)
        perf = row.get("perf", 1.0)
        od_row = overload_daily[overload_daily["date"] == date]
        overload_score = int(od_row["overload_score"].values[0]) if not od_row.empty else 0
        reason_codes = od_row["overload_flags"].values[0] if not od_row.empty else ""
        affected_lifts = od_row["overload_lifts"].values[0] if not od_row.empty else ""
        day_status = readiness_to_status(readiness, overload_score, acwr, sleep, perf)
        # Constraints por lift
        lifts_today = overload_lifts[overload_lifts["date"] == date]
        lift_constraints = []
        for _, lift in lifts_today.iterrows():
            constraints = lift_flag_to_constraints(lift["flag_type"], json.loads(lift["recommendations"].replace("'", '"')) if isinstance(lift["recommendations"], str) else [])
            lift_constraints.append({
                "exercise": lift["exercise"],
                "constraints": constraints,
                "why": [lift["flag_type"]],
                "severity": int(lift["severity"])
            })
        action_summary = day_status
        out_rows.append({
            "date": date,
            "day_status": day_status,
            "action_summary": action_summary,
            "reason_codes": reason_codes,
            "overload_score": overload_score,
            "affected_lifts": affected_lifts,
            "constraints_json": json.dumps(lift_constraints, ensure_ascii=False)
        })
    out_df = pd.DataFrame(out_rows)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"Exported: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decision Engine v2 CLI")
    parser.add_argument('--daily', required=True, help='Path to daily.csv')
    parser.add_argument('--overload_daily', required=True, help='Path to neural_overload_daily.csv')
    parser.add_argument('--overload_lifts', required=True, help='Path to neural_overload_lifts.csv')
    parser.add_argument('--out', required=True, help='Output CSV path (decision_daily_v2.csv)')
    args = parser.parse_args()
    main(args.daily, args.overload_daily, args.overload_lifts, args.out)
