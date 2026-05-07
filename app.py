"""
╔══════════════════════════════════════════════════════════════════════╗
║         RENTAL ANALYTICS PLATFORM  •  v1.0                         ║
║         Senior BI Dashboard — Streamlit + Plotly                    ║
╚══════════════════════════════════════════════════════════════════════╝
Run:  streamlit run app.py
"""

import sys
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from groq import Groq

# ── Add project root to path ──
sys.path.insert(0, ".")
from modules.etl         import load_file, clean_and_enrich, filter_confirmed_paid, quality_report
from modules.analytics   import (
    monthly_summary, quarterly_summary, dow_summary, seasonal_summary,
    channel_summary, property_summary, yearly_trend,
    monthly_heatmap_data, time_series_monthly,
    monthly_demand_peaks, outlier_report, price_elasticity,
    dynamic_pricing_recommendations,
    property_monthly_performance, property_peaks_valleys,
    property_deep_dive
)
from modules.forecasting import (
    seasonal_naive_forecast, price_opportunity_calendar, growth_metrics
)
# ── AI Config ──
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ─────────────────────────────────────────────
# STREAMLIT CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Rental Analytics Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global color palette ──
C_PRIMARY   = "#1E3A5F"
C_ACCENT    = "#E8A838"
C_SUCCESS   = "#2ECC71"
C_DANGER    = "#E74C3C"
C_LIGHT     = "#F0F4F8"
PALETTE     = [C_PRIMARY, C_ACCENT, "#3498DB", "#9B59B6", C_SUCCESS, C_DANGER,
               "#1ABC9C", "#F39C12", "#2C3E50", "#E91E63"]

