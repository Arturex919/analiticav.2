"""
Analytics Module — Rental Analytics Platform
Statistical analysis: seasonality, outliers, cyclicity, price elasticity.
"""

import numpy as np
import pandas as pd
from scipy import stats


# ─────────────────────────────────────────────
# SEASONALITY
# ─────────────────────────────────────────────

def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate key KPIs by month number."""
    g = (
        df.groupby("month")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ticket_medio=("amount", "mean"),
            noches_totales=("nights", "sum"),
            ppn_medio=("price_per_night", "mean"),
        )
        .round(2)
    )
    g["month_name"] = g.index.map(lambda m: {
        1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
        7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"
    }.get(m, str(m)))
    g["pct_ingresos"] = (g["ingresos"] / g["ingresos"].sum() * 100).round(1)
    return g.reset_index()


def quarterly_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("quarter")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ticket_medio=("amount", "mean"),
            ppn_medio=("price_per_night", "mean"),
        )
        .round(2)
        .reset_index()
    )


def dow_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Day-of-week analysis."""
    DOW_ORDER = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    g = (
        df.groupby("dow")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ppn_medio=("price_per_night", "mean"),
        )
        .round(2)
        .reindex([d for d in DOW_ORDER if d in df["dow"].unique()])
        .reset_index()
    )
    return g


def seasonal_summary(df: pd.DataFrame) -> pd.DataFrame:
    SEASON_ORDER = ["Invierno","Primavera","Verano","Otoño"]
    g = (
        df.groupby("season")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ticket_medio=("amount", "mean"),
            ppn_medio=("price_per_night", "mean"),
        )
        .round(2)
        .reindex([s for s in SEASON_ORDER if s in df["season"].unique()])
        .reset_index()
    )
    return g


def channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = (
        df.groupby("channel")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ticket_medio=("amount", "mean"),
            ppn_medio=("price_per_night", "mean"),
        )
        .sort_values("ingresos", ascending=False)
        .round(2)
        .reset_index()
    )
    g["comision_est"] = g["channel"].map({
        "Booking.com": 0.15,
        "Airbnb": 0.14,
        "HomeAway/VRBO": 0.12,
    }).fillna(0.0)
    g["ingresos_netos"] = (g["ingresos"] * (1 - g["comision_est"])).round(2)
    return g


def property_summary(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    g = (
        df.groupby("property")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ticket_medio=("amount", "mean"),
            noches_totales=("nights", "sum"),
            ppn_medio=("price_per_night", "mean"),
        )
        .sort_values("ingresos", ascending=False)
        .head(top_n)
        .round(2)
        .reset_index()
    )
    return g


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("year")
        .agg(
            reservas=("amount", "count"),
            ingresos=("amount", "sum"),
            ticket_medio=("amount", "mean"),
            ppn_medio=("price_per_night", "mean"),
        )
        .round(2)
        .reset_index()
    )


# ─────────────────────────────────────────────
# OUTLIER DETECTION
# ─────────────────────────────────────────────

def detect_outliers_iqr(series: pd.Series, factor: float = 1.5) -> pd.Series:
    """Returns boolean mask — True = outlier."""
    Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
    IQR = Q3 - Q1
    return (series < Q1 - factor * IQR) | (series > Q3 + factor * IQR)


def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    z = np.abs(stats.zscore(series.dropna()))
    mask = pd.Series(False, index=series.index)
    mask.loc[series.dropna().index] = z > threshold
    return mask


def outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    """Returns top outlier reservations by amount."""
    df = df.copy()
    df["is_outlier_iqr"]  = detect_outliers_iqr(df["amount"])
    df["is_outlier_z"]    = detect_outliers_zscore(df["amount"])
    df["is_outlier"]      = df["is_outlier_iqr"] | df["is_outlier_z"]
    return df[df["is_outlier"]].sort_values("amount", ascending=False)


def monthly_demand_peaks(df: pd.DataFrame) -> dict:
    """Identify statistical peak months vs valley months."""
    m = monthly_summary(df)
    mean_res = m["reservas"].mean()
    std_res  = m["reservas"].std()
    m["z_score"] = (m["reservas"] - mean_res) / std_res
    peaks   = m[m["z_score"] > 0.8]["month_name"].tolist()
    valleys = m[m["z_score"] < -0.8]["month_name"].tolist()
    return {"peaks": peaks, "valleys": valleys, "data": m}


# ─────────────────────────────────────────────
# PRICE ELASTICITY
# ─────────────────────────────────────────────

