"""Contrato base del tipo de agente ``navegación-plataforma`` en AulaTeX.

Proporciona las primitivas comunes de autenticación con la bóveda cifrada de
AulaTeX (``PlatformCredentialVault``), confinamiento de origen HTTPS,
normalización de enlaces sin tokens ni acciones mutantes y sanitización
estricta para garantizar que ninguna credencial, PIN, cookie o token se
escriba jamás en artefactos generados ni registros.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import ssl
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .llm_setup import load_aulatex_env
from .node_planning import _reject_credentials
from .platform_credentials import PlatformCredentialVault, default_vault_path

AGENT_TYPE_NAVEGACION_PLATAFORMA = "navegación-plataforma"
MAX_PLATFORM_DOWNLOAD_BYTES = 25 * 1024 * 1024

_FORBIDDEN_PATH_TOKENS = (
    "/login/logout.php",
    "/mod/quiz/startattempt.php",
    "/mod/quiz/processattempt.php",
    "/mod/assign/As",
    "/admin/",
    "/user/edit",
)
_FORBIDDEN_QUERY_ACTIONS = frozenset(
    {
        "editsubmission",
        "removesubmission",
        "submit",
        "confirm",
        "delete",
        "grading",
    }
)
_ALLOWED_QUERY_KEYS = frozenset({"id", "section", "forcedownload"})

_SECRET_KV_RE = re.compile(
    r"(?i)\b(?:sesskey|token|wstoken|password|passwd|secret|apikey|api_key|logintoken|"
    r"username|aulatex_master_pin|moodle_session|moodlesession|authorization|cookie)\s*[=:]\s*[^\s&\"',;]+"
)


class PlatformNavigationError(RuntimeError):
    """Error seguro de navegación en plataforma; nunca contiene secretos ni trazas crudas."""


class PlatformCredentialBlockedError(PlatformNavigationError):
    """Bloqueo explícito cuando faltan bóveda, PIN maestro o cuenta institucional."""


@dataclass(frozen=True)
class PlatformSessionSpec:
    institution: str
    platform: str
    host: str
    base_url: str
    login_url: str


def fold_text(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(ch)
    ).casefold()


def build_identity_variants(username: str, full_names: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    variants: list[str] = []
    if username and len(username.strip()) >= 4:
        variants.append(username.strip())
    for raw_name in full_names:
        clean = " ".join((raw_name or "").split()).strip()
        if len(clean) < 5:
            continue
        variants.append(clean)
        words = clean.split()
        if len(words) > 2:
            variants.append(" ".join(words[:2]))
        if len(words) >= 4:
            for size in (2, 3, 4):
                variants.append("".join(words[-size:]))
    return tuple(dict.fromkeys(variants))


def sanitize_platform_text(text: str, identities: tuple[str, ...] = ()) -> str:
    """Elimina identidades de sesión, matrículas y parámetros sensibles del texto extraído."""
    result = str(text or "")
    for value in sorted({v.strip() for v in identities if v and len(v.strip()) >= 4}, key=len, reverse=True):
        folded_value = fold_text(value)
        if not folded_value:
            continue
        for match in reversed(list(re.finditer(re.escape(folded_value), fold_text(result)))):
            result = result[: match.start()] + "[estudiante]" + result[match.end() :]
    result = _SECRET_KV_RE.sub("[dato omitido]", result)
    result = re.sub(r"(?i)[?&](?:sesskey|access_token|token|api_key)=[^&\s\"'<>]*", "?[parametro_omitido]", result)
    result = re.sub(r"(?i)\b(?:sesskey|access_token|token|api_key)\s*=\s*['\"]?[^&\s\"'<>;)]*", "[parametro_omitido]", result)
    result = re.sub(r"(?i)(matr[ií]cula\s*[:#]?\s*)[A-Z0-9-]+", r"\1[omitida]", result)
    return result


def assert_no_credential_leak(payload: Any, forbidden_literals: tuple[str, ...] = ()) -> None:
    """Verifica recursivamente que un objeto serializable no contenga secretos ni credenciales."""
    _reject_credentials(payload)
    serialized = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    if _SECRET_KV_RE.search(serialized):
        raise PlatformNavigationError("credential_pattern_detected_in_output")
    for secret in forbidden_literals:
        candidate = (secret or "").strip()
        if len(candidate) >= 4 and candidate in serialized:
            raise PlatformNavigationError("secret_literal_detected_in_output")


def ensure_same_https_host(url: str, host: str, base_url: str | None = None) -> str:
    resolved_base = base_url or f"https://{host}"
    candidate = urljoin(resolved_base, url or "")
    try:
        parsed = urlsplit(candidate)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname == host
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and not any(ch.isspace() for ch in candidate)
        )
    except ValueError:
        valid = False
    if not valid:
        raise PlatformNavigationError("platform_url_outside_allowed_origin")
    return candidate


def normalize_readonly_link(
    url: str,
    host: str,
    allowed_mod_paths: tuple[str, ...] = (
        "/course/view.php",
        "/mod/assign/view.php",
        "/mod/quiz/view.php",
        "/mod/resource/view.php",
        "/mod/folder/view.php",
        "/mod/forum/view.php",
        "/mod/url/view.php",
        "/mod/page/view.php",
    ),
) -> str | None:
    """Normaliza enlaces académicos de solo lectura, suprimiendo sesskey y rutas mutantes."""
    try:
        safe = ensure_same_https_host(url, host)
    except PlatformNavigationError:
        return None
    parsed = urlsplit(safe)
    lowered_path = parsed.path.lower()
    if any(tok.lower() in lowered_path for tok in _FORBIDDEN_PATH_TOKENS):
        return None
    raw_query = parse_qsl(parsed.query, keep_blank_values=False)
    for key, val in raw_query:
        if key.lower() == "action" and val.lower() in _FORBIDDEN_QUERY_ACTIONS:
            return None
    if parsed.path in allowed_mod_paths:
        filtered = [
            (k, v)
            for k, v in raw_query
            if k in _ALLOWED_QUERY_KEYS and v.isdigit()
        ]
        if not any(k == "id" for k, _ in filtered):
            return None
        return urlunsplit(("https", host, parsed.path, urlencode(filtered), ""))
    if parsed.path.startswith("/pluginfile.php/"):
        filtered = [(k, v) for k, v in raw_query if k == "forcedownload" and v in ("0", "1")]
        return urlunsplit(("https", host, parsed.path, urlencode(filtered), ""))
    return None


def resolve_doh_host_args(host: str) -> tuple[list[str], str]:
    """Resuelve DNS del host institucional y aplica DoH temporal solo si falla el DNS local."""
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return [], "system"
    except socket.gaierror:
        pass
    query = urlencode({"name": host, "type": "A"})
    for endpoint in ("https://cloudflare-dns.com/dns-query", "https://1.1.1.1/dns-query"):
        try:
            req = Request(f"{endpoint}?{query}", headers={"Accept": "application/dns-json"})
            with urlopen(req, timeout=12, context=ssl.create_default_context()) as resp:
                if urlsplit(resp.url).hostname not in ("cloudflare-dns.com", "1.1.1.1"):
                    continue
                raw = resp.read(65537)
            if len(raw) > 65536:
                continue
            payload = json.loads(raw)
            if payload.get("Status") != 0:
                continue
            for answer in payload.get("Answer", []):
                if answer.get("type") != 1:
                    continue
                ip = ipaddress.ip_address(answer.get("data", ""))
                if ip.version == 4 and ip.is_global:
                    return [f"--host-resolver-rules=MAP {host} {ip}"], "cloudflare_doh_temporary_map"
        except Exception:
            continue
    raise PlatformNavigationError("platform_dns_resolution_failed")


def load_vault_account(repo_root: Path, institution: str, expected_host: str) -> dict[str, str]:
    """Obtiene en memoria la credencial de ``PlatformCredentialVault`` sin exponerla en logs."""
    load_aulatex_env()
    pin = next(
        (value for key, value in os.environ.items() if key.casefold() == "aulatex_master_pin" and value.strip()),
        None,
    )
    if not pin:
        raise PlatformCredentialBlockedError("platform_master_pin_missing")
    vault_path = default_vault_path(repo_root)
    if not vault_path.is_file():
        raise PlatformCredentialBlockedError("platform_vault_missing")
    try:
        vault = PlatformCredentialVault(vault_path)
        accounts = [
            acc
            for acc in vault.list_accounts(pin)
            if acc.get("institution", "").casefold() == institution.casefold()
            and urlsplit(acc.get("url", "")).hostname == expected_host
        ]
        if not accounts:
            raise PlatformCredentialBlockedError(f"platform_account_not_found:{institution}")
        if len(accounts) > 1:
            raise PlatformCredentialBlockedError(f"platform_account_ambiguous:{institution}")
        record = vault.get_credentials(pin, accounts[0]["id"])
        ensure_same_https_host(record["url"], expected_host)
        return record
    except PlatformNavigationError:
        raise
    except Exception:
        raise PlatformCredentialBlockedError("platform_vault_unlock_failed") from None


class PlatformNavigationAgent(ABC):
    """Clase base para agentes especializados del tipo ``navegación-plataforma``."""

    agent_type: str = AGENT_TYPE_NAVEGACION_PLATAFORMA

    def __init__(self, repo_root: str | Path, spec: PlatformSessionSpec) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.spec = spec

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identificador canónico del agente especializado."""

    @abstractmethod
    def inspect(self, *args: Any, **kwargs: Any) -> Any:
        """Ejecuta inspección autenticada de solo lectura y devuelve evidencia sanitizada."""


__all__ = [
    "AGENT_TYPE_NAVEGACION_PLATAFORMA",
    "MAX_PLATFORM_DOWNLOAD_BYTES",
    "PlatformCredentialBlockedError",
    "PlatformNavigationAgent",
    "PlatformNavigationError",
    "PlatformSessionSpec",
    "assert_no_credential_leak",
    "build_identity_variants",
    "ensure_same_https_host",
    "fold_text",
    "load_vault_account",
    "normalize_readonly_link",
    "resolve_doh_host_args",
    "sanitize_platform_text",
]
