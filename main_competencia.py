"""
main_competencia.py — Coordinador del scraper de competencia.
Lee rows.csv, extrae ciudades por propiedad y lanza búsquedas de mercado
en Airbnb para las mismas fechas que tienen reservas reales.
"""

import asyncio
import random
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.airbnb import scrapear_airbnb

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

# Ruta del CSV de reservas propias
RUTA_ROWS_CSV = "rows.csv"

# Máximo de páginas por búsqueda (mantener bajo para evitar bloqueos)
MAX_PAGINAS = 2

# Número de adultos para las búsquedas
ADULTOS = 2

# Mostrar navegador (False = modo silencioso/headless)
HEADLESS = False

# Pausa entre búsquedas distintas (segundos) — evita bloqueo por IP
PAUSA_ENTRE_BUSQUEDAS_MIN = 20
PAUSA_ENTRE_BUSQUEDAS_MAX = 40

# ─────────────────────────────────────────────
# MAPEO DE PROPIEDADES → CIUDADES DE AIRBNB
# Añade aquí todas tus propiedades y la ciudad más cercana en Airbnb
# ─────────────────────────────────────────────
MAPA_CIUDAD = {
    "valdelinares":      "Valdelinares",
    "oropesa":           "Oropesa del Mar",
    "marina del cid":    "Castellón de la Plana",
    "castellon":         "Castellón de la Plana",
    "castellón":         "Castellón de la Plana",
    "valencia":          "Valencia",
    "madrid":            "Madrid",
    "barcelona":         "Barcelona",
    "benidorm":          "Benidorm",
    "alicante":          "Alicante",
    "torrevieja":        "Torrevieja",
    "gandia":            "Gandía",
    "peñiscola":         "Peñíscola",
    "peniscola":         "Peñíscola",
}


def _detectar_ciudad(nombre_propiedad: str) -> str:
    """
    Detecta la ciudad de Airbnb a buscar a partir del nombre de la propiedad.
    Busca coincidencias parciales (case-insensitive) en MAPA_CIUDAD.

    Args:
        nombre_propiedad: Valor de la columna R_PROPERTY_NAME.

    Returns:
        Ciudad de Airbnb o cadena vacía si no hay coincidencia.
    """
    nombre_lower = str(nombre_propiedad).lower()
    for clave, ciudad in MAPA_CIUDAD.items():
        if clave in nombre_lower:
            return ciudad
    print(f"  ⚠️  Sin mapeo para: '{nombre_propiedad}' — se omite.")
    return ""


def _parsear_fecha(fecha_str: str) -> datetime | None:
    """
    Convierte una fecha en formato DD/MM/YYYY a objeto datetime.

    Args:
        fecha_str: Fecha en formato DD/MM/YYYY.

    Returns:
        Objeto datetime o None si el formato es inválido.
    """
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(str(fecha_str).strip(), fmt)
        except ValueError:
            continue
    return None


def cargar_reservas() -> pd.DataFrame:
    """
    Carga rows.csv y extrae las columnas necesarias:
    R_PROPERTY_NAME, FECHA (checkin), R_NIGHTS.

    Returns:
        DataFrame limpio con columnas: propiedad, checkin, checkout, ciudad.
    """
    print(f"📂 Cargando {RUTA_ROWS_CSV}...")

    # Intentar varios separadores
    df = None
    for sep in [";", ",", "\t"]:
        try:
            df_test = pd.read_csv(RUTA_ROWS_CSV, sep=sep, encoding="latin-1", low_memory=False)
            if df_test.shape[1] > 2:
                df = df_test
                df.columns = [c.replace('"', '').strip() for c in df.columns]
                break
        except Exception:
            continue

    if df is None:
        raise FileNotFoundError(f"No se pudo leer {RUTA_ROWS_CSV}")

    print(f"  ✅ {len(df)} filas cargadas. Columnas: {list(df.columns[:8])}...")

    # Detectar columnas clave
    col_prop    = next((c for c in ["R_PROPERTY_NAME", "property", "propiedad"] if c in df.columns), None)
    col_fecha   = next((c for c in ["FECHA", "R_ARRIVAL", "arrival", "llegada", "checkin", "check_in"] if c in df.columns), None)
    col_noches  = next((c for c in ["R_NIGHTS", "nights", "noches"] if c in df.columns), None)
    col_status  = next((c for c in ["R_STATUS", "R_CONTA", "status", "estado"] if c in df.columns), None)

    if not col_prop:
        raise ValueError(f"No se encontró columna de propiedad. Disponibles: {list(df.columns)}")
    if not col_fecha:
        raise ValueError(f"No se encontró columna de fecha. Disponibles: {list(df.columns)}")

    print(f"  📌 Columnas detectadas: propiedad='{col_prop}', fecha='{col_fecha}', noches='{col_noches}'")

    # Filtrar solo reservas confirmadas si hay columna de estado
    if col_status:
        estados_validos = ["Booked", "Fact.", "Confirmada"]
        df = df[df[col_status].isin(estados_validos)]
        print(f"  🔎 Filtrando reservas confirmadas: {len(df)} filas válidas")

    # Construir DataFrame de trabajo
    filas = []
    for _, row in df.iterrows():
        nombre_prop = str(row[col_prop]).strip()
        ciudad = _detectar_ciudad(nombre_prop)
        if not ciudad:
            continue

        # Parsear fecha de entrada
        fecha_entrada = _parsear_fecha(row[col_fecha]) if col_fecha else None
        if not fecha_entrada:
            continue

        # Calcular fecha de salida
        noches = 1
        if col_noches:
            try:
                noches = max(int(float(str(row[col_noches]).replace(",", "."))), 1)
            except Exception:
                noches = 1
        fecha_salida = fecha_entrada + timedelta(days=noches)

        filas.append({
            "propiedad":  nombre_prop,
            "ciudad":     ciudad,
            "checkin":    fecha_entrada.strftime("%Y-%m-%d"),
            "checkout":   fecha_salida.strftime("%Y-%m-%d"),
            "noches":     noches,
        })

    df_out = pd.DataFrame(filas)
    print(f"  📊 {len(df_out)} reservas válidas con ciudad mapeada.")
    return df_out


