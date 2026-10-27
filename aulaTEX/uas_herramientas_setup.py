"""Collect the accessible UAS digital-tools course without submitting work."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.uas_course_inspect import BASE_URL, HOST, _credentials


ROOT = Path(__file__).resolve().parents[1]
SUBJECT = ROOT / "UAS/licenciatura-en-contaduria-uas/herramientas-digitales"
REFERENCES = SUBJECT / "referencias-herramientas-digitales"
NOTES = REFERENCES / "notas-herramientas-digitales"
COURSE_URL = f"{BASE_URL}/course/view.php?id=635"


def collect() -> dict:
    load_aulatex_env()
    credentials = _credentials(ROOT)
    records = []
    sources = {}
    pending = [COURSE_URL]
    seen = set()
    output = NOTES / "consulta-aula-2026-10-21"
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == HOST else route.abort())
        page = context.new_page()
        page.goto(f"{BASE_URL}/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        del credentials
        if "/login/" in page.url:
            raise RuntimeError("Authentication failed")
        while pending and len(seen) < 150:
            url = pending.pop(0)
            if url in seen:
                continue
            seen.add(url)
            navigation = page.goto(url, wait_until="networkidle")
            response = {
                "status": navigation.status if navigation else 0,
                "type": navigation.headers.get("content-type", "") if navigation else "",
                "text": page.content(),
            }
            if not response["text"]:
                records.append({"url": url, "http": response["status"], "content_type": response["type"]})
                continue
            soup = BeautifulSoup(response["text"], "html.parser")
            if soup.select_one("input[type=password]"):
                raise RuntimeError("Session expired")
            main = soup.select_one("#region-main")
            if main is None:
                continue
            for element in main.select("script,style,input,textarea"):
                element.decompose()
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            text = main.get_text("\n", strip=True)
            text = re.sub(r"(?i)(sesskey|token|password|logintoken)\s*[=:]\s*[^\s&]+", "[dato omitido]", text)
            identity = hashlib.sha256(url.encode()).hexdigest()[:12]
            path = output / f"pagina-{identity}.txt"
            path.write_text(text, encoding="utf-8")
            links = []
            for element in soup.select("#region-main a[href],#courseindex a[href],#region-main iframe[src],#region-main video[src],#region-main source[src]"):
                destination = urljoin(url, element.get("href") or element.get("src") or "")
                parsed = urlsplit(destination)
                query = parse_qs(parsed.query)
                if parsed.scheme not in ("https", "http") or any(key.lower() in ("sesskey", "token", "password") for key in query):
                    continue
                label = element.get_text(" ", strip=True) or element.get("title", "") or unquote(Path(parsed.path).name)
                safe = None
                if parsed.hostname == HOST:
                    if parsed.path == "/fca/course/view.php" and query.get("id") == ["635"]:
                        safe = COURSE_URL
                        if query.get("section", [""])[0].isdigit():
                            safe += "&section=" + query["section"][0]
                    elif re.fullmatch(r"/fca/mod/(page|url|assign|forum|quiz|lesson|feedback|folder)/view.php", parsed.path) and query.get("id", [""])[0].isdigit():
                        safe = f"https://{HOST}{parsed.path}?id={query['id'][0]}"
                    elif parsed.path == "/fca/mod/resource/view.php" and query.get("id", [""])[0].isdigit():
                        sources.setdefault(destination, {"url": destination, "title": label, "kind": "resource", "origins": []})["origins"].append(url)
                    elif "/pluginfile.php/" in parsed.path:
                        sources.setdefault(destination, {"url": destination, "title": label, "kind": "attachment", "origins": []})["origins"].append(url)
                elif not any(part in parsed.path for part in ("/user/", "/login")):
                    sources.setdefault(destination, {"url": destination, "title": label, "kind": "external", "origins": []})["origins"].append(url)
                if safe:
                    links.append({"title": label, "url": safe})
                    if safe not in seen and safe not in pending:
                        pending.append(safe)
            records.append({"url": url, "title": title, "http": response["status"], "text_path": path.relative_to(SUBJECT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "links": links})
        for source in sources.values():
            source["origins"] = sorted(set(source["origins"]))
            if source["kind"] != "attachment":
                source["status"] = "Enlace del aula; contenido externo pendiente de cotejo"
                continue
            extension = Path(unquote(urlsplit(source["url"]).path)).suffix.lower()
            if extension not in (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".ppsx", ".xlsx", ".xls", ".zip", ".png", ".jpg", ".jpeg"):
                source["status"] = "Tipo no descargado"
                continue
            try:
                download = page.evaluate("""async url => {
                    const response = await fetch(url, {redirect:'manual'});
                    if (response.status !== 200) return {status:response.status};
                    const blob = await response.blob();
                    if (blob.size > 30000000) return {status:200,tooLarge:true};
                    const data = await new Promise(resolve => {
                        const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsDataURL(blob);
                    });
                    return {status:200,type:blob.type,data:data.split(',')[1]};
                }""", source["url"])
                if not download.get("data"):
                    source.update(status="No descargado", http=download["status"])
                    continue
                data = base64.b64decode(download["data"])
                if download.get("type", "").startswith("text/html"):
                    source["status"] = "Respuesta HTML; no se guardo como archivo"
                    continue
                filename = re.sub(r"[^\w. -]", "_", unquote(Path(urlsplit(source["url"]).path).name))
                digest = hashlib.sha256(data).hexdigest()
                target = REFERENCES / "materiales-aula" / f"{digest[:10]}-{filename}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                source.update(status="Descargado", path=target.relative_to(SUBJECT).as_posix(), bytes=len(data), sha256=digest, content_type=download.get("type", ""))
            except Exception as error:
                source.update(status="Descarga no completada", error_type=type(error).__name__)
        browser.close()
    result = {"consulted_utc": datetime.now(timezone.utc).isoformat(), "course_id": 635, "course_url": COURSE_URL, "read_only": True, "limit_reached": bool(pending), "pages": records, "sources": list(sources.values()), "submission_performed": False}
    (REFERENCES / "consulta-aula-2026-10-21.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def complete_inventory() -> dict:
    catalog_path = REFERENCES / "consulta-aula-2026-10-21.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    load_aulatex_env()
    credentials = _credentials(ROOT)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == HOST else route.abort())
        page = context.new_page()
        page.goto(f"{BASE_URL}/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        del credentials
        if "/login/" in page.url:
            raise RuntimeError("Authentication failed")
        for record in catalog["pages"]:
            if not re.search(r"/mod/(assign|quiz|feedback)/view.php", record["url"]):
                continue
            page.goto(record["url"], wait_until="networkidle")
            if "/login/" in page.url:
                raise RuntimeError("Session expired")
            record["dates"] = page.locator(".activity-dates").all_inner_texts()
            record["description"] = page.locator(".activity-description,.description").all_inner_texts()
            record["controls"] = page.locator("#region-main button,#region-main input[type=submit],#region-main a.btn").evaluate_all("elements => elements.map(element => ({text:element.innerText || element.value,disabled:element.disabled || false}))")
            path = SUBJECT / record["text_path"]
            original = path.read_text(encoding="utf-8")
            text = "\n\n".join(record["dates"] + record["description"] + [original])
            path.write_text(text, encoding="utf-8")
            record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        for source in catalog["sources"]:
            if source["kind"] != "resource":
                continue
            try:
                response = page.evaluate("""async url => {
                    for (let hop=0;hop<5;hop++) {
                        const response=await fetch(url,{redirect:'follow'});
                        if (new URL(response.url).origin!==locationOrigin) return {status:0};
                        if (response.status>=300 && response.status<400) {
                            const location=response.headers.get('location');
                            if (!location) return {status:response.status};
                            const next=new URL(location,url);
                            if (next.origin!==locationOrigin) return {status:response.status};
                            url=next.href;continue;
                        }
                        if (response.status!==200) return {status:response.status};
                        const blob=await response.blob();
                        if (blob.size>30000000) return {status:200,tooLarge:true};
                        const data=await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.readAsDataURL(blob)});
                        return {status:200,type:blob.type,url:response.url,data:data.split(',')[1]};
                    }
                    return {status:0};
                }""".replace("locationOrigin", json.dumps(BASE_URL.split("/fca")[0])), source["url"])
                if not response.get("data") or response.get("type", "").startswith("text/html"):
                    source.update(status="No descargado; requiere revision", http=response["status"])
                    continue
                data = base64.b64decode(response["data"])
                digest = hashlib.sha256(data).hexdigest()
                filename = unquote(Path(urlsplit(response["url"]).path).name)
                filename = re.sub(r"[^\w. -]", "_", filename)
                if not Path(filename).suffix:
                    filename += ".pdf" if data.startswith(b"%PDF") else ".bin"
                path = REFERENCES / "materiales-aula" / f"{digest[:10]}-{filename}"
                path.write_bytes(data)
                source.update(status="Descargado", path=path.relative_to(SUBJECT).as_posix(), bytes=len(data), sha256=digest, content_type=response.get("type", ""))
            except Exception as error:
                source.update(status="Descarga no completada", error_type=type(error).__name__)
        browser.close()
    general_hosts = {"www.uas.edu.mx", "fca.uas.edu.mx", "download.moodle.org", "play.google.com", "apps.apple.com", "moodle.com", "conecti.me"}
    for source in catalog["sources"]:
        if source["kind"] == "external" and (urlsplit(source["url"]).hostname in general_hosts or "/error/" in source["url"] or "/mod/chat/" in source["url"]):
            source["kind"] = "site-navigation"
    catalog["completed_utc"] = datetime.now(timezone.utc).isoformat()
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def organize() -> dict:
    catalog = json.loads((REFERENCES / "consulta-aula-2026-10-21.json").read_text(encoding="utf-8"))
    planning = SUBJECT / "planeaciones-herramientas-digitales"
    planning.mkdir(exist_ok=True)
    activities = []
    for record in catalog["pages"]:
        if not re.search(r"/mod/(assign|quiz|lesson|feedback)/view.php", record["url"]):
            continue
        module = parse_qs(urlsplit(record["url"]).query)["id"][0]
        title = record.get("title", "").replace("2026_I_HERR_DIG_LCP: ", "").replace(" | Virtual", "")
        text_path = SUBJECT / record["text_path"]
        text = text_path.read_text(encoding="utf-8")
        dates = "\n\n".join(record.get("dates", [])) or "Fecha no acreditada en esta consulta."
        description = "\n\n".join(record.get("description", []))
        content = f"# {title}\n\nModulo: {module}. [Plataforma]({record['url']}).\n\n## Calendario\n\n{dates}\n\n## Consigna y evidencia\n\n"
        content += description or "Consultar la captura enlazada. Si no contiene la consigna completa, reconsultar al abrir la actividad; no sustituirla por una propuesta propia."
        content += f"\n\n[Captura consultada](../{record['text_path']}). SHA-256: `{record['sha256']}`.\n\n## Secuencia de trabajo\n\n1. Cotejar consigna, rubrica y recursos de la sesion.\n2. Realizar personalmente la practica o evaluacion requerida.\n3. Revisar el producto y su evidencia real; no simular capturas ni reuniones.\n4. Confirmar formato, nomenclatura y plazo antes del envio manual.\n\n## Control\n\n- [x] Modulo identificado en la consulta.\n- [ ] Consigna completa y criterios cotejados para ejecutar.\n- [ ] Producto realizado y revisado.\n- [ ] Envio confirmado.\n"
        filename = f"modulo-{module}.md"
        (planning / filename).write_text(content, encoding="utf-8")
        activities.append({"id":module,"title":title,"url":record["url"],"planning":filename,"dates":record.get("dates",[]),"submitted_by_setup":False})
    (planning / "modelo-planeacion-2026-10-21.json").write_text(json.dumps({"course_id":635,"activities":activities},ensure_ascii=False,indent=2),encoding="utf-8")
    index = "# Planeaciones de Herramientas digitales\n\nConsulta del 21/10/2026. Fechas en la hora mostrada por Moodle; zona horaria no acreditada. Las fichas distinguen consignas de propuestas de trabajo.\n\n"
    index += "\n".join(f"- [{item['title']}]({item['planning']})" for item in activities)
    index += "\n\nLas tareas futuras pueden mostrar fechas sin su descripcion. Reconsultar al abrir cada sesion. No se iniciaron examenes ni se enviaron respuestas; las lecciones pueden registrar automaticamente una visita al abrir su primera pantalla.\n"
    (planning / "README.md").write_text(index,encoding="utf-8")
    for folder, purpose in {
        "actividades":"Guias y productos de trabajo; no equivalen a entregas.",
        "entregas-herramientas-digitales":"Solo archivos finales revisados y acuses reales. Actualmente no hay entregas preparadas.",
        "extractor-aulatex":"Extracciones y fichas tecnicas de materiales; no son fuentes independientes.",
        "investigacion-aulatex":"Cotejo conceptual y bibliografico antes de usar fuentes en entregables.",
        "assets-herramientas-digitales":"Capturas autenticas e imagenes de trabajo; no simular evidencia.",
        "plantillas":"Adaptadores de la plantilla UAS compartida; compilacion con XeLaTeX y Biber desde la raiz de la materia.",
    }.items():
        path = SUBJECT / folder
        path.mkdir(exist_ok=True)
        (path / "README.md").write_text(f"# {folder}\n\n{purpose}\n",encoding="utf-8")
    source_index = "# Referencias y materiales\n\nEl catalogo conserva URL, origen, estado, tamanio y SHA-256. Descarga no equivale a lectura o verificacion bibliografica.\n\n"
    for source in catalog["sources"]:
        if source["kind"] == "site-navigation":
            continue
        title = source["title"].replace("[", "").replace("]", "") or source["url"]
        if source.get("path"):
            target = source["path"].removeprefix("referencias-herramientas-digitales/").replace(" ","%20")
            source_index += f"- [{title}]({target}): {source['status']}; SHA-256 `{source['sha256']}`.\n"
        else:
            source_index += f"- [{title}]({source['url']}): {source.get('status','Pendiente')}.\n"
    source_index += "\n## Cotejo externo inicial\n\n- Oracle, Michael Chen, 23/09/2024: Que es el big data. Titulo, autor y contenido cotejados; divulgacion corporativa, no investigacion arbitrada.\n- IBM: Que es blockchain. Titulo y contenido cotejados; divulgacion corporativa. Fecha no acreditada.\n- AWS, computacion cuantica: la herramienta no pudo extraer contenido; enlace conservado, cotejo pendiente.\n- Videos: enlaces registrados, sin afirmar reproduccion ni transcripcion.\n\n## Biblioteca local\n\nSe localizaron candidatos en `C:/Users/Sysx/Documents/Libros/Sistemas computacionales/Alberto Prieto Espinosa/`: Introduccion a la informatica y Conceptos de informatica. No se copiaron originales ni se verificaron edicion o paginas. El aula ya proporciona dos manuales de Excel y ejercicios; consultar la biblioteca para lagunas conceptuales concretas.\n"
    (REFERENCES / "README.md").write_text(source_index,encoding="utf-8")
    (NOTES / "README.md").write_text("# Notas de Herramientas digitales\n\n[Consulta y procedencia](../consulta-aula-2026-10-21.json). Las capturas textuales se conservan en consulta-aula-2026-10-21. No guardar credenciales ni cookies aqui.\n\n## Prioridad S1\n\nCrear una carpeta real de Drive y compartirla con el facilitador. Confirmar grupo, nombre y correo del facilitador antes de compartir. Registrar capturas propias del proceso y preparar S1_NombreApellido.pdf, maximo 2 MB; si se excede, la consigna permite enlace publico. Evitar exponer datos ajenos. Cierre: 25/10/2026 23:59, hora de Moodle. No hay capturas ni envio acreditados.\n",encoding="utf-8")
    bibliography = """@online{uasHerramientas635,
  author = {{Universidad Autonoma de Sinaloa}},
  title = {2026 I Herramientas digitales LCP},
  url = {https://virtual.uas.edu.mx/fca/course/view.php?id=635},
  urldate = {2026-10-21},
  note = {Fuente de consignas; acceso autenticado}
}
@online{chenBigData2024,
  author = {Chen, Michael},
  title = {Que es el big data},
  organization = {Oracle},
  date = {2024-09-23},
  url = {https://www.oracle.com/mx/big-data/what-is-big-data/},
  urldate = {2026-10-21}
}
@online{ibmBlockchain,
  author = {{IBM}},
  title = {Que es blockchain},
  url = {https://www.ibm.com/mx-es/topics/blockchain},
  urldate = {2026-10-21}
}
"""
    (SUBJECT / "herramientas-digitales.bib").write_text(bibliography,encoding="utf-8")
    (SUBJECT / "reporte-herramientas-digitales-plantilla-actividad.tex").write_text(r"""\providecommand{\uasmateria}{Herramientas digitales}
\providecommand{\uasbibliografia}{herramientas-digitales.bib}
\providecommand{\uaslogo}{../derecho-mercantil/assets-derecho-mercantil/escudo-uas.png}
\providecommand{\uasfacultadlogo}{../fcauas-logo.jpg}
\input{../../plantilla-actividad-uas.tex}
""",encoding="utf-8")
    for kind, title in [("reporte","Reporte de Herramientas digitales"),("actividad","Evidencia de practica")]:
        (SUBJECT / f"{kind}-herramientas-digitales.tex").write_text("\\newcommand{\\actividadtitulo}{"+title+"}\n\\input{reporte-herramientas-digitales-plantilla-actividad.tex}\n",encoding="utf-8")
    return {"course_id":635,"planning_count":len(activities),"downloaded":sum(source.get("status")=="Descargado" for source in catalog["sources"])}


if __name__ == "__main__":
    try:
        if "--organize" in sys.argv:
            print(json.dumps(organize(), ensure_ascii=True))
            raise SystemExit(0)
        result = complete_inventory() if "--complete" in sys.argv else collect()
        print(json.dumps({"pages": len(result["pages"]), "limit_reached": result["limit_reached"], "downloaded": sum(source.get("status") == "Descargado" for source in result["sources"]), "pending_resources": [source["title"] for source in result["sources"] if source["kind"] == "resource" and source.get("status") != "Descargado"], "activities": [{"url": record["url"], "title": record.get("title", ""), "dates": record.get("dates", []), "description": record.get("description", [])} for record in result["pages"] if "/assign/" in record["url"]]}, ensure_ascii=True))
    except Exception as error:
        print(json.dumps({"status": "Collection incomplete", "error_type": type(error).__name__}))
        raise SystemExit(1) from None