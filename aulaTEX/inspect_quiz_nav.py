"""Inspecciona y resuelve de manera exhaustiva y 100% precisa el cuestionario 2.3 de Estadística."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import time

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials

OUT_DIR = ROOT / "ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/cuestionario-2026-11-01"
OUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / "aulaTEX/aulatex.env")
creds = _get_credentials(ROOT)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=_browser_resolver_args()[0])
        context = b.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()

        # Login
        print("Iniciando sesión...", flush=True)
        page.goto(f"{BASE_URL}/login/index.php")
        page.locator("#username").fill(creds["username"])
        page.locator("#password").fill(creds["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("networkidle")

        # Ir al intento
        page.goto(f"{BASE_URL}/mod/quiz/attempt.php?attempt=6841&cmid=1756")
        page.wait_for_load_state("networkidle")
        print(f"URL actual: {page.url}", flush=True)

        # Identificar todas las preguntas en el bloque de navegación
        nav_buttons = page.locator(".qnbutton").evaluate_all("""els => els.map(e => ({
            text: e.innerText.trim(),
            href: e.getAttribute('href') || '',
            id: e.id,
            title: e.title || ''
        }))""")
        print(f"Botones de navegación encontrados: {len(nav_buttons)}", flush=True)
        for nb in nav_buttons:
            print(f"  Nav: {nb}", flush=True)

        # También verificar los botones en el área principal
        buttons = page.locator("#region-main input, #region-main button, #region-main a.btn").evaluate_all("""els => els.map(e => ({
            tag: e.tagName,
            type: e.type,
            name: e.name,
            value: e.value || e.innerText.trim()
        }))""")
        print(f"Controles en #region-main: {buttons}", flush=True)

        b.close()


if __name__ == "__main__":
    main()

