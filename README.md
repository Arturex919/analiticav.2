# 🏠 Rental Analytics Platform

> **Senior BI + Data Science solution para negocio de alquileres vacacionales**  
> Stack: Python · Streamlit · Plotly · Pandas · Scikit-learn · SciPy

---

## 📁 Estructura del Proyecto

```
rental_analytics/
├── app.py                    ← Aplicación Streamlit principal (6 tabs)
├── requirements.txt          ← Dependencias del proyecto
├── README.md                 ← Este archivo
│
├── modules/
│   ├── __init__.py
│   ├── etl.py               ← Pipeline ETL: carga, limpieza, enriquecimiento
│   ├── analytics.py         ← EDA estadístico: estacionalidad, outliers, elasticidad
│   └── forecasting.py       ← Forecast naïve estacional + calendario de pricing
│
├── config/
│   └── settings.py          ← (Opcional) variables de configuración
│
└── data_sample/             ← (Opcional) datos de prueba
```

---

## ⚡ Inicio Rápido

```bash
# 1. Clonar / descomprimir el proyecto
cd rental_analytics

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Lanzar la aplicación
streamlit run app.py
```

La app se abre en `http://localhost:8501`. Carga tu CSV de reservas en el panel izquierdo.

---

## 🔧 Stack Tecnológico

| Capa | Librería | Versión | Propósito |
|---|---|---|---|
| **Framework UI** | Streamlit | ≥1.35 | Dashboard interactivo |
| **Datos** | Pandas | ≥2.0 | Manipulación y ETL |
| **Numérico** | NumPy | ≥1.26 | Cálculos vectorizados |
| **Visualización** | Plotly | ≥5.20 | Charts interactivos |
| **Estadística** | SciPy | ≥1.13 | Regresión, z-score, IQR |
| **ML** | Scikit-learn | ≥1.4 | (Extensible: clustering, clasificación) |
| **PDF** | pypdf | ≥4.0 | Extracción de contratos PDF |
| **DOCX** | python-docx | ≥1.1 | Extracción de documentos Word |
| **Excel** | openpyxl / xlrd | ≥3.1 | Lectura de hojas de cálculo |

---

## 📊 Formatos de Archivo Soportados

| Formato | Caso de uso | Parser |
|---|---|---|
| `.csv` | Export de PMS (yourental, Lodgify, etc.) | Pandas (auto-detect `;` `,` `TAB`) |
| `.xlsx` / `.xls` | Reportes manuales de Excel | openpyxl / xlrd |
| `.pdf` | Contratos de alquiler, informes anuales | pypdf |
| `.docx` | Contratos Word con tablas de reservas | python-docx |

---

## 🗂️ Pipeline ETL — Detalle

### 1. Ingesta Multiformat
```
upload → detect_extension → parse(sep / engine) → raw_df
```

### 2. Limpieza
- **Importe**: limpia símbolos `€`, `$`, separadores de miles (`.`) y decimales (`,`)
- **Fechas**: prueba 5 formatos (`DD/MM/YYYY`, `YYYY-MM-DD`, etc.) con fallback `dayfirst=True`
- **Noches**: calcula `departure - arrival` si el campo viene vacío
- **Status**: normaliza a 4 grupos → `Confirmada / Cancelada / Bloqueada / Abierta`
- **Canal**: unifica aliases (ej: `BookingCom`, `booking.com`, `BOOKING` → `Booking.com`)

### 3. Enriquecimiento
Cada reserva recibe automáticamente:
```
month, month_name, year, quarter, season, dow, week_num,
is_weekend, is_holiday, year_month, price_per_night
```

---

## 📈 Análisis Estadístico — Metodología

### Estacionalidad Detectada (datos reales 2019-2026)

| Mes | Reservas | Ingresos | % Total | Tier |
|---|---|---|---|---|
| **Agosto** | **795** | **€ 755.532** | **37,1 %** | 🔴 PICO |
| **Julio** | **600** | **€ 604.510** | **29,7 %** | 🔴 PICO |
| Junio | 315 | € 166.956 | 8,2 % | 🟡 Alto |
| Abril | 202 | € 106.723 | 5,2 % | 🟡 Alto |
| Septiembre | 189 | € 104.895 | 5,2 % | 🟡 Alto |
| Mayo | 122 | € 67.764 | 3,3 % | 🟢 Normal |
| Diciembre | 87 | € 50.008 | 2,5 % | ⚠️ Alto PPN |
| Octubre | 91 | € 42.539 | 2,1 % | 🔵 Valle |
| Enero | 40 | € 28.337 | 1,4 % | 🔵 Valle |
| Noviembre | 37 | € 13.946 | 0,7 % | 🔵 Valle |

> **Insight clave:** Jul+Ago concentran el **66,8 %** de todos los ingresos del año.

---

### Detección de Outliers

Se usa un sistema **dual** de detección para máxima robustez:

```python
# IQR Method (resistente a distribuciones sesgadas)
Q1, Q3 = series.quantile([0.25, 0.75])
outlier = (valor < Q1 - 1.5*IQR) | (valor > Q3 + 1.5*IQR)

# Z-Score (para detectar extremos absolutos)
z = |zscore(valor)| > 3.0
```

Las reservas outlier (muy alto importe o noches anómalas) deben revisarse para:
- Identificar errores de imputación
- Detectar reservas de temporada larga (>30 noches) que distorsionan métricas
- Confirmar tarifas especiales justificadas

---

### Elasticidad Precio-Demanda

**Modelo log-log OLS:**
```
ln(Demanda) = α + β · ln(Precio)
β = elasticidad
```

