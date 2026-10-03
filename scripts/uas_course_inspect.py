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

from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path


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


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    course = int(os.getenv("UAS_COURSE_ID", "632"))
    output_path = Path(os.getenv("UAS_OUTPUT_DIR", str(repo / "UAS/licenciatura-en-contaduria-uas/derecho-mercantil/referencias-derecho-mercantil/consulta-aula-actual")))
    summary = inspect_course(repo, course, output_path)
    print(f"WROTE {len(summary['activities'])} sanitized UAS modules to {output_path}")