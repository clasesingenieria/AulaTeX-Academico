"""Script de inspección en vivo para Semana 6 en UnADM (cursos 3432, 3482, 3441).

Se autentica de forma segura con PlatformCredentialVault y navega a:
- Teoria del Estado y Constitucion (id=3432#section-7)
- Derecho penal especial mexicano (id=3482#section-7)
- Antecedentes de los derechos humanos (id=3441#section-7)

Extrae las secciones, consignas, fechas, módulos de tarea y estado de entrega.
Sanitiza identidades y secretos antes de persistir.
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
sys.path.insert(0, str(PROJECT_ROOT / "aulaTEX"))

from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.navegacion_plataforma import (
    assert_no_credential_leak,
    build_identity_variants,
    ensure_same_https_host,
    load_vault_account,
    normalize_readonly_link,
    resolve_doh_host_args,
    sanitize_platform_text,
)

HOST = "aulavirtual.unadmexico.mx"
BASE_URL = f"https://{HOST}"

COURSES = {
    3432: ("teoria-del-estado-y-constitucion", "Teoria del Estado y Constitucion"),
    3482: ("derecho-penal-especial-mexicano", "Derecho penal especial mexicano"),
    3441: ("antecedentes-de-los-derechos-humanos", "Antecedentes de los derechos humanos"),
}


def inspect_live_week6() -> dict[str, Any]:
    load_aulatex_env()
    credentials = load_vault_account(PROJECT_ROOT, "UnADM", HOST)
    username = credentials["username"]
    identities = build_identity_variants(username, ["Martin Jonathan de la Cruz Muñoz", "Martin Jonathan de la Cruz"])

    doh_args, _ = resolve_doh_host_args(HOST)
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
    ] + doh_args

    results: dict[str, Any] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=browser_args)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.set_default_timeout(45000)

        # 1. Login
        login_url = f"{BASE_URL}/login/index.php"
        page.goto(login_url, wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr|Usuario", re.I)).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi|Acceder", re.I)).click()
        page.wait_for_url(lambda u: "/login/" not in urlsplit(u).path, wait_until="domcontentloaded")

        del credentials  # Destruir credenciales de memoria

        # 2. Inspeccionar cada curso
        for cid, (slug, course_name) in COURSES.items():
            print(f"--- Inspeccionando curso {cid}: {course_name} ---", flush=True)
            c_url = f"{BASE_URL}/course/view.php?id={cid}"
            page.goto(c_url, wait_until="domcontentloaded")
            ensure_same_https_host(page.url, HOST, BASE_URL)

            # Extraer todas las secciones
            sections_raw = page.locator(".course-section, li.section").all()
            sections_list: list[dict[str, Any]] = []

            for s_idx, sec in enumerate(sections_raw):
                sec_id = sec.get_attribute("id") or f"section-{s_idx}"
                titles = sec.locator(".sectionname, .section-title, h3").all_inner_texts()
                sec_title = titles[0].strip() if titles else f"Sección {s_idx}"
                sec_text = sec.inner_text()
                
                sec_links = sec.locator("a[href]").evaluate_all(
                    "links => links.map(l => ({title: l.innerText.trim(), url: l.href}))"
                )
                clean_links = [
                    {"title": sanitize_platform_text(l["title"], identities), "url": l["url"]}
                    for l in sec_links if HOST in l.get("url", "")
                ]
                sections_list.append({
                    "id": sec_id,
                    "index": s_idx,
                    "title": sanitize_platform_text(sec_title, identities),
                    "text_preview": sanitize_platform_text(sec_text[:600], identities),
                    "full_text": sanitize_platform_text(sec_text, identities),
                    "links": clean_links,
                })

            # Localizar section-7 específicamente
            sec_7_node = page.locator("#section-7")
            sec_7_data: dict[str, Any] = {}
            if sec_7_node.count():
                s7_titles = sec_7_node.locator(".sectionname, .section-title, h3").all_inner_texts()
                s7_title = s7_titles[0].strip() if s7_titles else "section-7"
                s7_text = sec_7_node.inner_text()
                s7_links = sec_7_node.locator("a[href]").evaluate_all(
                    "links => links.map(l => ({title: l.innerText.trim(), url: l.href}))"
                )
                sec_7_data = {
                    "id": "section-7",
                    "title": sanitize_platform_text(s7_title, identities),
                    "text": sanitize_platform_text(s7_text, identities),
                    "links": [
                        {"title": sanitize_platform_text(l["title"], identities), "url": l["url"]}
                        for l in s7_links if HOST in l.get("url", "")
                    ],
                }

            # Localizar todos los assign y forum links en todo el curso
            all_assigns = page.locator('a[href*="/mod/assign/view.php"]').evaluate_all(
                "links => links.map(l => ({title: l.innerText.trim(), url: l.href}))"
            )
            all_forums = page.locator('a[href*="/mod/forum/view.php"]').evaluate_all(
                "links => links.map(l => ({title: l.innerText.trim(), url: l.href}))"
            )

            # Inspeccionar detalladamente cada tarea assign encontrada
            assign_details: list[dict[str, Any]] = []
            visited_ids: set[str] = set()
            for al in all_assigns:
                m_match = re.search(r"id=(\d+)", al.get("url", ""))
                if not m_match:
                    continue
                mid_str = m_match.group(1)
                if mid_str in visited_ids:
                    continue
                visited_ids.add(mid_str)

                assign_url = f"{BASE_URL}/mod/assign/view.php?id={mid_str}"
                page.goto(assign_url, wait_until="domcontentloaded")
                main_elem = page.locator("#region-main, [role='main']").first
                if main_elem.count():
                    main_t = main_elem.inner_text()
                    title_elem = main_elem.locator("h2, h3, .activity-title").all_inner_texts()
                    atitle = title_elem[0].strip() if title_elem else al.get("title", "")
                    dates_elem = main_elem.locator(".activity-dates, .activity-information").all_inner_texts()
                    adates = "\n".join(dates_elem).strip()
                    assign_details.append({
                        "module_id": int(mid_str),
                        "url": assign_url,
                        "title": sanitize_platform_text(atitle, identities),
                        "dates": sanitize_platform_text(adates, identities),
                        "full_main_text": sanitize_platform_text(main_t, identities),
                    })

            # Inspeccionar foros relevantes
            forum_details: list[dict[str, Any]] = []
            for fl in all_forums:
                m_match = re.search(r"id=(\d+)", fl.get("url", ""))
                if not m_match:
                    continue
                f_mid = m_match.group(1)
                forum_url = f"{BASE_URL}/mod/forum/view.php?id={f_mid}"
                page.goto(forum_url, wait_until="domcontentloaded")
                main_elem = page.locator("#region-main, [role='main']").first
                if main_elem.count():
                    forum_details.append({
                        "module_id": int(f_mid),
                        "url": forum_url,
                        "title": sanitize_platform_text(fl.get("title", ""), identities),
                        "intro_text": sanitize_platform_text(main_elem.inner_text()[:1000], identities),
                    })

            results[slug] = {
                "course_id": cid,
                "course_name": course_name,
                "section_7": sec_7_data,
                "sections": sections_list,
                "assign_modules": assign_details,
                "forum_modules": forum_details,
            }

        browser.close()

    assert_no_credential_leak(results)
    out_file = PROJECT_ROOT / "UnADM" / "estado_unadm_semana6.json"
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Inspección guardada en: {out_file}", flush=True)
    return results


if __name__ == "__main__":
    inspect_live_week6()