# ── Inject custom CSS ──
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #1E3A5F; }
  [data-testid="stSidebar"] label p, [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: white !important; }
  [data-testid="stSidebar"] .stCaption { color: #A0C4FF !important; }
  /* Fix para elementos con fondo claro (selects, botones, uploaders) */
  [data-testid="stSidebar"] div[data-baseweb="select"] * { color: #1E3A5F !important; }
  [data-testid="stSidebar"] button p { color: #1E3A5F !important; }
  [data-testid="stSidebar"] section[data-testid="stFileUploadDropzone"] p { color: #1E3A5F !important; }
  [data-testid="stSidebar"] [data-testid="stFileUploaderFileName"] { color: white !important; }
  .metric-card {
    background: white; border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,.08); border-left: 5px solid #1E3A5F;
    margin-bottom: 8px;
  }
  .metric-card.accent { border-left-color: #E8A838; }
  .metric-card.success { border-left-color: #2ECC71; }
  .metric-card.danger  { border-left-color: #E74C3C; }
  .metric-value { font-size: 2rem; font-weight: 700; color: #1E3A5F; }
  .metric-label { font-size: 0.85rem; color: #666; margin-top: 4px; }
  .metric-delta { font-size: 0.9rem; font-weight: 600; }
  .section-title { font-size: 1.3rem; font-weight: 700; color: #1E3A5F;
                   border-bottom: 3px solid #E8A838; padding-bottom: 8px; margin: 24px 0 16px; }
  .badge-peak   { background:#E74C3C; color:white; padding:2px 10px; border-radius:20px; font-size:.8rem; }
  .badge-valley { background:#3498DB; color:white; padding:2px 10px; border-radius:20px; font-size:.8rem; }
  .badge-ok     { background:#2ECC71; color:white; padding:2px 10px; border-radius:20px; font-size:.8rem; }
  .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
  
  /* --- ChatBot Styles --- */
  .chat-container {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(30, 58, 95, 0.1);
    backdrop-filter: blur(10px);
  }
  .stChatMessage {
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
  }
  .chat-bubble-assistant {
    background: linear-gradient(135deg, #1E3A5F 0%, #2c3e50 100%);
    color: white;
    padding: 15px 20px;
    border-radius: 18px 18px 18px 2px;
    margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(30, 58, 95, 0.2);
    font-size: 0.95rem;
    line-height: 1.5;
  }
  .chat-bubble-user {
    background: #F0F4F8;
    color: #1E3A5F;
    padding: 12px 18px;
    border-radius: 18px 18px 2px 18px;
    margin-bottom: 20px;
    border: 1px solid #D1D9E6;
    font-size: 0.95rem;
    text-align: right;
  }
  .assistant-avatar {
    width: 35px; height: 35px; border-radius: 50%;
    background: #E8A838; display: inline-flex;
    align-items: center; justify-content: center;
    margin-right: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  }
  .chat-scroll-area {
    height: 550px;
    overflow-y: auto;
    padding: 15px;
    border-radius: 12px;
    background: rgba(240, 244, 248, 0.3);
    margin-bottom: 10px;
    border: 1px solid rgba(30, 58, 95, 0.05);
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def fmt_eur(n: float) -> str:
    return f"€ {n:,.0f}".replace(",",".")

def fmt_pct(n: float) -> str:
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:.1f} %"

def metric_card(label: str, value: str, delta: str = "", cls: str = ""):
    delta_html = f'<div class="metric-delta" style="color:{"#2ECC71" if "+" in delta else "#E74C3C"}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="metric-card {cls}">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
      {delta_html}
    </div>""", unsafe_allow_html=True)

def plotly_defaults(fig, height=400):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E5E5E5", linecolor="#CCCCCC")
    fig.update_yaxes(showgrid=True, gridcolor="#E5E5E5", linecolor="#CCCCCC")
    return fig


# ─────────────────────────────────────────────
# SIDEBAR — FILE UPLOAD & FILTERS
# ─────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/FFFFFF/home.png", width=48)
    st.title("Rental Analytics")
    st.caption("v1.0 · BI Platform")
    st.markdown("---")

    uploaded = st.file_uploader(
        "📂 Cargar datos",
        type=["csv", "xlsx", "xls", "pdf", "docx"],
        help="CSV, Excel, PDF o DOCX de reservas"
    )

    st.markdown("---")
    st.markdown("**⚙️ Filtros globales**")

    # Placeholder before data loads
    year_filter      = []
    channel_filter   = []
    property_filter  = []
    status_filter    = "Solo confirmadas con ingreso"


# ─────────────────────────────────────────────
# MAIN — LOAD & PROCESS
# ─────────────────────────────────────────────

if uploaded is None:
    # ── Welcome screen ──
    st.markdown("# 🏠 Rental Analytics Platform")
    st.markdown(
        "Sube tu archivo de reservas en el panel izquierdo para comenzar el análisis. "
        "Formatos soportados: **CSV · Excel · PDF · DOCX**"
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**📊 Dashboard Ejecutivo**\nKPIs, tendencias y evolución temporal.")
    with c2:
        st.info("**📈 Análisis de Estacionalidad**\nPicos, valles, días festivos.")
    with c3:
        st.info("**💰 Dynamic Pricing**\nElasticidad y recomendaciones de precio.")
    st.stop()


# ── Load & clean ──
if uploaded is not None:
    @st.cache_data(show_spinner="⚙️ Procesando datos…")
    def process_v3(file):
        raw = load_file(file)
        clean = clean_and_enrich(raw)
        return raw, clean

    try:
        raw_df, clean_df = process_v3(uploaded)
        # ── Quality report ──
        qr = quality_report(raw_df, clean_df)
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        st.stop()
else:
    st.stop()

# ── Hybrid Cleaning Area (Master Prompt Task) ──
with st.sidebar:
    st.markdown("---")
    st.markdown("**🛡️ Auditoría de Datos**")
    manual_cleaning = st.toggle("Limpieza Manual (Modo Híbrido)", value=False, help="Permite decidir qué columnas borrar e imputar nulos.")

if manual_cleaning:
    with st.expander("🛠️ Estación de Limpieza Manual", expanded=True):
        st.info("Configura los parámetros de limpieza antes de proceder a la analítica.")
        
        c_cl1, c_cl2 = st.columns(2)
        with c_cl1:
            cols_to_drop = st.multiselect("Eliminar columnas ruidosas:", options=clean_df.columns)
            if cols_to_drop:
                clean_df = clean_df.drop(columns=cols_to_drop)
                
        with c_cl2:
            impute_opt = st.selectbox("Estrategia de Imputación (Nulos):", ["Ninguna", "Media", "Mediana", "Cero"])
            if impute_opt != "Ninguna":
                from modules.etl import impute_missing
                clean_df = impute_missing(clean_df, strategy=impute_opt.lower())

        remove_outliers = st.checkbox("Filtrar Outliers identificados (IQR x3)", value=True)
        if remove_outliers:
            if "_is_outlier" in clean_df.columns:
                clean_df = clean_df[~clean_df["_is_outlier"]]
                st.success(f"Filtrado completado. Filas útiles: {len(clean_df):,}")
            else:
                st.warning("No se pudo realizar el filtrado: columna de outliers no detectada.")

# Actualizar reporte de calidad tras limpieza híbrida
qr = quality_report(raw_df, clean_df)

# ── Sidebar filters (now we have data) ──
with st.sidebar:
    st.markdown("**⚙️ Filtros de tiempo**")
    
    # --- AÑO ---
    all_years = ["Todos"] + sorted(clean_df["year"].dropna().unique().astype(int).tolist(), reverse=True)
    sel_year = st.selectbox("Seleccionar Año", all_years, index=0)
    
    # --- MES ---
    all_months_names = ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    sel_month = st.selectbox("Seleccionar Mes", all_months_names, index=0)

    st.markdown("---")
    st.markdown("**⚙️ Otros Filtros**")

    # --- CANAL ---
    all_channels_list = ["Todos"] + sorted(clean_df["channel"].dropna().unique().tolist())
    sel_channel = st.selectbox("Canal de Venta", all_channels_list, index=0)

    status_filter = st.radio(
        "Estado de Reservas",
        ["Solo confirmadas con ingreso", "Todas las confirmadas", "Todas"],
        index=0
    )

    st.caption(f"📋 {qr['total_rows']:,} filas · {qr['properties']} propiedades")

# ── Apply filters ──
df = clean_df.copy()

if status_filter == "Solo confirmadas con ingreso":
    df = filter_confirmed_paid(df)
elif status_filter == "Todas las confirmadas":
    df = df[df["status_group"] == "Confirmada"]

# --- Aplicar Selectores ---
if sel_year != "Todos":
    df = df[df["year"] == int(sel_year)]

if sel_month != "Todos":
    month_map_inv = {
        "Enero":1, "Febrero":2, "Marzo":3, "Abril":4, "Mayo":5, "Junio":6,
        "Julio":7, "Agosto":8, "Septiembre":9, "Octubre":10, "Noviembre":11, "Diciembre":12
    }
    df = df[df["month"] == month_map_inv[sel_month]]

if sel_channel != "Todos":
    df = df[df["channel"] == sel_channel]

if df.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados.")
    st.stop()


# ─────────────────────────────────────────────
# HEADER KPIs
# ─────────────────────────────────────────────

st.markdown("# 🏠 Rental Analytics Platform")
st.caption(f"Periodo analizado: **{df['arrival'].min().strftime('%d/%m/%Y') if 'arrival' in df else '—'}** → **{df['arrival'].max().strftime('%d/%m/%Y') if 'arrival' in df else '—'}**")

st.markdown("---")


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📈 Tendencia Temporal",
    "🗓️ Estacionalidad",
    "💰 Precios & Elasticidad",
    "🔮 Forecast",
    "🏢 Propiedades & Canales",
    "🔍 Perfil de Propiedad",
    "⚠️ Outliers & Calidad",
    "🤖 BI Assistant",
])


# ══════════════════════════════════════════════
# TAB 1 — TEMPORAL TREND
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">Evolución mensual de ingresos y reservas</div>', unsafe_allow_html=True)
    ts = time_series_monthly(df)

    if not ts.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=ts["year_month"], y=ts["ingresos"], name="Ingresos (€)",
                   marker_color=C_PRIMARY, opacity=0.85),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=ts["year_month"], y=ts["reservas"], name="Reservas",
                       mode="lines+markers", line=dict(color=C_ACCENT, width=2.5),
                       marker=dict(size=5)),
            secondary_y=True
        )
        # Rolling avg
        ts["rolling_avg"] = ts["ingresos"].rolling(3, min_periods=1).mean()
        fig.add_trace(
            go.Scatter(x=ts["year_month"], y=ts["rolling_avg"], name="Media móvil 3M",
                       mode="lines", line=dict(color=C_SUCCESS, dash="dot", width=2)),
            secondary_y=False
        )
        fig.update_yaxes(title_text="Ingresos (€)", secondary_y=False)
        fig.update_yaxes(title_text="N.º Reservas", secondary_y=True)
        plotly_defaults(fig, height=420)
        st.plotly_chart(fig, use_container_width=True)

    # YoY comparison
    st.markdown('<div class="section-title">Comparativa Año a Año</div>', unsafe_allow_html=True)
    yt = yearly_trend(df)
    if not yt.empty:
        fig2 = make_subplots(1, 2, subplot_titles=("Ingresos por año", "Ticket medio y PPN"))
        fig2.add_trace(go.Bar(x=yt["year"].astype(str), y=yt["ingresos"],
                               marker_color=PALETTE[:len(yt)], name="Ingresos"), row=1, col=1)
        fig2.add_trace(go.Scatter(x=yt["year"].astype(str), y=yt["ticket_medio"],
                                   name="Ticket medio", line=dict(color=C_ACCENT, width=2.5)), row=1, col=2)
        fig2.add_trace(go.Scatter(x=yt["year"].astype(str), y=yt["ppn_medio"],
                                   name="PPN medio", line=dict(color=C_SUCCESS, width=2.5,dash="dot")), row=1, col=2)
        plotly_defaults(fig2, height=360)
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 2 — SEASONALITY
# ══════════════════════════════════════════════
with tab2:
    peaks_data = monthly_demand_peaks(df)
    peaks   = peaks_data["peaks"]
    valleys = peaks_data["valleys"]

    c_left, c_right = st.columns([2, 1])
    with c_left:
        st.markdown('<div class="section-title">Reservas por mes — Estacionalidad</div>', unsafe_allow_html=True)
        m = peaks_data["data"]
        colors = [
            C_DANGER  if mn in peaks else
            "#3498DB" if mn in valleys else
            C_PRIMARY
            for mn in m["month_name"]
        ]
        fig = go.Figure(go.Bar(
            x=m["month_name"], y=m["reservas"],
            marker_color=colors,
            text=m["reservas"], textposition="outside",
            customdata=np.stack([m["ingresos"], m["ppn_medio"]], axis=-1),
            hovertemplate="<b>%{x}</b><br>Reservas: %{y}<br>Ingresos: €%{customdata[0]:,.0f}<br>PPN: €%{customdata[1]:.1f}<extra></extra>"
        ))
        fig.add_hline(y=m["reservas"].mean(), line_dash="dot", line_color=C_ACCENT,
                      annotation_text="Media", annotation_position="right")
        plotly_defaults(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.markdown('<div class="section-title">Meses pico vs valle</div>', unsafe_allow_html=True)
        st.markdown("**🔴 Meses PICO** (mayor demanda)")
        for p in peaks:
            st.markdown(f'<span class="badge-peak">{p}</span>&nbsp;', unsafe_allow_html=True)
        st.markdown("<br>**🔵 Meses VALLE** (menor demanda)", unsafe_allow_html=True)
        for v in valleys:
            st.markdown(f'<span class="badge-valley">{v}</span>&nbsp;', unsafe_allow_html=True)

        st.markdown("---")
        qs = seasonal_summary(df)
        st.markdown("**Resumen por temporada**")
        for _, row in qs.iterrows():
            pct = row["ingresos"] / df["amount"].sum() * 100
            st.markdown(f"**{row['season']}** — {fmt_eur(row['ingresos'])} ({pct:.1f}%)")

    st.markdown('<div class="section-title">Heatmap: Reservas por Año × Mes</div>', unsafe_allow_html=True)
    hm = monthly_heatmap_data(df)
    if not hm.empty:
        fig_hm = px.imshow(
            hm,
            color_continuous_scale=["#F0F4F8", C_PRIMARY],
            aspect="auto",
            labels={"color": "Reservas"},
        )
        fig_hm.update_traces(
            hovertemplate="Año: %{y}<br>Mes: %{x}<br>Reservas: %{z}<extra></extra>"
        )
        plotly_defaults(fig_hm, height=300)
        st.plotly_chart(fig_hm, use_container_width=True)

    st.markdown('<div class="section-title">Día de la semana con mayor ocupación</div>', unsafe_allow_html=True)
    dw = dow_summary(df)
    if not dw.empty:
        fig_dow = px.bar(dw, x="dow", y="reservas", color="ppn_medio",
                         color_continuous_scale=["#3498DB", C_DANGER],
                         text="reservas",
                         labels={"dow":"Día","reservas":"Reservas","ppn_medio":"PPN (€)"})
        fig_dow.update_traces(textposition="outside")
        plotly_defaults(fig_dow, height=340)
        st.plotly_chart(fig_dow, use_container_width=True)

    # Quarterly
    st.markdown('<div class="section-title">Análisis Trimestral</div>', unsafe_allow_html=True)
    qs2 = quarterly_summary(df)
    cols_q = st.columns(4)
    for i, row in qs2.iterrows():
        with cols_q[i % 4]:
            metric_card(
                row["quarter"],
                fmt_eur(row["ingresos"]),
                f'{row["reservas"]} reservas',
                "accent" if row["ingresos"] == qs2["ingresos"].max() else ""
            )


# ══════════════════════════════════════════════
# TAB 3 — PRICING & ELASTICITY
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">Análisis de Elasticidad Precio-Demanda</div>', unsafe_allow_html=True)

    elast = price_elasticity(df)

    e_col1, e_col2, e_col3 = st.columns(3)
    with e_col1:
        metric_card("Elasticidad", str(elast["elasticity"]),
                    "Coeficiente log-log", "danger" if elast["elasticity"] < -1 else "success")
    with e_col2:
        metric_card("R² del modelo", str(elast["r_squared"]), f'p={elast["p_value"]}')
    with e_col3:
        metric_card("Precio Óptimo Estimado", f"€ {elast['sweet_spot']:.0f}/noche",
                    "Máximo ingreso por reserva", "accent")

    st.info(f"💡 **Interpretación:** {elast['interpretation']}")

    # Elasticity scatter
    bd = elast["binned"].dropna()
    tl = elast.get("trend_line", [])

    if not bd.empty:
        fig_e = make_subplots(1, 2, subplot_titles=("Curva de Demanda Estimada", "Frontera de Maximización de Ingresos"))
        
        # Plot 1: Points + Trend Line
        fig_e.add_trace(
            go.Scatter(x=bd["avg_price"], y=bd["demand"],
                       mode="markers", name="Datos reales",
                       marker=dict(size=12, color=C_PRIMARY, line=dict(width=1, color="white"))),
            row=1, col=1
        )
        if not tl.empty:
            fig_e.add_trace(
                go.Scatter(x=tl["price"], y=tl["demand_pred"],
                           mode="lines", name="Regresión Log-Log",
                           line=dict(color=C_ACCENT, width=3)),
                row=1, col=1
            )

        # Plot 2: Revenue Proxy
        fig_e.add_trace(
            go.Bar(x=bd["avg_price"].round(0), y=bd["revenue_proxy"],
                   name="Captura de Ingresos", marker_color=C_SUCCESS, opacity=0.7),
            row=1, col=2
        )
        # Mark sweet spot
        fig_e.add_vline(x=elast["sweet_spot"], line_dash="dash", line_color=C_DANGER,
                        annotation_text=f"Óptimo €{elast['sweet_spot']:.0f}", row=1, col=2)
        plotly_defaults(fig_e, height=380)
        st.plotly_chart(fig_e, use_container_width=True)

    st.markdown('<div class="section-title">Recomendaciones de Dynamic Pricing por Mes</div>', unsafe_allow_html=True)
    pricing_df = dynamic_pricing_recommendations(df)
    TIER_COLORS = {"Pico":"#E74C3C","Alto":"#F39C12","Normal":"#2ECC71","Valle":"#3498DB"}

    fig_p = go.Figure()
    for tier, color in TIER_COLORS.items():
        sub = pricing_df[pricing_df["demand_tier"] == tier]
        fig_p.add_trace(go.Bar(
            x=sub["month_name"], y=sub["precio_sugerido_ppn"],
            name=tier, marker_color=color,
            text=sub["delta_pct"].apply(lambda x: fmt_pct(x)),
            textposition="outside",
        ))
    fig_p.add_hline(y=pricing_df["base_ppn"].iloc[0], line_dash="dot", line_color="#666",
                    annotation_text=f"Base €{pricing_df['base_ppn'].iloc[0]:.0f}/noche")
    plotly_defaults(fig_p, height=380)
    fig_p.update_layout(barmode="group", xaxis_title="Mes", yaxis_title="PPN Sugerido (€)")
    st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("**📋 Tabla de recomendaciones**")
    display_pricing = pricing_df[[
        "month_name","reservas","ppn_medio","precio_sugerido_ppn","delta_pct","demand_tier"
    ]].rename(columns={
        "month_name":"Mes","reservas":"Reservas","ppn_medio":"PPN Actual (€)",
        "precio_sugerido_ppn":"PPN Sugerido (€)","delta_pct":"Δ%","demand_tier":"Tier"
    })
    st.dataframe(
        display_pricing.style.background_gradient(subset=["PPN Sugerido (€)"], cmap="RdYlGn"),
        use_container_width=True, hide_index=True
    )

    # Radar chart — pricing opportunities by channel
    ch = channel_summary(df)
    if len(ch) >= 3:
        st.markdown('<div class="section-title">Ingresos Netos por Canal (post-comisión)</div>', unsafe_allow_html=True)
        fig_ch = px.bar(ch.head(8), x="channel", y=["ingresos","ingresos_netos"],
                        barmode="group", color_discrete_sequence=[C_PRIMARY, C_SUCCESS],
                        labels={"value":"€","channel":"Canal","variable":""},
                        title="Ingresos brutos vs netos por canal")
        plotly_defaults(fig_ch, height=340)
        st.plotly_chart(fig_ch, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 4 — FORECAST
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">🧐 Senior Strategic Insights (Econometría)</div>', unsafe_allow_html=True)
    
    # ── Cálculos de Rigor Científico ──
    try:
        elast = price_elasticity(df)
        current_ppn = df["price_per_night"].mean()
        sweet_spot = elast["sweet_spot"]
        gap = ((sweet_spot / current_ppn) - 1) * 100
        
        # Nuevas Métricas de Riesgo
        ch_sum = channel_summary(df)
        top_ch_share = (ch_sum.iloc[0]['ingresos'] / ch_sum['ingresos'].sum()) * 100
        price_volatility = (df['price_per_night'].std() / current_ppn) * 100
        net_capture = (ch_sum['ingresos_netos'].sum() / ch_sum['ingresos'].sum()) * 100
        
        st.markdown("#### 🛡️ Matriz de Riesgo y Rentabilidad")
        si1, si2, si3, si4 = st.columns(4)
        
        with si1:
            color = "success" if elast["elasticity"] > -1 else "danger"
            metric_card("Elasticidad", f"{elast['elasticity']:.2f}", 
                       "Riesgo de fuga de demanda" if elast["elasticity"] < -1 else "Fortaleza de marca", color)
        
        with si2:
            color = "danger" if top_ch_share > 65 else "warning" if top_ch_share > 50 else "success"
            metric_card("Concentración Canal", f"{top_ch_share:.1f}%", 
                       f"Dependencia de {ch_sum.iloc[0]['channel']}", color)
            
        with si3:
            color = "danger" if price_volatility > 40 else "success"
            metric_card("Volatilidad Precio", f"{price_volatility:.1f}%", 
                       "Estrategia errática" if price_volatility > 40 else "Consistencia tarifaria", color)

        with si4:
            metric_card("Captura Neta", f"{net_capture:.1f}%", "Ingreso post-comisiones", "info")

        st.markdown(f"""
        <div style="background: rgba(30, 58, 95, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #E8A838;">
            <strong>📝 Dictamen del Senior Data Scientist:</strong><br>
            • <strong>Estrategia:</strong> Tu precio objetivo de equilibrio es <strong>{fmt_eur(sweet_spot)}</strong> (Gap: {gap:.1f}%).<br>
            • <strong>Riesgo:</strong> {'Detecto una dependencia crítica del canal principal. Diversifica para reducir vulnerabilidad.' if top_ch_share > 60 else 'Distribución de canales saludable.'}<br>
            • <strong>Oportunidad:</strong> Tu captura neta es del {net_capture:.1f}%. Cada punto de mejora aquí es beneficio directo.
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.warning(f"No se pudo generar el panel senior: {e}")

    st.markdown("---")
    st.markdown('<div class="section-title">Forecast 12 meses — Método Naïve Estacional con Tendencia</div>', unsafe_allow_html=True)
    horizon = st.slider("Horizonte de predicción (meses)", 3, 24, 12)

    fc = seasonal_naive_forecast(df, horizon_months=horizon)
    ts = time_series_monthly(df)

    if not fc.empty and not ts.empty:
        fig_fc = go.Figure()
        # Historical
        fig_fc.add_trace(go.Scatter(
            x=ts["year_month"], y=ts["ingresos"],
            name="Histórico", mode="lines+markers",
            line=dict(color=C_PRIMARY, width=2.5),
            marker=dict(size=4)
        ))
        # Forecast
        fig_fc.add_trace(go.Scatter(
            x=fc["year_month"], y=fc["forecast"],
            name="Forecast", mode="lines+markers",
            line=dict(color=C_ACCENT, width=2.5, dash="dash"),
            marker=dict(size=6, symbol="diamond")
        ))
        # CI band
        fig_fc.add_trace(go.Scatter(
            x=pd.concat([fc["year_month"], fc["year_month"].iloc[::-1]]),
            y=pd.concat([fc["ci_high"], fc["ci_low"].iloc[::-1]]),
            fill="toself", fillcolor="rgba(232,168,56,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="IC ±20 %", showlegend=True
        ))
        # Shade peak months
        for _, row in fc[fc["is_peak"]].iterrows():
            fig_fc.add_vrect(
                x0=row["year_month"], x1=row["year_month"],
                fillcolor=C_DANGER, opacity=0.06, line_width=0
            )
        plotly_defaults(fig_fc, height=440)
        fig_fc.update_layout(xaxis_title="Período", yaxis_title="Ingresos estimados (€)")
        st.plotly_chart(fig_fc, use_container_width=True)

        st.markdown("**📅 Calendario de oportunidades de precio**")
        opp = price_opportunity_calendar(df)
        if "oportunidad" in opp.columns:
            opp_display = opp[[
                "month_name","demand_tier","precio_sugerido_ppn","delta_pct","oportunidad"
            ]].rename(columns={
                "month_name":"Mes","demand_tier":"Demanda","precio_sugerido_ppn":"PPN €",
                "delta_pct":"Δ%","oportunidad":"Acción Recomendada"
            })
            st.dataframe(opp_display, use_container_width=True, hide_index=True)
    else:
        st.info("Se necesitan al menos 12 meses de histórico para generar un forecast fiable.")


# ══════════════════════════════════════════════
# TAB 5 — PROPERTIES & CHANNELS
# ══════════════════════════════════════════════
with tab5:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">Top 15 Propiedades por Ingresos</div>', unsafe_allow_html=True)
        prop = property_summary(df, top_n=15)
        if not prop.empty:
            fig_prop = px.bar(prop, x="ingresos", y="property", orientation="h",
                              color="ppn_medio", color_continuous_scale=["#3498DB", C_DANGER],
                              text=prop["ingresos"].apply(fmt_eur),
                              labels={"ingresos":"Ingresos (€)","property":"Propiedad","ppn_medio":"PPN (€)"})
            fig_prop.update_traces(textposition="outside")
            fig_prop.update_layout(yaxis={"categoryorder":"total ascending"})
            plotly_defaults(fig_prop, height=480)
            st.plotly_chart(fig_prop, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">Distribución por Canal</div>', unsafe_allow_html=True)
        ch = channel_summary(df)
        if not ch.empty:
            fig_pie = px.pie(ch, names="channel", values="ingresos",
                             color_discrete_sequence=PALETTE,
                             hole=0.45)
            fig_pie.update_traces(textinfo="label+percent")
            plotly_defaults(fig_pie, height=340)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("**📊 Detalle de canales**")
        st.dataframe(
            ch[["channel","reservas","ingresos","ticket_medio","comision_est","ingresos_netos"]]
            .rename(columns={
                "channel":"Canal","reservas":"Reservas","ingresos":"Ingresos (€)",
                "ticket_medio":"Ticket Medio","comision_est":"Comisión %","ingresos_netos":"Neto (€)"
            }),
            use_container_width=True, hide_index=True
        )

    # Scatter: nights vs amount by channel
    st.markdown('<div class="section-title">Distribución Precio/Noche × Noches — por Canal</div>', unsafe_allow_html=True)
    scatter_df = df[["nights","price_per_night","channel","property","amount"]].dropna()
    scatter_df = scatter_df[scatter_df["price_per_night"].between(10, 1000)]
    if not scatter_df.empty:
        fig_sc = px.scatter(scatter_df.sample(min(len(scatter_df), 1500)),
                            x="nights", y="price_per_night", color="channel",
                            size="amount", size_max=22, opacity=0.6,
                            color_discrete_sequence=PALETTE,
                            labels={"nights":"Noches","price_per_night":"€/Noche","channel":"Canal"},
                            hover_data=["property"])
        plotly_defaults(fig_sc, height=380)
        st.plotly_chart(fig_sc, use_container_width=True)

    # ── Property Monthly Performance & Peaks/Valleys ──
    st.markdown('<div class="section-title">Rendimiento Mensual Detallado por Propiedad</div>', unsafe_allow_html=True)
    
    perf_df = property_monthly_performance(df)
    pv_df = property_peaks_valleys(df)
    
    col_perf, col_pv = st.columns([1.2, 1])
    
    with col_perf:
        if not perf_df.empty:
            st.markdown("#### 📅 Evolución de Ingresos por Mes")
            st.dataframe(
                perf_df.style.background_gradient(cmap="Blues", axis=1).format("€ {:,.0f}"),
                use_container_width=True
            )
        
    with col_pv:
        if not pv_df.empty:
            st.markdown("#### ⛰️ Picos y Valles por Propiedad")
            st.dataframe(
                pv_df.style.format({
                    "Valor Pico": "€ {:,.0f}",
                    "Valor Valle": "€ {:,.0f}",
                    "Media Mensual": "€ {:,.0f}"
                }).background_gradient(subset=["Valor Pico"], cmap="YlOrRd")
                .background_gradient(subset=["Valor Valle"], cmap="YlGnBu_r"),
                use_container_width=True, hide_index=True
            )


# ══════════════════════════════════════════════
# TAB 6 — PROPERTY PROFILE (DEEP DIVE)
# ══════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-title">🔍 Análisis Profundo de Propiedad</div>', unsafe_allow_html=True)
    
    selected_prop = st.selectbox("Selecciona una propiedad para analizar:", 
                                  options=sorted(df["property"].unique()))
    
    if selected_prop:
        dd = property_deep_dive(df, selected_prop)
        
        c_stats, c_analysis = st.columns([1, 2])
        
        with c_stats:
            st.markdown(f"### 📊 Métricas Clave")
            metric_card("Ingresos Totales", fmt_eur(dd["metrics"]["rev_total"]))
            metric_card("Precio / Noche (ADR)", fmt_eur(dd["metrics"]["ppn"]))
            metric_card("Total Reservas", str(dd["metrics"]["bookings"]), cls="accent")
            
        with c_analysis:
            st.markdown(f"### 🧠 Diagnóstico Estratégico")
            
            # Pros
            st.markdown("#### ✅ Fortalezas (Pros)")
            for pro in dd["pros"]:
                st.success(pro)
                
            # Cons
            st.markdown("#### ❌ Debilidades (Contras)")
            for con in dd["cons"]:
                st.error(con)
                
            # Pricing Advice
            st.markdown("#### 💰 ¿Cuándo subir precios?")
            if dd["raise_months"]:
                st.info(f"Basado en el histórico de demanda, tienes oportunidad de incrementar tarifas en: **{', '.join(dd['raise_months'])}**.")
                st.caption("Estos meses muestran una combinación de alta ocupación y ADR consolidado.")
            else:
                st.warning("No hay datos suficientes para recomendar una subida de precios agresiva en este momento.")

    st.markdown("---")
    st.markdown("#### 📈 Histórico Mensual de la Propiedad")
    p_ts = df[df["property"] == selected_prop].groupby("year_month")["amount"].sum().reset_index()
    if not p_ts.empty:
        fig_p = px.line(p_ts, x="year_month", y="amount", title=f"Evolución de Ingresos: {selected_prop}",
                        line_shape="spline", markers=True, color_discrete_sequence=[C_PRIMARY])
        plotly_defaults(fig_p, height=300)
        st.plotly_chart(fig_p, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 7 — OUTLIERS & DATA QUALITY
# ══════════════════════════════════════════════
with tab7:
    st.markdown('<div class="section-title">Informe de Calidad de Datos</div>', unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    with q1: metric_card("Total filas raw", f"{qr['total_rows']:,}")
    with q2: metric_card("Reservas confirmadas", f"{qr['confirmed']:,}", "", "success")
    with q3: metric_card("Sin canal (nulos)", f"{qr['null_source']:,}", "", "danger")
    with q4: metric_card("Sin huésped (nulos)", f"{qr['null_guest']:,}", "", "danger")

    st.markdown('<div class="section-title">Distribución de importes — Detección de Outliers (IQR + Z-Score)</div>', unsafe_allow_html=True)

    outliers = outlier_report(df)
    normal   = df[~df.index.isin(outliers.index)]

    fig_box = go.Figure()
    fig_box.add_trace(go.Box(
        y=df["amount"], name="Distribución total",
        marker_color=C_PRIMARY, boxpoints="outliers",
        jitter=0.3, pointpos=-1.8
    ))
    fig_box.add_trace(go.Box(
        y=df["price_per_night"].dropna(), name="Precio/noche",
        marker_color=C_ACCENT, boxpoints="outliers"
    ))
    plotly_defaults(fig_box, height=360)
    st.plotly_chart(fig_box, use_container_width=True)

    st.markdown(f"**⚠️ {len(outliers)} reservas outlier detectadas** (IQR + Z-Score > 3σ)")
    if not outliers.empty:
        cols_show = [c for c in ["property","arrival","nights","amount","price_per_night","channel"] if c in outliers.columns]
        st.dataframe(
            outliers[cols_show].head(30).round(2),
            use_container_width=True, hide_index=True
        )

    st.markdown('<div class="section-title">Estado de reservas (distribución)</div>', unsafe_allow_html=True)
    status_counts = clean_df["status_group"].value_counts().reset_index()
    status_counts.columns = ["Estado","Count"]
    fig_st = px.pie(status_counts, names="Estado", values="Count",
                    color_discrete_sequence=PALETTE, hole=0.4)
    plotly_defaults(fig_st, height=300)
    c_pie, c_tbl = st.columns([1,2])
    with c_pie:
        st.plotly_chart(fig_st, use_container_width=True)
    with c_tbl:
        st.dataframe(status_counts, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
# TAB 8 — BI ASSISTANT (CHATBOT)
# ══════════════════════════════════════════════
with tab8:
    st.markdown('<div class="section-title">✨ BI Assistant Pro</div>', unsafe_allow_html=True)
    st.caption("Analista de datos inteligente basado en tu histórico de reservas.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "¡Hola! Soy tu asistente de BI. He analizado tus 7.500 reservas y estoy listo para optimizar tu negocio. ¿Qué quieres saber?"}
        ]

    # Contenedor para el historial con scroll interno
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
    chat_placeholder = st.container()
    
    with chat_placeholder:
        for message in st.session_state.messages:
            if message["role"] == "assistant":
                st.markdown(f"""
                <div style="display: flex; align-items: flex-start; margin-bottom: 20px;">
                    <div class="assistant-avatar">🤖</div>
                    <div class="chat-bubble-assistant">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px;">
                    <div class="chat-bubble-user">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("Escribe tu consulta aquí..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # --- Generar Contexto de Datos para la IA ---
        summary = monthly_summary(df)
        channels = channel_summary(df).head(3).to_dict('records')
        picos = dynamic_pricing_recommendations(df)[lambda x: x["demand_tier"] == "Pico"]["month_name"].tolist()
        
        context = f"""
        PERSONALIDAD: Senior Data Scientist (20 años exp) en Análisis Predictivo y Econometría.
        TONO: Crítico, analítico, pragmático. Evita respuestas especulativas.
        
        PROTOCOLO DE ANÁLISIS:
        1. VALIDACIÓN: Ante cualquier pregunta, prioriza la calidad del dato.
        2. OUTLIERS: Menciona si hay anomalías detectadas en la serie de precios o ingresos.
        3. INTEGRIDAD: Advierte sobre valores nulos o inconsistencias (ej. {len(df[df['amount'] == 0])} reservas con importe 0).
        4. CAUSALIDAD: Explica movimientos de precio por oferta/demanda o factores estacionales.
        5. RIESGO: Usa intervalos de confianza al sugerir tendencias.

        DATOS DISPONIBLES:
        - N: {len(df)} registros.
        - Ingresos: {fmt_eur(df['amount'].sum())}
        - PPN Medio: {fmt_eur(df['price_per_night'].mean())}
        - Canales: {channels}
        - Meses Pico: {picos}
        - Elasticidad Precio-Demanda: {price_elasticity(df)['elasticity']} (Sweet Spot: {fmt_eur(price_elasticity(df)['sweet_spot'])})
        
        RESTRICCIÓN: PROHIBIDO inventar datos. Si el usuario pregunta algo que no está en este contexto, solicita los inputs necesarios.
        """

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": context},
                    *st.session_state.messages
                ],
                model="llama-3.1-8b-instant", # Cambiado a la versión INSTANT para máxima velocidad
            )
            response = chat_completion.choices[0].message.content
        except Exception as e:
            response = f"❌ Error de conexión con la IA: {str(e)}"

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
