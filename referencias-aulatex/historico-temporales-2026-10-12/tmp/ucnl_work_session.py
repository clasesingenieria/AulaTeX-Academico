from __future__ import annotations

from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

HOST = "licenciatura.ucnl.edu.mx"
BASE = "https://" + HOST
OUTPUT = ROOT / "UCNL" / "envios-2026-10-09"


def main():
    load_aulatex_env()
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    accounts = [account for account in vault.list_accounts(pin)
                if account["institution"].casefold() == "ucnl"
                and urlsplit(account["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("Cuenta UCNL unica requerida")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    private = [credentials["username"], credentials["password"]]

    def sanitize(value):
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        for item in private:
            if item:
                serialized = serialized.replace(item, "[privado]")
        serialized = re.sub(r"(?i)(sesskey|logintoken|token|pwd)=[^&\s\"<>]+", r"\1=[omitido]", serialized)
        return json.loads(serialized)

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block", viewport={"width": 1400, "height": 1000})
        context.set_default_timeout(20000)

        def guard(route):
            parsed = urlsplit(route.request.url)
            if parsed.scheme == "https" and parsed.hostname == HOST:
                route.continue_()
            else:
                route.abort()

        context.route("**/*", guard)
        page = context.new_page()
        for login_attempt in range(2):
            page.goto(BASE + "/login/index.php", wait_until="domcontentloaded")
            page.locator("#username").fill(credentials["username"])
            page.locator("#password").fill(credentials["password"])
            page.locator("#loginbtn").click()
            try:
                page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path, wait_until="domcontentloaded", timeout=15000)
                break
            except PlaywrightTimeoutError:
                message = page.locator("#region-main").inner_text()
                if login_attempt == 0 and "excedido el tiempo" in message.casefold():
                    context.clear_cookies()
                    continue
                raise RuntimeError(sanitize({"login_error": message})["login_error"]) from None
        del credentials
        if "--check-login" in sys.argv:
            print(json.dumps({"authenticated": True}), flush=True)
            browser.close()
            return

        def snapshot():
            frames = []
            for index, frame in enumerate(page.frames):
                parsed = urlsplit(frame.url)
                if parsed.hostname not in (None, HOST):
                    continue
                region = frame.locator("#region-main")
                if not region.count():
                    region = frame.locator("body")
                if not region.count():
                    continue
                frames.append({"index": index, "url": frame.url, "text": region.inner_text()[:25000],
                               "controls": region.locator("input:visible:not([type=password]), textarea:visible, select:visible, button:visible, [role=button]:visible").evaluate_all("""items => items.map(item => ({
                                   tag:item.tagName, type:item.type, id:item.id, name:item.name,
                                   text:item.innerText, value:item.value, checked:item.checked,
                                   label:item.getAttribute('aria-label'), disabled:item.disabled,
                                   options:item.options ? [...item.options].map(option => ({text:option.text, value:option.value})) : undefined
                               }))""")})
            return sanitize({"at": datetime.now().astimezone().isoformat(), "url": page.url, "frames": frames})

        running = True

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_POST(self):
                nonlocal running
                if self.headers.get("Origin") or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    self.send_error(403)
                    return
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 100000:
                    self.send_error(413)
                    return
                try:
                    command = json.loads(self.rfile.read(size))
                    frame = page.frames[command.get("frame", 0)]
                    action = command["action"]
                    result = None
                    if action == "goto":
                        if urlsplit(command["url"]).hostname != HOST:
                            raise ValueError("Host no autorizado")
                        page.goto(command["url"], wait_until="domcontentloaded")
                    elif action == "click":
                        frame.locator(command["selector"]).click()
                    elif action == "fill":
                        frame.locator(command["selector"]).fill(command["text"])
                    elif action == "check":
                        frame.locator(command["selector"]).check()
                    elif action == "upload":
                        page.wait_for_load_state("networkidle")
                        frame.locator(command["selector"]).set_input_files(command["path"])
                    elif action == "download":
                        with page.expect_download() as pending:
                            frame.locator(command["selector"]).click()
                        download = pending.value
                        OUTPUT.mkdir(parents=True, exist_ok=True)
                        destination = OUTPUT / download.suggested_filename
                        download.save_as(destination)
                        import hashlib
                        result = {"filename": destination.name, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
                    elif action == "select":
                        frame.locator(command["selector"]).select_option(command["value"])
                    elif action == "evaluate":
                        result = frame.evaluate(command["code"], command.get("arg"))
                    elif action == "capture":
                        name = command["name"]
                        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
                            raise ValueError("Nombre de evidencia invalido")
                        OUTPUT.mkdir(parents=True, exist_ok=True)
                        (OUTPUT / (name + ".json")).write_text(json.dumps(snapshot(), ensure_ascii=False, indent=2), encoding="utf-8")
                        result = {"saved": name + ".json"}
                    elif action == "close":
                        running = False
                        result = {"closed": True}
                    elif action != "snapshot":
                        raise ValueError("Accion desconocida")
                    body = json.dumps(sanitize({"ok": True, "result": result,
                                               "state": snapshot() if command.get("snapshot", True) else None}), ensure_ascii=True).encode()
                except Exception as error:
                    body = json.dumps(sanitize({"ok": False, "error": str(error)}), ensure_ascii=True).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(("127.0.0.1", 0), Handler)
        print(json.dumps({"ready": True, "port": server.server_port}), flush=True)
        while running:
            server.handle_request()
        server.server_close()
        browser.close()


if __name__ == "__main__":
    main()