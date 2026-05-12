"""
browser.py — Configuración del navegador con técnicas anti-detección.
Rota User-Agent, viewport, locale y oculta firmas de Playwright.
"""

import random
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ─────────────────────────────────────────────
# PERFILES DE USER-AGENT REALES
# ─────────────────────────────────────────────
USER_AGENTS = [
    # Chrome 120 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome 119 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Edge 120 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Firefox 121 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Chrome 118 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

# ─────────────────────────────────────────────
# RESOLUCIONES DE PANTALLA REALES
# ─────────────────────────────────────────────
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 720},
]

# ─────────────────────────────────────────────
# SCRIPT ANTI-DETECCIÓN
# Oculta navigator.webdriver y otras firmas de automatización
# ─────────────────────────────────────────────
ANTI_DETECTION_SCRIPT = """
    // Ocultar navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // Simular plugins reales del navegador
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' }
        ]
    });
    
    // Simular idiomas del navegador
    Object.defineProperty(navigator, 'languages', {
        get: () => ['es-ES', 'es', 'en-US', 'en']
    });
    
    // Ocultar automatización en el chrome object
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    
    // Evitar detección por permisos
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
"""


async def crear_navegador(headless: bool = False) -> tuple:
    """
    Crea y devuelve (playwright, browser, context, page) con configuración anti-detección.
    
    Args:
        headless: Si True, el navegador no será visible.
    
    Returns:
        Tupla (playwright, browser, context, page)
    """
    # Seleccionar UA y viewport aleatorios para esta sesión
    user_agent = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    
    print(f"🌐 User-Agent: {user_agent[:60]}...")
    print(f"📐 Viewport: {viewport['width']}x{viewport['height']}")
    
    playwright = await async_playwright().start()
    
    # Lanzar Chromium con argumentos para reducir detección
    browser: Browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--start-maximized",
            "--disable-extensions",
            "--disable-plugins-discovery",
            "--disable-web-security",
            "--lang=es-ES",
        ]
    )
    
    # Crear contexto con configuración realista
    context: BrowserContext = await browser.new_context(
        user_agent=user_agent,
        viewport=viewport,
        locale="es-ES",
        timezone_id="Europe/Madrid",
        # Headers HTTP como un navegador real
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        },
        # Simular dispositivo real
        device_scale_factor=1,
        has_touch=False,
        is_mobile=False,
        java_script_enabled=True,
    )
    
    # Inyectar script anti-detección en cada nueva página
    await context.add_init_script(ANTI_DETECTION_SCRIPT)
    
    # Crear primera página
    page: Page = await context.new_page()
    
    return playwright, browser, context, page


async def cerrar_navegador(playwright, browser) -> None:
    """Cierra el navegador y libera recursos."""
    await browser.close()
    await playwright.stop()
    print("🔒 Navegador cerrado correctamente.")
