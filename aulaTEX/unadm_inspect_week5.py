"""Inspecciona el estado de la Semana 5 en UnADM para las tres asignaturas activas:
1. Teoria del Estado y Constitucion (3432)
2. Derecho penal especial mexicano (3482)
3. Antecedentes de los derechos humanos (3441)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

COURSES = {
    3432: ("teoria-del-estado-y-constitucion-lde", "Teoria del Estado y Constitucion", "020"),
    3482: ("derecho-penal-especial-mexicano-lde", "Derecho penal especial mexicano", "020"),
    3441: ("antecedentes-de-los-derechos-humanos-lde", "Antecedentes de los derechos humanos", "005"),
}
HOST = "aulavirtual.unadmexico.mx"


def main() -> None:
    load_aulatex_env()
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
    accounts = [
        account for account in vault.list_accounts(pin)
        if account["institution"].casefold() == "unadm"
        and urlsplit(account["url"]).hostname == HOST
    ]
    if len(accounts) != 1:
        raise RuntimeError("Se requiere una unica cuenta UnADM para el sitio autorizado.")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    root = PROJECT_ROOT / "UnADM" / "licenciatura-en-derecho-unadm"

    results = {}

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path, wait_until="domcontentloaded")
        del credentials

        for course_id, (slug, title, group) in COURSES.items():
            print(f"=== Inspeccionando curso {course_id}: {title} ===")
            directory = root / slug
            course_url = f"https://{HOST}/course/view.php?id={course_id}"
            page.goto(course_url, wait_until="domcontentloaded")
            
            # Find section for Week 5
            sections = page.locator(".course-section, li.section").all()
            s5_section = None
            for s in sections:
                txt = s.locator(".sectionname, .section-title, h3").all_inner_texts()
                full_s_txt = s.inner_text()
                if any("Semana 5" in t for t in txt) or "Semana 5" in full_s_txt:
                    s5_section = s
                    break

            s5_info = {"title": title, "course_id": course_id, "url": course_url}
            if s5_section:
                s5_text = s5_section.inner_text()
                s5_links = s5_section.locator("a[href]").evaluate_all(
                    "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
                )
                s5_info["section_text"] = s5_text
                s5_info["links"] = s5_links
                print(f"Semana 5 encontrada en {title} con {len(s5_links)} enlaces.")
            else:
                s5_info["error"] = "No se encontro seccion explicita Semana 5"
                print(f"Semana 5 no encontrada explicitamente en {title}")

            # Inspect assignments / tasks in the course
            assign_links = page.locator('a[href*="/mod/assign/view.php"]').evaluate_all(
                "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
            )
            s5_info["assign_links"] = assign_links
            
            # Also check forums
            forum_links = page.locator('a[href*="/mod/forum/view.php"]').evaluate_all(
                "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
            )
            s5_info["forum_links"] = forum_links

            results[slug] = s5_info

        # Detail inspect each relevant assign
        # 1. Teoria del Estado S5
        teoria_s5 = [l for l in results["teoria-del-estado-y-constitucion-lde"].get("assign_links", []) if "S5" in l["title"] or "Valoraci" in l["title"]]
        if teoria_s5:
            page.goto(teoria_s5[0]["url"], wait_until="domcontentloaded")
            results["teoria-del-estado-y-constitucion-lde"]["s5_assign_detail"] = {
                "title": teoria_s5[0]["title"],
                "url": teoria_s5[0]["url"],
                "text": page.locator("#region-main").inner_text()
            }
        
        # 2. Penal S5
        penal_s5 = [l for l in results["derecho-penal-especial-mexicano-lde"].get("assign_links", []) if "S5" in l["title"] or "ACTIVIDAD S5" in l["title"]]
        if penal_s5:
            page.goto(penal_s5[0]["url"], wait_until="domcontentloaded")
            results["derecho-penal-especial-mexicano-lde"]["s5_assign_detail"] = {
                "title": penal_s5[0]["title"],
                "url": penal_s5[0]["url"],
                "text": page.locator("#region-main").inner_text()
            }

        # 3. Antecedentes DH S5
        dh_links = results["antecedentes-de-los-derechos-humanos-lde"].get("assign_links", []) + results["antecedentes-de-los-derechos-humanos-lde"].get("forum_links", [])
        results["antecedentes-de-los-derechos-humanos-lde"]["modules_detail"] = []
        for l in dh_links:
            page.goto(l["url"], wait_until="domcontentloaded")
            results["antecedentes-de-los-derechos-humanos-lde"]["modules_detail"].append({
                "title": l["title"],
                "url": l["url"],
                "text": page.locator("#region-main").inner_text()
            })

        out_path = root / "estado_unadm_semana5.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Resultados guardados en {out_path}")
        browser.close()


if __name__ == "__main__":
    main()
