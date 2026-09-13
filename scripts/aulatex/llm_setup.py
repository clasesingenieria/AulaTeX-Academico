"""Validación y reparación interactiva de model-router, compatible con SSH."""
from __future__ import annotations

import getpass
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit
import warnings

from .config import ENC_PREFIX, MODEL_ROUTER_ENGINE, _secrets_module, _strip_env_value, load_aulatex_env
from .llm_bridge import AulaTeXLLMConfig, validate_llm_response


class ConfigurationError(Exception):
    """Error seguro para mostrar al operador (nunca contiene credenciales)."""


def _read_secret(prompt: str) -> str:
    # getpass puede recurrir a stdin con eco si /dev/tty no está disponible.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            value = getpass.getpass(prompt).strip()
        except getpass.GetPassWarning:
            raise ConfigurationError("No hay una terminal con entrada oculta; operación cancelada.") from None
    if not value or any(char in value for char in "\r\n\x00"):
        raise ConfigurationError("El secreto no puede estar vacío ni contener saltos de línea.")
    return value


def _env_entry(line: str) -> tuple[str, str]:
    text = line.strip()
    if text.lower().startswith("export "):
        text = text[7:].strip()
    if not text or text.startswith("#") or "=" not in text:
        return "", ""
    name, _, value = text.partition("=")
    return name.strip(), _strip_env_value(value)


