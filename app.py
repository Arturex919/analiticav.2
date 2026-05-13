import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")
from modules.etl import load_file, clean_and_enrich, filter_confirmed_paid

# ─────────────────────────────────────────────
# ESTILOS GLOBALES
# ─────────────────────────────────────────────
def apply_styles():
    st.markdown("""<style>
        .stPopover{position:fixed;top:.5rem;right:140px;z-index:1000001}
        .stPopover>button{background:#1E3A5F!important;color:white!important;
            border-radius:50%!important;width:48px!important;height:48px!important;
            border:2px solid white!important;box-shadow:0 4px 15px rgba(0,0,0,.2)!important}
        .kpi-card{background:white;padding:20px;border-radius:18px;
            border:1px solid #F1F5F9;box-shadow:0 4px 12px rgba(0,0,0,.04);
            text-align:center;margin-bottom:12px}
        .kpi-label{font-size:.75rem;color:#94A3B8;font-weight:600;
            text-transform:uppercase;margin-bottom:6px}
        .kpi-value{font-size:1.6rem;font-weight:800;color:#1E3A5F}
        .gold{color:#D4AF37!important}
        .green{color:#10B981!important}
        .red{color:#EF4444!important}
        .rec-card{background:#F0F7FF;padding:16px;border-radius:14px;
            border-left:4px solid #1E3A5F;margin-bottom:10px}
        [data-testid="stTabs"] button{font-weight:600}
        
        /* GEMINI STYLE CHAT */
        .stChatMessage {
            background-color: transparent !important;
            border: none !important;
            padding: 1rem 0 !important;
        }
        .stChatMessage [data-testid="stMarkdownContainer"] {
            font-size: 1rem;
            line-height: 1.6;
            color: #1E293B;
        }
        .stChatMessage[data-testid="stChatMessageUser"] {
            background-color: #F8FAFC !important;
            border-radius: 20px 20px 0 20px !important;
            padding: 1.2rem !important;
            margin-left: 20% !important;
            border: 1px solid #E2E8F0 !important;
        }
        .stChatMessage[data-testid="stChatMessageAssistant"] {
            margin-right: 10% !important;
        }
        .chat-container {
            max-width: 850px;
            margin: 0 auto;
        }
    </style>""", unsafe_allow_html=True)

def kpi(label, value, color=""):
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color}">{value}</div></div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Property Intelligence Dashboard", layout="wide")
apply_styles()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

MONTHS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
MONTH_NUM = {m: i+1 for i,m in enumerate(MONTHS)}

if "data_ready" not in st.session_state: st.session_state.data_ready = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🏢 Property Intelligence")
    uploaded_file = st.file_uploader("📂 Cargar rows.csv", type=["csv"])
    if st.button("🔄 Resetear datos"):
        st.session_state.data_ready = None
        st.rerun()

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
if not uploaded_file:
    st.title("🚀 Property Intelligence Dashboard")
    st.info("👋 Sube tu archivo rows.csv para generar el análisis completo por propiedad.")
    st.stop()

if st.session_state.data_ready is None:
    with st.expander("✨ Archivo detectado — ¿Optimizamos los datos?", expanded=True):
        st.write("La limpieza garantiza que los cálculos de ocupación e ingresos sean exactos.")
        c1, c2 = st.columns(2)
        if c1.button("✅ Sí, optimizar", use_container_width=True):
            st.session_state.data_ready = True; st.rerun()
        if c2.button("❌ Usar crudos", use_container_width=True):
            st.session_state.data_ready = False; st.rerun()
    st.stop()

df_load = load_file(uploaded_file)
if st.session_state.data_ready:
    df = filter_confirmed_paid(clean_and_enrich(df_load))
else:
    df = df_load