def price_elasticity(df: pd.DataFrame, n_bins: int = 10) -> dict:
    """
    Estimate price elasticity of demand.
    Bins bookings by price-per-night; computes occupancy proxy per bin.
    Returns elasticity coefficient and binned data.
    """
    d = df[["price_per_night","nights"]].dropna()
    d = d[d["price_per_night"] > 0]

    # Winsorize at 95th percentile to remove extreme outliers
    cap = d["price_per_night"].quantile(0.95)
    d   = d[d["price_per_night"] <= cap]

    d["price_bin"] = pd.cut(d["price_per_night"], bins=n_bins)
    binned = (
        d.groupby("price_bin", observed=True)
        .agg(
            bookings=("nights", "count"),
            avg_nights=("nights", "mean"),
            avg_price=("price_per_night", "mean"),
        )
        .reset_index()
    )
    binned = binned.dropna()
    binned["demand"] = binned["bookings"] * binned["avg_nights"]

    # OLS log-log regression: ln(Q) = a + b·ln(P)
    x = np.log(binned["avg_price"].values + 1)
    y = np.log(binned["demand"].values + 1)
    
    slope, intercept, r_sq, p_val = 0.0, 0.0, 0.0, 1.0
    trend_line = []

    try:
        if len(x) >= 3:
            slope, intercept, r, p, se = stats.linregress(x, y)
            r_sq = r**2
            p_val = p
            # Generar línea de tendencia en espacio original
            x_range = np.linspace(x.min(), x.max(), 50)
            y_pred = intercept + slope * x_range
            trend_line = pd.DataFrame({
                "price": np.exp(x_range) - 1,
                "demand_pred": np.exp(y_pred) - 1
            })
    except Exception:
        pass

    # Find sweet-spot: highest revenue (P*Q) bin
    binned["revenue_proxy"] = binned["avg_price"] * binned["demand"]
    sweet_spot = binned.loc[binned["revenue_proxy"].idxmax(), "avg_price"] if not binned.empty else 0.0

    return {
        "elasticity":   round(slope, 3),
        "r_squared":    round(r_sq, 3),
        "p_value":      round(p_val, 4),
        "sweet_spot":   round(sweet_spot, 2),
        "binned":       binned,
        "trend_line":   trend_line,
        "interpretation": _elasticity_label(slope),
    }


def _elasticity_label(e: float) -> str:
    if e > -0.5:
        return "Demanda inelástica — puedes subir precios sin perder muchas reservas."
    elif e > -1.0:
        return "Elasticidad moderada — incrementos de precio moderados son sostenibles."
    else:
        return "Demanda elástica — los clientes son sensibles al precio, sube gradualmente."


def dynamic_pricing_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-month price recommendation:
    - Peak months   → +15-25 % sobre precio base
    - High months   → +8-12 %
    - Normal months → precio base
    - Valley months → -5-10 % (impulso con descuento temprano)
    """
    m = monthly_summary(df)
    base = m["ppn_medio"].median()

    thresholds = {
        "Pico":   m["reservas"].quantile(0.80),
        "Alto":   m["reservas"].quantile(0.60),
        "Normal": m["reservas"].quantile(0.40),
    }

    def tier(row):
        if row["reservas"] >= thresholds["Pico"]:
            return "Pico", base * 1.22
        elif row["reservas"] >= thresholds["Alto"]:
            return "Alto", base * 1.10
        elif row["reservas"] >= thresholds["Normal"]:
            return "Normal", base
        else:
            return "Valle", base * 0.92

    m[["demand_tier","precio_sugerido_ppn"]] = m.apply(
        lambda r: pd.Series(tier(r)), axis=1
    )
    m["precio_sugerido_ppn"] = m["precio_sugerido_ppn"].round(2)
    m["delta_pct"] = ((m["precio_sugerido_ppn"] - base) / base * 100).round(1)
    m["base_ppn"] = round(base, 2)
    return m


# ─────────────────────────────────────────────
# HEATMAP / TIME-SERIES HELPERS
# ─────────────────────────────────────────────

def monthly_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """Year × Month pivot of booking counts."""
    piv = (
        df.groupby(["year","month"])["amount"]
        .count()
        .reset_index()
        .pivot(index="year", columns="month", values="amount")
        .fillna(0)
    )
    piv.columns = [
        {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}.get(c,c)
        for c in piv.columns
    ]
    return piv


def time_series_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Month-level revenue time series."""
    ts = (
        df.groupby("year_month")
        .agg(
            reservas=("amount","count"),
            ingresos=("amount","sum"),
            ppn_medio=("price_per_night","mean"),
        )
        .round(2)
        .reset_index()
    )
    ts["period"] = pd.to_datetime(ts["year_month"])
    return ts.sort_values("period")