def construir_busquedas_unicas(df_reservas: pd.DataFrame) -> list[dict]:
    """
    Agrupa las reservas por propiedad y crea búsquedas únicas por ciudad.
    Para cada propiedad, selecciona hasta 3 fechas representativas
    (la más próxima, una en verano y una en temporada media).

    Args:
        df_reservas: DataFrame con columnas propiedad, ciudad, checkin, checkout.

    Returns:
        Lista de dicts con ciudad, checkin, checkout, propiedad_referencia.
    """
    busquedas = []
    hoy = datetime.today()

    for propiedad, grupo in df_reservas.groupby("propiedad"):
        ciudad = grupo["ciudad"].iloc[0]

        # Ordenar por fecha y filtrar solo fechas futuras o recientes
        grupo = grupo.copy()
        grupo["dt_checkin"] = pd.to_datetime(grupo["checkin"])
        grupo_futuro = grupo[grupo["dt_checkin"] >= hoy].sort_values("dt_checkin")

        # Si no hay fechas futuras, usar las más recientes del pasado
        if grupo_futuro.empty:
            grupo_futuro = grupo.sort_values("dt_checkin", ascending=False).head(3)

        # Seleccionar hasta 3 fechas distintas para variedad
        seleccionadas = grupo_futuro.drop_duplicates("checkin").head(3)

        for _, fila in seleccionadas.iterrows():
            busquedas.append({
                "ciudad":               fila["ciudad"],
                "checkin":              fila["checkin"],
                "checkout":             fila["checkout"],
                "propiedad_referencia": fila["propiedad"],
            })

    print(f"\n🗺️  Total de búsquedas planificadas: {len(busquedas)}")
    for b in busquedas:
        print(f"  → {b['propiedad_referencia'][:35]} | {b['ciudad']} | {b['checkin']} → {b['checkout']}")
    return busquedas


async def ejecutar_todas_las_busquedas(busquedas: list[dict]) -> None:
    """
    Ejecuta el scraper de Airbnb para cada búsqueda planificada.
    Aplica pausa de seguridad entre búsquedas para evitar bloqueos.

    Args:
        busquedas: Lista de dicts con ciudad, checkin, checkout, propiedad_referencia.
    """
    total = len(busquedas)
    exitosas = 0
    fallidas = 0

    for i, busqueda in enumerate(busquedas, 1):
        print(f"\n{'='*60}")
        print(f"🔍 BÚSQUEDA {i}/{total}: {busqueda['ciudad']}")
        print(f"   Propiedad referencia: {busqueda['propiedad_referencia']}")
        print(f"   Fechas: {busqueda['checkin']} → {busqueda['checkout']}")
        print(f"{'='*60}")

        try:
            resultados = await scrapear_airbnb(
                ciudad=busqueda["ciudad"],
                checkin=busqueda["checkin"],
                checkout=busqueda["checkout"],
                adultos=ADULTOS,
                max_paginas=MAX_PAGINAS,
                headless=HEADLESS,
                propiedad_referencia=busqueda["propiedad_referencia"],
            )
            print(f"  ✅ Completada: {len(resultados)} propiedades extraídas.")
            exitosas += 1

        except Exception as e:
            print(f"  ❌ Error en búsqueda {i}: {e}")
            fallidas += 1

        # Pausa de seguridad entre búsquedas (excepto en la última)
        if i < total:
            pausa = random.uniform(PAUSA_ENTRE_BUSQUEDAS_MIN, PAUSA_ENTRE_BUSQUEDAS_MAX)
            print(f"\n⏳ Pausa de seguridad: {pausa:.0f}s antes de la siguiente búsqueda...")
            await asyncio.sleep(pausa)

    # Resumen final
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"  ✅ Búsquedas exitosas: {exitosas}/{total}")
    print(f"  ❌ Búsquedas fallidas: {fallidas}/{total}")
    print(f"  💾 Datos guardados en: data/mercado_airbnb.csv")
    print(f"{'='*60}")


async def main():
    """Punto de entrada principal del coordinador."""
    print("🚀 Iniciando análisis de competencia basado en rows.csv\n")

    # 1. Cargar y procesar reservas
    try:
        df_reservas = cargar_reservas()
    except Exception as e:
        print(f"❌ Error cargando reservas: {e}")
        return

    if df_reservas.empty:
        print("⚠️  No se encontraron reservas válidas con ciudad mapeada.")
        print("   Revisa el MAPA_CIUDAD en este archivo para añadir tus propiedades.")
        return

    # 2. Construir lista de búsquedas únicas
    busquedas = construir_busquedas_unicas(df_reservas)

    if not busquedas:
        print("⚠️  No se generaron búsquedas. Revisa las fechas del CSV.")
        return

    # 3. Ejecutar scraping
    await ejecutar_todas_las_busquedas(busquedas)


if __name__ == "__main__":
    asyncio.run(main())
