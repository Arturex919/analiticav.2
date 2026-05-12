"""
airbnb.py — Scraper principal de Airbnb con comportamiento humano y anti-detección.
Extrae precios, ratings y datos de propiedades para análisis de mercado.
"""

import asyncio
import random
import re
import os
from datetime import date, datetime
import pandas as pd
from playwright.async_api import Page

from scraper.browser import crear_navegador, cerrar_navegador
from scraper.human import (
    mover_raton_humano, scroll_humano, simular_lectura,
    pausa_humana, pausa_entre_paginas
)

# ─────────────────────────────────────────────
# CONSTANTES Y SELECTORES
# ─────────────────────────────────────────────

# Selectores para tarjetas de propiedad (en orden de preferencia)
SELECTORES_TARJETA = [
    '[data-testid="card-container"]',
    '[itemprop="itemListElement"]',
    'div[data-testid="listing-card-wrapper"]',
    'div[class*="c4mnd7m"]',
]

# Selectores para precio
SELECTORES_PRECIO = [
    '[data-testid="price-availability-row"]',
    '._1jo4hgw',
    '[class*="pricingText"]',
    'span[class*="Price"]',
    'div[class*="price"]',
]

# Selectores para título
SELECTORES_TITULO = [
    '[data-testid="listing-card-title"]',
    'div[data-testid="listing-card-name"]',
    '[class*="title"]',
    'span[class*="name"]',
]

# Selectores para rating
SELECTORES_RATING = [
    '[class*="r1dxllyb"]',
    '[aria-label*="estrellas"]',
    '[aria-label*="stars"]',
    'span[class*="rating"]',
]

# Columnas del CSV de salida
COLUMNAS_CSV = [
    "nombre", "precio_noche", "rating", "num_reviews",
    "tipo", "capacidad", "url", "fecha_scraping",
    "checkin", "checkout", "ciudad"
]

# Ruta de salida del CSV
RUTA_CSV = "data/mercado_airbnb.csv"


# ─────────────────────────────────────────────
# FUNCIONES AUXILIARES DE EXTRACCIÓN
# ─────────────────────────────────────────────

def _limpiar_precio(texto: str) -> int | None:
    """Extrae el número entero de un texto de precio (ej: '€ 120 noche' → 120)."""
    if not texto:
        return None
    # Buscar número entre 2 y 5 dígitos (precio por noche razonable)
    numeros = re.findall(r'\d{2,5}', texto.replace('.', '').replace(',', ''))
    if numeros:
        return int(numeros[0])
    return None


def _limpiar_rating(texto: str) -> float | None:
    """Extrae el float de rating de un texto (ej: '4,85 (203)' → 4.85)."""
    if not texto:
        return None
    match = re.search(r'(\d+)[,.](\d+)', texto)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    return None


def _limpiar_reviews(texto: str) -> int | None:
    """Extrae el número de reseñas de un texto (ej: '(203 reseñas)' → 203)."""
    if not texto:
        return None
    numeros = re.findall(r'\d+', texto)
    if numeros:
        return int(numeros[-1])  # El último número suele ser el de reseñas
    return None


async def _primer_selector_valido(tarjeta, selectores: list) -> str | None:
    """Prueba selectores en orden y devuelve el texto del primero que funcione."""
    for selector in selectores:
        try:
            el = tarjeta.locator(selector).first
            if await el.count() > 0:
                return await el.inner_text(timeout=1000)
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────
# EXTRACCIÓN DE UNA TARJETA
# ─────────────────────────────────────────────

async def _extraer_tarjeta(tarjeta, checkin: str, checkout: str, ciudad: str) -> dict | None:
    """
    Extrae todos los datos de una tarjeta de propiedad individual.
    Devuelve None si no se puede extraer el precio (dato obligatorio).
    """
    try:
        # ── Título ──
        titulo_raw = await _primer_selector_valido(tarjeta, SELECTORES_TITULO)
        nombre = titulo_raw.strip().split('\n')[0] if titulo_raw else "Sin nombre"

        # ── Precio ──
        precio_raw = await _primer_selector_valido(tarjeta, SELECTORES_PRECIO)
        precio_noche = _limpiar_precio(precio_raw) if precio_raw else None

        # Sin precio no hay dato útil
        if not precio_noche:
            return None

        # ── Rating ──
        rating_raw = await _primer_selector_valido(tarjeta, SELECTORES_RATING)
        rating = _limpiar_rating(rating_raw) if rating_raw else None
        num_reviews = _limpiar_reviews(rating_raw) if rating_raw else None

        # ── Tipo de alojamiento ──
        tipo = "Desconocido"
        try:
            # Buscar en texto completo de la tarjeta
            texto_completo = await tarjeta.inner_text(timeout=2000)
            for keyword in ["Apartamento entero", "Habitación privada", "Habitación compartida", "Casa entera", "Cabaña"]:
                if keyword.lower() in texto_completo.lower():
                    tipo = keyword
                    break
        except Exception:
            pass

        # ── Capacidad ──
        capacidad = None
        try:
            texto_completo = texto_completo if 'texto_completo' in dir() else await tarjeta.inner_text(timeout=2000)
            match_cap = re.search(r'(\d+)\s*(?:huésped|huesped|guest)', texto_completo, re.IGNORECASE)
            if match_cap:
                capacidad = int(match_cap.group(1))
        except Exception:
            pass

        # ── URL ──
        url = ""
        try:
            enlace = tarjeta.locator("a").first
            if await enlace.count() > 0:
                href = await enlace.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"https://www.airbnb.es{href}"
        except Exception:
            pass

        return {
            "nombre": nombre,
            "precio_noche": precio_noche,
            "rating": rating,
            "num_reviews": num_reviews,
            "tipo": tipo,
            "capacidad": capacidad,
            "url": url,
            "fecha_scraping": date.today().strftime("%Y-%m-%d"),
            "checkin": checkin,
            "checkout": checkout,
            "ciudad": ciudad,
        }

    except Exception as e:
        print(f"  ⚠️  Error en tarjeta individual: {e}")
        return None


