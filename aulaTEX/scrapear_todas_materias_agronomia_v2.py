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

COURSES = [
    {"name": "Álgebra lineal", "slug": "algebra-lineal"},
    {"name": "Biología celular", "slug": "biologia-celular"},
    {"name": "Cálculo integral", "slug": "calculo-integral"},
    {"name": "Ética y cultura de la legalidad", "slug": "etica-y-cultura-de-la-legalidad"},
    {"name": "Física", "slug": "fisica"},
    {"name": "Responsabilidad social y desarrollo sustentable", "slug": "responsabilidad-social-y-desarrollo-sustentable"}
]

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
        raise RuntimeError('No existe cuenta UANL / Nexus en el vault')
    credentials = vault.get_credentials(pin, account['id'])
    return credentials['username'], credentials['password']

def main():
    USER, PASS = get_credentials()
    base_uanl = PROJECT_ROOT / "UANL" / "ingeniero-agronomo"
    base_uanl.mkdir(parents=True, exist_ok=True)

    print(f"=== INICIANDO SCRAPER INTEGRAL NEXUS (Usuario: {USER}) ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1366, 'height': 900})
        page = context.new_page()

        print("Navegando a https://www.uanl.mx/enlinea/...")
        page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)

        frame = page.frame_locator('iframe')
        frame.locator('#tipo').select_option(label='Alumno')
        frame.locator('#cuenta').fill(USER)
        frame.locator('#pass').fill(PASS)
        frame.locator('button:has-text("Entrar")').click()
        print("Login enviado, esperando autenticacion...")
        page.wait_for_timeout(10000)

        nexus_menu = page.locator('a[onmouseover*="nexus"]')
        if nexus_menu.count():
            nexus_menu.first.dispatch_event('mouseover')
            page.wait_for_timeout(1000)

        btn = page.locator('input[name="btnNexus"], a:has-text("Nexus"), input[value*="Nexus"]')
        with page.expect_popup() as popup_info:
            btn.first.click(force=True)
        nexus_page = popup_info.value

        print("Esperando dashboard de Nexus...")
        nexus_page.wait_for_load_state('domcontentloaded')
        nexus_page.wait_for_timeout(12000)
        print(f"URL Dashboard: {nexus_page.url}")

        dashboard_url = "https://plataformanexus.uanl.mx/?#/App/UnidadesAprendizaje"

        for course in COURSES:
            c_name = course["name"]
            c_slug = course["slug"]
            print(f"\n========================================================")
            print(f">>> PROCESANDO: {c_name} ({c_slug})")
            print(f"========================================================")

            subject_dir = base_uanl / c_slug
            planeaciones_dir = subject_dir / f"planeaciones-{c_slug}"
            referencias_dir = subject_dir / f"referencias-{c_slug}"
            recursos_dir = subject_dir / f"recursos-{c_slug}"
            capturas_dir = planeaciones_dir / "capturas_nexus"

            planeaciones_dir.mkdir(parents=True, exist_ok=True)
            referencias_dir.mkdir(parents=True, exist_ok=True)
            recursos_dir.mkdir(parents=True, exist_ok=True)
            capturas_dir.mkdir(parents=True, exist_ok=True)

            # Volver al dashboard de Unidades de Aprendizaje
            print("Navegando a Unidades de Aprendizaje...")
            nexus_page.goto(dashboard_url, wait_until='domcontentloaded')
            nexus_page.wait_for_timeout(6000)

            # Localizar la tarjeta por nombre de curso
            card_title_locator = nexus_page.locator('mat-card.nx-mat-card-curso').filter(has_text=re.compile(rf'^{re.escape(c_name)}$', re.I | re.M)).locator('.text-ellipsis')
            if not card_title_locator.count():
                card_title_locator = nexus_page.locator(f'mat-card.nx-mat-card-curso:has-text("{c_name}") .text-ellipsis')

            if not card_title_locator.count():
                print(f"[ALERTA] No se encontró tarjeta para {c_name}")
                continue

            print(f"Haciendo click en tarjeta de {c_name}...")
            card_title_locator.first.click()
            nexus_page.wait_for_timeout(6000)
            print(f"URL tras click: {nexus_page.url}")

            # 1. Portada del curso
            portada_text = nexus_page.locator('body').inner_text()
            nexus_page.screenshot(path=str(capturas_dir / "00_portada_curso.png"), full_page=True)
            with open(planeaciones_dir / "portada_texto.txt", "w", encoding="utf-8") as f:
                f.write(portada_text)

            # Extraer metadatos
            ref_match = re.search(r'REF#(\d+)', portada_text)
            docente_match = re.search(r'(?:Docente|Profesor|Facilitador)?\s*([A-ZÁÉÍÓÚÑ\s]{4,40})\s*(?:Del \d|Competencias)', portada_text)
            periodo_match = re.search(r'Del\s+([^\n\r]+)', portada_text)

            ref_code = f"REF#{ref_match.group(1)}" if ref_match else "Por confirmar"
            docente = docente_match.group(1).strip() if docente_match else "Por confirmar"
            periodo = periodo_match.group(1).strip() if periodo_match else "Del 03/AGOSTO/2026 al 18/DICIEMBRE/2026"

            course_meta = {
                "nombre": c_name,
                "slug": c_slug,
                "codigo_referencia": ref_code,
                "docente": docente,
                "periodo": periodo,
                "modalidad": "Competencias / Mixta",
                "programa": "Ingeniero Agrónomo",
                "institucion": "Universidad Autónoma de Nuevo León",
                "facultad": "Facultad de Agronomía"
            }
            print(f"Metadatos: {course_meta}")

            # 2. Navegar a Estructura
            print("Entrando a Estructura...")
            est_btn = nexus_page.locator('.sidebar-nav a:has-text("Estructura"), a:has-text("Estructura")').first
            est_btn.click()
            nexus_page.wait_for_timeout(6000)
            nexus_page.screenshot(path=str(capturas_dir / "01_estructura_arbol.png"), full_page=True)

            estructura_text = nexus_page.locator('body').inner_text()
            with open(planeaciones_dir / "arbol_estructura.txt", "w", encoding="utf-8") as f:
                f.write(estructura_text)

            # Parsear actividades y fases de la estructura
            fases = []
            current_fase = {"fase": "General", "descripcion": "", "actividades": []}

            lines = estructura_text.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                if re.match(r'^(?:Fase|Etapa|Unidad|Módulo)\s+\d+[:\s]', line, re.I):
                    if current_fase["actividades"] or current_fase["fase"] != "General":
                        fases.append(current_fase)
                    desc = ""
                    if i + 1 < len(lines) and not re.match(r'^\d+\.\d+', lines[i+1]) and "pts" not in lines[i+1]:
                        desc = lines[i+1].strip()
                        i += 1
                    current_fase = {"fase": line, "descripcion": desc, "actividades": []}
                elif re.match(r'^Producto Integrador', line, re.I):
                    if current_fase["actividades"] or current_fase["fase"] != "General":
                        fases.append(current_fase)
                    current_fase = {"fase": "Producto Integrador de Aprendizaje (PIA)", "descripcion": "", "actividades": []}
                elif re.match(r'^\d+\.\d+', line) or (current_fase["fase"] != "General" and ("pts" in line or (i+1 < len(lines) and "pts" in lines[i+1]))):
                    act_name = line
                    pts = ""
                    if i + 1 < len(lines) and "pts" in lines[i+1].lower():
                        pts = lines[i+1].strip()
                        i += 1
                    elif "pts" in line.lower():
                        parts = line.split("pts")
                        act_name = parts[0].strip()
                        pts = "pts"
                    current_fase["actividades"].append({"actividad": act_name, "puntos": pts})
                i += 1

            if current_fase["actividades"] or current_fase["fase"] != "General":
                fases.append(current_fase)

            course_meta["fases"] = fases
            with open(planeaciones_dir / "extraccion_nexus.json", "w", encoding="utf-8") as f:
                json.dump(course_meta, f, indent=2, ensure_ascii=False)

            print(f"Fases extraídas: {len(fases)}")
            for f_item in fases:
                print(f"  * {f_item['fase']} ({len(f_item['actividades'])} actividades)")

            # 3. Navegar a Recursos
            print("Entrando a Recursos...")
            rec_btn = nexus_page.locator('.sidebar-nav a:has-text("Recursos"), a:has-text("Recursos")').first
            rec_btn.click()
            nexus_page.wait_for_timeout(6000)
            nexus_page.screenshot(path=str(capturas_dir / "02_recursos_vista.png"), full_page=True)

            recursos_text = nexus_page.locator('body').inner_text()
            with open(planeaciones_dir / "recursos_listado.txt", "w", encoding="utf-8") as f:
                f.write(recursos_text)

            # Descargar archivos en Recursos si existen botones de descarga
            dl_buttons = nexus_page.locator('i.fa-download, a[href*="download"], a[title*="Descargar"], button:has-text("Descargar")')
            print(f"Botones de descarga encontrados en Recursos: {dl_buttons.count()}")
            for dl_idx in range(dl_buttons.count()):
                dl_el = dl_buttons.nth(dl_idx)
                if dl_el.is_visible():
                    try:
                        with nexus_page.expect_download(timeout=5000) as dl_info:
                            dl_el.click(force=True)
                        dl_file = dl_info.value
                        fn = dl_file.suggested_filename or f"recurso_{c_slug}_{dl_idx}.bin"
                        dl_file.save_as(str(recursos_dir / fn))
                        print(f"    [OK] Recurso descargado: {fn}")
                    except Exception as e:
                        pass

        print("\n=== EXTRACCIÓN Y SCRAPING DE TODAS LAS MATERIAS FINALIZADO CON ÉXITO ===")
        browser.close()

if __name__ == '__main__':
    main()
