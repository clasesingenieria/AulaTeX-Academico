"""Read-only ITESCA activity inspection with local vault authentication.

No LLM calls, submissions, persistent browser sessions or secret-bearing logs.
Only the authenticated browser receives credentials. Callers may give the returned
academic summary to a model; local evidence is sanitized by the same rules.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import unicodedata
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

HOST = "cursos3.e-itesca.edu.mx"
BASE_URL = f"https://{HOST}"
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


class PortalInspectionError(RuntimeError):
    """Safe error code; never wraps browser traces or credential values."""


def _same_host_url(value: str, base: str = BASE_URL) -> str:
    value = urljoin(base, value)
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname == HOST
                 and parsed.port in (None, 443) and parsed.username is None
                 and parsed.password is None and not any(c.isspace() for c in value))
    except ValueError:
        valid = False
    if not valid:
        raise PortalInspectionError("portal_url_not_allowed")
    return value


def _normalized_link(value: str) -> str | None:
    """Only public academic view/attachment paths, with no session/user query."""
    try:
        parsed = urlsplit(_same_host_url(value))
    except PortalInspectionError:
        return None
    if parsed.path in ("/mod/assign/view.php", "/mod/resource/view.php", "/course/view.php"):
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k == "id" and v.isdigit()]
        if len(query) != 1:
            return None
    elif parsed.path.startswith("/pluginfile.php/") and "/introattachment/" in parsed.path:
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k == "forcedownload" and v == "1"]
    else:
        return None
    return urlunsplit(("https", HOST, parsed.path, urlencode(query), ""))


def _fold(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)).casefold()


def _sanitize(text: str, identities: tuple[str, ...]) -> str:
    """Remove portal-sourced student identity and secret/token-like parameters."""
    result = str(text)
    for value in sorted({v.strip() for v in identities if v and v.strip()}, key=len, reverse=True):
        # Same-length accented characters retain reliable match offsets.
        folded_value = _fold(value)
        for match in reversed(list(re.finditer(re.escape(folded_value), _fold(result)))):
            result = result[:match.start()] + "[estudiante]" + result[match.end():]
    result = re.sub(r"(?i)(?:sesskey|token|password|logintoken|username)\s*[=:]\s*[^\s&]+", "[dato omitido]", result)
    result = re.sub(r"(?i)(matr[ií]cula\s*[:#]?\s*)[A-Z0-9-]+", r"\1[omitida]", result)
    return result


def _identity_variants(username: str, full_names: list[str]) -> tuple[str, ...]:
    variants = [username]
    for name in full_names:
        clean = " ".join(name.split()).strip()
        if len(clean) < 5:
            continue
        variants.append(clean)
        words = clean.split()
        if len(words) > 2:
            variants.append(" ".join(words[:2]))
        # Moodle submission filenames often concatenate the surname.
        if len(words) >= 4:
            for size in (2, 3, 4):
                variants.append("".join(words[-size:]))
    return tuple(variants)


def _resolve_doh_address() -> str:
    query = urlencode({"name": HOST, "type": "A"})
    for endpoint in ("https://cloudflare-dns.com/dns-query", "https://1.1.1.1/dns-query"):
        try:
            request = Request(f"{endpoint}?{query}", headers={"Accept": "application/dns-json"})
            with urlopen(request, timeout=12, context=ssl.create_default_context()) as response:
                # DoH must not silently redirect to another provider.
                if urlsplit(response.url).hostname not in ("cloudflare-dns.com", "1.1.1.1"):
                    continue
                data = response.read(65537)
            if len(data) > 65536:
                continue
            payload = json.loads(data)
            if payload.get("Status") != 0 or not any(
                q.get("name", "").rstrip(".").casefold() == HOST and q.get("type") == 1
                for q in payload.get("Question", [])
            ):
                continue
            for answer in payload.get("Answer", []):
                if answer.get("type") != 1:
                    continue
                address = ipaddress.ip_address(answer.get("data", ""))
                if address.version == 4 and address.is_global:
                    return str(address)
        except Exception:
            # TLS/network/provider errors are never echoed with request details.
            continue
    raise PortalInspectionError("portal_dns_resolution_failed")


def _browser_resolver_args() -> tuple[list[str], str]:
    try:
        socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
        return [], "system"
    except socket.gaierror:
        address = _resolve_doh_address()
        return [f"--host-resolver-rules=MAP {HOST} {address}"], "cloudflare_doh_temporary_map"


def _positive_id(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PortalInspectionError("invalid_activity_identifier")
    return value


def _get_credentials(repo_root: Path) -> dict:
    from .platform_credentials import PlatformCredentialVault, default_vault_path

    pin = next((value for key, value in os.environ.items() if key.casefold() == "aulatex_master_pin"), None)
    if not pin:
        raise PortalInspectionError("portal_master_pin_missing")
    try:
        vault = PlatformCredentialVault(default_vault_path(repo_root))
        accounts = [a for a in vault.list_accounts(pin) if a["institution"].casefold() == "itesca"]
        accounts = [a for a in accounts if urlsplit(a["url"]).hostname == HOST]
        if len(accounts) != 1:
            raise PortalInspectionError("portal_account_selection_required")
        record = vault.get_credentials(pin, accounts[0]["id"])
        _same_host_url(record["url"])
        return record
    except PortalInspectionError:
        raise
    except Exception:
        raise PortalInspectionError("portal_vault_unavailable") from None


def _download_pdf(page, observed_url: str) -> bytes:
    """Use Chromium's DNS mapping and cookies; redirects are blocked by routing."""
    url = _same_host_url(observed_url)
    value = page.evaluate("""async ({url, limit}) => {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 45000);
        try {
            const response = await fetch(url, {credentials:'same-origin', signal:controller.signal});
            if (!response.ok || new URL(response.url).origin !== location.origin) throw new Error('download');
            const reader = response.body.getReader();
            const chunks = []; let size = 0;
            while (true) {
                const {done,value} = await reader.read(); if (done) break;
                size += value.length; if (size > limit) { await reader.cancel(); throw new Error('size'); }
                chunks.push(value);
            }
            let binary = '';
            for (const chunk of chunks) for (let n=0;n<chunk.length;n+=8192)
                binary += String.fromCharCode(...chunk.subarray(n,n+8192));
            return btoa(binary);
        } finally { clearTimeout(timer); }
    }""", {"url": url, "limit": MAX_ATTACHMENT_BYTES})
    data = base64.b64decode(value, validate=True)
    if len(data) > MAX_ATTACHMENT_BYTES or not data.startswith(b"%PDF-"):
        raise PortalInspectionError("portal_attachment_not_pdf")
    return data


