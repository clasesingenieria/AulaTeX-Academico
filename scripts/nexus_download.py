"""Descarga recursos desde Plataforma Nexus (UANL) usando Playwright.

Uso seguro:
- Define las credenciales en variables de entorno `NEXUS_USER` y `NEXUS_PASS` o en un archivo `.env` (no lo comites).
- Ejecuta: `python scripts/nexus_download.py --download-dir downloads/nexus`.

Este script intenta iniciar sesión, navegar a la sección de Recursos y descargar enlaces detectables.
Los selectores son ejemplos y deben ajustarse según la UI real de la plataforma.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda *a, **k: None

from playwright.sync_api import sync_playwright


def get_credentials() -> tuple[Optional[str], Optional[str]]:
    # Intentar cargar .env si existe
    load_dotenv()
    user = os.getenv("NEXUS_USER")
    pwd = os.getenv("NEXUS_PASS")
    return user, pwd


def login_uanl_sia_se(page, user: str, pwd: str):
    page.goto("https://www.uanl.mx/enlinea/", wait_until="domcontentloaded")
    frame = page.frame_locator("iframe")

    frame.locator("#tipo").select_option(label="Alumno")
    frame.locator("#cuenta").fill(user)
    frame.locator("#pass").fill(pwd)
    frame.locator("button:has-text(\"Entrar\")").click()

    page.wait_for_load_state("networkidle")

    # En este flujo real no se selecciona la carrera: el botón de Nexus se despliega
    # directamente desde SIASE y hace la autenticación correcta al portal.
    nexus_btn = page.locator('input[name="btnNexus"]')
    if not nexus_btn.count():
        raise RuntimeError("No se encontró el botón de Nexus en SIASE")

    # El formulario usa target="_new" y entrega un token temporal a Nexus.
    # Debemos continuar en esa pestaña; una navegación directa pierde el token.
    with page.expect_popup() as popup_info:
        nexus_btn.first.click(force=True)
    nexus_page = popup_info.value
    nexus_page.wait_for_load_state("domcontentloaded")
    nexus_page.wait_for_timeout(10000)
    return nexus_page


def download_resources(download_dir: Path, headless: bool = True, base_url: str | None = None) -> None:
    user, pwd = get_credentials()
    if not user or not pwd:
        raise SystemExit("Credenciales no encontradas. Define NEXUS_USER y NEXUS_PASS en el entorno.")

    download_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        nexus_page = login_uanl_sia_se(page, user, pwd)

        # La pestaña abierta por SIASE ya contiene la autenticación.
        if base_url:
            nexus_page.goto(base_url, wait_until="domcontentloaded")
        nexus_page.wait_for_load_state("networkidle")

        # Buscar posibles elementos de recurso; los selectores son heurísticos.
        candidates = nexus_page.query_selector_all("a[href$='.pdf'], a[href$='.zip'], a[title*='Descargar'], button[title*='Descargar'], .resource-row a, .resource-item a")

        if not candidates:
            print("No se detectaron enlaces de recursos con los selectores actuales. Revisa y ajusta los selectores en el script.")

        seen = set()
        for i, el in enumerate(candidates, start=1):
            try:
                href = el.get_attribute("href")
            except Exception:
                href = None

            if href and href not in seen:
                seen.add(href)
                print(f"Descargando enlace directo: {href}")
                with nexus_page.expect_download() as dl:
                    nexus_page.evaluate("(u) => window.open(u, '_blank')", href)
                download = dl.value
                dest = download_dir / f"{i}_{Path(download.suggested_filename).name}"
                download.save_as(str(dest))
                print("Guardado:", dest)
                continue

            try:
                with nexus_page.expect_download() as dl:
                    el.click()
                download = dl.value
                dest = download_dir / f"{i}_{Path(download.suggested_filename).name}"
                download.save_as(str(dest))
                print("Guardado:", dest)
            except Exception:
                try:
                    link = el.query_selector("a[href]")
                    if link:
                        href2 = link.get_attribute("href")
                        if href2 and href2 not in seen:
                            seen.add(href2)
                            with nexus_page.expect_download() as dl:
                                nexus_page.evaluate("(u) => window.open(u, '_blank')", href2)
                            download = dl.value
                            dest = download_dir / f"{i}_{Path(download.suggested_filename).name}"
                            download.save_as(str(dest))
                            print("Guardado:", dest)
                except Exception:
                    print(f"No se pudo descargar el elemento #{i}.")

        context.close()
        browser.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Descargar recursos desde Plataforma Nexus (UANL)")
    p.add_argument("--download-dir", default="downloads/nexus_biologia_celular")
    p.add_argument("--no-headless", dest="headless", action="store_false", help="Ejecutar con UI visible")
    p.add_argument("--base-url", default=None, help="URL de recursos (solo si se requiere navegar después del acceso SIASE)")
    args = p.parse_args()

    download_dir = Path(args.download_dir)
    try:
        download_resources(download_dir, headless=args.headless, base_url=args.base_url)
    except SystemExit as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
