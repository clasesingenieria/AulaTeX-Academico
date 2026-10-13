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


def current_snapshot(page, save, user_id):
    import hashlib
    import unicodedata
    from bs4 import BeautifulSoup

    baseline = json.loads((ROOT / 'UCNL/envios-2026-10-09/verificacion-posterior-foro.json').read_text(encoding='utf-8'))
    previous_ids = {int(course['course']): {int(module['id']) for module in course['modules']} for course in baseline['courses']}
    expected_grades = {802325: '9.00', 802326: '10.00', 803536: '10.00', 803541: '10.00', 804730: '10.00', 804731: '10.00', 806393: '10.00', 825100: '10.00', 806395: '10.00', 806399: '10.00', 811777: '9.00'}
    result = {'consulta': datetime.now().astimezone().isoformat(), 'solo_lectura': True, 'intentos_iniciados': False, 'envios_realizados': False, 'cursos': [], 'foro_comprobantes': []}

    def read(url):
        parsed = urlsplit(url)
        allowed = parsed.path in ('/course/view.php', '/grade/report/user/index.php', '/mod/forum/discuss.php') or re.fullmatch(r'/mod/(assign|quiz|forum|scorm|h5pactivity|hvp)/view.php', parsed.path)
        if parsed.hostname != HOST or not allowed or not set(parse_qs(parsed.query)).issubset({'id', 'd'}):
            raise RuntimeError('Destino no autorizado para auditoria')
        response = page.evaluate('async url=>{const response=await fetch(url,{method:"GET",redirect:"manual"});const type=response.headers.get("content-type")||"";return {status:response.status,html:response.status===200&&type.includes("text/html")?await response.text():""}}', url)
        if response['status'] != 200 or not response['html']:
            return None, response['status']
        soup = BeautifulSoup(response['html'], 'html.parser')
        if soup.select_one('input[type=password]'):
            raise RuntimeError('Sesion caducada; auditoria no completada')
        return soup, response['status']

    for old_course in baseline['courses']:
        course_id = int(old_course['course'])
        course_url = BASE + f'/course/view.php?id={course_id}'
        soup, status = read(course_url)
        course = {'curso': course_id, 'titulo': old_course['title'], 'origen': course_url, 'http': status, 'modulos': [], 'calificaciones': [], 'actividades': []}
        content = soup.select_one('.course-content') if soup else None
        if content is None:
            course['estado'] = 'Curso no inspeccionado; no se infiere ausencia de actividades'
            result['cursos'].append(course)
            continue
        modules = {}
        for anchor in content.select('a[href]'):
            target = urljoin(course_url, anchor['href'])
            parsed = urlsplit(target)
            if parsed.hostname != HOST or not re.fullmatch(r'/mod/(assign|quiz|forum|scorm|h5pactivity|hvp)/view.php', parsed.path):
                continue
            identifier = parse_qs(parsed.query).get('id', [''])[0]
            if not identifier.isdigit():
                continue
            section = anchor.find_parent(lambda tag: tag.get('id', '').startswith('section-'))
            heading = section.select_one('.sectionname') if section else None
            if heading and re.search(r's[o\u00f3]lo\s+docentes', heading.get_text(' ', strip=True), re.I):
                continue
            identifier = int(identifier)
            modules[identifier] = {'id': identifier, 'tipo': parsed.path.split('/')[2], 'titulo': anchor.get_text(' ', strip=True), 'url': BASE + parsed.path + f'?id={identifier}', 'nueva': identifier not in previous_ids[course_id]}
        course['modulos'] = list(modules.values())
        course['modulos_previos_no_visibles'] = sorted(previous_ids[course_id] - modules.keys())
        grades, grade_status = read(BASE + f'/grade/report/user/index.php?id={course_id}')
        course['calificaciones_http'] = grade_status
        if grades:
            for row in grades.select('tr'):
                name = row.select_one('.column-itemname')
                grade = row.select_one('.column-grade')
                if name is None or grade is None:
                    continue
                identifier = None
                for anchor in name.select('a[href]'):
                    parsed = urlsplit(urljoin(BASE, anchor['href']))
                    if parsed.path.startswith('/mod/'):
                        candidate = parse_qs(parsed.query).get('id', [''])[0]
                        if candidate.isdigit():
                            identifier = int(candidate)
                            break
                value = grade.get_text(' ', strip=True)
                item = {'modulo': identifier, 'actividad': name.get_text(' ', strip=True), 'nota': value}
                if identifier in expected_grades:
                    item.update(nota_previa=expected_grades[identifier], coincide_previa=value == expected_grades[identifier])
                course['calificaciones'].append(item)
        for module in course['modulos']:
            activity, activity_status = read(module['url'])
            item = {'id': module['id'], 'tipo': module['tipo'], 'titulo': module['titulo'], 'url': module['url'], 'http': activity_status, 'nueva': module['nueva']}
            main = activity.select_one('#region-main') if activity else None
            if main:
                if module['tipo'] == 'forum':
                    item['texto'] = '\n'.join(element.get_text('\n', strip=True) for element in main.select('.activity-description,.activity-dates,.alert,.completion-info'))
                else:
                    for element in main.select('script,style'):
                        element.decompose()
                    item['texto'] = main.get_text('\n', strip=True)
                    item['tablas'] = [table.get_text(' | ', strip=True) for table in main.select('table')]
                item['fechas_html'] = [element.get('datetime') for element in main.select('time[datetime]')]
            course['actividades'].append(item)
        result['cursos'].append(course)
        save(f'curso-{course_id}.json', course)
        save('comprobacion-actividades.json', result)
        print(json.dumps({'curso': course_id, 'modulos': len(modules), 'nuevas': [item['id'] for item in course['modulos'] if item['nueva']], 'calificaciones': course['calificaciones']}, ensure_ascii=True), flush=True)

    for filename in ('foro-1-confirmacion-principal.json', 'foro-1-confirmacion-replica.json'):
        previous = json.loads((ROOT / 'UCNL/envios-2026-10-09' / filename).read_text(encoding='utf-8'))
        url = BASE + f'/mod/forum/discuss.php?d={previous["discussion_id"]}'
        soup, status = read(url)
        post_id = str(previous['post_id'])
        node = soup.select_one(f'#p{post_id},#post{post_id},[data-post-id="{post_id}"]') if soup else None
        item = {'discussion_id': previous['discussion_id'], 'post_id': post_id, 'url': url, 'http': status, 'presente': node is not None}
        if node:
            content = node.select_one('.post-content-container,.posting.fullpost,.content')
            text = content.get_text(' ', strip=True) if content else ''
            normalize = lambda value: re.sub(r'\s+', '', unicodedata.normalize('NFKC', value))
            authors = node.select('.author a[href],.row.header a[href],header a[href]')
            item['autor_propio'] = bool(user_id) and any(parse_qs(urlsplit(anchor['href']).query).get('id') == [str(user_id)] for anchor in authors)
            item['contenido_coincide_comprobante'] = bool(text) and normalize(text) == normalize(previous['text'])
            item['sha256_texto_normalizado'] = hashlib.sha256(normalize(text).encode('utf-8')).hexdigest()
            item['caracteres_texto'] = len(text)
            if previous.get('parent_post_id'):
                parent = str(previous['parent_post_id'])
                item['mensaje_replicado_presente'] = soup.select_one(f'#p{parent},#post{parent},[data-post-id="{parent}"]') is not None
        result['foro_comprobantes'].append(item)
    save('comprobacion-actividades.json', result)
    print(json.dumps({'foro': result['foro_comprobantes'], 'evidencia': OUTPUT.relative_to(ROOT).as_posix()}, ensure_ascii=True), flush=True)


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
        if '--current' in sys.argv:
            user_id = page.evaluate('()=>globalThis.M?.cfg?.userid||null') or user_id
            current_snapshot(page, save, user_id)
            browser.close()
            return
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
    if '--current' in sys.argv:
        OUTPUT = ROOT / 'UCNL' / ('auditoria-actividades-' + datetime.now().strftime('%Y-%m-%d-%H%M%S'))
    try:
        run()
    except Exception as error:
        print(json.dumps({'estado': 'Auditoria no completada', 'clase_error': type(error).__name__}))
        raise SystemExit(1) from None