**Resultado real de tus datos:**
- **Elasticidad = -0.56** → Demanda **moderadamente inelástica**
- Subir el precio un 10 % reduce la demanda ~5,6 %
- El punto óptimo de revenue está en torno a **€125-130/noche** (considerando toda la cartera)
- En meses PICO la inelasticidad es aún mayor → subidas de precio se absorben mejor

---

## 💰 Estrategia de Dynamic Pricing

### Framework de 4 Tiers

| Tier | Umbral | Ajuste PPN | Acción |
|---|---|---|---|
| 🔴 **Pico** | Top 20 % meses | **+22 %** | Subir precios ya, mínimas de 3 noches |
| 🟡 **Alto** | Top 20-40 % | **+10 %** | Subir precios, permitir 2 noches en fin de semana |
| 🟢 **Normal** | Top 40-60 % | **0 %** | Mantener, foco en early-bird (−5 % hasta 60 días) |
| 🔵 **Valle** | Bottom 40 % | **−8 %** | Early-bird / last-minute, paquetes con servicios |

### Recomendaciones Específicas (datos 2019-2026)

```
Junio, Julio, Agosto   → PPN sugerido: €197 (+22 % sobre base €162)
Abril, Septiembre      → PPN sugerido: €178 (+10 %)
Marzo, Mayo            → Mantener precio base
Enero, Feb, Oct, Nov   → PPN sugerido: €149 (−8 %, impulso)
Diciembre              → ⚠️ Precio actual €215 ya es el más alto; mantener
```

### Canal vs Comisión — Impacto en Margen Neto

| Canal | Ingresos brutos | Comisión | Ingresos netos |
|---|---|---|---|
| Booking.com | € 767.580 | 15 % | **€ 652.443** |
| **Manual / Directo** | **€ 625.819** | **0 %** | **€ 625.819** |
| Airbnb | € 351.291 | 14 % | € 302.110 |
| Other Holiday | € 181.029 | 0 % | € 181.029 |
| HomeAway/VRBO | € 51.987 | 12 % | € 45.748 |

> **💡 Booking.com vs Directo:** Booking genera más volumen pero el margen neto de reserva directa es €150 más alto por reserva. Invertir en captación directa (web propia, email marketing) tiene ROI muy alto.

---

## 🔮 Modelo de Forecast

**Método:** Naïve Estacional con corrección de tendencia OLS

```python
# Índice estacional
seasonal_idx[mes] = avg_mes / avg_total

# Baseline rolling
baseline = últimos_12_meses.rolling(12).mean().last()

# Forecast por mes futuro i
forecast[i] = baseline × seasonal_idx[mes_i] + trend_mensual × i

# Intervalo de confianza empírico (±20 %)
CI = [forecast * 0.80, forecast * 1.20]
```

**Limitaciones conocidas:**
- Años con datos incompletos (2020-COVID, 2026 en curso) pueden sesgar la tendencia
- Para forecasts >18 meses, considerar Prophet o SARIMA
- El CI ±20 % es empírico; se puede calibrar con errores históricos (MAPE)

---

## 🧭 Guía de Interpretación de Resultados para Maximizar ROI

### 1. Lectura del Dashboard Ejecutivo
- Si los **ingresos YoY** caen más del 20 %, revisar outliers de años COVID en el filtro
- El **ticket medio** es más fiable que ingresos totales para medir pricing

### 2. Lectura de Estacionalidad
- El heatmap Año×Mes revela **patrones de crecimiento a largo plazo**
- Si un mes mejora año a año (ej: abril cada vez tiene más reservas) → anticipar subida de precio
- Los **valles persistentes** (noviembre siempre bajo) sugieren redireccionar presupuesto de marketing

### 3. Lectura de la Elasticidad
- Elasticidad entre **−0.5 y −1.0** = zona segura para subidas graduales
- Si el R² < 0.2 → los datos son muy heterogéneos (mezcla de propiedades de precio muy distinto)
- Solución: aplicar análisis de elasticidad por segmento (villas vs apartamentos)

### 4. Implementación del Dynamic Pricing
```
Semana 1: Subir precios Jun-Ago en todos los canales (+20%)
Semana 2: Crear descuento early-bird Nov-Feb (−8% reservas >60 días)
Mes 2:    Activar mínimos de estancia en pico (Jul-Ago: 5 noches)
Mes 3:    Medir conversión y ajustar elasticidad real
```

### 5. KPIs para monitorizar
| KPI | Objetivo | Alerta |
|---|---|---|
| RevPAR (Revenue per Available Room) | +15 % YoY | < 0 % |
| Occupancy Rate (temporada alta) | > 85 % | < 70 % |
| ADR (Average Daily Rate) | > €180 en pico | < €150 |
| Booking lead time | > 45 días | < 21 días |
| % reservas directas | > 35 % | < 20 % |

---

## 🔌 Extensiones Futuras

```python
# 1. LangChain para contratos PDF
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA

# 2. Forecast avanzado con Prophet
from prophet import Prophet
m = Prophet(yearly_seasonality=True, weekly_seasonality=True)
m.fit(df.rename(columns={'arrival':'ds','amount':'y'}))

# 3. Clustering de propiedades (K-Means por perfil de demanda)
from sklearn.cluster import KMeans
features = ['ppn_medio', 'avg_nights', 'pct_weekend', 'ocupacion']
km = KMeans(n_clusters=4).fit(property_features[features])

# 4. Dashboard multi-tenant (Streamlit + Supabase)
# Autenticación por propietario + filtro automático de propiedades
```

---

*Desarrollado como solución integral de BI para alquileres vacacionales.*  
*Datos procesados: 7.500 registros · 211 propiedades · 2019-2026*