# ─────────────────────────────────────────────
# CARGA DE DATOS DE MERCADO (Disponible para todo el app)
# ─────────────────────────────────────────────
market_file_path = "data/mercado_airbnb.csv"
df_m = None
if os.path.exists(market_file_path):
    try:
        df_m = pd.read_csv(market_file_path)
        df_m["precio_noche"] = pd.to_numeric(df_m["precio_noche"], errors="coerce").dropna()
    except: pass

if df_m is None:
    # Fallback a simulación si no hay archivo (para que el chat siempre tenga contexto)
    df_m = pd.DataFrame({
        "precio_noche": np.random.randint(80, 250, 50),
        "rating": np.random.uniform(4.2, 5.0, 50)
    })

col_prop = next((c for c in ["property","R_PROPERTY_NAME"] if c in df.columns), None)
if not col_prop:
    st.error(f"No se encontró columna de propiedades. Disponibles: {list(df.columns)}")
    st.stop()

col_amt  = "amount"          if "amount"          in df.columns else "R_TOTAL_AMOUNT"
col_adr  = "price_per_night" if "price_per_night" in df.columns else col_amt
col_nights = "nights"        if "nights"          in df.columns else None

# ─────────────────────────────────────────────
# SELECTORES: PROPIEDAD + MES
# ─────────────────────────────────────────────
sel_col1, sel_col2 = st.columns([2, 1])
with sel_col1:
    prop_list = sorted(df[col_prop].dropna().unique().tolist())
    selected_prop = st.selectbox("🏠 Selecciona la propiedad a analizar:", prop_list)

# Obtener meses disponibles para la propiedad
df_prop_all = df[df[col_prop] == selected_prop].copy()
available_months = []
if "month" in df_prop_all.columns and "month_short" in df_prop_all.columns:
    month_map_available = df_prop_all.drop_duplicates("month")[["month","month_short"]].sort_values("month")
    available_months = month_map_available["month_short"].tolist()

with sel_col2:
    if available_months:
        selected_months = st.multiselect(
            "📅 Filtrar por mes(es):",
            options=available_months,
            default=available_months,
            help="Selecciona uno o varios meses. Por defecto se muestran todos."
        )
    else:
        selected_months = []

# Aplicar filtro de meses
if selected_months and "month_short" in df_prop_all.columns:
    df_p = df_prop_all[df_prop_all["month_short"].isin(selected_months)].copy()
else:
    df_p = df_prop_all.copy()

# Datos comparativos (resto de propiedades, mismos meses)
if selected_months and "month_short" in df.columns:
    df_other = df[(df[col_prop] != selected_prop) & (df["month_short"].isin(selected_months))].copy()
else:
    df_other = df[df[col_prop] != selected_prop].copy()

month_label = ", ".join(selected_months) if selected_months and len(selected_months) < len(available_months) else "Todos los meses"
st.markdown(f"## 📊 Dashboard: *{selected_prop}*")
st.caption(f"📅 Periodo: **{month_label}**")
st.markdown("---")

# ─────────────────────────────────────────────
# CÁLCULOS COMUNES
# ─────────────────────────────────────────────
total_ingresos  = df_p[col_amt].sum()
ingresos_mes    = df_p[col_amt].mean() if not df_p.empty else 0
precio_medio    = df_p[col_adr].mean() if col_adr in df_p.columns else 0
total_reservas  = len(df_p)
total_noches    = df_p[col_nights].sum() if col_nights else 0

# Ocupación estimada: noches vendidas / días del periodo
if "arrival" in df_p.columns and col_nights:
    min_d = df_p["arrival"].min()
    max_d = df_p["arrival"].max()
    dias_periodo = max((max_d - min_d).days, 1)
    ocupacion_pct = min((total_noches / dias_periodo) * 100, 100)
else:
    ocupacion_pct = 0.0

# Serie mensual
if "month_short" in df_p.columns:
    monthly = (df_p.groupby(["month","month_short"])[col_amt]
               .sum().reset_index().sort_values("month"))
    monthly_nights = (df_p.groupby(["month","month_short"])[col_nights]
                      .sum().reset_index().sort_values("month")
                      if col_nights else None)
