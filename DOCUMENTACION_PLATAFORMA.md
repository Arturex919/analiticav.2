# 📘 Guía Técnica y Operativa: Rental Analytics Platform v1.0

Este documento detalla la arquitectura, métricas y lógica de cálculo del ecosistema de Business Intelligence (BI) diseñado para la gestión avanzada de alquileres vacacionales.

---

## 1. Arquitectura del Sistema

La plataforma está dividida en cuatro pilares fundamentales:

### A. Módulo ETL (`modules/etl.py`)
**Función:** Ingesta, limpieza y normalización de datos.
- **Limpieza de Importes:** Utiliza expresiones regulares para limpiar símbolos de moneda y convertir formatos europeos (coma decimal) a formatos computacionales (punto decimal).
- **Mapeo Inteligente:** Detecta automáticamente columnas críticas (`R_TOTAL_AMOUNT`, `R_ARRIVAL`, etc.) mediante un sistema de alias para soportar archivos de diferentes fuentes (Airbnb, Booking, VRBO, etc.).
- **Enriquecimiento Temporal:** Calcula automáticamente el mes, año, temporada, trimestre y si una reserva cae en fin de semana o festivo nacional.

### B. Módulo Analítico (`modules/analytics.py`)
**Función:** Análisis estadístico y detección de patrones.
- **Detección de Outliers:** Utiliza el método **IQR (Rango Intercuartílico)** y **Z-Score** para identificar reservas con precios anómalos que podrían sesgar la media.
- **Elasticidad Precio-Demanda:** Calcula mediante una regresión log-log cómo varía la ocupación al cambiar el precio.

### C. Módulo de Forecasting (`modules/forecasting.py`)
**Función:** Predicción de ingresos futuros.
- **Método Naïve Estacional:** Predice los próximos 12 meses basándose en el rendimiento del mismo mes del año anterior, ajustado por la tendencia de crecimiento actual de la cartera.

### D. Dashboard Ejecutivo (`app.py`)
**Función:** Visualización interactiva y asistente de IA.

---

## 2. Lógica de los Cálculos Principales

### 📈 Precio por Noche (ADR / PPN)
**Cálculo:** `Importe Total / Número de Noches`
- Solo se calcula para reservas confirmadas y con importe positivo.
- Es la métrica base para comparar la rentabilidad real de diferentes propiedades sin importar su tamaño.

### 💰 Elasticidad de la Demanda
**Cálculo:** Regresión lineal sobre el logaritmo del precio y el logaritmo de la demanda.
- **Interpretación:** Un coeficiente de -1.5 significa que por cada 10% que subas el precio, la demanda caerá un 15%.
- **Sweet Spot:** Es el punto de precio donde el producto `Precio * Probabilidad de Reserva` es máximo (punto de equilibrio de rentabilidad).

### 🔍 Análisis de Propiedad (Deep Dive)
Esta es la función de "Diagnóstico Estratégico":
- **Pros:** Se activan si el ADR es >10% que la media global o si la propiedad tiene reservas de múltiples canales (baja dependencia).
- **Contras:** Se activan si la volatilidad de ingresos (desviación estándar) es muy alta o si un solo canal aporta >70% de las reservas.
- **Recomendación de Subida:** El sistema identifica los meses donde la propiedad tiene un volumen de reservas superior a su propia mediana histórica. Si el mercado acepta volumen a ese precio, se marca como "Oportunidad de Subida".

---

## 3. Guía de Pestañas del Dashboard

1.  **Tendencia Temporal:** Visión general de la salud financiera del negocio a lo largo de los años.
2.  **Estacionalidad:** Identifica los "Meses Pico" (donde puedes ser agresivo con el precio) y "Meses Valle" (donde necesitas ofertas).
3.  **Precios & Elasticidad:** Herramienta científica para saber si tus propiedades son caras o baratas respecto a la demanda real.
4.  **Forecast:** Proyección de flujo de caja para los próximos meses.
5.  **Propiedades & Canales:** Comparativa de qué casas rinden mejor y qué portales (Airbnb vs Booking) son más rentables tras comisiones.
6.  **Perfil de Propiedad:** Diagnóstico individualizado por casa con consejos tácticos.
7.  **Outliers & Calidad:** Auditoría de datos para asegurar que no hay errores de carga.
8.  **BI Assistant:** Chat con inteligencia artificial que conoce todos tus datos y responde preguntas complejas en lenguaje natural.
