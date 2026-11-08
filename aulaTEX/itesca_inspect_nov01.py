"""Inspecciona en Moodle ITESCA:
1. Modulo 2914: Seminario I - Tarea 14: Marco Teórico
2. Modulo 1756: Estadistica Aplicada - 2.3 Evaluacion 6% Cuestionario
"""
import json
from pathlib import Path
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials

OUT = ROOT / "ITESCA/inspeccion_nov01"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    load_dotenv(ROOT / "aulaTEX/aulatex.env", override=False)
    creds = _get_credentials(ROOT)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, args=_browser_resolver_args()[0])
        try:
            context = browser.new_context(service_workers="block", accept_downloads=True)
            context.set_default_timeout(60000)
            page = context.new_page()
            page.goto(BASE_URL + "/login/index.php")
            page.locator("#username").fill(creds["username"])
            page.locator("#password").fill(creds["password"])
            page.locator("#loginbtn").click()
            del creds

            # Inspect Module 2914 (Tarea 14)
            page.goto(f"{BASE_URL}/mod/assign/view.php?id=2914", wait_until="networkidle")
            t14_text = page.locator("#region-main").inner_text()
            (OUT / "t14_texto.txt").write_text(t14_text, encoding="utf-8")
            page.screenshot(path=str(OUT / "t14_screenshot.png"), full_page=True)

            # Inspect Module 1756 (Cuestionario 2.3)
            page.goto(f"{BASE_URL}/mod/quiz/view.php?id=1756", wait_until="networkidle")
            q23_text = page.locator("#region-main").inner_text()
            (OUT / "q23_texto.txt").write_text(q23_text, encoding="utf-8")
            page.screenshot(path=str(OUT / "q23_screenshot.png"), full_page=True)

            summary = {
                "t14_text": t14_text,
                "q23_text": q23_text
            }
            (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Inspeccion ITESCA completada exitosamente.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