else:
    monthly = pd.DataFrame(columns=["month","month_short", col_amt])
    monthly_nights = None

# Mes de oro
if not monthly.empty:
    gold_row   = monthly.loc[monthly[col_amt].idxmax()]
    gold_month = gold_row["month_short"]
    gold_value = gold_row[col_amt]
else:
    gold_month, gold_value = "N/A", 0

# ─────────────────────────────────────────────
# 5 PESTAÑAS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 Resumen", "📈 Ocupación", "🏁 Competencia",
    "💡 Recomendaciones", "🔮 Proyecciones", "🤖 Asesor IA", "🌍 Mercado"
])

# ══════════════════════════════════════════════
# TAB 1 — RESUMEN
# ══════════════════════════════════════════════
with tab1:
    st.subheader("Indicadores Clave de Rendimiento")
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1: kpi("Ocupación Est.", f"{ocupacion_pct:.1f}%", "green" if ocupacion_pct>60 else "red")
    with r2: kpi("Precio / Noche", f"€{precio_medio:,.0f}")
    with r3: kpi("Ingresos Mes Medio", f"€{ingresos_mes:,.0f}")
    with r4: kpi("Ingresos Totales", f"€{total_ingresos:,.0f}")
    with r5: kpi("Mes de Oro ⭐", f"{gold_month} — €{gold_value:,.0f}", "gold")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.write("### 💰 Ingresos por Mes")
        if not monthly.empty:
            fig = px.bar(monthly, x="month_short", y=col_amt,
                         color_discrete_sequence=["#1E3A5F"],
                         labels={"month_short":"Mes", col_amt:"Ingresos (€)"})
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.write("### 📅 Distribución por Trimestre")
        if "quarter" in df_p.columns:
            q_data = df_p.groupby("quarter")[col_amt].sum().reset_index()
            fig2 = px.pie(q_data, values=col_amt, names="quarter",
                          color_discrete_sequence=px.colors.sequential.Blues_r)
            st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 2 — OCUPACIÓN
# ══════════════════════════════════════════════
with tab2:
    st.subheader("Análisis de Ocupación y Estacionalidad")

    if monthly_nights is not None and not monthly_nights.empty:
        # Estimar ocupación mensual (noches vendidas / días del mes)
        days_per_month = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
        monthly_nights["dias_mes"] = monthly_nights["month"].map(days_per_month)
        monthly_nights["ocupacion_pct"] = (
            monthly_nights[col_nights] / monthly_nights["dias_mes"] * 100
        ).clip(0, 100)

        fig_occ = px.line(monthly_nights, x="month_short", y="ocupacion_pct",
                          markers=True, line_shape="spline",
                          color_discrete_sequence=["#10B981"],
                          labels={"month_short":"Mes","ocupacion_pct":"Ocupación (%)"},
                          title="Curva de Ocupación Mensual")
        fig_occ.update_traces(marker=dict(size=10, line=dict(width=2, color="white")))
        fig_occ.add_hline(y=70, line_dash="dash", line_color="#EF4444",
                          annotation_text="Objetivo 70%", annotation_position="top right")
        st.plotly_chart(fig_occ, use_container_width=True)

        # Por trimestre
        if "quarter" in df_p.columns and col_nights:
            q_occ = df_p.groupby("quarter")[col_nights].sum().reset_index()
            q_occ["dias"] = q_occ["quarter"].map({"Q1":90,"Q2":91,"Q3":92,"Q4":92})
            q_occ["ocupacion"] = (q_occ[col_nights] / q_occ["dias"] * 100).clip(0,100)
            st.write("### Ocupación por Trimestre")
            fig_q = px.bar(q_occ, x="quarter", y="ocupacion",
                           color="ocupacion",
                           color_continuous_scale=["#EF4444","#F59E0B","#10B981"],
                           labels={"quarter":"Trimestre","ocupacion":"Ocupación (%)"},
                           range_y=[0,100])
            st.plotly_chart(fig_q, use_container_width=True)
    else:
        st.info("ℹ️ Selecciona '✅ Sí, optimizar' para ver el análisis de ocupación detallado.")