# ─────────────────────────────────────────────
# EXTRACCIÓN DE UNA PÁGINA COMPLETA
# ─────────────────────────────────────────────

async def _extraer_pagina(page: Page, checkin: str, checkout: str, ciudad: str) -> list[dict]:
    """
    Extrae todas las propiedades de la página actual.
    Hace scroll completo para cargar contenido lazy antes de extraer.
    """
    print("  📜 Cargando contenido con scroll...")
    await simular_lectura(page)

    resultados = []

    # Probar selectores de tarjeta en orden hasta encontrar uno que funcione
    tarjetas = None
    for selector in SELECTORES_TARJETA:
        try:
            count = await page.locator(selector).count()
            if count > 0:
                print(f"  ✅ Selector de tarjeta válido: {selector} ({count} tarjetas)")
                tarjetas = page.locator(selector)
                break
        except Exception:
            continue

    if not tarjetas:
        print("  ❌ No se encontraron tarjetas con ningún selector.")
        return []

    total = await tarjetas.count()
    print(f"  🏠 Extrayendo {total} propiedades...")

    for i in range(total):
        tarjeta = tarjetas.nth(i)
        datos = await _extraer_tarjeta(tarjeta, checkin, checkout, ciudad)
        if datos:
            resultados.append(datos)
            print(f"    ✓ {datos['nombre'][:40]} — €{datos['precio_noche']}/noche")

    print(f"  📦 {len(resultados)}/{total} propiedades extraídas con precio.")
    return resultados


# ─────────────────────────────────────────────
# GESTIÓN DEL CSV
# ─────────────────────────────────────────────

def guardar_csv(nuevos_datos: list[dict]) -> None:
    """
    Guarda los datos en el CSV principal haciendo append si ya existe.
    Elimina duplicados por url+checkin y genera backup con fecha.
    """
    if not nuevos_datos:
        print("⚠️  Sin datos para guardar.")
        return

    os.makedirs("data", exist_ok=True)
    df_nuevo = pd.DataFrame(nuevos_datos, columns=COLUMNAS_CSV)

    # Hacer append si ya existe el CSV
    if os.path.exists(RUTA_CSV):
        df_existente = pd.read_csv(RUTA_CSV, encoding="utf-8-sig")
        df_total = pd.concat([df_existente, df_nuevo], ignore_index=True)
        # Eliminar duplicados por url + checkin
        df_total = df_total.drop_duplicates(subset=["url", "checkin"], keep="last")
    else:
        df_total = df_nuevo

    # Asegurar tipos correctos
    df_total["precio_noche"] = pd.to_numeric(df_total["precio_noche"], errors="coerce").fillna(0).astype(int)

    # Guardar CSV principal
    df_total.to_csv(RUTA_CSV, index=False, encoding="utf-8-sig")
    print(f"💾 CSV guardado: {RUTA_CSV} ({len(df_total)} propiedades totales)")

    # Guardar backup con fecha
    fecha_hoy = date.today().strftime("%Y%m%d")
    ruta_backup = f"data/mercado_airbnb_{fecha_hoy}.csv"
    df_total.to_csv(ruta_backup, index=False, encoding="utf-8-sig")
    print(f"📋 Backup guardado: {ruta_backup}")


# ─────────────────────────────────────────────
# SCRAPER PRINCIPAL
# ─────────────────────────────────────────────

