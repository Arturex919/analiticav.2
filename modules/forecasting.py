"""
Forecasting Module — Rental Analytics Platform
Simple predictive models: trend decomposition + seasonal naive forecast.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def _build_ts(df: pd.DataFrame, metric: str = "ingresos") -> pd.DataFrame:
    """Build a clean monthly time series."""
    ts = (
        df.groupby("year_month")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ppn_medio=("price_per_night", "mean"),
        )
        .reset_index()
    )
    ts["period"] = pd.to_datetime(ts["year_month"])
    ts = ts.sort_values("period").reset_index(drop=True)
    ts["ppn_medio"] = ts["ppn_medio"].ffill()
    return ts


def seasonal_naive_forecast(df: pd.DataFrame,
                             horizon_months: int = 12,
                             metric: str = "ingresos") -> pd.DataFrame:
    """
    Seasonal naïve forecast: each future month = same month last year ± trend_delta.
    Adds simple OLS trend correction on annual aggregates.
    """
    ts = _build_ts(df, metric)
    if ts.empty or len(ts) < 12:
        return pd.DataFrame()

    # Only use completed years for stable seasonality
    ts["month"] = ts["period"].dt.month
    ts["year"]  = ts["period"].dt.year

    # Seasonal index: avg by month / overall avg
    seasonal_avg = ts.groupby("month")[metric].mean()
    overall_avg  = ts[metric].mean()
    seasonal_idx = (seasonal_avg / overall_avg).to_dict()

    # Trend: OLS on annual totals
    annual = ts.groupby("year")[metric].sum().reset_index()
    if len(annual) >= 2:
        x = annual["year"].values - annual["year"].min()
        y = annual[metric].values
        slope = np.polyfit(x, y, 1)[0]   # € per year
        monthly_trend = slope / 12
    else:
        monthly_trend = 0

    # Baseline = last 12-month rolling avg
    baseline = ts[metric].rolling(12, min_periods=3).mean().iloc[-1]

    # Generate future periods
    last_period = ts["period"].max()
    forecast_rows = []
    for i in range(1, horizon_months + 1):
        future = last_period + pd.DateOffset(months=i)
        m = future.month
        trend_adj = monthly_trend * i
        point = max(0, baseline * seasonal_idx.get(m, 1.0) + trend_adj)
        # Confidence interval ±20 % (empirical)
        ci_lo = point * 0.80
        ci_hi = point * 1.20
        forecast_rows.append({
            "period":    future,
            "year_month": future.strftime("%Y-%m"),
            "month":     m,
            "forecast":  round(point, 2),
            "ci_low":    round(ci_lo, 2),
            "ci_high":   round(ci_hi, 2),
            "is_peak":   m in [7, 8],
        })

    forecast_df = pd.DataFrame(forecast_rows)
    return forecast_df


def price_opportunity_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recommends months where pricing can be raised based on:
    - High demand (top 30 % months)
    - Lead time signal (early bookings = strong demand)
    - Historical PPNs well below seasonal peak
    """
    from modules.analytics import monthly_summary, dynamic_pricing_recommendations
    pricing = dynamic_pricing_recommendations(df)
    forecast = seasonal_naive_forecast(df, horizon_months=12)

    if forecast.empty:
        return pricing

    pricing = pricing.merge(
        forecast[["month","forecast","is_peak"]].rename(
            columns={"forecast":"forecast_ingresos"}
        ),
        on="month", how="left"
    )
    pricing["oportunidad"] = pricing.apply(_opportunity_label, axis=1)
    return pricing


def _opportunity_label(row) -> str:
    tier = row.get("demand_tier","Normal")
    if tier == "Pico":
        return "🔴 Subir precio YA (+20-25 %)"
    elif tier == "Alto":
        return "🟡 Subir precio moderado (+8-12 %)"
    elif tier == "Normal":
        return "🟢 Mantener precio"
    else:
        return "🔵 Ofrecer early-bird (-8 %)"


def growth_metrics(df: pd.DataFrame) -> dict:
    """YoY and MoM growth rates."""
    ts = _build_ts(df)
    ts["year"]  = ts["period"].dt.year
    ts["month"] = ts["period"].dt.month

    annual = ts.groupby("year")["ingresos"].sum()
    if len(annual) >= 2:
        yoy = ((annual.iloc[-1] - annual.iloc[-2]) / annual.iloc[-2] * 100)
    else:
        yoy = 0.0

    if len(ts) >= 2:
        mom = ((ts["ingresos"].iloc[-1] - ts["ingresos"].iloc[-2]) / ts["ingresos"].iloc[-2] * 100)
    else:
        mom = 0.0

    return {
        "yoy_growth_pct": round(yoy, 1),
        "mom_growth_pct": round(mom, 1),
        "total_revenue":  round(ts["ingresos"].sum(), 2),
        "avg_monthly":    round(ts["ingresos"].mean(), 2),
        "best_month":     ts.loc[ts["ingresos"].idxmax(), "year_month"] if not ts.empty else "-",
    }
