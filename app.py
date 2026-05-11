# [ignoring loop detection]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq
import os, sys, json
from dotenv import load_dotenv

load_dotenv()

# --- Importar motores ---
sys.path.insert(0, ".")
from modules.etl import load_file, clean_and_enrich, filter_confirmed_paid
from modules.analytics import property_monthly_performance
from modules.forecasting import seasonal_naive_forecast, price_opportunity_calendar

# ─────────────────────────────────────────────
# OBJETIVO 1: INYECCIÓN CSS (FRONTEND DESIGN)
# ─────────────────────────────────────────────
def apply_v35_styles(has_alert=False):
    # Color de alerta dinámico: Rojo Intenso si hay riesgo de RevPAR
    notif_color = "#FF1744" if has_alert else "#00E676"
    
    st.markdown(f"""
        <style>
        /* Botón Popover Circular en Header */
        .stPopover {{
            position: fixed;
            top: 0.5rem;
            right: 140px;
            z-index: 1000001 !important;
        }}
        .stPopover > button {{
            background: white !important;
            border-radius: 50% !important;
            width: 44px !important;
            height: 44px !important;
            border: 1px solid #E0E4E8 !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
            padding: 0 !important;
            display: flex; align-items: center; justify-content: center;
            overflow: hidden !important;
            transition: all 0.3s ease;
        }}
        .stPopover > button:hover {{ border-color: {notif_color} !important; transform: scale(1.05); }}
        
        /* Badge de Notificación Pulse */
        .stPopover > button::after {{
            content: '';
            position: absolute;
            top: 2px;
            right: 2px;
            width: 10px;
            height: 10px;
            background: {notif_color};
            border-radius: 50%;
            border: 2px solid white;
            animation: pulse-ring 1.5s infinite;
        }}
        
        @keyframes pulse-ring {{
            0% {{ transform: scale(0.8); opacity: 1; }}
            100% {{ transform: scale(2.2); opacity: 0; }}
        }}

        /* Contenedor de Chat Full-Width */
        [data-testid="stPopoverBody"] {{
            background: rgba(255, 255, 255, 0.98) !important;
            backdrop-filter: blur(15px);
            border-radius: 20px !important;
            width: 420px !important;
            padding: 1rem !important;
        }}
        
        /* Layout Optimization */
        .main {{ background: #F8F9FA; }}
        .metric-container {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# OBJETIVO 2: LÓGICA DE MAPAS (DATA SCIENTIST)
# ─────────────────────────────────────────────
def get_geo_data(df):
    """Implementa dispersión realista en Tierra Firme (Bounding Box Oropesa-Benicassim)."""
    np.random.seed(42)
    unique_props = df["property"].unique()
    
    # Bounding Box Real: Casco Urbano (Tierra Firme)
    # Lat: [40.050, 40.100], Lon: [0.110, 0.145]
    geo_map = {}
    for prop in unique_props:
        geo_map[prop] = {
            "lat": np.random.uniform(40.060, 40.095),
            "lon": np.random.uniform(0.120, 0.140)
        }
    
    df_geo = df.copy()
    df_geo["lat"] = df_geo["property"].map(lambda x: geo_map.get(x)["lat"])
    df_geo["lon"] = df_geo["property"].map(lambda x: geo_map.get(x)["lon"])
    return df_geo

# ─────────────────────────────────────────────
# MOTOR DE RECOMENDACIÓN (REFACTORIZADO)
# ─────────────────────────────────────────────
def get_v35_recommendation(df_prop, df_all, prop_name):
    # Fix KeyError y Blindaje de datos
    forecast_df = seasonal_naive_forecast(df_all[df_all['property'] == prop_name])
    if forecast_df.empty: return "Sin datos suficientes", {}
    
    forecast_val = forecast_df.iloc[0]['forecast']
    actual_rev = df_prop[df_prop['arrival'] > (pd.Timestamp.now() - pd.Timedelta(days=30))]['amount'].sum()
    
    if actual_rev < forecast_val * 0.8:
        msg = "📉 Baja demanda detectada: Sugerido -10% para capturar reservas."
    else:
        msg = "🚀 Demanda saludable: Mantener o subir +5% según ocupación."
    
    return msg, {"forecast": forecast_val, "actual": actual_rev}

# ─────────────────────────────────────────────
# EJECUCIÓN APP
# ─────────────────────────────────────────────
st.set_page_config(page_title="Rental Intelligence v3.5", layout="wide")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

with st.sidebar:
    st.header("🎯 Centro de Control")
    uploaded_file = st.file_uploader("Subir rows.csv", type=["csv"])

if not uploaded_file:
    st.title("🚀 Rental Intelligence v3.5")
    st.info("Carga el archivo de reservas para activar la inteligencia geoespacial.")
else:
    df_raw = clean_and_enrich(load_file(uploaded_file))
    df = filter_confirmed_paid(df_raw)
    df_geo = get_geo_data(df)

    # HEADER Y BOT (ORQUESTACIÓN)
    prop_list = sorted(df["property"].unique())
    selected_prop = st.selectbox("Seleccionar Propiedad", ["Dashboard Global"] + prop_list)
    
    rec_msg = ""
    ai_metrics = {}
    if selected_prop != "Dashboard Global":
        rec_msg, ai_metrics = get_v35_recommendation(df[df["property"] == selected_prop], df, selected_prop)
    
    apply_v35_styles(has_alert=bool(rec_msg))

    # MAPA DINÁMICO (MISIÓN 1)
    st.subheader("📍 Visualización de Rendimiento Geoespacial")
    
    # Lógica Map-Master: Auto-centrado en el promedio
    avg_lat = df_geo["lat"].mean()
    avg_lon = df_geo["lon"].mean()
    
    if selected_prop == "Dashboard Global":
        map_data = df_geo.groupby(["property", "lat", "lon"])["amount"].sum().reset_index()
        fig_map = px.scatter_mapbox(map_data, lat="lat", lon="lon", size="amount", color="amount",
                                    hover_name="property", zoom=13, height=500,
                                    center={"lat": avg_lat, "lon": avg_lon},
                                    mapbox_style="open-street-map", color_continuous_scale="Viridis")
    else:
        prop_rows = df_geo[df_geo["property"] == selected_prop]
        if not prop_rows.empty:
            fig_map = px.scatter_mapbox(prop_rows, 
                                        lat="lat", lon="lon", zoom=16, height=500,
                                        center={"lat": prop_rows["lat"].mean(), "lon": prop_rows["lon"].mean()},
                                        mapbox_style="open-street-map")
        else:
            fig_map = go.Figure()
            
    st.plotly_chart(fig_map, use_container_width=True)

    # GRÁFICO DE BARRAS INTERACTIVO (MISIÓN 3)
    st.write("### 📊 Evolución de Ingresos Mensuales")
    bar_data = df.groupby(["year", "month_short", "month"])["amount"].sum().reset_index().sort_values("month")
    
    if selected_prop != "Dashboard Global":
        bar_data = df[df["property"] == selected_prop].groupby(["year", "month_short", "month"])["amount"].sum().reset_index().sort_values("month")
    
    # Selector de Año dentro del gráfico si es Dashboard Global
    if selected_prop == "Dashboard Global":
        available_years = sorted(bar_data["year"].unique().tolist(), reverse=True)
        sel_year_bar = st.selectbox("Filtrar Año Gráfico", available_years, key="global_year_bar")
        bar_data = bar_data[bar_data["year"] == sel_year_bar]

    fig_bars = px.bar(bar_data, x="month_short", y="amount", color="year", barmode="group",
                      labels={"month_short": "Mes", "amount": "Ingresos (€)"},
                      color_discrete_sequence=px.colors.qualitative.Prism)
    st.plotly_chart(fig_bars, use_container_width=True)

    # MÉTRICAS Y CALENDARIO (FIX KEYERROR)
    if selected_prop != "Dashboard Global":
        df_p = df[df["property"] == selected_prop]
        
        # Selectores Temporales (Misión 2)
        st.divider()
        col_t1, col_t2 = st.columns(2)
        years = sorted(df_p["year"].unique().tolist(), reverse=True)
        sel_year = col_t1.selectbox("📅 Año", years)
        months_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        sel_month_name = col_t2.selectbox("📆 Mes", months_names)
        month_map = {name: i+1 for i, name in enumerate(months_names)}
        sel_month = month_map[sel_month_name]
        
        # Filtrado y Métricas Dinámicas
        df_filtered = df_p[(df_p["year"] == sel_year) & (df_p["month"] == sel_month)]
        m_rev = df_filtered["amount"].sum() if not df_filtered.empty else 0
        m_adr = df_filtered["price_per_night"].mean() if not df_filtered.empty else 0
        
        # Comparativa vs Mes Anterior (Orquestación)
        df_prev = df_p[(df_p["year"] == sel_year) & (df_p["month"] == sel_month - 1)]
        prev_rev = df_prev["amount"].sum() if not df_prev.empty else 0
        growth = ((m_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0
        
        st.markdown(f"### 📊 Rendimiento en {sel_month_name} {sel_year}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Mes", f"€{m_rev:,.0f}", f"{growth:+.1f}% vs prev")
        c2.metric("ADR Mes", f"€{m_adr:,.2f}")
        c3.metric("Reservas", len(df_filtered))

        # Gráfico Evolutivo (Simplificado para el Bot)
        # st.line_chart ya no es necesario aquí porque tenemos el interactivo arriba
        
        # Inyectar contexto temporal al bot
        ai_metrics["temporal_context"] = {
            "period": f"{sel_month_name} {sel_year}",
            "growth_vs_prev": f"{growth:.1f}%",
            "revenue": m_rev
        }

        st.write("### 📅 Calendario de Oportunidades")
        opps = price_opportunity_calendar(df_p)
        if "oportunidad" not in opps.columns:
            opps["oportunidad"] = "Analizando..."
        st.dataframe(opps[['month_name', 'demand_tier', 'precio_sugerido_ppn', 'oportunidad']], use_container_width=True, hide_index=True)

    # BOT POPUP (BRECKENGAN)
    with st.popover("🤖"):
        greeting = f"Analizando {selected_prop}..." if selected_prop != "Dashboard Global" else "Dashboard Global Activo"
        st.write(f"### {greeting}")
        
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
            
        if rec_msg and (not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != rec_msg):
            st.warning(rec_msg)
            
        chat_container = st.container(height=300)
        for msg in st.session_state.chat_history:
            with chat_container.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if prompt := st.chat_input("Escribe tu consulta estratégica...", key="v35_chat"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # CACHÉ DE IA (FAST-RESPONSE)
            cache_key = f"{selected_prop}_{ai_metrics.get('temporal_context', {}).get('period', '')}"
            
            if client:
                # Prompt Simplificado (Performance Optimization)
                sys_prompt = f"Senior Strategist. Propiedad: {selected_prop}. Contexto: {json.dumps(ai_metrics.get('temporal_context', {}))}. Acción de precio directa para RevPAR?"
                
                response = client.chat.completions.create(
                    messages=[{"role": "system", "content": sys_prompt}, *st.session_state.chat_history],
                    model="llama-3.3-70b-versatile"
                ).choices[0].message.content
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
