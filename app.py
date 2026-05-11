# [ignoring loop detection]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os, sys, json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- Motores ---
sys.path.insert(0, ".")
from modules.etl import load_file, clean_and_enrich, filter_confirmed_paid

# ─────────────────────────────────────────────
# FRONTEND DESIGN: APP CARDS & CLEAN UI
# ─────────────────────────────────────────────
def apply_pro_styles():
    st.markdown("""
        <style>
        .stPopover { position: fixed; top: 0.5rem; right: 140px; z-index: 1000001; }
        .stPopover > button {
            background: #1E3A5F !important; color: white !important;
            border-radius: 50% !important; width: 48px !important; height: 48px !important;
            border: 2px solid white !important; box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
        }
        .metric-card {
            background: white; padding: 22px; border-radius: 20px;
            border: 1px solid #F1F5F9; box-shadow: 0 6px 15px rgba(0,0,0,0.03);
            margin-bottom: 15px; text-align: center;
        }
        .metric-label { font-size: 0.8rem; color: #94A3B8; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; }
        .metric-value { font-size: 1.6rem; font-weight: 800; color: #0F172A; }
        .main { background: #F8FAFC; }
        </style>
    """, unsafe_allow_html=True)

def draw_card(label, value):
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CORE APP: INTERANUAL PRO (2026+)
# ─────────────────────────────────────────────
st.set_page_config(page_title="Renta Intelligence 2026", layout="wide")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if 'data_optimized' not in st.session_state: st.session_state.data_optimized = None

with st.sidebar:
    st.title("📊 Renta Pro 2026")
    uploaded_file = st.file_uploader("📂 Cargar rows.csv", type=["csv"])
    if st.button("🔄 Resetear"):
        st.session_state.data_optimized = None
        st.rerun()

if not uploaded_file:
    st.title("🚀 Terminal de Control Interanual")
    st.info("👋 Sube tu archivo de reservas para iniciar la comparativa de 2026 en adelante.")
else:
    # 1. MAGIA DE DATOS (PUSH-UP)
    if st.session_state.data_optimized is None:
        st.markdown("---")
        with st.expander("✨ **He detectado tus datos**", expanded=True):
            st.write("¿Quieres que optimice el formato para la comparativa 2026+?")
            c1, c2 = st.columns(2)
            if c1.button("✅ Sí, optimizar", use_container_width=True):
                st.session_state.data_optimized = True
                st.rerun()
            if c2.button("❌ No, usar crudos", use_container_width=True):
                st.session_state.data_optimized = False
                st.rerun()
        st.stop()

    # Procesamiento
    df_load = load_file(uploaded_file)
    if st.session_state.data_optimized:
        df = clean_and_enrich(df_load)
        df = filter_confirmed_paid(df)
        # Filtro estricto: Solo 2026 en adelante
        df = df[df["year"] >= 2026]
    else:
        df = df_load

    # 2. SELECTORES DE COMPARATIVA
    st.write("### 🎛️ Filtros de Comparativa")
    col_f1, col_f2 = st.columns([2, 1])
    
    try:
        if "year" in df.columns:
            available_years = sorted(df["year"].unique().tolist())
            selected_years = col_f1.multiselect("📅 Seleccionar Años a Comparar", 
                                                available_years, 
                                                default=[2026] if 2026 in available_years else available_years[:1])
        else:
            selected_years = [2026]

        months_list = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        sel_month_name = col_f2.selectbox("📆 Mes de Análisis", months_list)
        month_map = {n: i+1 for i, n in enumerate(months_list)}
        sel_month = month_map[sel_month_name]

        # Filtrado por selección
        df_plot = df.copy()
        if "year" in df_plot.columns: df_plot = df_plot[df_plot["year"].isin(selected_years)]
        if "month" in df_plot.columns: df_plot = df_plot[df_plot["month"] == sel_month]

        # 3. KPIs ESTILO APP (2026)
        apply_pro_styles()
        st.divider()
        st.markdown(f"## 🏁 Resultados: {sel_month_name} ({', '.join(map(str, selected_years))})")
        
        k1, k2, k3, k4 = st.columns(4)
        with k1: draw_card("Ingresos Totales", f"€{df_plot['amount'].sum():,.0f}")
        with k2: draw_card("Precio por Noche", f"€{df_plot['price_per_night'].mean():,.0f}" if "price_per_night" in df_plot else "N/A")
        with k3: draw_card("Reservas", len(df_plot))
        with k4: draw_card("Años Analizados", f"{len(selected_years)}")

        # 4. GRÁFICO DE BARRAS COMPARATIVO (SUSTITUYE BURBUJAS)
        st.divider()
        st.write("### 📈 Comparativa de Rendimiento por Propiedad")
        if not df_plot.empty and "property" in df_plot.columns:
            bar_data = df_plot.groupby(["property", "year"])["amount"].sum().reset_index()
            fig = px.bar(bar_data, x="property", y="amount", color="year",
                         barmode="group",
                         labels={"property": "Propiedad", "amount": "Ingresos Brutos (€)", "year": "Año"},
                         color_discrete_sequence=px.colors.qualitative.Prism,
                         height=600)
            
            # Optimización de etiquetas largas
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos suficientes para mostrar la comparativa en este periodo.")

        # 5. ASESOR AMIGABLE
        with st.popover("🤖"):
            st.write("### ✨ Tu Asesor de Crecimiento")
            if 'chat_history' not in st.session_state: st.session_state.chat_history = []
            chat_container = st.container(height=300)
            for m in st.session_state.chat_history:
                with chat_container.chat_message(m["role"]): st.markdown(m["content"])
                    
            if prompt := st.chat_input("¿Hablamos del futuro de tus rentas?"):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                if client:
                    sys_msg = "Eres un asesor amigable. Enfócate en el crecimiento interanual. Si ves que un año supera al anterior, celébralo con 🚀. Explica los datos de forma sencilla."
                    res = client.chat.completions.create(
                        messages=[{"role": "system", "content": sys_msg}, *st.session_state.chat_history],
                        model="llama-3.3-70b-versatile"
                    ).choices[0].message.content
                    st.session_state.chat_history.append({"role": "assistant", "content": res})
                st.rerun()

    except Exception as e:
        st.error(f"Error en la arquitectura de datos: {e}")
