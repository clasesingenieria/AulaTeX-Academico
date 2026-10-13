"""Download sanitized activity planning from a UAS Moodle course.

Credentials are read only from the local AulaTeX vault and are never logged.
The browser is restricted to virtual.uas.edu.mx and output contains no session
cookies, login forms, or personal identity fields.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
import unicodedata

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path


HOST = "virtual.uas.edu.mx"
BASE_URL = f"https://{HOST}/fca"


def _fold(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)).casefold()


def _sanitize(text: str, identities: tuple[str, ...]) -> str:
    result = str(text)
    for identity in sorted({item.strip() for item in identities if item and item.strip()}, key=len, reverse=True):
        folded = _fold(result)
        target = _fold(identity)
        for match in reversed(list(re.finditer(re.escape(target), folded))):
            result = result[:match.start()] + "[estudiante]" + result[match.end():]
    return re.sub(r"(?i)(?:sesskey|token|password|logintoken|username)\s*[=:]\s*[^\s&]+", "[dato omitido]", result)


def _credentials(repo_root: Path) -> dict[str, str]:
    pin = os.getenv("AULATEX_MASTER_PIN", "")
    if not pin:
        raise RuntimeError("AULATEX_MASTER_PIN no está definido")
    vault = PlatformCredentialVault(default_vault_path(repo_root))
    accounts = [account for account in vault.list_accounts(pin) if account["institution"].casefold() == "uas"]
    accounts = [account for account in accounts if urlsplit(account["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("La bóveda no contiene una única cuenta UAS para este sitio")
    return vault.get_credentials(pin, accounts[0]["id"])


def inspect_course(repo_root: str | Path, course_id: int, output_dir: str | Path) -> dict:
    from playwright.sync_api import sync_playwright

    root = Path(repo_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    credentials = _credentials(root)
    result: dict[str, object] = {"host": HOST, "course_id": course_id, "activities": []}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        context.set_default_timeout(30000)

        def same_origin(route):
            parsed = urlsplit(route.request.url)
            if parsed.scheme != "https" or parsed.hostname != HOST:
                route.abort()
                return
            route.continue_()

        context.route("**/*", same_origin)
        page = context.new_page()
        page.goto(f"{BASE_URL}/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        del credentials
        if "/login/" in urlsplit(page.url).path:
            raise RuntimeError("La autenticación UAS falló")

        course_url = f"{BASE_URL}/course/view.php?id={course_id}"
        page.goto(course_url, wait_until="domcontentloaded")
        if urlsplit(page.url).hostname != HOST or "/login/" in urlsplit(page.url).path:
            raise RuntimeError("No se pudo abrir el curso UAS")
        links = page.locator("a[href]").evaluate_all("els => els.map(e => ({text:e.innerText, url:e.href}))")
        known_model = root / "UAS/licenciatura-en-contaduria-uas/derecho-mercantil/planeaciones-derecho-mercantil/modelo-planeacion-2026-09-22.json"
        if known_model.exists():
            model = json.loads(known_model.read_text(encoding="utf-8"))
            for activity in model.get("activities", []):
                for source in activity.get("sources", []):
                    links.append({"text": source.get("title", ""), "url": source.get("url", "")})
                for resource in activity.get("weekly_resources", []):
                    links.append({"text": resource.get("title", ""), "url": resource.get("url", "")})
        seen: set[str] = set()
        for link in links:
            url = urljoin(BASE_URL, link["url"])
            parsed = urlsplit(url)
            if parsed.hostname != HOST or not re.search(r"/mod/(assign|forum|lesson|quiz|feedback|page|resource)/", parsed.path):
                continue
            if url in seen:
                continue
            seen.add(url)
            page.goto(url, wait_until="domcontentloaded")
            main = page.locator("#region-main")
            if not main.count():
                continue
            text = main.inner_text()
            heading = main.locator("h1, h2, .page-header-headings").first
            title = heading.inner_text().strip() if heading.count() else link["text"].strip()
            parsed_id = re.search(r"[?&]id=(\d+)", url)
            safe_id = parsed_id.group(1) if parsed_id else hashlib.sha256(url.encode()).hexdigest()[:12]
            destination = output / f"modulo-{safe_id}.txt"
            destination.write_text(text, encoding="utf-8")
            result["activities"].append({
                "id": safe_id,
                "title": _sanitize(title, ()),
                "url": url.split("?", 1)[0] + ("?id=" + safe_id if safe_id.isdigit() else ""),
                "text_path": str(destination),
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            })
        browser.close()

    (output / "inspection.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def inspect_recordings(repo_root: str | Path) -> list[dict]:
    from datetime import datetime, timezone
    from urllib.parse import parse_qs
    from bs4 import BeautifulSoup
    from playwright.sync_api import sync_playwright
    from aulaTEX.aulatex.config import load_aulatex_env

    root = Path(repo_root).resolve()
    load_aulatex_env()
    credentials = _credentials(root)
    results = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        page.goto(f"{BASE_URL}/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        del credentials
        if "/login/" in urlsplit(page.url).path:
            raise RuntimeError("Acceso UAS pendiente; completar login en navegador")
        for course_id, slug in [(632, "derecho-mercantil"), (634, "investigacion-aplicada-a-la-contaduria")]:
            course_url = f"{BASE_URL}/course/view.php?id={course_id}"
            pending = [course_url]
            seen = set()
            found = {}
            record = {"consulta_utc": datetime.now(timezone.utc).isoformat(), "curso": course_id, "materia": slug, "origen": course_url, "solo_lectura": True, "paginas": [], "candidatos": [], "reuniones_excluidas": 0}
            while pending and len(seen) < 120:
                url = pending.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                response = page.evaluate('async url=>{const response=await fetch(url,{redirect:"manual"});const type=response.headers.get("content-type")||"";return {status:response.status,type,text:response.status===200&&type.includes("text/html")?await response.text():""}}', url)
                if response['status'] != 200 or not response['text']:
                    record["paginas"].append({"url": url, "http": response['status'], "estado": "No HTML o redireccion; no seguido"})
                    continue
                soup = BeautifulSoup(response['text'], "html.parser")
                if soup.select_one("input[type=password]"):
                    raise RuntimeError("Sesion UAS caducada; completar login en navegador")
                main = soup.select_one("#region-main") or soup
                record["paginas"].append({"url": url, "http": response['status']})
                for element in main.select("a[href],iframe[src],video[src],audio[src],source[src]"):
                    destination = urljoin(url, element.get("href") or element.get("src") or "")
                    parsed = urlsplit(destination)
                    query = parse_qs(parsed.query)
                    label = re.sub(r"https?://\S+", "[enlace omitido]", element.get_text(" ", strip=True) or element.get("title", ""))[:200]
                    if parsed.hostname == HOST:
                        safe = None
                        if parsed.path == "/fca/course/view.php" and query.get("id") == [str(course_id)]:
                            safe = course_url
                            if query.get("section", [""])[0].isdigit():
                                safe += "&section=" + query["section"][0]
                        elif re.fullmatch(r"/fca/mod/(page|url|resource|forum)/view.php", parsed.path) and query.get("id", [""])[0].isdigit():
                            safe = f"https://{HOST}{parsed.path}?id={query['id'][0]}"
                        elif parsed.path == "/fca/mod/forum/discuss.php" and query.get("d", [""])[0].isdigit():
                            safe = f"https://{HOST}{parsed.path}?d={query['d'][0]}"
                        if safe and safe not in seen and safe not in pending:
                            pending.append(safe)
                    host = parsed.hostname or ""
                    youtube = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|live/))([\w-]{11})", destination)
                    if youtube and youtube.group(1) == "videoseries":
                        continue
                    if parsed.path.lower().endswith(".pdf"):
                        continue
                    is_recording = bool(re.search(r"grabaci|grabada|recording|videoclase|sesi.n", label, re.I))
                    is_meeting = (host.endswith("zoom.us") and "/rec/" not in parsed.path) or (host == "teams.microsoft.com" and ("meetup-join" in parsed.path or parsed.path.startswith('/meet/')))
                    if is_meeting:
                        record["reuniones_excluidas"] += 1
                        continue
                    if youtube or element.name in ("video", "audio", "source", "iframe") or (is_recording and host != HOST):
                        identity = youtube.group(1) if youtube else f"{url}|{host}|{label}"
                        heading = main.select_one("h2,h1,h3") or soup.title
                        resource_title = heading.get_text(" ", strip=True) if heading else ""
                        item = {"titulo_enlace": label, "titulo_recurso": re.sub(r"https?://\S+", "[enlace omitido]", resource_title)[:200], "origen": url, "dominio": host, "grabacion_rotulada": is_recording, "estado": "Candidato; titulo y contenido por verificar"}
                        if youtube:
                            item.update(video_id=youtube.group(1), url="https://www.youtube.com/watch?v=" + youtube.group(1))
                        found[identity] = item
            record["candidatos"] = list(found.values())
            record["limite_alcanzado"] = bool(pending)
            record["alcance"] = "Pestanas y enlaces HTML accesibles de paginas, recursos, URL y foros; sin abrir evaluaciones ni reuniones. No acredita ausencia en adjuntos ni recursos restringidos."
            control = root / f"UAS/licenciatura-en-contaduria-uas/{slug}/referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones"
            control.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            (control / f"busqueda-grabaciones-{stamp}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(record)
            print(json.dumps({"curso": course_id, "paginas": len(seen), "candidatos": record["candidatos"], "reuniones_excluidas": record["reuniones_excluidas"], "limite_alcanzado": bool(pending)}, ensure_ascii=True), flush=True)
        browser.close()
    return results


if __name__ == "__main__":
    import sys

    repo = Path(__file__).resolve().parents[1]
    if "--recordings" in sys.argv:
        try:
            inspect_recordings(repo)
        except Exception as error:
            print(json.dumps({'estado': 'Revision UAS no completada', 'clase_error': type(error).__name__}))
            raise SystemExit(1) from None
        raise SystemExit(0)
    course = int(os.getenv("UAS_COURSE_ID", "632"))
    output_path = Path(os.getenv("UAS_OUTPUT_DIR", str(repo / "UAS/licenciatura-en-contaduria-uas/derecho-mercantil/referencias-derecho-mercantil/consulta-aula-actual")))
    summary = inspect_course(repo, course, output_path)
    print(f"WROTE {len(summary['activities'])} sanitized UAS modules to {output_path}")