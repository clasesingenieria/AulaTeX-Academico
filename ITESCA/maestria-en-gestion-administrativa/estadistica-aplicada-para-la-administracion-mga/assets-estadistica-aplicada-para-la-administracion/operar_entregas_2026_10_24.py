"""Operación HTTP puntual de la entrega expresamente autorizada el 24/10/2026.

Sesión y credenciales solo en memoria; TLS con almacén de confianza del sistema.
No usa ni modifica el inspector de solo lectura de AulaTeX.
"""
from pathlib import Path
import sys, json, ssl, http.cookiejar, urllib.request, urllib.parse, types, importlib.util, re, uuid, hashlib
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[4]
# Carga el módulo puntual sin arrancar toda la suite editorial/GUI.
package = types.ModuleType('aulatex_portal_task')
package.__path__ = [str(ROOT / 'aulaTEX/aulatex')]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location('aulatex_portal_task.itesca_activity_portal', ROOT / 'aulaTEX/aulatex/itesca_activity_portal.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
from aulatex_portal_task.itesca_activity_portal import (
    BASE_URL, _get_credentials, _same_host_url, _sanitize, _identity_variants,
)

class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _same_host_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Portal:
    def __init__(self):
        print(json.dumps({'phase': 'loading_configuration'}), flush=True)
        load_dotenv(ROOT / 'aulaTEX/aulatex.env', override=False)
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            SameHostRedirect())
        self.identities = ()
        print(json.dumps({'phase': 'connecting'}), flush=True)
        self.get('/login/index.php')
        print(json.dumps({'phase': 'unlocking_vault'}), flush=True)
        creds = _get_credentials(ROOT)
        form = self.soup.select_one('form#login')
        if form is None:
            form = self.soup.find('form', action=lambda v: v and '/login/' in v)
        data = self.formdata(form)
        data.update(username=creds['username'], password=creds['password'])
        self.identities = _identity_variants(creds['username'], [])
        print(json.dumps({'phase': 'authenticating'}), flush=True)
        self.send(form.get('action'), data)
        del creds, data
        if '/login/' in self.url:
            raise RuntimeError('authentication_failed')
        names = [e.get_text(' ', strip=True) for e in self.soup.select('.usermenu .usertext,.usermenu .userfullname')]
        self.identities = self.identities + tuple(names)

    def get(self, url):
        return self.send(url)

    def send(self, url, data=None, body=None, headers=None):
        url = _same_host_url(url, getattr(self, 'url', BASE_URL))
        if data is not None:
            body = urllib.parse.urlencode(data, doseq=True).encode()
        req = urllib.request.Request(url, data=body, headers=headers or {})
        with self.opener.open(req, timeout=45) as res:
            self.url = _same_host_url(res.url)
            raw = res.read(25 * 1024 * 1024)
        self.raw = raw
        self.soup = BeautifulSoup(raw, 'html.parser')
        return raw

    def formdata(self, form):
        if form is None:
            raise RuntimeError('form_missing')
        data = {}
        for el in form.select('input[name],textarea[name],select[name]'):
            name = el.get('name')
            typ = el.get('type', '').lower()
            if el.has_attr('disabled') or typ in ('submit', 'button', 'reset', 'file'):
                continue
            if typ in ('checkbox', 'radio') and not el.has_attr('checked'):
                continue
            if el.name == 'textarea':
                data[name] = el.get_text()
            elif el.name == 'select':
                selected = el.find('option', selected=True) or el.find('option')
                if selected is not None:
                    data[name] = selected.get('value', selected.get_text())
            else:
                data[name] = el.get('value', '')
        return data

    def file_options(self):
        scripts = '\n'.join(el.get_text() for el in self.soup.find_all('script'))
        match = re.search(r'M\.form_filemanager\.init\(Y,\s*', scripts)
        if not match:
            raise RuntimeError('filemanager_configuration_not_observed')
        return json.JSONDecoder().raw_decode(scripts[match.end():])[0]

    def snapshot(self):
        main = self.soup.select_one('#region-main') or self.soup
        forms = []
        for i, form in enumerate(self.soup.find_all('form')):
            controls = []
            for el in form.select('input[name],button,select[name],textarea[name]'):
                typ = el.get('type', el.name)
                control = {'name': el.get('name'), 'type': typ}
                if typ != 'hidden' and el.get('name') != 'jump':
                    control['label'] = el.get_text(' ', strip=True) or el.get('value', '')
                    if typ in ('radio', 'checkbox'):
                        control['value'] = el.get('value', '')
                        label = self.soup.find('label', attrs={'for': el.get('id')})
                        if label:
                            control['label'] = label.get_text(' ', strip=True)
                controls.append(control)
            forms.append({'index': i, 'id': form.get('id'), 'action_path': urllib.parse.urlsplit(form.get('action', '')).path, 'controls': controls})
        links = [{'text': a.get_text(' ', strip=True), 'url': a['href']} for a in main.select('a[href]')
                 if any(s in a['href'] for s in ('/mod/quiz/', '/mod/assign/', '/pluginfile.php/'))
                 and not any(s in a['href'].lower() for s in ('sesskey', 'token', 'logout'))]
        return {'path': urllib.parse.urlsplit(self.url).path,
                'text': _sanitize(main.get_text('\n', strip=True), self.identities), 'forms': forms, 'links': links}

    def command(self, cmd):
        op = cmd['op']
        if op == 'get':
            self.get(cmd['url'])
        elif op == 'form':
            forms = self.soup.find_all('form')
            form = forms[cmd['index']]
            data = self.formdata(form)
            data.update(cmd.get('values', {}))
            button = cmd.get('button')
            if button:
                el = form.find(attrs={'name': button})
                if el is None:
                    raise RuntimeError('button_not_observed')
                data[button] = cmd.get('button_value', el.get('value', ''))
            self.send(form.get('action') or self.url, data)
        elif op == 'questions':
            return [{'slot': el.get('id'), 'text': el.get_text('\n', strip=True)} for el in self.soup.select('.que')]
        elif op == 'file_config':
            opts = self.file_options()
            return {'filecount': opts['filecount'], 'maxfiles': opts['maxfiles'], 'context_id': opts['context']['id'],
                    'upload_available': any(v['type'] == 'upload' for v in opts['filepicker']['repositories'].values())}
        elif op == 'upload':
            path = Path(cmd['path']).resolve()
            deliveries = Path(__file__).resolve().parents[1] / 'entregas-estadistica-aplicada-para-la-administracion'
            if not path.is_relative_to(deliveries) or path.suffix != '.pdf':
                raise RuntimeError('upload_path_not_allowed')
            content = path.read_bytes()
            if not content.startswith(b'%PDF-') or len(content) > 25 * 1024 * 1024:
                raise RuntimeError('upload_not_pdf_or_too_large')
            # Los parámetros deben proceder de la configuración observada del selector.
            form = self.soup.find_all('form')[cmd['form_index']]
            data = self.formdata(form)
            if 'files_filemanager' not in data or 'sesskey' not in data:
                raise RuntimeError('not_submission_filemanager')
            opts = self.file_options()
            repos = [v for v in opts['filepicker']['repositories'].values() if v['type'] == 'upload']
            if len(repos) != 1 or opts['filecount'] != 0:
                raise RuntimeError('upload_requires_empty_draft_and_unique_repository')
            fields = {'repo_id': repos[0]['id'], 'ctx_id': opts['context']['id'], 'env': 'filemanager',
                      'savepath': '/', 'title': path.name, 'license': opts['defaultlicense'],
                      'author': opts.get('author', ''), 'accepted_types[]': '*'}
            fields['itemid'] = data['files_filemanager']
            fields['sesskey'] = data['sesskey']
            boundary = 'AulaTeX' + uuid.uuid4().hex
            chunks = []
            for key, value in fields.items():
                chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="repo_upload_file"; filename="{path.name}"\r\nContent-Type: application/pdf\r\n\r\n'.encode())
            chunks += [content, f'\r\n--{boundary}--\r\n'.encode()]
            previous = (self.soup, self.url, self.raw)
            raw = self.send('/repository/repository_ajax.php?action=upload', body=b''.join(chunks), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
            result = json.loads(raw)
            self.soup, self.url, self.raw = previous
            if result.get('error'):
                return {'upload_ok': False, 'error': _sanitize(str(result['error']), self.identities)}
            return {'upload_ok': True, 'response_keys': list(result), 'filename': path.name, 'sha256': hashlib.sha256(content).hexdigest()}
        elif op == 'verify_file':
            path = Path(cmd['path']).resolve()
            links = [a['href'] for a in self.soup.select('a[href]') if '/pluginfile.php/' in a['href'] and a.get_text(strip=True) == path.name]
            if len(set(links)) != 1:
                raise RuntimeError('submitted_file_link_not_unique')
            previous = (self.soup, self.url, self.raw)
            raw = self.get(links[0])
            self.soup, self.url, self.raw = previous
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            actual = hashlib.sha256(raw).hexdigest()
            return {'filename': path.name, 'downloaded_bytes': len(raw), 'sha256': actual, 'matches_local': actual == expected}
        elif op == 'save_text':
            path = Path(cmd['path']).resolve()
            subject = Path(__file__).resolve().parents[1]
            if not path.is_relative_to(subject):
                raise RuntimeError('evidence_path_outside_subject')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.snapshot(), ensure_ascii=False, indent=2), encoding='utf-8')
        elif op != 'inspect':
            raise RuntimeError('unknown_operation')
        return self.snapshot()

if __name__ == '__main__':
    try:
        portal = Portal()
        print(json.dumps({'authenticated': True}, ensure_ascii=True), flush=True)
    except Exception as e:
        print(json.dumps({'authenticated': False, 'error_type': type(e).__name__}), flush=True)
        sys.exit(1)
    for line in sys.stdin:
        try:
            print(json.dumps(portal.command(json.loads(line)), ensure_ascii=True), flush=True)
        except Exception as e:
            print(json.dumps({'error_type': type(e).__name__, 'operation_failed': True}), flush=True)