def _inspect(repo_root: Path, outdir: Path, module_id: int, course_id: int, related_modules: tuple[int, ...]) -> dict:
    from playwright.sync_api import sync_playwright

    credentials = _get_credentials(repo_root)
    args, resolver = _browser_resolver_args()
    modules = list(dict.fromkeys((module_id, *related_modules)))
    summary = {"schema_version": 1, "operation": "inspect_activity", "read_only": True,
               "model_invoked": False, "host": HOST, "course_id": course_id,
               "module_id": module_id, "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
               "dns": resolver, "activities": [], "attachments": []}
    outdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=args)
        try:
            context = browser.new_context(accept_downloads=False, service_workers="block")
            context.set_default_timeout(30000)
            context.set_default_navigation_timeout(60000)

            def limit_origin(route):
                try:
                    _same_host_url(route.request.url)
                except PortalInspectionError:
                    route.abort()
                    return
                route.continue_()

            context.route("**/*", limit_origin)
            page = context.new_page()
            page.goto(f"{BASE_URL}/login/index.php", wait_until="domcontentloaded")
            page.locator("#username").fill(credentials["username"])
            page.locator("#password").fill(credentials["password"])
            page.locator("#loginbtn").click()
            page.wait_for_load_state("domcontentloaded")
            _same_host_url(page.url)
            if "/login/" in urlsplit(page.url).path:
                raise PortalInspectionError("portal_authentication_failed")
            names = page.locator(".usermenu .usertext, .usermenu .userfullname, .logininfo a[href*='/user/profile.php']").all_text_contents()
            identities = _identity_variants(credentials["username"], names)
            del credentials
            for current in modules:
                page.goto(f"{BASE_URL}/mod/assign/view.php?id={current}", wait_until="domcontentloaded")
                _same_host_url(page.url)
                if "/login/" in urlsplit(page.url).path:
                    raise PortalInspectionError("portal_session_expired")
                course_links = page.locator("a[href*='/course/view.php']").evaluate_all("els => els.map(e=>e.href)")
                if not any(_normalized_link(link) == f"{BASE_URL}/course/view.php?id={course_id}" for link in course_links):
                    raise PortalInspectionError("portal_course_not_verified")
                main = page.locator("#region-main")
                main.wait_for(state="visible")
                content = _sanitize(main.inner_text(), identities)
                full_feedback = main.locator('[class*="full_assignfeedback_comments_"]')
                feedback_text = "\n\n".join(
                    _sanitize(block.text_content() or "", identities).strip()
                    for block in full_feedback.all()
                ).strip()
                if feedback_text:
                    content += "\n\nRetroalimentación docente completa\n" + feedback_text
                    (outdir / f"{current}-retroalimentacion-completa.txt").write_text(feedback_text, encoding="utf-8")
                intro = page.locator("#intro")
                instructions = _sanitize(intro.inner_text(), identities) if intro.count() else content
                observed = main.locator("a[href]").evaluate_all("els => els.map(e=>({text:e.innerText,url:e.href}))")
                links = []
                for link in observed:
                    normalized = _normalized_link(link["url"])
                    if normalized and not any(x["url"] == normalized for x in links):
                        links.append({"text": _sanitize(link["text"], identities), "url": normalized})
                text_path = outdir / f"{current}-consigna-estado.txt"
                text_path.write_text(content, encoding="utf-8")
                (outdir / f"{current}-intro.txt").write_text(instructions, encoding="utf-8")
                (outdir / f"{current}-links.json").write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
                entry = {"module_id": current, "url": f"{BASE_URL}/mod/assign/view.php?id={current}",
                         "instructions": instructions, "state_and_feedback": content,
                         "links": links, "evidence_path": str(text_path.resolve()),
                         "sha256": hashlib.sha256(text_path.read_bytes()).hexdigest()}
                summary["activities"].append(entry)
                if current == module_id:
                    for link in links:
                        label = _fold(unquote(link["text"] + " " + link["url"]))
                        if "/introattachment/" not in link["url"] or not re.search(r"3[._\s-]*3\b", label) or "objetivo" not in label:
                            continue
                        data = _download_pdf(page, link["url"])
                        destination = outdir / "3.3-Formulacion-de-objetivos.pdf"
                        destination.write_bytes(data)
                        summary["attachments"].append({"kind": "teaching_material_3.3", "url": link["url"],
                            "path": str(destination.resolve()), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
                        break
        finally:
            browser.close()
    summary["teaching_material_3_3_downloaded"] = bool(summary["attachments"])
    (outdir / "inspection.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def inspect_activity(repo_root: str | Path, outdir: str | Path, module_id: int = 2910,
                     course_id: int = 215, related_modules: tuple[int, ...] = (2909, 2908)) -> dict:
    """Inspect authenticated instructions, rubric, dates and previous feedback.

    PIN is read only from AULATEX_MASTER_PIN. TLS verification stays enabled.
    Resolver fallback maps the one allowed hostname in this Chromium process only.
    Outdir stores sanitized evidence, plus the observed teaching PDF if available.
    Raises PortalInspectionError with safe codes, never raw Playwright exceptions.
    """
    from .agentic_patterns import safe_invoke

    module_id, course_id = _positive_id(module_id), _positive_id(course_id)
    related_modules = tuple(_positive_id(value) for value in related_modules)
    root = Path(repo_root).resolve()
    output = Path(outdir).resolve()

    def guarded_inspection():
        try:
            return _inspect(root, output, module_id, course_id, related_modules)
        except PortalInspectionError:
            raise
        except Exception:
            raise PortalInspectionError("portal_inspection_failed") from None

    result = safe_invoke(guarded_inspection)
    if not result.ok:
        # The guard guarantees that safe_invoke only sees a fixed public code.
        code = result.error.split(": ", 1)[-1]
        raise PortalInspectionError(code) from None
    return result.result


__all__ = ["inspect_activity", "PortalInspectionError"]