# ─────────────────────────────────────────────
# PROPERTY-LEVEL MONTHLY ANALYSIS
# ─────────────────────────────────────────────

def property_monthly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a pivot table of Property vs Year-Month revenue."""
    if df.empty or "property" not in df.columns or "year_month" not in df.columns:
        return pd.DataFrame()
    
    perf = (
        df.groupby(["property", "year_month"])["amount"]
        .sum()
        .unstack(fill_value=0)
    )
    # Sort columns (year_month) chronologically
    perf = perf.reindex(sorted(perf.columns), axis=1)
    return perf


def property_peaks_valleys(df: pd.DataFrame) -> pd.DataFrame:
    """Identifies max and min revenue months for each property."""
    if df.empty or "property" not in df.columns or "year_month" not in df.columns:
        return pd.DataFrame()

    # Group by property and year_month to get monthly revenue per property
    m_perf = df.groupby(["property", "year_month"])["amount"].sum().reset_index()
    
    results = []
    for prop in m_perf["property"].unique():
        prop_data = m_perf[m_perf["property"] == prop].sort_values("amount")
        if prop_data.empty: continue
        
        valley = prop_data.iloc[0]
        peak = prop_data.iloc[-1]
        avg = prop_data["amount"].mean()
        
        results.append({
            "Propiedad": prop,
            "Mes Pico": peak["year_month"],
            "Valor Pico": peak["amount"],
            "Mes Valle": valley["year_month"],
            "Valor Valle": valley["amount"],
            "Media Mensual": avg
        })
    
    return pd.DataFrame(results).sort_values("Valor Pico", ascending=False)


def property_deep_dive(df: pd.DataFrame, prop_name: str) -> dict:
    """Detailed SWOT-like analysis for a specific property."""
    if df.empty or prop_name not in df["property"].unique():
        return {}
    
    p_df = df[df["property"] == prop_name]
    global_avg_ppn = df["price_per_night"].mean()
    global_avg_ticket = df["amount"].mean()
    
    p_avg_ppn = p_df["price_per_night"].mean()
    p_avg_ticket = p_df["amount"].mean()
    p_total_rev = p_df["amount"].sum()
    
    # 1. PROS
    pros = []
    if p_avg_ppn > global_avg_ppn * 1.1:
        pros.append(f"ADR Superior: Su precio por noche ({p_avg_ppn:.0f}€) es un {((p_avg_ppn/global_avg_ppn)-1)*100:.1f}% superior a la media.")
    if len(p_df) > df.groupby("property")["amount"].count().mean():
        pros.append("Alta Rotación: Tiene un volumen de reservas superior al promedio de la cartera.")
    
    # Channel health
    ch_dist = p_df["channel"].value_counts(normalize=True)
    if ch_dist.iloc[0] < 0.5:
        pros.append("Diversificación de Canales: No depende críticamente de una sola fuente de ingresos.")
    
    # 2. CONTRAS
    cons = []
    if p_avg_ppn < global_avg_ppn * 0.9:
        cons.append(f"ADR Bajo: El precio por noche está por debajo de la media global ({global_avg_ppn:.0f}€).")
    
    # Volatility
    m_rev = p_df.groupby("month")["amount"].sum()
    if m_rev.std() / m_rev.mean() > 0.5:
        cons.append("Alta Volatilidad Estacional: Los ingresos fluctúan drásticamente entre meses.")
        
    if ch_dist.iloc[0] > 0.7:
        cons.append(f"Riesgo de Dependencia: El {ch_dist.iloc[0]*100:.0f}% de reservas vienen de {ch_dist.index[0]}.")

    # 3. PRICING ADVICE
    # Identify months with high PPN but also high volume -> consistent demand
    m_stats = p_df.groupby("month").agg(
        rev=("amount", "sum"),
        count=("amount", "count"),
        ppn=("price_per_night", "mean")
    )
    
    # Months to RAISE prices (High volume, high PPN already)
    peak_months = m_stats[m_stats["count"] >= m_stats["count"].median()].index.tolist()
    
    # Map back to names
    month_map = {
        1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
        7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
    }
    
    raise_months = [month_map[m] for m in peak_months if m in month_map]
    
    return {
        "pros": pros if pros else ["Rendimiento estable."],
        "cons": cons if cons else ["No se detectan riesgos críticos."],
        "raise_months": raise_months,
        "metrics": {
            "rev_total": p_total_rev,
            "ppn": p_avg_ppn,
            "bookings": len(p_df)
        }
    }
