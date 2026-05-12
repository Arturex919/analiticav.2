"""
test_scraper.py — Script de verificación rápida del scraper.
Abre el navegador, navega a Airbnb, prueba selectores e imprime resultados.
NO extrae datos completos, solo verifica que los selectores funcionan.
"""

import asyncio
import os
from playwright.async_api import async_playwright

# ─────────────────────────────────────────────
# SELECTORES A PROBAR
# ─────────────────────────────────────────────

SELECTORES_TARJETA = [
    '[data-testid="card-container"]',
    '[itemprop="itemListElement"]',
    'div[data-testid="listing-card-wrapper"]',
    'div[class*="c4mnd7m"]',
]

SELECTORES_PRECIO = [
    '[data-testid="price-availability-row"]',
    '._1jo4hgw',
    'span[class*="Price"]',
    'div[class*="price"]',
]

SELECTORES_TITULO = [
    '[data-testid="listing-card-title"]',
    'div[data-testid="listing-card-name"]',
]

SELECTORES_RATING = [
    '[class*="r1dxllyb"]',
    '[aria-label*="estrellas"]',
    '[aria-label*="stars"]',
]


async def test_scraper():
    """
    Test rápido: navega a Airbnb Valencia, prueba selectores y guarda screenshot.
    """
    print("🚀 Iniciando test del scraper...")
    os.makedirs("data", exist_ok=True)

    async with async_playwright() as p:
        # Lanzar navegador visible
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="es-ES",
        )

        # Script anti-detección básico
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        # ── PASO 1: Ir a la home primero ──
        print("\n1️⃣  Navegando a airbnb.es...")
        await page.goto("https://www.airbnb.es", wait_until="domcontentloaded", timeout=30000)
        print("   ✅ Home cargada.")
        await asyncio.sleep(3)

        # ── PASO 2: Ir a búsqueda de Valencia ──
        url_busqueda = (
            "https://www.airbnb.es/s/Valencia/homes"
            "?checkin=2026-07-15&checkout=2026-07-20&adults=2&currency=EUR"
        )
        print(f"\n2️⃣  Navegando a búsqueda de Valencia...")
        await page.goto(url_busqueda, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(4)

        # ── PASO 3: Guardar screenshot ──
        screenshot_path = "data/screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"\n3️⃣  Screenshot guardado: {screenshot_path}")

        # ── PASO 4: Probar selectores de tarjeta ──
        print("\n4️⃣  Probando selectores de TARJETA:")
        selector_valido = None
        for selector in SELECTORES_TARJETA:
            try:
                count = await page.locator(selector).count()
                estado = "✅" if count > 0 else "❌"
                print(f"   {estado} {selector}: {count} elementos")
                if count > 0 and not selector_valido:
                    selector_valido = selector
            except Exception as e:
                print(f"   ⚠️  {selector}: ERROR — {e}")

        # ── PASO 5: Probar selectores de precio ──
        print("\n5️⃣  Probando selectores de PRECIO:")
        for selector in SELECTORES_PRECIO:
            try:
                count = await page.locator(selector).count()
                estado = "✅" if count > 0 else "❌"
                print(f"   {estado} {selector}: {count} elementos")
            except Exception as e:
                print(f"   ⚠️  {selector}: ERROR — {e}")

        # ── PASO 6: Probar selectores de título ──
        print("\n6️⃣  Probando selectores de TÍTULO:")
        for selector in SELECTORES_TITULO:
            try:
                count = await page.locator(selector).count()
                estado = "✅" if count > 0 else "❌"
                print(f"   {estado} {selector}: {count} elementos")
            except Exception as e:
                print(f"   ⚠️  {selector}: ERROR — {e}")

        # ── PASO 7: Probar selectores de rating ──
        print("\n7️⃣  Probando selectores de RATING:")
        for selector in SELECTORES_RATING:
            try:
                count = await page.locator(selector).count()
                estado = "✅" if count > 0 else "❌"
                print(f"   {estado} {selector}: {count} elementos")
            except Exception as e:
                print(f"   ⚠️  {selector}: ERROR — {e}")

        # ── PASO 8: Mostrar texto plano de la primera tarjeta ──
        if selector_valido:
            print(f"\n8️⃣  Texto plano de la PRIMERA TARJETA ({selector_valido}):")
            try:
                primera = page.locator(selector_valido).first
                texto = await primera.inner_text(timeout=3000)
                print("─" * 40)
                print(texto[:500])  # Limitamos a 500 chars para no saturar la consola
                print("─" * 40)
            except Exception as e:
                print(f"   ❌ Error al leer primera tarjeta: {e}")
        else:
            print("\n8️⃣  ⚠️  No se encontró ningún selector de tarjeta válido.")
            print("      Prueba a revisar el HTML de la página con las DevTools.")

        # ── PASO 9: Mostrar URL actual por si hubo redirect ──
        print(f"\n9️⃣  URL actual de la página: {page.url}")

        print("\n✨ Test completado. El navegador se cerrará en 5 segundos...")
        await asyncio.sleep(5)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_scraper())
