"""Finaliza y envía el intento 6841 del Cuestionario 2.3 en ITESCA Moodle,
obtiene la revisión oficial pregunta por pregunta y guarda toda la evidencia académica.
"""
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

        print("1. Iniciando sesión...", flush=True)
        page.goto(f"{BASE_URL}/login/index.php")
        page.locator("#username").fill(creds["username"])
        page.locator("#password").fill(creds["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("networkidle")

        # Ir a summary.php
        summary_url = f"{BASE_URL}/mod/quiz/summary.php?attempt=6841&cmid=1756"
        print(f"2. Navegando a {summary_url}...", flush=True)
        page.goto(summary_url, wait_until="networkidle")
        time.sleep(1)

        # Si estamos en attempt.php, clickear "Terminar intento..."
        if "attempt.php" in page.url:
            print("Estamos en attempt.php, buscando botón Terminar intento...", flush=True)
            finish_btn = page.locator("input[value='Terminar intento...'], button:has-text('Terminar intento')").first
            if finish_btn.count():
                finish_btn.click()
                page.wait_for_load_state("networkidle")

        print(f"URL de resumen: {page.url}", flush=True)
        page.screenshot(path=str(OUT_DIR / "resumen_preguntas_guardadas.png"), full_page=True)
        summary_text = page.locator("#region-main").inner_text()
        print("Texto del resumen:\n", summary_text, flush=True)
        (OUT_DIR / "resumen_plataforma_texto.txt").write_text(summary_text, encoding="utf-8")

        # Clickear "Enviar todo y terminar"
        print("3. Clickeando Enviar todo y terminar...", flush=True)
        btn_submit = page.locator("button:has-text('Enviar todo y terminar'), input[value='Enviar todo y terminar']").first
        btn_submit.click()
        time.sleep(2)

        # Modal de confirmación
        print("4. Confirmando en modal...", flush=True)
        modal_btn = page.locator(".moodle-dialogue-confirm button:has-text('Enviar todo y terminar'), .moodle-dialogue-confirm input[value='Enviar todo y terminar'], .modal-dialog button:has-text('Enviar todo y terminar')")
        if modal_btn.count():
            modal_btn.first.click()
        else:
            # Buscar cualquier botón primario de confirmación
            prim = page.locator("input[id*='submitbutton'], button.btn-primary:has-text('Enviar')")
            if prim.count():
                prim.first.click()

        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print(f"5. URL alcanzada tras envío: {page.url}", flush=True)
        page.screenshot(path=str(OUT_DIR / "revision_calificacion_final.png"), full_page=True)

        # Extraer todo el contenido de la revisión
        review_main = page.locator("#region-main")
        review_text = review_main.inner_text()
        (OUT_DIR / "revision_final_texto.txt").write_text(review_text, encoding="utf-8")
        print("\n=== REVISIÓN FINAL DE CALIFICACIÓN ===")
        print(review_text[:1500], flush=True)

        # Extraer cada pregunta individualmente de la revisión
        preguntas_revision = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.que')).map(que => {
                const qnum = que.querySelector('.info .no')?.innerText.trim() || '';
                const estado = que.querySelector('.info .state')?.innerText.trim() || '';
                const puntaje = que.querySelector('.info .grade')?.innerText.trim() || '';
                const qtext = que.querySelector('.formulation .qtext')?.innerText.trim() || '';
                const rta_elegida = que.querySelector('.formulation .answer input:checked ~ label, .formulation .answer input:checked ~ td.text, .formulation .answer .checked')?.innerText.trim() || '';
                const rta_correcta_feedback = que.querySelector('.outcome .feedback, .outcome .rightanswer')?.innerText.trim() || '';
                const todas_opciones = Array.from(que.querySelectorAll('.formulation .answer > div, .formulation .answer tr')).map(el => el.innerText.trim());
                return { qnum, estado, puntaje, qtext, rta_elegida, rta_correcta_feedback, todas_opciones };
            });
        }""")

        record = {
            "fecha": "2026-11-01",
            "curso": 209,
            "modulo": 1756,
            "intento": 6841,
            "url_revision": page.url,
            "preguntas": preguntas_revision,
            "texto_completo": review_text
        }
        (OUT_DIR / "revision_detallada_plataforma.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSe extrajeron {len(preguntas_revision)} preguntas detalladas de la revisión.", flush=True)

        b.close()


if __name__ == "__main__":
    main()

