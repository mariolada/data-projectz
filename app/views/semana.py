"""Vista Semana - dashboard semanal limpio (NASA cards).

Objetivos:
- El selector de semana manda sobre TODO (KPIs, tablas, charts, secuencia).
- Semana basada en lunes (week_start) y truncada a hoy si es la semana actual.
- Estado OK/WARN/RISK robusto: percentiles históricos (evita el bug de 'siempre RISK').
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from charts.daily_charts import (
    create_readiness_chart,
    create_strain_chart,
    create_volume_chart,
)
from ui.components import render_section_title
from ui.loader import loading
from ui.styles import inject_main_css

# Import desde src (estos se añaden al path en streamlit_app.py)
try:
    # streamlit_app.py añade /src al sys.path, por eso este import es el más fiable en runtime.
    from personalization_engine import suggest_weekly_sequence  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover
    # fallback si se ejecuta sin el sys.path tweak de Streamlit
    from src.personalization_engine import suggest_weekly_sequence


@dataclass(frozen=True)
class WeekContext:
    week_start: pd.Timestamp
    week_end: pd.Timestamp
    label: str
    range_label: str
    is_current_week: bool


def _inject_weekly_view_css() -> None:
    st.markdown(
        """
<style>
.weekly-card {
  background: rgba(18,20,28,0.98);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  box-shadow: 0 0 12px rgba(0,0,0,0.16);
  padding: 20px 24px;
  margin: 12px 0 16px 0;
}
.weekly-card .wk-title { font-size: 1.18rem; font-weight: 850; color: #FFB81C; margin-bottom: 2px; }
.weekly-card .wk-sub { font-size: 0.98rem; color: #9CA3AF; margin-bottom: 12px; }
.weekly-kpi-grid { display:flex; flex-wrap:wrap; gap: 22px; }
.weekly-kpi { min-width: 130px; }
.weekly-kpi .k { color:#9CA3AF; font-size: 0.95rem; }
.weekly-kpi .v { color:#FFFFFF; font-weight: 900; font-size: 1.35rem; }
.weekly-chips { display:flex; gap:10px; flex-wrap:wrap; margin-top: 8px; }
.weekly-chip {
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(35,38,58,0.92);
  border: 1px solid rgba(255,255,255,0.08);
  color:#E5E7EB;
  font-weight: 700;
}
.weekly-chip.ok { border-color: rgba(0,208,132,0.35); color: #CFFAEA; }
.weekly-chip.warn { border-color: rgba(255,184,28,0.35); color: #FFE6B3; }
.weekly-chip.risk { border-color: rgba(255,107,107,0.35); color: #FFD1D1; }
.weekly-table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 12px;
}
.weekly-table th {
  text-align: left;
  padding: 10px 12px;
  font-size: 0.9rem;
  color: #E5E7EB;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  background: rgba(10, 12, 18, 0.35);
}
.weekly-table td {
  padding: 10px 12px;
  font-size: 0.92rem;
  color: #E5E7EB;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.weekly-table tr:nth-child(even) td { background: rgba(10, 12, 18, 0.18); }
.weekly-muted { color: #9CA3AF; }
</style>
        """,
        unsafe_allow_html=True,
    )


def _as_timestamp(value: Any) -> Optional[pd.Timestamp]:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).normalize()


def _monday_week_start(date_ts: pd.Timestamp) -> pd.Timestamp:
    date_ts = pd.Timestamp(date_ts).normalize()
    return date_ts - pd.to_timedelta(int(date_ts.dayofweek), unit="D")


def _fmt_date(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).strftime("%d/%m/%Y")


def _fmt_int(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    try:
        return f"{int(round(float(value))):,}".replace(",", ".")
    except Exception:
        return "—"


def _fmt_float(value: Any, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def _fmt_kpi(value: Any, kind: str) -> str:
    if kind == "readiness":
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "—"
        return f"{float(value):.0f}/100"
    if kind == "volume":
        base = _fmt_int(value)
        return f"{base} kg" if base != "—" else "—"
    if kind == "strain":
        return _fmt_int(value)
    if kind == "monotony":
        return _fmt_float(value, 2)
    if kind == "days":
        return _fmt_int(value)
    return str(value) if value is not None else "—"


def _confidence_from_days(days: Optional[int]) -> str:
    if days is None:
        return "Insuficiente"
    if days >= 5:
        return "Alta"
    if days >= 3:
        return "Media"
    if days >= 1:
        return "Baja"
    return "Insuficiente"


def _quantiles(series: pd.Series) -> Dict[str, float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 6:
        return {}
    return {
        "p10": float(clean.quantile(0.10)),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "p90": float(clean.quantile(0.90)),
        "n": float(len(clean)),
    }


def _compute_week_context(df_weekly: pd.DataFrame) -> WeekContext:
    today = pd.Timestamp.now().normalize()
    week_options = (
        df_weekly["week_start"].dropna().sort_values(ascending=False).unique().tolist()
    )
    if not week_options:
        raise ValueError("No hay weeks válidas en weekly.csv")

    def _week_label(ws: pd.Timestamp) -> str:
        we = ws + pd.Timedelta(days=6)
        return f"{_fmt_date(ws)}"

    st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
    col_sel, col_hint = st.columns([2, 1])
    with col_sel:
        selected_ws = st.selectbox(
            "Semana (lunes)",
            options=week_options,
            index=0,
            format_func=_week_label,
            help="El selector controla TODA la vista semanal.",
        )
    with col_hint:
        st.markdown(
            "<div class='weekly-muted' style='padding-top:26px;font-weight:700;'>Vista semanal · premium</div>",
            unsafe_allow_html=True,
        )

    selected_ws = pd.Timestamp(selected_ws).normalize()
    week_end = selected_ws + pd.Timedelta(days=6)
    is_current_week = (selected_ws <= today) and (today <= week_end)
    effective_end = min(today, week_end) if is_current_week else week_end

    range_label = f"{_fmt_date(selected_ws)} → {_fmt_date(effective_end)}"
    label = _fmt_date(selected_ws)

    return WeekContext(
        week_start=selected_ws,
        week_end=effective_end,
        label=label,
        range_label=range_label,
        is_current_week=is_current_week,
    )


def _safe_week_row(df_weekly: pd.DataFrame, week_start: pd.Timestamp) -> pd.Series:
    match = df_weekly.loc[df_weekly["week_start"] == week_start]
    if match.empty:
        return pd.Series(dtype="object")
    return match.iloc[0]


def _filter_daily_for_week(df_daily: pd.DataFrame, ctx: WeekContext) -> pd.DataFrame:
    df = df_daily.copy()
    if "date" not in df.columns:
        return df.iloc[0:0]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.normalize()
    df["week_start"] = df["date"].apply(_monday_week_start)
    df = df.loc[df["week_start"] == ctx.week_start]
    df = df.loc[(df["date"] >= ctx.week_start) & (df["date"] <= ctx.week_end)]
    return df.sort_values("date")


def _compute_monotony_from_daily(df_week_days: pd.DataFrame) -> Optional[float]:
    load_col = "strain" if "strain" in df_week_days.columns else ("volume" if "volume" in df_week_days.columns else None)
    if load_col is None:
        return None
    load = pd.to_numeric(df_week_days[load_col], errors="coerce").dropna()
    if load.empty:
        return None
    # Monotonía clásica: mean / std (guardando std=0)
    mean = float(load.mean())
    std = float(load.std(ddof=0))
    if std <= 1e-9:
        return 0.0
    return mean / std


def _compute_week_kpis(week_row: pd.Series, df_week_days: pd.DataFrame) -> Dict[str, Any]:
    def _pick_weekly_or_fallback(col_weekly: str, fallback_fn) -> Any:
        value = week_row.get(col_weekly, None)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return fallback_fn()
        return value

    readiness = _pick_weekly_or_fallback(
        "readiness_avg",
        lambda: float(pd.to_numeric(df_week_days.get("readiness_score", pd.Series(dtype=float)), errors="coerce").dropna().mean())
        if "readiness_score" in df_week_days.columns and not df_week_days.empty
        else None,
    )
    volume = _pick_weekly_or_fallback(
        "volume_week",
        lambda: float(pd.to_numeric(df_week_days.get("volume", pd.Series(dtype=float)), errors="coerce").dropna().sum())
        if "volume" in df_week_days.columns and not df_week_days.empty
        else None,
    )
    strain = _pick_weekly_or_fallback(
        "strain",
        lambda: float(pd.to_numeric(df_week_days.get("strain", pd.Series(dtype=float)), errors="coerce").dropna().sum())
        if "strain" in df_week_days.columns and not df_week_days.empty
        else None,
    )
    monotony = _pick_weekly_or_fallback(
        "monotony",
        lambda: _compute_monotony_from_daily(df_week_days),
    )

    days = _pick_weekly_or_fallback(
        "days",
        lambda: int(df_week_days["date"].nunique()) if "date" in df_week_days.columns else int(len(df_week_days)),
    )

    return {
        "readiness": readiness,
        "volume": volume,
        "strain": strain,
        "monotony": monotony,
        "days": days,
        "confidence": _confidence_from_days(int(days) if days is not None and str(days) != "—" else None),
    }


def _compute_week_status(kpis: Dict[str, Any], df_weekly_hist: pd.DataFrame) -> Dict[str, Any]:
    # Percentiles históricos (si hay data suficiente)
    q_strain = _quantiles(df_weekly_hist.get("strain", pd.Series(dtype=float)))
    q_mono = _quantiles(df_weekly_hist.get("monotony", pd.Series(dtype=float)))
    q_read = _quantiles(df_weekly_hist.get("readiness_avg", pd.Series(dtype=float)))

    # Fallback thresholds (clásicos)
    fallback = {
        "strain_warn": 1200.0,
        "strain_risk": 1800.0,
        "mono_warn": 1.5,
        "mono_risk": 2.0,
        "read_warn": 70.0,
        "read_risk": 55.0,
    }

    strain_warn = q_strain.get("p75", fallback["strain_warn"])
    strain_risk = q_strain.get("p90", fallback["strain_risk"])
    mono_warn = q_mono.get("p75", fallback["mono_warn"])
    mono_risk = q_mono.get("p90", fallback["mono_risk"])
    read_warn = q_read.get("p25", fallback["read_warn"])  # bajo es malo
    read_risk = q_read.get("p10", fallback["read_risk"])  # muy bajo es peor

    strain = kpis.get("strain")
    mono = kpis.get("monotony")
    read = kpis.get("readiness")

    drivers_risk: List[str] = []
    drivers_warn: List[str] = []

    if strain is not None and not (isinstance(strain, float) and np.isnan(strain)):
        if float(strain) >= float(strain_risk):
            drivers_risk.append("Strain muy alto")
        elif float(strain) >= float(strain_warn):
            drivers_warn.append("Strain alto")

    if mono is not None and not (isinstance(mono, float) and np.isnan(mono)):
        if float(mono) >= float(mono_risk):
            drivers_risk.append("Monotonía muy alta")
        elif float(mono) >= float(mono_warn):
            drivers_warn.append("Monotonía alta")

    if read is not None and not (isinstance(read, float) and np.isnan(read)):
        if float(read) <= float(read_risk):
            drivers_risk.append("Readiness muy bajo")
        elif float(read) <= float(read_warn):
            drivers_warn.append("Readiness bajo")

    if drivers_risk:
        status = "RISK"
    elif drivers_warn:
        status = "WARN"
    else:
        status = "OK"

    action = {
        "OK": "Semana dentro de parámetros óptimos. Mantén el rumbo.",
        "WARN": "Precaución: ajusta intensidad/volumen y prioriza recuperación.",
        "RISK": "Riesgo alto: considera deload (-20%/-30%) o descanso extra.",
    }[status]

    return {
        "status": status,
        "drivers": drivers_risk + drivers_warn,
        "action": action,
        "thresholds": {
            "strain_warn": float(strain_warn),
            "strain_risk": float(strain_risk),
            "mono_warn": float(mono_warn),
            "mono_risk": float(mono_risk),
            "read_warn": float(read_warn),
            "read_risk": float(read_risk),
            "mode": "percentiles" if (q_strain and q_mono and q_read) else "fallback",
        },
    }


def _chip(label: str, variant: str) -> str:
    variant = variant.lower()
    return f"<span class='weekly-chip {variant}'>{label}</span>"


def _render_header(ctx: WeekContext, kpis: Dict[str, Any], status_info: Dict[str, Any]) -> None:
    status = status_info["status"]
    status_variant = {"OK": "ok", "WARN": "warn", "RISK": "risk"}.get(status, "warn")
    conf = kpis.get("confidence", "Insuficiente")
    conf_variant = {"Alta": "ok", "Media": "warn", "Baja": "warn", "Insuficiente": "risk"}.get(conf, "warn")

    st.markdown(
        f"""
<div class='weekly-card'>
  <div class='wk-title'>🗓️ Resumen semanal</div>
  <div class='wk-sub'>Semana (lunes): <b style='color:#FFB81C'>{ctx.label}</b> · Rango: {ctx.range_label}{' · (semana actual)' if ctx.is_current_week else ''}</div>
  <div class='weekly-kpi-grid'>
    <div class='weekly-kpi'><div class='k'>Readiness</div><div class='v'>{_fmt_kpi(kpis.get('readiness'), 'readiness')}</div></div>
    <div class='weekly-kpi'><div class='k'>Volumen</div><div class='v'>{_fmt_kpi(kpis.get('volume'), 'volume')}</div></div>
    <div class='weekly-kpi'><div class='k'>Strain</div><div class='v'>{_fmt_kpi(kpis.get('strain'), 'strain')}</div></div>
    <div class='weekly-kpi'><div class='k'>Monotonía</div><div class='v'>{_fmt_kpi(kpis.get('monotony'), 'monotony')}</div></div>
    <div class='weekly-kpi'><div class='k'>Días</div><div class='v'>{_fmt_kpi(kpis.get('days'), 'days')}</div></div>
  </div>
  <div class='weekly-chips'>
    {_chip(f"Estado: {status}", status_variant)}
    {_chip(f"Confianza: {conf}", conf_variant)}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_card(status_info: Dict[str, Any]) -> None:
    status = status_info["status"]
    color = {"OK": "#00D084", "WARN": "#FFB81C", "RISK": "#FF6B6B"}.get(status, "#9CA3AF")
    emoji = {"OK": "✅", "WARN": "⚠️", "RISK": "🔴"}.get(status, "⚠️")
    drivers = status_info.get("drivers") or []
    driver_line = "; ".join(drivers) if drivers else "Sin alertas relevantes."
    action = status_info["action"]
    mode = status_info.get("thresholds", {}).get("mode", "fallback")

    st.markdown(
        f"""
<div class='weekly-card'>
  <div class='wk-title'>{emoji} Estado semanal: <span style='color:{color}'>{status}</span></div>
  <div class='wk-sub'>{driver_line}</div>
  <div style='color:#E5E7EB;font-size:1.02rem;line-height:1.45;'>
    <b>Acción principal:</b> <span style='color:{color};font-weight:800'>{action}</span>
  </div>
  <div class='weekly-muted' style='margin-top:10px;font-size:0.92rem;'>
    Umbrales: <b>{mode}</b> (percentiles sobre tu histórico si hay datos suficientes)
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _plotly_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=45, b=10),
        font=dict(color="#E5E7EB"),
        title_font=dict(color="#E5E7EB", size=16),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _full_week_index(ctx: WeekContext) -> pd.DatetimeIndex:
    return pd.date_range(start=ctx.week_start, end=ctx.week_end, freq="D")


def _series_for_week(
    df_week_days: pd.DataFrame,
    ctx: WeekContext,
    value_col: str,
    fill_missing: Optional[float] = None,
) -> Optional[pd.Series]:
    if df_week_days.empty or value_col not in df_week_days.columns or "date" not in df_week_days.columns:
        return None
    df = df_week_days[["date", value_col]].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return None
    s = df.set_index("date")[value_col]
    # En caso de múltiples registros por día, sumar (p.ej. volume/strain)
    s = s.groupby(level=0).sum(min_count=1)

    s = s.reindex(_full_week_index(ctx))
    if fill_missing is not None:
        s = s.fillna(fill_missing)
    return s


def _create_monotony_chart(data: pd.Series, title: str = "Monotonía") -> go.Figure:
    fig = go.Figure()
    x_vals = pd.to_datetime(data.index)
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=data.values,
            mode="lines+markers",
            name="Monotonía",
            line=dict(color="#A78BFA", width=3, shape="spline"),
            marker=dict(size=8, color="#A78BFA", line=dict(color="#FFFFFF", width=2)),
            fill="tozeroy",
            fillcolor="rgba(167, 139, 250, 0.18)",
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Monotonía: %{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#A78BFA", family="Orbitron")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E0E0E0"),
        xaxis=dict(showgrid=True, gridcolor="rgba(167, 139, 250, 0.10)", zeroline=False, tickformat="%d/%m/%Y"),
        yaxis=dict(showgrid=True, gridcolor="rgba(167, 139, 250, 0.10)", zeroline=False),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
    )
    return fig


def _render_performance(df_week_days: pd.DataFrame, ctx: WeekContext) -> None:
    render_section_title("Performance (semana seleccionada)", accent="#FFB81C")

    if df_week_days.empty:
        st.info("No hay datos diarios para esta semana.")
        return

    cols = st.columns(2)
    with cols[0]:
        readiness = _series_for_week(df_week_days, ctx, "readiness_score", fill_missing=None)
        if readiness is not None and readiness.notna().any():
            st.plotly_chart(create_readiness_chart(readiness.dropna(), title="Readiness diario"))

        volume = _series_for_week(df_week_days, ctx, "volume", fill_missing=0.0)
        if volume is not None and volume.notna().any():
            st.plotly_chart(create_volume_chart(volume, title="Volumen por día"))

    with cols[1]:
        strain = _series_for_week(df_week_days, ctx, "strain", fill_missing=0.0)
        if strain is not None and strain.notna().any():
            st.plotly_chart(create_strain_chart(strain, title="Strain por día"))

        monotony = _series_for_week(df_week_days, ctx, "monotony", fill_missing=None)
        if monotony is not None and monotony.notna().any():
            st.plotly_chart(_create_monotony_chart(monotony.dropna(), title="Monotonía diaria"))


def _render_daily_table(df_week_days: pd.DataFrame) -> None:
    st.markdown(
        """
<div class='weekly-card'>
  <div class='wk-title'>Días entrenados</div>
  <div class='wk-sub'>Tabla compacta de la semana seleccionada</div>
        """,
        unsafe_allow_html=True,
    )

    if df_week_days.empty:
        st.markdown("<div class='weekly-muted'>No hay datos diarios para esta semana.</div></div>", unsafe_allow_html=True)
        return

    df = df_week_days.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    df["Día"] = df["date"].dt.strftime("%a %d/%m")

    wanted = [
        "Día",
        "split",
        "volume",
        "strain",
        "readiness_score",
        "rpe",
        "rir",
        "top_lifts",
        "notes",
    ]
    cols = [c for c in wanted if c in df.columns]
    df_disp = df[cols].copy()

    # Formateo suave
    for c in ["volume", "strain"]:
        if c in df_disp.columns:
            df_disp[c] = pd.to_numeric(df_disp[c], errors="coerce").round(0).astype("Int64")
    if "readiness_score" in df_disp.columns:
        df_disp["readiness_score"] = pd.to_numeric(df_disp["readiness_score"], errors="coerce").round(0).astype("Int64")
    if "rpe" in df_disp.columns:
        df_disp["rpe"] = pd.to_numeric(df_disp["rpe"], errors="coerce").round(1)
    if "rir" in df_disp.columns:
        df_disp["rir"] = pd.to_numeric(df_disp["rir"], errors="coerce").round(1)

    # Render HTML table (evita que se rompa el estilo con st.dataframe)
    headers = "".join([f"<th>{h}</th>" for h in df_disp.columns])
    rows: List[str] = []
    for _, row in df_disp.iterrows():
        cells: List[str] = []
        for col in df_disp.columns:
            val = row.get(col)
            if pd.isna(val):
                cell = "—"
            else:
                cell = str(val)
            cells.append(f"<td>{cell}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")

    st.markdown(
        f"""
  <table class='weekly-table'>
    <thead><tr>{headers}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_multiweek_trends(df_weekly: pd.DataFrame) -> None:
    render_section_title("Tendencias multi-semana", accent="#FFB81C")
    n_weeks = st.selectbox("Mostrar últimas N semanas", [8, 12, 16], index=1)

    df = df_weekly.copy().sort_values("week_start", ascending=False).head(int(n_weeks))
    if df.empty:
        st.info("No hay semanas suficientes para tendencias.")
        return

    # Tabla macro
    table_cols = [c for c in ["week_start", "days", "volume_week", "strain", "monotony", "readiness_avg"] if c in df.columns]
    df_table = df[table_cols].copy()
    if "week_start" in df_table.columns:
        df_table["week_start"] = df_table["week_start"].dt.strftime("%d/%m/%Y")

    st.markdown("<div class='weekly-card'>", unsafe_allow_html=True)
    st.markdown("<div class='wk-title'>Macro (semanas)</div>", unsafe_allow_html=True)
    st.markdown("<div class='wk-sub'>Comparativa rápida por semana</div>", unsafe_allow_html=True)

    headers = "".join([f"<th>{h}</th>" for h in df_table.columns])
    rows = []
    for _, row in df_table.iterrows():
        cells = []
        for col in df_table.columns:
            val = row.get(col)
            if pd.isna(val):
                cell = "—"
            elif col in ("volume_week", "strain"):
                cell = _fmt_int(val)
            elif col in ("monotony", "readiness_avg"):
                cell = _fmt_float(val, 2 if col == "monotony" else 0)
            else:
                cell = str(val)
            cells.append(f"<td>{cell}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f"<table class='weekly-table'><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    # Charts (mismo estilo que Modo Hoy)
    cols = st.columns(2)
    with cols[0]:
        if "volume_week" in df.columns:
            s = pd.to_numeric(df.set_index("week_start")["volume_week"], errors="coerce").dropna()
            if not s.empty:
                st.plotly_chart(create_volume_chart(s, title="Volumen semanal"))

        if "readiness_avg" in df.columns:
            s = pd.to_numeric(df.set_index("week_start")["readiness_avg"], errors="coerce").dropna()
            if not s.empty:
                st.plotly_chart(create_readiness_chart(s, title="Readiness promedio"))

    with cols[1]:
        if "strain" in df.columns:
            s = pd.to_numeric(df.set_index("week_start")["strain"], errors="coerce").dropna()
            if not s.empty:
                st.plotly_chart(create_strain_chart(s, title="Strain semanal"))

        if "monotony" in df.columns:
            s = pd.to_numeric(df.set_index("week_start")["monotony"], errors="coerce").dropna()
            if not s.empty:
                st.plotly_chart(_create_monotony_chart(s, title="Monotonía semanal"))


def _render_suggested_sequence(df_week_days: pd.DataFrame, kpis: Dict[str, Any], df_weekly: pd.DataFrame) -> None:
    render_section_title("Secuencia sugerida (próxima semana)", accent="#00D084")

    # Construir strain de 7 días (rellena 0 para días sin data)
    week_strain: List[float] = []
    if not df_week_days.empty and "date" in df_week_days.columns:
        df = df_week_days.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
        df = df.dropna(subset=["date"]).sort_values("date")
        start = df["date"].min()
        if pd.notna(start):
            ws = _monday_week_start(pd.Timestamp(start))
            dates = [ws + pd.Timedelta(days=i) for i in range(7)]
            for d in dates:
                day_rows = df.loc[df["date"] == d]
                if day_rows.empty:
                    week_strain.append(0.0)
                else:
                    if "strain" in day_rows.columns:
                        week_strain.append(float(pd.to_numeric(day_rows["strain"], errors="coerce").fillna(0).sum()))
                    elif "volume" in day_rows.columns:
                        week_strain.append(float(pd.to_numeric(day_rows["volume"], errors="coerce").fillna(0).sum()))
                    else:
                        week_strain.append(0.0)

    if not week_strain:
        week_strain = [0.0] * 7

    # Baselines para el motor (p75 de strain semanal si existe)
    baselines: Dict[str, Any] = {}
    if "strain" in df_weekly.columns:
        strain_clean = pd.to_numeric(df_weekly["strain"], errors="coerce").dropna()
        if len(strain_clean) >= 6:
            baselines["_strain_p75"] = float(strain_clean.quantile(0.75))

    seq = suggest_weekly_sequence(
        last_7_days_strain=week_strain,
        last_7_days_monotony=float(kpis.get("monotony") or 0.0),
        last_7_days_readiness_mean=float(kpis.get("readiness") or 0.0),
        baselines=baselines,
        last_week_high_days=int(sum(1 for x in week_strain if x > 0)),
    )

    st.markdown(
        f"<div class='weekly-muted' style='margin:8px 0 10px 0;'><b>Base:</b> {seq.get('reasoning','')}</div>",
        unsafe_allow_html=True,
    )

    days = seq.get("sequence", [])
    if not days:
        st.info("No se pudo generar una secuencia para la próxima semana.")
        return

    cols = st.columns(7)
    for i, item in enumerate(days[:7]):
        with cols[i]:
            st.markdown(
                f"""
<div class='weekly-card' style='padding:14px 14px;margin:0;'>
  <div style='font-weight:900;color:#E5E7EB'>{item.get('day','')}</div>
  <div class='weekly-muted' style='margin-top:2px;font-weight:800'>{item.get('type','')}</div>
  <div style='margin-top:6px;font-size:0.9rem;color:#E5E7EB;line-height:1.25'>{item.get('description','')}</div>
</div>
                """,
                unsafe_allow_html=True,
            )


def render_semana(df_daily: pd.DataFrame, df_weekly: pd.DataFrame) -> None:
    """Entry point de la vista semanal. Debe mantenerse estable para streamlit_app.py."""
    inject_main_css(st)
    _inject_weekly_view_css()

    if df_weekly is None or df_weekly.empty:
        st.error("❌ weekly.csv no se cargó o está vacío (data/processed/weekly.csv)")
        return
    if "week_start" not in df_weekly.columns:
        st.error("❌ weekly.csv no tiene la columna 'week_start'.")
        return

    df_weekly = df_weekly.copy()
    df_weekly["week_start"] = pd.to_datetime(df_weekly["week_start"], errors="coerce").dt.normalize()
    df_weekly = df_weekly.dropna(subset=["week_start"]).sort_values("week_start")

    with loading("Cargando semana...", compact=True):
        ctx = _compute_week_context(df_weekly)
        week_row = _safe_week_row(df_weekly, ctx.week_start)
        df_week_days = _filter_daily_for_week(df_daily if df_daily is not None else pd.DataFrame(), ctx)

        kpis = _compute_week_kpis(week_row, df_week_days)
        status_info = _compute_week_status(kpis, df_weekly)

    _render_header(ctx, kpis, status_info)
    _render_summary_card(status_info)

    _render_performance(df_week_days, ctx)
    _render_daily_table(df_week_days)

    with st.expander("📈 Tendencias (multi-semana)", expanded=False):
        _render_multiweek_trends(df_weekly)

    _render_suggested_sequence(df_week_days, kpis, df_weekly)