# ══════════════════════════════════════════════
# TAB 3 — COMPETENCIA
# ══════════════════════════════════════════════
with tab3:
    st.subheader("Benchmarking vs Resto de Cartera")

    if not df_other.empty:
        comp = (df_other.groupby(col_prop)
                .agg(ingresos=(col_amt,"sum"),
                     reservas=(col_amt,"count"),
                     precio=(col_adr,"mean"))
                .reset_index()
                .sort_values("ingresos", ascending=False)
                .head(10))

        prop_row = pd.DataFrame([{
            col_prop: f"⭐ {selected_prop}",
            "ingresos": total_ingresos,
            "reservas": total_reservas,
            "precio": precio_medio
        }])
        comp_full = pd.concat([prop_row, comp], ignore_index=True)

        col_x, col_y = st.columns(2)
        with col_x:
            st.write("### Ingresos Totales vs Competencia")
            colors = ["#D4AF37" if "⭐" in str(r) else "#1E3A5F"
                      for r in comp_full[col_prop]]
            fig_c1 = px.bar(comp_full, x=col_prop, y="ingresos",
                            labels={col_prop:"Propiedad","ingresos":"Ingresos (€)"},
                            color_discrete_sequence=colors)
            fig_c1.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig_c1, use_container_width=True)

        with col_y:
            st.write("### Precio por Noche vs Competencia")
            fig_c2 = px.bar(comp_full, x=col_prop, y="precio",
                            labels={col_prop:"Propiedad","precio":"Precio/Noche (€)"},
                            color_discrete_sequence=colors)
            fig_c2.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig_c2, use_container_width=True)

        st.write("### Tabla Comparativa Completa")
        comp_full_display = comp_full.rename(columns={
            col_prop:"Propiedad","ingresos":"Ingresos (€)",
            "reservas":"Reservas","precio":"Precio/Noche (€)"
        })
        comp_full_display["Ingresos (€)"] = comp_full_display["Ingresos (€)"].map("€{:,.0f}".format)
        comp_full_display["Precio/Noche (€)"] = comp_full_display["Precio/Noche (€)"].map("€{:,.0f}".format)
        st.dataframe(comp_full_display, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
# TAB 4 — RECOMENDACIONES
# ══════════════════════════════════════════════
with tab4:
    st.subheader("💡 Recomendaciones Estratégicas")

    # Recomendaciones automáticas basadas en datos
    recs = []

    if not monthly.empty:
        top3 = monthly.nlargest(3, col_amt)["month_short"].tolist()
        bot3 = monthly.nsmallest(3, col_amt)["month_short"].tolist()
        recs.append(("🚀 Subida de Precios",
            f"En los meses de {', '.join(top3)} tienes la mayor demanda. "
            f"Sube el precio un 10-15% para maximizar el RevPAR sin perder ocupación."))
        recs.append(("🎯 Oferta de Temporada Baja",
            f"Los meses de {', '.join(bot3)} son tus valles de demanda. "
            "Crea paquetes de 'Escapada Express' con descuento del 10% "
            "o elimina la estancia mínima para capturar reservas de último minuto."))

    if precio_medio > 0:
        media_cartera = df_other[col_adr].mean() if col_adr in df_other.columns else precio_medio
        diff = ((precio_medio - media_cartera) / media_cartera * 100) if media_cartera else 0
        if diff < -10:
            recs.append(("💰 Ajuste de Precio",
                f"Tu precio medio (€{precio_medio:,.0f}) está un {abs(diff):.0f}% "
                f"por debajo de la media de la cartera (€{media_cartera:,.0f}). "
                "Considera subir gradualmente el precio base un 5%."))
        elif diff > 15:
            recs.append(("⚖️ Revisión de Precio",
                f"Tu precio está un {diff:.0f}% por encima de la media. "
                "Asegúrate de que las reseñas y los servicios justifiquen la diferencia."))

    recs.append(("⭐ Gestión de Reseñas",
        "Responde a todas las reseñas en menos de 24h. "
        "Un aumento de 0.1 en la puntuación media puede incrementar "
        "los ingresos hasta un 5% según estudios del sector."))

    recs.append(("📅 Mínimo de Estancia",
        f"Tu mes de oro es {gold_month}. Durante ese mes, "
        "establece una estancia mínima de 3-5 noches para maximizar la eficiencia operativa "
        "y reducir costes de rotación."))

    for i, (titulo, texto) in enumerate(recs, 1):
        st.markdown(f"""<div class="rec-card">
            <strong>Rec. {i}: {titulo}</strong><br>{texto}
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.info("💡 ¿Necesitas una estrategia personalizada? Ve a la pestaña **🤖 Asesor IA** para consultar al chatbot.")

# ══════════════════════════════════════════════
# TAB 5 — PROYECCIONES
# ══════════════════════════════════════════════
with tab5:
    st.subheader("🔮 Proyecciones de Crecimiento")

    # Proyección simple: +10% precio en pico, tendencia lineal
    if not monthly.empty:
        proj = monthly.copy()
        crecimiento = 0.12  # 12% optimista
        proj["proyeccion"] = proj[col_amt] * (1 + crecimiento)

        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=proj["month_short"], y=proj[col_amt],
            name="Real", mode="lines+markers",
            line=dict(color="#1E3A5F", width=2),
            marker=dict(size=8)))
        fig_proj.add_trace(go.Scatter(
            x=proj["month_short"], y=proj["proyeccion"],
            name="Proyectado (+12%)", mode="lines+markers",
            line=dict(color="#10B981", width=2, dash="dash"),
            marker=dict(size=8)))
        fig_proj.update_layout(
            title="Ingresos Reales vs Proyección",
            xaxis_title="Mes", yaxis_title="Ingresos (€)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_proj, use_container_width=True)

    # KPIs de proyección
    p1, p2, p3 = st.columns(3)
    with p1: kpi("Proyección Ing. Mensual", f"€{ingresos_mes*1.12:,.0f}", "green")
    with p2: kpi("Proyección Ing. Anual", f"€{total_ingresos*1.12:,.0f}", "green")
    with p3: kpi("Ocupación Objetivo", f"{min(ocupacion_pct*1.07, 100):.1f}%", "green")

    st.markdown("---")
    st.info("📌 Las proyecciones asumen un crecimiento del 12% basado en optimización de precios en temporada alta y reducción de valles mediante ofertas estratégicas.")

# ══════════════════════════════════════════════
# TAB 6 — ASESOR IA (CHATBOT)
# ══════════════════════════════════════════════
with tab6:
    st.subheader("🤖 Asesor de Revenue Management")
    st.caption("Consulta estrategias personalizadas basadas en los datos reales de tu propiedad.")

    # Contexto resumido para el usuario
    with st.expander("📊 Contexto que el asesor tiene sobre tu propiedad", expanded=False):
        ctx_c1, ctx_c2, ctx_c3 = st.columns(3)
        with ctx_c1:
            st.metric("Ingresos Totales", f"€{total_ingresos:,.0f}")
        with ctx_c2:
            st.metric("Precio/Noche", f"€{precio_medio:,.0f}")
        with ctx_c3:
            st.metric("Ocupación Est.", f"{ocupacion_pct:.1f}%")
        st.write(f"**Propiedad:** {selected_prop} | **Mes de Oro:** {gold_month} (€{gold_value:,.0f}) | **Reservas:** {total_reservas}")

    if not client:
        st.warning("⚠️ No se ha configurado la API key de Groq. Añade `GROQ_API_KEY` en tu archivo `.env` para activar el asesor.")
    else:
        # Mostrar historial de chat
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])

        # Input del chat
        if prompt := st.chat_input("Escribe tu pregunta al asesor... (ej: ¿Cómo subo la ocupación en febrero?)"):
            # Mostrar mensaje del usuario
            with st.chat_message("user", avatar="🧑‍💼"):
                st.markdown(prompt)
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            # 3. CONTEXTO DE MERCADO PARA LA IA
            m_mean = df_m["precio_noche"].mean() if df_m is not None else 0
            m_median = df_m["precio_noche"].median() if df_m is not None else 0
            diff_m = ((precio_medio - m_mean) / m_mean * 100) if m_mean else 0
            
            # Generar respuesta
            sys_msg = (
                f"Eres un Revenue Manager de ÉLITE y asesor estratégico estilo Gemini. "
                f"Tu objetivo es maximizar la rentabilidad de la propiedad '{selected_prop}'.\n\n"
                f"📊 DATOS PROPIOS:\n"
                f"- Ingresos: €{total_ingresos:,.0f} | Precio/Noche medio: €{precio_medio:,.0f}\n"
                f"- Ocupación: {ocupacion_pct:.1f}% | Reservas: {total_reservas}\n"
                f"- Mes de Oro: {gold_month} (€{gold_value:,.0f})\n\n"
                f"🌍 DATOS DE MERCADO (AIRBNB):\n"
                f"- Precio medio competidores: €{m_mean:,.0f}\n"
                f"- Mediana de mercado: €{m_median:,.0f}\n"
                f"- Tu posicionamiento: Estás un {diff_m:+.1f}% respecto a la media.\n\n"
                "INSTRUCCIONES:\n"
                "1. Responde en español con un tono profesional, analítico pero cercano.\n"
                "2. Conecta SIEMPRE tus datos con los del mercado. Ejemplo: 'Tu precio es alto comparado con la media de €X...'\n"
                "3. Usa negritas para destacar cifras clave.\n"
                "4. Si el usuario pregunta por el mercado, usa los datos de €{m_mean:,.0f} para argumentar.\n"
                "5. Estructura con bullet points claros y termina con una 'Acción Recomendada'."
            )
            
            with st.chat_message("assistant", avatar="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ef1013757475.svg"):
                with st.spinner("Analizando mercado y propiedad..."):
                    try:
                        res = client.chat.completions.create(
                            messages=[{"role": "system", "content": sys_msg},
                                       *st.session_state.chat_history],
                            model="llama-3.3-70b-versatile"
                        ).choices[0].message.content
                        st.markdown(res)
                        st.session_state.chat_history.append({"role": "assistant", "content": res})
                    except Exception as e:
                        st.error(f"Error al contactar con el asesor: {e}")

        # Botón para limpiar historial
        if st.session_state.chat_history:
            if st.button("🗑️ Limpiar conversación", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

# ══════════════════════════════════════════════
# TAB 7 — MERCADO (MERCADO EXTERNO AIRBNB)
# ══════════════════════════════════════════════
with tab7:
    st.subheader("🌍 Análisis de Mercado Externo (Airbnb)")
    st.caption("Comparativa de tu propiedad frente a la oferta real del mercado extraída vía scraping.")

    # 1. CARGA DE DATOS DE MERCADO
    # (Ya cargados al inicio para el Chatbot)
    if df_m is not None:
        # Limpieza básica y conversión de fechas
        df_m["precio_noche"] = pd.to_numeric(df_m["precio_noche"], errors="coerce")
        df_m["rating"] = pd.to_numeric(df_m["rating"], errors="coerce")
        
        if "checkin" in df_m.columns:
            df_m["checkin"] = pd.to_datetime(df_m["checkin"], errors="coerce")
        
        df_m = df_m.dropna(subset=["precio_noche"])

        # 6. SELECTOR DE TEMPORADA / FECHAS
        st.markdown("---")
        col_f1, col_f2 = st.columns([2, 2])
        with col_f1:
            temporada = st.selectbox("📅 Filtrar por Temporada de Mercado:", 
                                     ["Ver Todo", "Alta (Jul-Ago)", "Media (May-Jun-Sep)", "Baja (Oct-Abr)"])
        
        # Lógica de filtrado por mes de checkin
        if temporada != "Ver Todo" and "checkin" in df_m.columns and not df_m["checkin"].isna().all():
            if "Alta" in temporada: meses = [7, 8]
            elif "Media" in temporada: meses = [5, 6, 9]
            else: meses = [10, 11, 12, 1, 2, 3, 4]
            df_m = df_m[df_m["checkin"].dt.month.isin(meses)]

        last_scrap = df_m["fecha_scraping"].iloc[0] if "fecha_scraping" in df_m.columns else "N/A"
        st.caption(f"Propiedades en muestra: **{len(df_m)}** | Último scraping: **{last_scrap}**")

        # 2. KPIs COMPARATIVOS
        m_mean = df_m["precio_noche"].mean()
        m_median = df_m["precio_noche"].median()
        m_p75 = df_m["precio_noche"].quantile(0.75)
        
        # Calcular posición (percentil)
        if len(df_m) > 1:
            pos_pct = (df_m["precio_noche"] < precio_medio).mean() * 100
        else:
            pos_pct = 0

        diff_vs_mean = ((precio_medio - m_mean) / m_mean * 100) if m_mean else 0

        st.write("### Comparativa de Precios vs Mercado")
        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi("Tu Precio Medio", f"€{precio_medio:,.0f}", "gold")
        with k2: kpi("Media Airbnb", f"€{m_mean:,.0f}")
        with k3: kpi("Percentil 75", f"€{m_p75:,.0f}")
        with k4: 
            color_pos = "red" if diff_vs_mean > 20 else "green"
            kpi("Dif. vs Media", f"{diff_vs_mean:+.1f}%", color_pos)

        # 5. ANÁLISIS DE POSICIONAMIENTO (Lógica Python)
        pos_txt = "por debajo" if precio_medio < m_mean else "por encima"
        perc_inv = 100 - pos_pct
        st.markdown(f"""
        <div class="rec-card">
            <strong>📍 Análisis de Posicionamiento:</strong><br>
            Tu precio de <strong>€{precio_medio:,.0f}</strong> está {pos_txt} de la media del mercado (€{m_mean:,.0f}). 
            Actualmente eres más caro que el <strong>{pos_pct:.0f}%</strong> de las propiedades similares y más barato que el <strong>{perc_inv:.0f}%</strong>.
            <br>🎯 <strong>Sugerencia:</strong> Para maximizar ocupación podrías ajustar a <strong>€{m_median:,.0f}</strong> (mediana). 
            Para maximizar ingresos en alta demanda, tu techo competitivo es <strong>€{m_p75:,.0f}</strong>.
        </div>
        """, unsafe_allow_html=True)

        # 3. GRÁFICOS
        g1, g2 = st.columns(2)
        
        with g1:
            # Histograma
            fig_hist = px.histogram(df_m, x="precio_noche", nbins=20, 
                                    title="Distribución de Precios en Airbnb",
                                    color_discrete_sequence=["#1E3A5F"],
                                    labels={"precio_noche": "Precio por Noche (€)", "count": "Cantidad"})
            fig_hist.add_vline(x=precio_medio, line_dash="dash", line_color="#D4AF37", 
                               annotation_text="Tú", annotation_position="top right")
            fig_hist.add_vline(x=m_mean, line_dash="dot", line_color="#10B981", 
                               annotation_text="Media", annotation_position="top left")
            st.plotly_chart(fig_hist, use_container_width=True)

        with g2:
            # Precio vs Rating (Scatter)
            # Añadimos tu propiedad como un punto destacado
            df_scatter = df_m.copy()
            if "rating" in df_scatter.columns:
                fig_scat = px.scatter(df_scatter, x="rating", y="precio_noche", 
                                      hover_name="nombre" if "nombre" in df_scatter.columns else None, 
                                      title="Calidad (Rating) vs Precio",
                                      color_discrete_sequence=["#94A3B8"], opacity=0.6)
                # Tu punto (estimado en el centro del rating para visibilidad)
                fig_scat.add_trace(go.Scatter(x=[4.85], y=[precio_medio], mode='markers',
                                             marker=dict(size=15, color='#D4AF37', symbol='star'),
                                             name=f"Tú ({selected_prop})"))
                st.plotly_chart(fig_scat, use_container_width=True)
            else:
                st.info("No hay datos de rating disponibles para el gráfico de dispersión.")

        g3, g4 = st.columns(2)
        with g3:
            # Boxplot comparativo
            comp_box = pd.concat([
                pd.DataFrame({"Origen": "Mercado", "Precio": df_m["precio_noche"]}),
                pd.DataFrame({"Origen": "Tu Propiedad", "Precio": [precio_medio] * 10}) # Duplicamos para visibilidad
            ])
            fig_box = px.box(comp_box, x="Origen", y="Precio", color="Origen",
                             title="Rango Competitivo",
                             color_discrete_map={"Mercado": "#1E3A5F", "Tu Propiedad": "#D4AF37"})
            st.plotly_chart(fig_box, use_container_width=True)
            
        with g4:
            # Barras por tipo
            if "tipo" in df_m.columns:
                df_tipo = df_m.groupby("tipo")["precio_noche"].mean().reset_index().sort_values("precio_noche")
                fig_bar = px.bar(df_tipo, x="precio_noche", y="tipo", orientation='h',
                                 title="Precio Medio por Tipo de Alojamiento",
                                 color_discrete_sequence=["#1E3A5F"])
                fig_bar.add_vline(x=precio_medio, line_dash="dash", line_color="#D4AF37")
                st.plotly_chart(fig_bar, use_container_width=True)

        # 4. TABLA DE COMPETIDORES DIRECTOS (±30%)
        st.write("### 🏁 Competidores Directos (Rango ±30% de tu precio)")
        lower_bound = precio_medio * 0.7
        upper_bound = precio_medio * 1.3
        
        df_comp = df_m[(df_m["precio_noche"] >= lower_bound) & (df_m["precio_noche"] <= upper_bound)].copy()
        
        if not df_comp.empty:
            # Función para colorear según precio vs el mío
            def style_competitors(row):
                color = "#EF4444" if row["precio_noche"] < precio_medio else "#10B981"
                return [f'color: {color}' for _ in row]

            # Preparar tabla para visualización
            display_cols = [c for c in ["nombre", "precio_noche", "rating", "tipo", "url"] if c in df_comp.columns]
            df_comp_disp = df_comp[display_cols].sort_values("precio_noche")
            
            # Formatear visualización
            st.dataframe(
                df_comp_disp.style.apply(style_competitors, axis=1),
                column_config={
                    "url": st.column_config.LinkColumn("Enlace Airbnb"),
                    "precio_noche": st.column_config.NumberColumn("Precio (€)", format="€%d"),
                    "rating": st.column_config.NumberColumn("Rating ⭐", format="%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
            st.caption("🔴 Rojo: Más baratos que tú | 🟢 Verde: Más caros que tú")
        else:
            st.info("No se encontraron competidores directos en el rango de precio ±30%.")

    else:
        st.error("No se pudieron cargar datos de mercado. Asegúrate de que el archivo existe o sube uno manualmente.")