def normalize_router_endpoint(endpoint: str, deployment: str) -> str:
    """Acepta la raíz Azure, /openai/v1 o una URL completa de inferencia."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", deployment):
        raise ConfigurationError("Deployment inválido: usa letras, números, puntos, guiones o guiones bajos.")
    try:
        parsed = urlsplit(endpoint.strip())
        port = parsed.port
        if (
            parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or port == 0
            or any(char.isspace() or ord(char) < 32 for char in endpoint)
        ):
            raise ValueError
        query = parse_qs(parsed.query, keep_blank_values=True)
        if any(name != "api-version" for name in query):
            raise ValueError
    except ValueError:
        raise ConfigurationError("Usa un endpoint HTTPS válido, sin claves, usuario, contraseña ni fragmentos en la URL.") from None
    path = parsed.path.rstrip("/")
    if not path:
        path = "/openai/v1/chat/completions"
    elif path in ("/openai/v1", "/v1"):
        path += "/chat/completions"
    elif not (path.endswith("/chat/completions") or path.endswith("/responses")):
        raise ConfigurationError("El endpoint debe ser la raíz del recurso, /openai/v1, /v1 o una URL de inferencia completa.")
    # En endpoints Azure antiguos el deployment también forma parte de la URL.
    # Al editarlo, no debe seguir usándose por accidente el deployment anterior.
    path = re.sub(r"(/openai/deployments/)[^/]+(?=/)", lambda match: match[1] + quote(deployment, safe=""), path)
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


def _read_candidate() -> AulaTeXLLMConfig:
    endpoint = input("Endpoint HTTPS: ").strip()
    deployment = input("Deployment [model-router]: ").strip() or "model-router"
    endpoint = normalize_router_endpoint(endpoint, deployment)
    api_key = _read_secret("API key (entrada oculta): ")
    if api_key.startswith(ENC_PREFIX):
        raise ConfigurationError("Introduce la API key original del proveedor, no el valor enc: almacenado.")
    return AulaTeXLLMConfig(
        engine_label=MODEL_ROUTER_ENGINE, base_url=endpoint,
        api_key=api_key, deployment=deployment,
    )


def _save_candidate(candidate: AulaTeXLLMConfig, path: Path) -> None:
    """Cifra antes de escribir y reemplaza el .env atómicamente con modo 0600."""
    mod = _secrets_module()
    if mod is None:
        raise ConfigurationError("Falta el módulo de cifrado; instala las dependencias LLM del proyecto.")
    original = path.read_bytes() if path.exists() else None
    lines = original.decode("utf-8").splitlines() if original is not None else []
    # La clave que se reemplaza puede estar dañada. Solo hay que garantizar
    # que los secretos conservados siguen siendo accesibles con la misma clave.
    encrypted = [
        value for name, value in map(_env_entry, lines)
        if name != "MODEL_ROUTER_API_KEY" and value.startswith(ENC_PREFIX)
    ]

    def unlocks_all(fernet) -> bool:
        if fernet is None:
            return False
        try:
            for value in encrypted:
                fernet.decrypt(value[len(ENC_PREFIX):].encode("ascii"))
        except Exception:
            return False
        return True

    try:
        fernet = mod.resolve_fernet(create=False)
    except Exception:
        fernet = None
    if not unlocks_all(fernet):
        pin = _read_secret("PIN maestro para guardar la API key cifrada: ")
        # Nunca crear otro salt cuando ya hay secretos cifrados.
        fernet = mod.fernet_from_pin(pin, create_salt=not encrypted)
        if not unlocks_all(fernet):
            raise ConfigurationError("El PIN no descifra los secretos existentes o falta su salt. No se guardó ningún cambio.")
        os.environ["AULATEX_MASTER_PIN"] = pin

    values = {
        "MODEL_ROUTER_BASE_URL": candidate.base_url,
        "MODEL_ROUTER_CHAT_DEPLOYMENT": candidate.deployment,
        "MODEL_ROUTER_API_KEY": ENC_PREFIX + fernet.encrypt(candidate.api_key.encode("utf-8")).decode("ascii"),
        "AULATEX_LLM_VALIDATION_ENABLED": "1",
        "AULATEX_LLM_ENGINE": MODEL_ROUTER_ENGINE,
        "AULATEX_LLM_REVIEW_ENGINE": MODEL_ROUTER_ENGINE,
        "TB_BOOKS_LLM_REVIEW_ENGINE": MODEL_ROUTER_ENGINE,
        "AULATEX_LLM_PROVIDER": "model-router",
        "LLM_PROVIDER": "model-router",
    }
    updated = []
    written = set()
    for line in lines:
        name, _ = _env_entry(line)
        if name in values:
            if name not in written:
                updated.append(f"{name}={values[name]}")
                written.add(name)
        else:
            updated.append(line)
    updated.extend(f"{name}={value}" for name, value in values.items() if name not in written)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            stream.write("\n".join(updated) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        current = path.read_bytes() if path.exists() else None
        if current != original:
            raise ConfigurationError("La configuración cambió durante la edición. No se sobrescribieron esos cambios; vuelve a intentarlo.")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    load_aulatex_env(path)


def configure_model_router(*, timeout_seconds: int = 45, max_tokens: int = 32, non_interactive: bool = False) -> dict:
    """Valida primero; ofrece PIN, corrección, reintento o cancelación si falla."""
    inherited_pin = bool(os.getenv("AULATEX_MASTER_PIN"))
    path = load_aulatex_env().path
    options = {"timeout_seconds": timeout_seconds, "max_tokens": max_tokens}
    result = validate_llm_response(MODEL_ROUTER_ENGINE, **options)
    if result["ok"] or non_interactive or not (sys.stdin.isatty() and sys.stdout.isatty()):
        return result
    while not result["ok"]:
        print(f"model-router no validado: {result['error']}")
        print("1. Introducir endpoint, API key y deployment")
        print("2. Introducir/reintentar el PIN de las credenciales actuales")
        print("3. Revalidar la configuración actual")
        print("0. Cancelar sin guardar cambios")
        try:
            choice = input("Selecciona una opción: ").strip()
            if choice == "0":
                result.update(ok=False, error="Configuración cancelada; no se guardaron cambios.")
                return result
            if choice == "1":
                candidate = _read_candidate()
                result = validate_llm_response(MODEL_ROUTER_ENGINE, config=candidate, **options)
                if result["ok"]:
                    _save_candidate(candidate, path)
                    result["configured"] = True
                    print("model-router validado. Configuración guardada con API key cifrada.")
            elif choice in ("2", "3"):
                if choice == "2":
                    os.environ["AULATEX_MASTER_PIN"] = _read_secret("PIN maestro (entrada oculta): ")
                result = validate_llm_response(MODEL_ROUTER_ENGINE, **options)
            else:
                print("Selecciona 0, 1, 2 o 3.")
        except ConfigurationError as exc:
            result.update(ok=False, error=str(exc))
        except (EOFError, KeyboardInterrupt):
            print()
            result.update(ok=False, error="Configuración cancelada; no se guardaron cambios.")
            return result
        except Exception:
            result.update(ok=False, error="No se pudo guardar la configuración de forma segura.")
    if not inherited_pin and os.getenv("AULATEX_MASTER_PIN"):
        print("El PIN introducido solo vive en este proceso; exporta AULATEX_MASTER_PIN en Bash para otras ejecuciones.")
    return result