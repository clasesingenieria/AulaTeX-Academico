from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

HOST = "licenciatura.ucnl.edu.mx"
BASE = f"https://{HOST}"
OUTPUT = ROOT / "UCNL" / "auditoria-2026-10-09"


def run():
    load_aulatex_env()
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    accounts = [account for account in vault.list_accounts(pin)
                if account["institution"].casefold() == "ucnl"
                and urlsplit(account["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("Se requiere una unica cuenta UCNL para el dominio autorizado")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    identities = [credentials["username"], credentials["password"]]

    def sanitize(value):
        if isinstance(value, str):
            for identity in sorted(set(identities), key=len, reverse=True):
                if identity:
                    value = value.replace(identity, "[dato privado]")
            value = re.sub(r"(?i)(sesskey|logintoken|password|token|pwd)=[^&\s]+", r"\1=[omitido]", value)
            return re.sub(r"(?im)((?:passcode|pass|c[oó]digo de acceso)\s*:)\s*[^\n]+", r"\1 [omitido]", value)
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        return value

    def save(name, data):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / name).write_text(json.dumps(sanitize(data), ensure_ascii=False, indent=2), encoding="utf-8")

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        context.set_default_timeout(45000)

        def guard(route):
            parsed = urlsplit(route.request.url)
            if parsed.scheme != "https" or parsed.hostname != HOST:
                route.abort()
            else:
                route.continue_()

        context.route("**/*", guard)
        page = context.new_page()
        page.goto(BASE + "/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        try:
            page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path, wait_until="domcontentloaded", timeout=15000)
        except PlaywrightTimeoutError:
            print(json.dumps(sanitize({"authenticated": False, "path": urlsplit(page.url).path,
                                      "message": page.locator("#region-main").inner_text()}), ensure_ascii=True))
            browser.close()
            return
        del credentials
        for name in page.locator(".usertext, .userbutton .usertext").all_inner_texts():
            if name.strip():
                identities.append(name.strip())
        profile_links = page.locator('a[href*="/user/profile.php?id="]').evaluate_all(
            "items => items.map(item => item.href)")
        user_id = parse_qs(urlsplit(profile_links[0]).query)["id"][0] if profile_links else ""
        if "--reports" in sys.argv:
            inert_context = browser.new_context(java_script_enabled=False, service_workers="block")
            inert_context.route("**/*", lambda route: route.abort())
            inert = inert_context.new_page()

            def read_html(url):
                if urlsplit(url).hostname != HOST:
                    raise RuntimeError("Destino fuera del sitio autorizado")
                response = context.request.get(url, max_redirects=0)
                if response.status != 200:
                    return {"url": url, "http_status": response.status}
                response_html = response.text()
                inert.set_content(response_html, wait_until="domcontentloaded")
                for name in inert.locator('a[href*="/user/view.php"], a[href*="/user/profile.php"]').all_inner_texts():
                    if name.strip():
                        identities.append(name.strip())
                main = inert.locator("#region-main")
                if not main.count():
                    return {"url": url, "http_status": response.status, "text": "Sin region principal"}
                return {"url": url, "http_status": response.status, "text": main.inner_text(),
                        "links": inert.locator("a[href]").evaluate_all(
                            "items => items.map(item => ({text:item.innerText,href:item.getAttribute('href')}))")}

            for evidence_path in sorted(OUTPUT.glob("curso-*.json")):
                course = json.loads(evidence_path.read_text(encoding="utf-8"))
                match = re.search(r"Reporte de usuario\s*\n[^\n]+\n([^\n]+)\n", course.get("grades", ""))
                if match:
                    identities.append(match.group(1))
                course["interactive_reports"] = []
                for module in course["modules"]:
                    parsed = urlsplit(module["url"])
                    if parsed.path not in ("/mod/scorm/view.php", "/mod/h5pactivity/view.php"):
                        continue
                    report = read_html(module["url"])
                    report["module"] = module
                    followups = []
                    for link in report.pop("links", []):
                        target = urljoin(module["url"], link["href"])
                        target_path = urlsplit(target).path
                        if target_path in ("/mod/h5pactivity/report.php", "/mod/scorm/report.php", "/mod/scorm/userreport.php"):
                            followup = read_html(target)
                            followup.pop("links", None)
                            followups.append(followup)
                    report["reports"] = followups
                    course["interactive_reports"].append(report)
                for activity in course["activities"]:
                    if "/mod/forum/" not in activity["url"]:
                        continue
                    listing = read_html(activity["url"])
                    discussion_ids = {parse_qs(urlsplit(link["href"]).query).get("d", [""])[0]
                                      for link in listing.pop("links", []) if "/mod/forum/discuss.php" in link["href"]}
                    discussion_urls = [BASE + "/mod/forum/discuss.php?d=" + identifier
                                       for identifier in sorted(discussion_ids) if identifier.isdigit()]
                    discussion_counts = []
                    if course["id"] == "20322":
                        for discussion_url in discussion_urls:
                            detail = read_html(discussion_url)
                            counts = inert.locator(".forumpost").evaluate_all("""(posts, userId) => ({
                                posts: posts.length,
                                identified: posts.filter(post => [...post.querySelectorAll('.author a[href], .row.header a[href], header a[href]')]
                                    .some(anchor => new URL(anchor.getAttribute('href'), 'https://licenciatura.ucnl.edu.mx').pathname.startsWith('/user/'))).length,
                                own: posts.filter(post => [...post.querySelectorAll('.author a[href], .row.header a[href], header a[href]')]
                                    .some(anchor => {
                                        const url = new URL(anchor.getAttribute('href'), 'https://licenciatura.ucnl.edu.mx');
                                        return url.pathname.startsWith('/user/') && url.searchParams.get('id') === userId;
                                    })).length
                            })""", user_id)
                            discussion_counts.append({"url": discussion_url, "http_status": detail["http_status"], **counts})
                    activity["forum_audit"] = {"own_user_identified": bool(user_id), "discussions": discussion_counts,
                                               "visible_discussions": len(discussion_urls)}
                    activity["text"] = listing["text"].split("Lista de discusiones.")[0]
                    activity["tables"] = []
                course["reports_consulted"] = datetime.now().astimezone().isoformat()
                save(evidence_path.name, course)
                print(json.dumps(sanitize({"course": course["id"], "interactive_reports": course["interactive_reports"],
                                  "forums": [activity.get("forum_audit") for activity in course["activities"]
                                             if "forum_audit" in activity]}), ensure_ascii=True, default=str), flush=True)
            inert_context.close()
            browser.close()
            return
        page.goto(BASE + "/my/courses.php", wait_until="networkidle")
        links = page.locator('a[href*="/course/view.php?id="]').evaluate_all(
            "items => items.map(item => ({title:item.innerText.trim(), url:item.href}))")
        courses = {}
        for link in links:
            parsed = urlsplit(link["url"])
            identifier = parse_qs(parsed.query).get("id", [""])[0]
            if parsed.hostname == HOST and identifier.isdigit():
                if identifier not in courses or len(link["title"]) > len(courses[identifier]["title"]):
                    courses[identifier] = {"id": identifier, "title": link["title"],
                                           "url": BASE + "/course/view.php?id=" + identifier}
        discovery = {"consultado": datetime.now().astimezone().isoformat(), "solo_lectura": True,
                     "courses": list(courses.values()),
                     "dashboard": page.locator("#region-main").inner_text()}
        save("cursos.json", discovery)
        print(json.dumps(sanitize({"authenticated": True, "courses": list(courses.values())}), ensure_ascii=True))
        if "--discover" in sys.argv:
            browser.close()
            return
        for course in courses.values():
            page.goto(course["url"], wait_until="networkidle")
            main = page.locator("#region-main")
            course["text"] = main.inner_text()
            course["modules"] = page.locator('.course-content li.activity').evaluate_all("""items => items.map(item => {
                const anchor = item.querySelector('a.aalink, .activityname a, a[href*="/mod/"]');
                const section = item.closest('li.section, .course-section');
                return {text:item.innerText, url:anchor ? anchor.href : '',
                    section:section?.querySelector('.sectionname')?.textContent || '',
                    completion:[...item.querySelectorAll('[data-action*="completion"], [aria-label], img[alt]')]
                        .map(element => element.getAttribute('aria-label') || element.getAttribute('alt') || element.innerText)};
            })""")
            course["activities"] = []
            save(f"curso-{course['id']}.json", course)
            for module in course["modules"]:
                parsed = urlsplit(module["url"])
                if parsed.hostname != HOST or not re.fullmatch(r"/mod/(assign|quiz|forum|feedback|choice)/view.php", parsed.path):
                    continue
                if re.search(r"s[oó]lo\s+docentes", module["section"], re.I):
                    continue
                identifier = parse_qs(parsed.query).get("id", [""])[0]
                if not identifier.isdigit():
                    continue
                url = BASE + parsed.path + "?id=" + identifier
                page.goto(url, wait_until="domcontentloaded")
                activity = {"id": identifier, "url": url, "module": module,
                            "text": page.locator("#region-main").inner_text(),
                            "tables": page.locator("#region-main table").all_inner_texts(),
                            "files": page.locator('#region-main a[href*="pluginfile.php"]').evaluate_all(
                                "items => items.map(item => ({name:item.innerText, url:item.href}))")}
                course["activities"].append(activity)
                save(f"curso-{course['id']}.json", course)
            page.goto(BASE + "/grade/report/user/index.php?id=" + course["id"], wait_until="domcontentloaded")
            course["grades"] = page.locator("#region-main").inner_text()
            save(f"curso-{course['id']}.json", course)
            print(json.dumps({"course": course["id"], "modules": len(course["modules"]),
                              "activities": len(course["activities"])}, ensure_ascii=True), flush=True)
        browser.close()


if __name__ == "__main__":
    run()