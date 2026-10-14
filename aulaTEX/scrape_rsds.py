import os
import sys
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

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
    credentials = vault.get_credentials(pin, account['id'])
    return credentials['username'], credentials['password']

def main():
    USER, PASS = get_credentials()
    c_name = "Responsabilidad social y desarrollo sustentable"
    c_slug = "responsabilidad-social-y-desarrollo-sustentable"

    subject_dir = PROJECT_ROOT / "UANL" / "ingeniero-agronomo" / c_slug
    planeaciones_dir = subject_dir / f"planeaciones-{c_slug}"
    recursos_dir = subject_dir / f"recursos-{c_slug}"
    capturas_dir = planeaciones_dir / "capturas_nexus"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1366, 'height': 900})
        page = context.new_page()

        page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)

        frame = page.frame_locator('iframe')
        frame.locator('#tipo').select_option(label='Alumno')
        frame.locator('#cuenta').fill(USER)
        frame.locator('#pass').fill(PASS)
        frame.locator('button:has-text("Entrar")').click()
        page.wait_for_timeout(10000)

        nexus_menu = page.locator('a[onmouseover*="nexus"]')
        if nexus_menu.count():
            nexus_menu.first.dispatch_event('mouseover')
            page.wait_for_timeout(1000)

        btn = page.locator('input[name="btnNexus"], a:has-text("Nexus"), input[value*="Nexus"]')
        with page.expect_popup() as popup_info:
            btn.first.click(force=True)
        nexus_page = popup_info.value

        nexus_page.wait_for_load_state('domcontentloaded')
        nexus_page.wait_for_timeout(12000)

        print("Entrando a Responsabilidad social...")
        card = nexus_page.locator('mat-card.nx-mat-card-curso').filter(has_text=re.compile(rf'{re.escape(c_name)}', re.I)).locator('.text-ellipsis').first
        card.click()
        nexus_page.wait_for_timeout(5000)

        # Navegar directamente a la ruta Estructura en el hash de Angular
        print("Navegando directamente a Estructura...")
        nexus_page.goto("https://plataformanexus.uanl.mx/?#/App/UnidadesAprendizaje/UA/Estructura", wait_until='domcontentloaded')
        nexus_page.wait_for_timeout(6000)
        nexus_page.screenshot(path=str(capturas_dir / "01_estructura_arbol.png"), full_page=True)

        estructura_text = nexus_page.locator('body').inner_text()
        with open(planeaciones_dir / "arbol_estructura.txt", "w", encoding="utf-8") as f:
            f.write(estructura_text)

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

        course_meta = {
            "nombre": c_name,
            "slug": c_slug,
            "codigo_referencia": "REF#261013755032",
            "docente": "Cavazos Galindo Jaime Manuel",
            "periodo": "Del 03/AGOSTO/2026 al 18/DICIEMBRE/2026",
            "modalidad": "Competencias / Mixta",
            "programa": "Ingeniero Agrónomo",
            "institucion": "Universidad Autónoma de Nuevo León",
            "facultad": "Facultad de Agronomía",
            "fases": fases
        }

        with open(planeaciones_dir / "extraccion_nexus.json", "w", encoding="utf-8") as f:
            json.dump(course_meta, f, indent=2, ensure_ascii=False)

        print(f"Fases extraídas en Responsabilidad Social: {len(fases)}")
        for f_item in fases:
            print(f"  * {f_item['fase']} ({len(f_item['actividades'])} actividades)")

        # Navegar directamente a Recursos
        print("Navegando directamente a Recursos...")
        nexus_page.goto("https://plataformanexus.uanl.mx/?#/App/UnidadesAprendizaje/UA/Recursos", wait_until='domcontentloaded')
        nexus_page.wait_for_timeout(6000)
        nexus_page.screenshot(path=str(capturas_dir / "02_recursos_vista.png"), full_page=True)

        recursos_text = nexus_page.locator('body').inner_text()
        with open(planeaciones_dir / "recursos_listado.txt", "w", encoding="utf-8") as f:
            f.write(recursos_text)

        browser.close()
        print("Responsabilidad Social completada con éxito!")

if __name__ == '__main__':
    main()
