"""Cifrado local y autónomo de secretos para AulaTeX-Académico.

Gestiona sus propias credenciales de forma INDEPENDIENTE de otros repos, con
una clave Fernet propia (``secret.key``) junto al ``.env`` correspondiente.
La aplicación accede a sus claves por sí misma sin depender de otro proyecto.

Comandos:
    python secrets_local.py init-key                 # genera secret.key local
    python secrets_local.py encrypt aulatex.env      # cifra los secretos del .env
    python secrets_local.py decrypt-env aulatex.env  # imprime NAME<TAB>plano (PowerShell)
    python secrets_local.py hydrate aulatex.env      # descifra en os.environ (Python)
    python secrets_local.py set-value aulatex.env NOMBRE  # cifra un valor leído de stdin
    python secrets_local.py rotate-pin aulatex.env   # recifra con un PIN nuevo (stdin)

Resolución de la clave:
    1. Variable de entorno ``AULATEX_MASTER_PIN`` (PIN maestro; deriva la clave
       Fernet con PBKDF2-SHA256 sobre ``secret.salt``).
    2. Variable de entorno ``AULATEX_SECRET_KEY`` (clave Fernet directa).
    3. Archivo ``secret.key`` junto a este script (modo heredado).
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = Path(__file__).resolve().parent
SECRET_KEY_PATH = HERE / "secret.key"
SECRET_SALT_PATH = HERE / "secret.salt"
ENC_PREFIX = "enc:"
PIN_ENV_VAR = "AULATEX_MASTER_PIN"
PBKDF2_ITERATIONS = 480_000

# Claves que se consideran secretas (se cifran). El resto queda en claro.
_SECRET_HINTS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "_KEY", "ACCESS_KEY_ID")

# Nombres que contienen una pista de secreto pero NO lo son (limites, flags...).
_SECRET_EXCLUDES = ("MAX_TOKENS", "TOKENS_LIMIT", "TOKEN_LIMIT", "KEY_VAULT_NAME")


def _is_secret_name(name: str) -> bool:
    up = name.upper()
    if any(x in up for x in _SECRET_EXCLUDES):
        return False
    return any(h in up for h in _SECRET_HINTS)


def _restrict_permissions(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _resolve_salt(create: bool = False) -> bytes | None:
    """Devuelve el salt estable usado para derivar la clave desde el PIN."""
    if SECRET_SALT_PATH.exists():
        return SECRET_SALT_PATH.read_bytes().strip()
    if create:
        salt = base64.urlsafe_b64encode(os.urandom(16))
        SECRET_SALT_PATH.write_bytes(salt)
        _restrict_permissions(SECRET_SALT_PATH)
        return salt
    return None


def _fernet_from_pin_and_salt(pin: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return Fernet(base64.urlsafe_b64encode(kdf.derive(pin.encode("utf-8"))))


def fernet_from_pin(pin: str, create_salt: bool = False) -> Fernet | None:
    salt = _resolve_salt(create=create_salt)
    if salt is None:
        return None
    return _fernet_from_pin_and_salt(pin, salt)


def resolve_fernet(create: bool = False) -> Fernet | None:
    pin = os.getenv(PIN_ENV_VAR, "").strip()
    if pin:
        fernet = fernet_from_pin(pin, create_salt=create)
        if fernet is not None:
            return fernet
    env_key = os.getenv("AULATEX_SECRET_KEY", "").strip()
    if env_key:
        return Fernet(env_key.encode("utf-8"))
    if SECRET_KEY_PATH.exists():
        return Fernet(SECRET_KEY_PATH.read_bytes().strip())
    if create:
        key = Fernet.generate_key()
        SECRET_KEY_PATH.write_bytes(key)
        _restrict_permissions(SECRET_KEY_PATH)
        return Fernet(key)
    return None


def _parse_line(line: str):
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None, None
    name, _, value = stripped.partition("=")
    name = name.strip()
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return name, value


def cmd_init_key() -> int:
    if SECRET_KEY_PATH.exists():
        print(f"Ya existe: {SECRET_KEY_PATH}")
        return 0
    resolve_fernet(create=True)
    print(f"Clave local generada: {SECRET_KEY_PATH}")
    print("IMPORTANTE: añade 'secret.key' a .gitignore; NO la subas al repo.")
    return 0


def cmd_encrypt(env_file: str) -> int:
    path = HERE / env_file if not Path(env_file).is_absolute() else Path(env_file)
    if not path.exists():
        print(f"No existe: {path}")
        return 1
    f = resolve_fernet(create=True)
    if f is None:
        print("No hay clave disponible.")
        return 1

    out_lines: list[str] = []
    cifrados = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        name, value = _parse_line(line)
        if name and value and _is_secret_name(name) and not value.startswith(ENC_PREFIX):
            token = f.encrypt(value.encode("utf-8")).decode("ascii")
            out_lines.append(f"{name}={ENC_PREFIX}{token}")
            cifrados += 1
        else:
            out_lines.append(line)
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Cifrados {cifrados} secretos en {path.name}")
    return 0


def cmd_decrypt_env(env_file: str) -> int:
    path = HERE / env_file if not Path(env_file).is_absolute() else Path(env_file)
    f = resolve_fernet(create=False)
    if f is None or not path.exists():
        return 0
    for line in path.read_text(encoding="utf-8").splitlines():
        name, value = _parse_line(line)
        if name and value and value.startswith(ENC_PREFIX):
            try:
                plain = f.decrypt(value[len(ENC_PREFIX):].encode("ascii")).decode("utf-8")
            except InvalidToken:
                continue
            sys.stdout.write(f"{name}\t{plain}\n")
    return 0


def cmd_set_value(env_file: str, name: str) -> int:
    """Cifra un valor leído de stdin y lo guarda sin exponerlo en argv."""
    path = HERE / env_file if not Path(env_file).is_absolute() else Path(env_file)
    f = resolve_fernet(create=True)
    if f is None:
        print("No hay clave disponible: define AULATEX_MASTER_PIN.", file=sys.stderr)
        return 1

    plain = sys.stdin.read().lstrip("\ufeff").strip()
    if not plain:
        print("No se recibió ningún valor por stdin.", file=sys.stderr)
        return 1

    token = ENC_PREFIX + f.encrypt(plain.encode("utf-8")).decode("ascii")
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out_lines: list[str] = []
    replaced = False
    for line in lines:
        existing, _ = _parse_line(line)
        if existing == name:
            out_lines.append(f"{name}={token}")
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        out_lines.append(f"{name}={token}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"{name} cifrado en {path.name}")
    return 0


def cmd_rotate_pin(env_file: str) -> int:
    """Recifra todos los valores ``enc:`` usando dos PIN leídos de stdin."""
    path = HERE / env_file if not Path(env_file).is_absolute() else Path(env_file)
    if not path.exists():
        print(f"No existe: {path}", file=sys.stderr)
        return 1

    payload = sys.stdin.read().lstrip("\ufeff").splitlines()
    if len(payload) < 2:
        print("Se esperaban dos líneas por stdin: PIN actual y PIN nuevo.", file=sys.stderr)
        return 1
    old_pin, new_pin = payload[0].strip(), payload[1].strip()
    if not old_pin or not new_pin:
        print("Ningún PIN puede quedar vacío.", file=sys.stderr)
        return 1
    if old_pin == new_pin:
        print("El PIN nuevo es igual al actual.", file=sys.stderr)
        return 1

    old_salt = _resolve_salt(create=False)
    if old_salt is None:
        print(f"No existe {SECRET_SALT_PATH.name}: no hay nada que rotar.", file=sys.stderr)
        return 1
    old_f = _fernet_from_pin_and_salt(old_pin, old_salt)
    lines = path.read_text(encoding="utf-8").splitlines()
    plain_by_index: dict[int, str] = {}
    for index, line in enumerate(lines):
        name, value = _parse_line(line)
        if not (name and value and value.startswith(ENC_PREFIX)):
            continue
        try:
            plain_by_index[index] = old_f.decrypt(
                value[len(ENC_PREFIX):].encode("ascii")
            ).decode("utf-8")
        except InvalidToken:
            print(f"PIN actual incorrecto: no se pudo descifrar {name}.", file=sys.stderr)
            return 1

    if not plain_by_index:
        print("No hay valores enc: que rotar.", file=sys.stderr)
        return 1

    backup = path.with_suffix(path.suffix + ".bak-rotate")
    backup.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _restrict_permissions(backup)

    new_salt = base64.urlsafe_b64encode(os.urandom(16))
    new_f = _fernet_from_pin_and_salt(new_pin, new_salt)
    for index, plain in plain_by_index.items():
        name, _ = _parse_line(lines[index])
        token = new_f.encrypt(plain.encode("utf-8")).decode("ascii")
        lines[index] = f"{name}={ENC_PREFIX}{token}"

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    SECRET_SALT_PATH.write_bytes(new_salt)
    _restrict_permissions(SECRET_SALT_PATH)
    print(f"Recifrados {len(plain_by_index)} secretos en {path.name}")
    print(f"Salt renovado: {SECRET_SALT_PATH.name}")
    print(f"Respaldo previo: {backup.name} (bórralo cuando confirmes el acceso)")
    return 0


def hydrate(env_file: str) -> None:
    """Descifra los valores enc: del .env directamente en os.environ."""
    path = HERE / env_file if not Path(env_file).is_absolute() else Path(env_file)
    f = resolve_fernet(create=False)
    if f is None or not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        name, value = _parse_line(line)
        if not name:
            continue
        if value.startswith(ENC_PREFIX):
            try:
                value = f.decrypt(value[len(ENC_PREFIX):].encode("ascii")).decode("utf-8")
            except InvalidToken:
                continue
        os.environ[name] = value


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "init-key":
        return cmd_init_key()
    if cmd == "encrypt" and len(sys.argv) >= 3:
        return cmd_encrypt(sys.argv[2])
    if cmd == "decrypt-env" and len(sys.argv) >= 3:
        return cmd_decrypt_env(sys.argv[2])
    if cmd == "set-value" and len(sys.argv) >= 4:
        return cmd_set_value(sys.argv[2], sys.argv[3])
    if cmd == "rotate-pin" and len(sys.argv) >= 3:
        return cmd_rotate_pin(sys.argv[2])
    if cmd == "hydrate" and len(sys.argv) >= 3:
        hydrate(sys.argv[2])
        return 0
    print(f"Comando no reconocido: {cmd}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
