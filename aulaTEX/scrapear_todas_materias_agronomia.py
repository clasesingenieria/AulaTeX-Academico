import os
import sys
import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

COURSE_MAP = {
    "Álgebra lineal": "algebra-lineal",
    "Biología celular": "biologia-celular",
    "Cálculo integral": "calculo-integral",
    "Ética y cultura de la legalidad": "etica-y-cultura-de-la-legalidad",
    "Física": "fisica",
    "Responsabilidad social y desarrollo sustentable": "responsabilidad-social-y-desarrollo-sustentable"
}

def get_credentials():
    pin = os.getenv('AULATEX_MASTER_PIN', '5632').strip()
    vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
    accounts = vault.list_accounts(pin)
    account = next(
        (item for item in accounts
         if item['institution'].casefold() == 'uanl'
         and item['platform'].casefold() == 'nexus / siase'),
        None,
    )
    if account is None:
        raise RuntimeError('No existe una cuenta UANL / Nexus-SIASE en la GUI')
    credentials = vault.get_credentials(pin, account['id'])
    return credentials['username'], credentials['password']

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', '_', name)
    return clean.strip()

def scrape_all():
    USER, PASS = get_credentials()
    base_dir = PROJECT_ROOT / "UANL" / "ingeniero-agronomo"
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== INICIANDO SCRAPING EXHAUSTIVO NEXUS UANL (Usuario: {USER}) ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1366, 'height': 900})
        page = context.new_page()

        print("1. Navegando a portal de acceso SIASE...")
        page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)

        frame = page.frame_locator('iframe')
        frame.locator('#tipo').select_option(label='Alumno')
        frame.locator('#cuenta').fill(USER)
        frame.locator('#pass').fill(PASS)
        frame.locator('button:has-text("Entrar")').click()
        print("Credenciales enviadas, esperando autenticacion...")
        page.wait_for_timeout(10000)

        nexus_menu = page.locator('a[onmouseover*="nexus"]')
        if nexus_menu.count():
            nexus_menu.first.dispatch_event('mouseover')
            page.wait_for_timeout(1000)

        btn = page.locator('input[name="btnNexus"], a:has-text("Nexus"), input[value*="Nexus"]')
        if not btn.count():
            raise RuntimeError('No se encontró el botón de enlace a Nexus en SIASE')

        with page.expect_popup() as popup_info:
            btn.first.click(force=True)
        nexus_page = popup_info.value

        print("2. Esperando carga del dashboard de Nexus...")
        nexus_page.wait_for_load_state('domcontentloaded')
        nexus_page.wait_for_timeout(12000)
        print(f"Nexus Dashboard URL: {nexus_page.url}")

        dashboard_url = nexus_page.url

        # Iterar sobre las 6 materias
        for course_title, course_slug in COURSE_MAP.items():
            print(f"\n========================================================")
            print(f"PROCESANDO MATERIA: {course_title} [{course_slug}]")
            print(f"========================================================")

            subject_dir = base_dir / course_slug
            planeaciones_dir = subject_dir / f"planeaciones-{course_slug}"
            recursos_dir = subject_dir / f"recursos-{course_slug}"
            capturas_dir = planeaciones_dir / "capturas_nexus"

            planeaciones_dir.mkdir(parents=True, exist_ok=True)
            recursos_dir.mkdir(parents=True, exist_ok=True)
            capturas_dir.mkdir(parents=True, exist_ok=True)

            # Volver al dashboard de Nexus si no estamos allí
            if "mis-cursos" not in nexus_page.url:
                print("Regresando al dashboard de Nexus...")
                nexus_page.goto(dashboard_url, wait_until='domcontentloaded')
                nexus_page.wait_for_timeout(6000)

            # Buscar la tarjeta de la materia
            card_locator = nexus_page.locator(f'div:has-text("{course_title}"), a:has-text("{course_title}"), span:has-text("{course_title}")')
            target_el = None
            for idx in range(card_locator.count()):
                el = card_locator.nth(idx)
                if el.is_visible() and course_title in el.inner_text():
                    target_el = el
                    break

            if not target_el:
                print(f"[ALERTA] No se encontró tarjeta visible para {course_title}")
                continue

            print(f"Entrando a {course_title}...")
            target_el.click()
            nexus_page.wait_for_timeout(8000)
            print(f"URL de la materia: {nexus_page.url}")
            nexus_page.screenshot(path=str(capturas_dir / "00_portada_materia.png"))

            # Extraer metadatos de la materia en pantalla
            body_text = nexus_page.locator('body').inner_text()
            with open(planeaciones_dir / "info_materia_cruda.txt", "w", encoding="utf-8") as f:
                f.write(body_text)

            # Extraer profesor y grupo si aparecen en pantalla
            profesor_match = re.search(r'(?:Docente|Profesor|Facilitador)[:\s]+([^\n\r]+)', body_text, re.IGNORECASE)
            grupo_match = re.search(r'(?:Grupo|Gpo)[:\s]+([^\n\r]+)', body_text, re.IGNORECASE)
            profesor = profesor_match.group(1).strip() if profesor_match else "Por confirmar"
            grupo = grupo_match.group(1).strip() if grupo_match else "Por confirmar"

            print(f"Profesor detectado: {profesor} | Grupo: {grupo}")

            # Clic en "Estructura" en el menú de la materia
            print("Navegando a 'Estructura'...")
            est_menu = nexus_page.locator('.sidebar-nav a:has-text("Estructura"), a:has-text("Estructura"), button:has-text("Estructura")')
            for i in range(est_menu.count()):
                if est_menu.nth(i).is_visible():
                    est_menu.nth(i).click()
                    nexus_page.wait_for_timeout(6000)
                    break

            nexus_page.screenshot(path=str(capturas_dir / "01_estructura_arbol.png"))

            # Extraer texto del árbol de estructura
            estructura_text = nexus_page.locator('body').inner_text()
            with open(planeaciones_dir / "arbol_estructura.txt", "w", encoding="utf-8") as f:
                f.write(estructura_text)

            # Buscar todas las actividades en la estructura
            # En Nexus las actividades suelen tener clases o etiquetas como "Evidencia", "Actividad", "PIA", "Producto Integrador", "Examen", "Foro"
            print("Extrayendo lista de actividades y elementos evaluables...")

            # Buscar elementos clickeables que correspondan a actividades
            activity_items = nexus_page.locator('a, div.cursor-pointer, div[role="button"], tr, li').filter(has_text=re.compile(r'(?:Evidencia|Actividad|PIA|Producto Integrador|Examen|Diagnóstica|Foro|Etapa|Fase)', re.IGNORECASE))

            print(f"Elementos candidatos de actividades: {activity_items.count()}")

            activities_found = []
            seen_titles = set()

            # Extraer textos y nombres de actividades del arbol
            lines = estructura_text.split('\n')
            current_unit = "General"
            for line in lines:
                l = line.strip()
                if not l: continue
                if any(k in l.lower() for k in ["etapa", "fase", "unidad", "módulo"]):
                    current_unit = l
                elif any(k in l.lower() for k in ["evidencia", "actividad", "pia", "producto integrador", "laboratorio", "tarea"]):
                    if l not in seen_titles and len(l) > 3 and len(l) < 150:
                        seen_titles.add(l)
                        activities_found.append({
                            "titulo": l,
                            "unidad": current_unit,
                            "tipo": "Actividad"
                        })

            print(f"Actividades identificadas en {course_title}: {len(activities_found)}")
            for act in activities_found:
                print(f"  - [{act['unidad']}] {act['titulo']}")

            # Guardar inventario preliminar
            with open(planeaciones_dir / "actividades_detectadas.json", "w", encoding="utf-8") as f:
                json.dump(activities_found, f, indent=2, ensure_ascii=False)

            # Revisar si hay sección de "Recursos" o "Documentos" en el menú lateral
            print("Buscando sección de Recursos generales...")
            recursos_menu = nexus_page.locator('.sidebar-nav a:has-text("Recursos"), a:has-text("Recursos"), a:has-text("Documentos")')
            if recursos_menu.count():
                for r_i in range(recursos_menu.count()):
                    r_el = recursos_menu.nth(r_i)
                    if r_el.is_visible():
                        r_el.click()
                        nexus_page.wait_for_timeout(5000)
                        nexus_page.screenshot(path=str(capturas_dir / "02_recursos_generales.png"))
                        # Descargar archivos disponibles
                        dl_buttons = nexus_page.locator('i.fa-download, a[href*="download"], a[title*="Descargar"], button:has-text("Descargar")')
                        print(f"Archivos descargables en Recursos: {dl_buttons.count()}")
                        for dl_i in range(dl_buttons.count()):
                            dl_item = dl_buttons.nth(dl_i)
                            if dl_item.is_visible():
                                try:
                                    with nexus_page.expect_download(timeout=5000) as d_info:
                                        dl_item.click(force=True)
                                    d_file = d_info.value
                                    fn = d_file.suggested_filename or f"recurso_materia_{dl_i}.bin"
                                    d_file.save_as(str(recursos_dir / fn))
                                    print(f"  [+] Descargado: {fn}")
                                except Exception as exc:
                                    pass
                        break

            # También revisar Tareas/Actividades directamente
            print("Revisando vista de Tareas / Calendario si existe...")
            tareas_menu = nexus_page.locator('.sidebar-nav a:has-text("Tareas"), a:has-text("Actividades")')
            if tareas_menu.count():
                for t_i in range(tareas_menu.count()):
                    t_el = tareas_menu.nth(t_i)
                    if t_el.is_visible():
                        t_el.click()
                        nexus_page.wait_for_timeout(5000)
                        nexus_page.screenshot(path=str(capturas_dir / "03_tareas_listado.png"))
                        with open(planeaciones_dir / "tareas_listado.txt", "w", encoding="utf-8") as f:
                            f.write(nexus_page.locator('body').inner_text())
                        break

        print("\n=== SCRAPING DE MATERIAS COMPLETADO CON ÉXITO ===")
        browser.close()

if __name__ == '__main__':
    scrape_all()
