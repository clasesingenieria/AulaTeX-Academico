import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

SUBJECT = Path(__file__).resolve().parents[1]
ROOT = SUBJECT.parents[2]
sys.path.insert(0, str(ROOT))

from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials, _same_host_url


def main():
    load_dotenv(ROOT / "aulaTEX/aulatex.env", override=False)
    output = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/materiales-aula/2026-10-23"
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "enlaces-intro.json"
    if manifest_path.exists():
        print(manifest_path.read_text(encoding="utf-8"))
        return
    credentials = _get_credentials(ROOT)
    records = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True, args=_browser_resolver_args()[0])
        try:
            context = browser.new_context(service_workers="block")

            def limit_origin(route):
                try:
                    _same_host_url(route.request.url)
                except Exception:
                    route.abort()
                    return
                route.continue_()

            context.route("**/*", limit_origin)
            page = context.new_page()
            page.goto(BASE_URL + "/login/index.php")
            page.locator("#username").fill(credentials["username"])
            page.locator("#password").fill(credentials["password"])
            page.locator("#loginbtn").click()
            del credentials
            for module_id in (1754, 1755):
                page.goto(BASE_URL + f"/mod/assign/view.php?id={module_id}")
                assert "/login/" not in page.url
                links = page.locator("#intro a[href]").evaluate_all("elements => elements.map(element => ({text: element.innerText, url: element.href}))")
                for index, link in enumerate(links, 1):
                    record = {"module_id": module_id, **link}
                    url = _same_host_url(link["url"])
                    suffix = Path(unquote(urlparse(url).path)).suffix.lower()
                    if "/pluginfile.php/" in url and suffix in (".pdf", ".docx", ".xlsx"):
                        encoded = page.evaluate("""async url => {
                            const response = await fetch(url, {credentials: 'same-origin', redirect: 'error', signal: AbortSignal.timeout(60000)});
                            if (!response.ok) throw new Error('attachment_download_failed');
                            const bytes = new Uint8Array(await response.arrayBuffer());
                            if (bytes.length > 20000000) throw new Error('attachment_too_large');
                            let binary = '';
                            for (let offset = 0; offset < bytes.length; offset += 8192)
                                binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
                            return btoa(binary);
                        }""", url)
                        data = base64.b64decode(encoded, validate=True)
                        assert len(data) <= 20_000_000
                        assert data.startswith(b"%PDF" if suffix == ".pdf" else b"PK")
                        destination = output / f"{module_id}-adjunto-{index}{suffix}"
                        destination.write_bytes(data)
                        record.update(path=destination.relative_to(SUBJECT).as_posix(), sha256=hashlib.sha256(data).hexdigest())
                    records.append(record)
        finally:
            browser.close()
    manifest = {"read_only": True, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "links": records}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()