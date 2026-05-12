"""
human.py — Simulación de comportamiento humano en el navegador.
Movimientos de ratón en curva de Bézier, scroll progresivo y pausas naturales.
"""

import asyncio
import random
import math
from playwright.async_api import Page


async def pausa_humana(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """
    Pausa aleatoria para simular tiempo de lectura/reacción humana.
    
    Args:
        min_s: Tiempo mínimo de espera en segundos.
        max_s: Tiempo máximo de espera en segundos.
    """
    tiempo = random.uniform(min_s, max_s)
    await asyncio.sleep(tiempo)


def _bezier_cubica(p0, p1, p2, p3, t):
    """
    Calcula un punto en una curva de Bézier cúbica.
    
    Args:
        p0, p1, p2, p3: Puntos de control (x, y).
        t: Parámetro entre 0 y 1.
    
    Returns:
        Tupla (x, y) del punto en la curva.
    """
    x = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0]
    y = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


async def mover_raton_humano(page: Page, x_destino: int, y_destino: int) -> None:
    """
    Mueve el ratón desde la posición actual hasta (x_destino, y_destino)
    siguiendo una curva de Bézier cúbica para simular movimiento humano natural.
    
    Args:
        page: Página de Playwright.
        x_destino: Coordenada X de destino.
        y_destino: Coordenada Y de destino.
    """
    # Obtener posición actual del ratón (aproximada al centro si no hay historial)
    viewport = page.viewport_size or {"width": 1366, "height": 768}
    x_inicio = random.randint(100, viewport["width"] - 100)
    y_inicio = random.randint(100, viewport["height"] - 100)
    
    # Puntos de control aleatorios para la curva (dan naturalidad al movimiento)
    cp1 = (
        x_inicio + random.randint(-100, 100),
        y_inicio + random.randint(-100, 100)
    )
    cp2 = (
        x_destino + random.randint(-100, 100),
        y_destino + random.randint(-100, 100)
    )
    
    # Número de pasos (más pasos = movimiento más suave pero más lento)
    pasos = random.randint(20, 40)
    
    for i in range(pasos + 1):
        t = i / pasos
        punto = _bezier_cubica(
            (x_inicio, y_inicio), cp1, cp2, (x_destino, y_destino), t
        )
        await page.mouse.move(punto[0], punto[1])
        # Pausa mínima entre cada movimiento (simula velocidad variable)
        await asyncio.sleep(random.uniform(0.01, 0.03))
    
    # Pequeña pausa al llegar al destino
    await asyncio.sleep(random.uniform(0.1, 0.3))


async def scroll_humano(page: Page, distancia: int = 500) -> None:
    """
    Hace scroll progresivo hacia abajo simulando comportamiento humano.
    Incluye micro-pausas variables para parecer natural.
    
    Args:
        page: Página de Playwright.
        distancia: Píxeles totales a bajar.
    """
    # Dividir el scroll en segmentos variables
    recorrido = 0
    while recorrido < distancia:
        # Tamaño de cada "golpe" de scroll (variable)
        paso = random.randint(80, 200)
        recorrido += paso
        
        await page.mouse.wheel(0, paso)
        
        # Pausa variable entre golpes de scroll
        await asyncio.sleep(random.uniform(0.05, 0.2))
    
    # Pausa final después del scroll
    await asyncio.sleep(random.uniform(0.3, 0.8))


async def simular_lectura(page: Page) -> None:
    """
    Simula que un humano está leyendo la página: scroll lento progresivo
    con pausas como si detuviese la vista en distintos puntos.
    
    Args:
        page: Página de Playwright.
    """
    print("👁️  Simulando lectura de página...")
    
    # Obtener altura aproximada de la página
    altura_pagina = await page.evaluate("document.body.scrollHeight")
    
    # Scroll progresivo cubriendo toda la página
    posicion_actual = 0
    while posicion_actual < altura_pagina:
        # Avanzar un bloque
        bloque = random.randint(200, 400)
        posicion_actual = min(posicion_actual + bloque, altura_pagina)
        
        await page.evaluate(f"window.scrollTo(0, {posicion_actual})")
        
        # Pausa como si estuviera leyendo (más larga que el scroll normal)
        await asyncio.sleep(random.uniform(0.4, 1.2))
        
        # 20% de probabilidad de hacer una pausa larga (como si leyera algo interesante)
        if random.random() < 0.2:
            await asyncio.sleep(random.uniform(1.5, 3.0))
    
    # Volver al inicio suavemente
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(random.uniform(0.5, 1.0))


async def pausa_entre_paginas(larga: bool = False) -> None:
    """
    Pausa entre carga de páginas del scraper.
    Si 'larga' es True, la pausa es considerablemente mayor.
    
    Args:
        larga: Si True, aplica pausa extra de 15-25 segundos.
    """
    # Pausa base: 8-15 segundos
    base = random.uniform(8, 15)
    await asyncio.sleep(base)
    print(f"⏱️  Pausa base: {base:.1f}s")
    
    if larga:
        extra = random.uniform(15, 25)
        print(f"⏳ Pausa extra larga: {extra:.1f}s (simulando comportamiento humano)")
        await asyncio.sleep(extra)
