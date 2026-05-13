"""
airbnb.py — Scraper principal de Airbnb con comportamiento humano y anti-detección.
Extrae precios, ratings y datos de propiedades para análisis de mercado.
"""

import asyncio
import random
import re
import os
import sys
from datetime import date, datetime
import pandas as pd
from playwright.async_api import Page

# Soporte para ejecución directa (py -m scraper.airbnb) e importación
try:
    from scraper.browser import crear_navegador, cerrar_navegador
    from scraper.human import (
        mover_raton_humano, scroll_humano, simular_lectura,
        pausa_humana, pausa_entre_paginas
    )
except ModuleNotFoundError:
    # Fallback: añadir raíz del proyecto al path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scraper.browser import crear_navegador, cerrar_navegador
    from scraper.human import (
        mover_raton_humano, scroll_humano, simular_lectura,
        pausa_humana, pausa_entre_paginas
    )

# ─────────────────────────────────────────────
# CONSTANTES Y SELECTORES
# ─────────────────────────────────────────────

# Selectores para tarjetas de propiedad — validados con test_scraper.py
SELECTORES_TARJETA = [
    '[data-testid="card-container"]',       # ✅ Confirmado (18 elementos)
    '[itemprop="itemListElement"]',          # ✅ Confirmado fallback
    'div[data-testid="listing-card-wrapper"]',
]

# Selectores para precio — validados con test_scraper.py
SELECTORES_PRECIO = [
    '[data-testid="price-availability-row"]',  # ✅ Confirmado (18 elementos)
    '._1jo4hgw',
    '[class*="pricingText"]',
]

# Selectores para título — validados con test_scraper.py
SELECTORES_TITULO = [
    '[id^="title_"]',                       # El más específico (ej: title_12345)
    '[data-testid="listing-card-title"]',   # ✅ Confirmado (18 elementos)
    'div[data-testid="listing-card-name"]',
]

# Nota: el rating NO tiene selector CSS válido en Airbnb actualmente.
# Se extrae vía regex del texto completo de la tarjeta (ej: "4,81 (113)")
SELECTORES_RATING = []

# Columnas del CSV de salida (incluyendo propiedad_referencia)
COLUMNAS_CSV = [
    "nombre", "precio_noche", "rating", "num_reviews",
    "tipo", "capacidad", "url", "fecha_scraping",
    "checkin", "checkout", "ciudad", "propiedad_referencia"
]

# Ruta de salida del CSV
RUTA_CSV = "data/mercado_airbnb.csv"


# ─────────────────────────────────────────────
# FUNCIONES AUXILIARES DE EXTRACCIÓN
# ─────────────────────────────────────────────

