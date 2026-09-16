"""Local platform vault. No environment loading, networking, or LLM integration."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
import uuid

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


ITERATIONS = 600_000
MAX_BYTES = 4 * 1024 * 1024


class VaultError(Exception):
    """Safe, user-facing error; never includes credentials or raw exceptions."""


def default_vault_path(repo_root: Path) -> Path:
    """User-local storage separated by workspace, outside editorial indexing."""
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    workspace_id = hashlib.sha256(os.path.normcase(str(repo_root.resolve())).encode()).hexdigest()[:24]
    return root / "AulaTeX" / workspace_id / "platform-credentials.vault.json"


def _cipher(pin: str, salt: bytes) -> Fernet:
    if not isinstance(pin, str) or not pin.strip():
        raise VaultError("Introduce AULATEX_MASTER_PIN; no se usará una clave alternativa.")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(pin.encode("utf-8"))))


def _text(value: str, label: str, *, required: bool = True) -> str:
    if not isinstance(value, str) or len(value) > 4096 or (required and not value.strip()):
        raise VaultError(f"Revisa el campo {label}.")
    return value


def _validate_record(record: dict) -> None:
    for key in ("id", "institution", "platform", "url", "username", "password"):
        _text(record.get(key), key)
    try:
        url = urlsplit(record["url"])
        if (url.scheme != "https" or not url.hostname or url.username is not None
                or url.password is not None or any(c.isspace() for c in record["url"])):
            raise ValueError
        _ = url.port
    except ValueError:
        raise VaultError("El sitio debe ser una URL HTTPS sin credenciales incrustadas.") from None


class PlatformCredentialVault:
    """Stateless access: every operation requires the PIN; no secret cache."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _read(self, pin: str) -> tuple[list[dict], bytes, Fernet]:
        if not isinstance(pin, str) or not pin.strip():
            raise VaultError("Introduce AULATEX_MASTER_PIN; no se usará una clave alternativa.")
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
        except FileNotFoundError:
            salt = os.urandom(16)
            return [], salt, _cipher(pin, salt)
        except OSError:
            raise VaultError("No se pudo leer la bóveda local.") from None
        try:
            if len(raw) > MAX_BYTES:
                raise ValueError
            envelope = json.loads(raw)
            if (envelope["version"] != 1 or envelope["kdf"] != "pbkdf2-sha256"
                    or envelope["iterations"] != ITERATIONS):
                raise ValueError
            salt = base64.b64decode(envelope["salt"], validate=True)
            if len(salt) != 16:
                raise ValueError
            cipher = _cipher(pin, salt)
            records = json.loads(cipher.decrypt(envelope["token"].encode("ascii")))
            if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
                raise ValueError
            ids = set()
            for record in records:
                _validate_record(record)
                if record["id"] in ids:
                    raise ValueError
                ids.add(record["id"])
            return records, salt, cipher
        except (ValueError, KeyError, TypeError, AttributeError, InvalidToken, VaultError):
            raise VaultError("PIN incorrecto o bóveda dañada/incompatible. No se modificó el archivo.") from None

    @contextmanager
    def _writer(self):
        """Serialize cooperating writers, fail closed on a stale lock."""
        lock = self.path.with_name(self.path.name + ".lock")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise VaultError("Bóveda ocupada. Cierra otras operaciones e inténtalo de nuevo.") from None
        except OSError:
            raise VaultError("No se pudo bloquear la bóveda para escritura.") from None
        try:
            os.close(fd)
            yield
        finally:
            lock.unlink(missing_ok=True)

    def _write(self, records: list[dict], salt: bytes, cipher: Fernet) -> None:
        # Encryption happens BEFORE creating a temporary file. No plaintext backup.
        token = cipher.encrypt(json.dumps(records, ensure_ascii=False).encode()).decode("ascii")
        encoded = json.dumps({
            "version": 1, "kdf": "pbkdf2-sha256", "iterations": ITERATIONS,
            "salt": base64.b64encode(salt).decode("ascii"), "token": token,
        }).encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise VaultError("La bóveda supera el tamaño máximo permitido.")
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent)
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise VaultError("No se pudo guardar la bóveda; se conserva la versión anterior.") from None
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def list_accounts(self, pin: str) -> list[dict[str, str]]:
        records, _, _ = self._read(pin)
        return [{key: record[key] for key in ("id", "institution", "platform", "url")} for record in records]

    def get_credentials(self, pin: str, account_id: str) -> dict[str, str]:
        """Explicit local consumption only. Callers must not log the result."""
        records, _, _ = self._read(pin)
        for record in records:
            if record["id"] == account_id:
                return dict(record)
        raise VaultError("La cuenta seleccionada ya no existe.")

    def save(self, pin: str, *, institution: str, platform: str, url: str,
             username: str, password: str, account_id: str | None = None) -> str:
        with self._writer():
            records, salt, cipher = self._read(pin)
            old = next((r for r in records if r["id"] == account_id), None)
            if account_id is not None and old is None:
                raise VaultError("La cuenta seleccionada ya no existe. Recarga la lista.")
            record = {
                "id": old["id"] if old else uuid.uuid4().hex,
                "institution": institution.strip(), "platform": platform.strip(), "url": url.strip(),
                "username": username if username or old is None else old["username"],
                "password": password if password or old is None else old["password"],
            }
            _validate_record(record)
            if any(r["id"] != record["id"] and
                   (r["institution"].casefold(), r["platform"].casefold(), r["url"], r["username"]) ==
                   (record["institution"].casefold(), record["platform"].casefold(), record["url"], record["username"])
                   for r in records):
                raise VaultError("Esta cuenta ya existe; selecciónala para editarla.")
            records = [record if r["id"] == record["id"] else r for r in records]
            if old is None:
                records.append(record)
            self._write(records, salt, cipher)
            return record["id"]

    def delete(self, pin: str, account_id: str) -> None:
        with self._writer():
            records, salt, cipher = self._read(pin)
            remaining = [r for r in records if r["id"] != account_id]
            if len(records) == len(remaining):
                raise VaultError("La cuenta seleccionada ya no existe.")
            self._write(remaining, salt, cipher)

    def rotate_pin(self, old_pin: str, new_pin: str) -> None:
        with self._writer():
            records, _, _ = self._read(old_pin)
            salt = os.urandom(16)
            self._write(records, salt, _cipher(new_pin, salt))