import base64
import hashlib
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

SUBJECT = Path(__file__).resolve().parents[1]
ROOT = SUBJECT.parents[2]
sys.path.insert(0, str(ROOT))

from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials, _same_host_url, inspect_activity


def inspect_cover(output):
    from playwright.sync_api import sync_playwright

    credentials = _get_credentials(ROOT)
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
            page.goto(BASE_URL + "/mod/assign/view.php?id=1748")
            assert "/login/" not in page.url
            rows = page.locator("#intro tr").filter(has_text="Portada Oficial")
            result = {"module_id": 1748, "read_only": True, "rows": rows.all_text_contents(),
                      "link_count": rows.locator("a[href]").count(),
                      "links": rows.locator("a[href]").evaluate_all("elements => elements.map(element => ({text:element.innerText, url:element.href}))")}
            assert result["rows"]
            for link in result["links"]:
                url = _same_host_url(link["url"])
                if ".docx" not in url:
                    continue
                encoded = page.evaluate("""async url => {
                    const response = await fetch(url, {credentials: 'same-origin'});
                    if (!response.ok) throw new Error('cover_download_failed');
                    const bytes = new Uint8Array(await response.arrayBuffer());
                    if (bytes.length > 5000000) throw new Error('cover_too_large');
                    let binary = '';
                    for (let offset = 0; offset < bytes.length; offset += 8192)
                        binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
                    return btoa(binary);
                }""", url)
                data = base64.b64decode(encoded, validate=True)
                assert data.startswith(b"PK")
                destination = output / "DocumentoMGAVirtual-oficial.docx"
                destination.write_bytes(data)
                result["download"] = {"path": destination.relative_to(SUBJECT).as_posix(),
                                      "sha256": hashlib.sha256(data).hexdigest()}
            (output / "portada.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result
        finally:
            browser.close()


def main():
    load_dotenv(ROOT / "aulaTEX/aulatex.env", override=False)
    output = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/materiales-aula/2026-10-22"
    if "--portada" in sys.argv:
        print(json.dumps(inspect_cover(output), ensure_ascii=True, indent=2))
        return
    evidence = output / "inspection.json"
    if evidence.exists():
        result = json.loads(evidence.read_text(encoding="utf-8"))
    else:
        result = inspect_activity(ROOT, output, module_id=1747, course_id=209, related_modules=(1748,))
    assert result["read_only"]
    assert {item["module_id"] for item in result["activities"]} == {1747, 1748}
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()