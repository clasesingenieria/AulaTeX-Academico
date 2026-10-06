import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".tmp-itesca-20260928"))
from moodle_common import login, BASE
from playwright.sync_api import sync_playwright

path = ROOT / "ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/reporte-plan-de-negocios-Actividad-12-Recursos-Humanos-Portada-Oficial.pdf"
with sync_playwright() as runtime:
    browser, context, page = login(runtime)
    try:
        page.goto(BASE + "/mod/assign/view.php?id=6551")
        assert "Todavía no se han realizado envíos" in page.locator("#region-main").inner_text()
        page.get_by_role("button", name="Agregar entrega", exact=True).click()
        page.get_by_title("Agregar...", exact=True).click()
        page.get_by_text("Subir un archivo", exact=True).click()
        upload = page.locator(".moodle-dialogue-focused input[name=repo_upload_file]")
        upload.wait_for(state="visible")
        upload.set_input_files(str(path))
        with page.expect_response(lambda response: "repository_ajax.php" in response.url and "upload" in response.url) as pending:
            page.get_by_role("button", name="Subir este archivo", exact=True).click()
        response = pending.value
        request = response.request
        body = request.post_data_buffer or b""
        text = body.decode("utf-8", errors="replace")
        print(json.dumps({"http": response.status, "content_type": request.headers.get("content-type"), "body_bytes": len(body), "has_pdf_header": b"%PDF-" in body, "has_filename": path.name in text, "field_names": re.findall(r'name="([^"]+)"', text), "response_error": response.json().get("error")}, ensure_ascii=True))
    finally:
        browser.close()