def _limpiar_precio(texto: str, noches: int = 1) -> int | None:
    """
    Extrae el precio por noche de un texto.
    Airbnb puede mostrar el precio total ('513 € en total') o por noche.
    Si detecta 'total', divide entre noches para obtener precio/noche.
    """
    if not texto:
        return None
    # Limpiar separadores de miles europeos (1.234 → 1234) y espacios raros
    texto_limpio = texto.replace('.', '').replace(',', '').replace('\xa0', ' ')
    # Buscar el primer número de 2 a 5 dígitos (precio)
    numeros = re.findall(r'\d{2,5}', texto_limpio)
    if not numeros:
        return None
    
    # Si hay múltiples números y dice "total", el primero suele ser el total
    precio = int(numeros[0])
    
    # Si el texto indica precio total, dividir entre noches
    if ('total' in texto.lower() or 'estancia' in texto.lower()) and noches > 1:
        precio = max(1, precio // noches)
    return precio


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

async def _extraer_tarjeta(
    tarjeta, checkin: str, checkout: str, ciudad: str,
    noches: int = 1, propiedad_referencia: str = ""
) -> dict | None:
    """
    Extrae todos los datos de una tarjeta de propiedad individual.
    Devuelve None si no se puede extraer el precio (dato obligatorio).
    """
    try:
        # Obtener texto completo de la tarjeta (usado para rating y tipo)
        texto_completo = ""
        try:
            texto_completo = await tarjeta.inner_text(timeout=2000)
        except Exception:
            pass

        # ── Título ──
        # Intentamos obtener el título vía selector específico
        titulo_raw = await _primer_selector_valido(tarjeta, SELECTORES_TITULO)
        
        nombre = "Sin nombre"
        if titulo_raw:
            nombre = titulo_raw.strip().split('\n')[0]
        
        # Palabras que suelen indicar un título genérico de Airbnb
        palabras_genericas = ["apartamento en", "casa en", "estudio en", "habitación en", "loft en", "villa en", "vivienda en", "alojamiento en"]
        es_generico = any(g in nombre.lower() for g in palabras_genericas)
        
        # Si el nombre es genérico o no tenemos título, buscamos en el texto completo
        if (not titulo_raw or es_generico) and texto_completo:
            lineas = [l.strip() for l in texto_completo.split('\n') if len(l.strip()) > 5]
            
            # Filtros de exclusión para limpiar el ruido
            excluir = ["superanfitrión", "nuevo", "★", "evaluaciones", "reseñas", "profesional", "anfitrión", "dormitorio", "cama", "baño", "noche", "total"]
            candidatos = [l for l in lineas if not any(e in l.lower() for e in excluir)]
            
            # Buscamos la línea que sea más descriptiva y no sea la genérica ya detectada
            mejor_nombre = nombre
            for c in candidatos:
                c_lower = c.lower()
                # Si encontramos una línea que no tenga las palabras genéricas y sea larga, esa es la buena
                if not any(g in c_lower for g in palabras_genericas) and len(c) > 8:
                    mejor_nombre = c
                    break
                # Si la línea tiene palabras genéricas pero es distinta a la que ya tenemos y es más larga
                elif c != nombre and len(c) > len(mejor_nombre) and len(c) > 15:
                    mejor_nombre = c
            
            nombre = mejor_nombre

        # ── Precio ──
        precio_raw = await _primer_selector_valido(tarjeta, SELECTORES_PRECIO)
        # Fallback: buscar precio en texto completo si el selector falla
        if not precio_raw and texto_completo:
            # Buscar patrón de precio (ej: 513 €)
            match_precio = re.search(r'(\d[\d\.\s,]*)\s*€', texto_completo)
            precio_raw = match_precio.group(0) if match_precio else None
        
        precio_noche = _limpiar_precio(precio_raw, noches=noches) if precio_raw else None

        # Sin precio no hay dato útil
        if not precio_noche:
            return None

        # ── Rating — extraído via regex del texto completo ──
        # Formato en Airbnb.es: "4,81 (113)" o "Valoración media de 4,81 sobre 5"
        rating = None
        num_reviews = None
        if texto_completo:
            # Patrón: número decimal seguido de paréntesis con reviews
            match_rating = re.search(r'(\d)[,\.](\d{2})\s*\((\d+)\)', texto_completo)
            if match_rating:
                rating = float(f"{match_rating.group(1)}.{match_rating.group(2)}")
                num_reviews = int(match_rating.group(3))
            else:
                # Fallback: buscar solo el decimal
                match_r2 = re.search(r'(\d)[,\.](\d{2})\s*(?:sobre|out)', texto_completo)
                if match_r2:
                    rating = float(f"{match_r2.group(1)}.{match_r2.group(2)}")

        # ── Tipo de alojamiento — búsqueda en texto completo ──
        tipo = "Desconocido"
        for keyword in ["Apartamento entero", "Habitación privada", "Habitación compartida", "Casa entera", "Cabaña", "Apartamento en"]:
            if keyword.lower() in texto_completo.lower():
                tipo = keyword
                break

        # ── Capacidad ──
        capacidad = None
        match_cap = re.search(r'(\d+)\s*(?:huésped|huesped|guest)', texto_completo, re.IGNORECASE)
        if match_cap:
            capacidad = int(match_cap.group(1))

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
            "propiedad_referencia": propiedad_referencia,
        }

    except Exception as e:
        print(f"  ⚠️  Error en tarjeta individual: {e}")
        return None


# ─────────────────────────────────────────────
# EXTRACCIÓN DE UNA PÁGINA COMPLETA
# ─────────────────────────────────────────────

async def _extraer_pagina(
    page: Page, checkin: str, checkout: str, ciudad: str,
    noches: int = 1, propiedad_referencia: str = ""
) -> list[dict]:
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
                print(f"  ✅ Selector de tarjeta: {selector} ({count} tarjetas)")
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
        datos = await _extraer_tarjeta(
                tarjeta, checkin, checkout, ciudad,
                noches=noches, propiedad_referencia=propiedad_referencia
            )
        if datos:
            resultados.append(datos)
            print(f"    ✓ {datos['nombre'][:40]} — €{datos['precio_noche']}/noche | ⭐{datos['rating']}")

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
    headless: bool = False,
    propiedad_referencia: str = "",
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
    # Calcular noches para convertir precio total → precio por noche
    from datetime import date as _date
    try:
        d1 = _date.fromisoformat(checkin)
        d2 = _date.fromisoformat(checkout)
        noches = max((d2 - d1).days, 1)
    except Exception:
        noches = 1
    print(f"🌙 Noches calculadas: {noches}")
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

                    # ── Detección de CAPTCHA (más estricta para evitar falsos positivos) ──
                    contenido = await page.content()
                    # Solo es CAPTCHA real si NO hay tarjetas de listado en la página
                    hay_tarjetas = '[data-testid="card-container"]' in contenido or 'itemListElement' in contenido
                    es_captcha = (
                        ("captcha" in contenido.lower() or "are you a robot" in contenido.lower())
                        and not hay_tarjetas
                    )
                    if es_captcha:
                        print("  🤖 CAPTCHA real detectado. Guardando screenshot y esperando 60s...")
                        await page.screenshot(path=f"data/captcha_p{num_pagina}.png")
                        await asyncio.sleep(60)
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
                    resultados_pagina = await _extraer_pagina(
                        page, checkin, checkout, ciudad,
                        noches=noches, propiedad_referencia=propiedad_referencia
                    )
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