async def scrapear_airbnb(
    ciudad: str = "Valencia",
    checkin: str = "2026-07-15",
    checkout: str = "2026-07-20",
    adultos: int = 2,
    max_paginas: int = 3,
    headless: bool = False
) -> list[dict]:
    """
    Scraper principal de Airbnb. Extrae propiedades con comportamiento humano.

    Args:
        ciudad: Ciudad a buscar.
        checkin: Fecha de entrada (YYYY-MM-DD).
        checkout: Fecha de salida (YYYY-MM-DD).
        adultos: Número de adultos.
        max_paginas: Máximo de páginas a procesar (máx recomendado: 5).
        headless: Si True, el navegador no es visible.

    Returns:
        Lista de diccionarios con datos de cada propiedad.
    """
    playwright, browser, context, page = await crear_navegador(headless=headless)

    # URL de búsqueda de Airbnb
    url_busqueda = (
        f"https://www.airbnb.es/s/{ciudad}/homes"
        f"?checkin={checkin}&checkout={checkout}&adults={adultos}"
        f"&currency=EUR&locale=es"
    )

    todos_resultados = []
    paginas_procesadas = 0
    errores = 0

    try:
        # ── PASO 1: Visitar la home primero (regla anti-bloqueo) ──
        print("🏠 Visitando airbnb.es home...")
        await page.goto("https://www.airbnb.es", wait_until="domcontentloaded", timeout=30000)
        await pausa_humana(3, 6)
        await simular_lectura(page)
        await pausa_humana(2, 4)

        print(f"\n🔍 Iniciando búsqueda en {ciudad}: {checkin} → {checkout}, {adultos} adultos")
        print(f"📄 Máximo {max_paginas} páginas\n")

        # ── PASO 2: Procesar páginas de resultados ──
        url_actual = url_busqueda

        for num_pagina in range(1, max_paginas + 1):
            print(f"\n{'='*50}")
            print(f"📄 PÁGINA {num_pagina}/{max_paginas}")
            print(f"{'='*50}")

            # Reintentos por página
            exito_pagina = False
            for intento in range(3):
                try:
                    print(f"  🌐 Navegando a página {num_pagina}... (intento {intento + 1})")
                    await page.goto(url_actual, wait_until="domcontentloaded", timeout=40000)
                    await pausa_humana(2, 4)

                    # ── Detección de CAPTCHA ──
                    contenido = await page.content()
                    if "captcha" in contenido.lower() or "robot" in contenido.lower():
                        print("  🤖 CAPTCHA detectado. Guardando screenshot y esperando 60s...")
                        await page.screenshot(path=f"data/captcha_p{num_pagina}.png")
                        await asyncio.sleep(60)
                        # Reintentar desde la home
                        await page.goto("https://www.airbnb.es", wait_until="domcontentloaded")
                        await pausa_humana(5, 10)
                        continue

                    # ── Mover ratón de forma humana ──
                    viewport = page.viewport_size or {"width": 1366, "height": 768}
                    await mover_raton_humano(
                        page,
                        random.randint(200, viewport["width"] - 200),
                        random.randint(200, viewport["height"] - 200)
                    )

                    # ── Extraer datos ──
                    resultados_pagina = await _extraer_pagina(page, checkin, checkout, ciudad)
                    todos_resultados.extend(resultados_pagina)
                    paginas_procesadas += 1
                    exito_pagina = True
                    break

                except Exception as e:
                    errores += 1
                    print(f"  ❌ Error en página {num_pagina}, intento {intento + 1}: {e}")
                    try:
                        await page.screenshot(path=f"data/error_p{num_pagina}_i{intento}.png")
                    except Exception:
                        pass
                    if intento < 2:
                        print("  ⏳ Esperando 30s antes de reintentar...")
                        await asyncio.sleep(30)

            if not exito_pagina:
                print(f"  ⛔ Página {num_pagina} fallida tras 3 intentos. Pasando a la siguiente.")
                continue

            # ── Buscar enlace de siguiente página ──
            if num_pagina < max_paginas:
                try:
                    # Pausa entre páginas
                    pausa_larga = random.random() < 0.30  # 30% de probabilidad
                    print(f"\n⏱️  Pausa entre páginas (larga: {pausa_larga})...")
                    await pausa_entre_paginas(larga=pausa_larga)

                    # Buscar botón de siguiente página
                    siguiente = page.locator('[aria-label="Siguiente"], [data-testid="pagination-next"]').first
                    if await siguiente.count() > 0:
                        href = await siguiente.get_attribute("href")
                        if href:
                            url_actual = href if href.startswith("http") else f"https://www.airbnb.es{href}"
                        else:
                            await mover_raton_humano(page, 0, 0)
                            await siguiente.click()
                            await pausa_humana(2, 4)
                            url_actual = page.url
                    else:
                        print("  📭 No hay más páginas disponibles.")
                        break
                except Exception as e:
                    print(f"  ⚠️  Error navegando a siguiente página: {e}")
                    break

    except Exception as e:
        print(f"\n💥 Error crítico en el scraper: {e}")
        try:
            await page.screenshot(path="data/error_critico.png")
        except Exception:
            pass

    finally:
        await cerrar_navegador(playwright, browser)

    # ── RESUMEN FINAL ──
    print(f"\n{'='*50}")
    print(f"📊 RESUMEN DEL SCRAPING")
    print(f"{'='*50}")
    print(f"  ✅ Páginas procesadas: {paginas_procesadas}/{max_paginas}")
    print(f"  🏠 Propiedades extraídas: {len(todos_resultados)}")
    print(f"  ❌ Errores: {errores}")
    print(f"{'='*50}\n")

    # Guardar resultados
    if todos_resultados:
        guardar_csv(todos_resultados)

    return todos_resultados


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA DIRECTO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(scrapear_airbnb(
        ciudad="Valencia",
        checkin="2026-07-15",
        checkout="2026-07-20",
        adultos=2,
        max_paginas=3,
        headless=False
    ))
