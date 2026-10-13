"""Cifra credenciales AWS dentro de un ``.env`` del hub, con la clave del proyecto.

Complementa ``setup_aws_credentials.ps1``: recibe las llaves por VARIABLES DE
ENTORNO temporales (nunca por argumentos de linea de comandos, que quedarian
visibles en la lista de procesos y en el historial) y las escribe cifradas con
prefijo ``enc:`` usando el mecanismo Fernet de ``ahk-Autohokey``.

Variables de entrada (las define el script de PowerShell y las borra despues):
    AULATEX_TMP_AKID    -> AWS_ACCESS_KEY_ID en claro
    AULATEX_TMP_SECRET  -> AWS_SECRET_ACCESS_KEY en claro

Contexto: la clave anterior del hub se perdio y dejo 108 valores ilegibles. La
clave actual se DERIVA DEL PIN (PBKDF2-SHA256, 600k iteraciones, sal
``ahk-autohotkey/pin/v1``), de modo que es reproducible: si se extravia, se
regenera con el mismo PIN y no se vuelve a perder el acceso.

Seguridad:
  * Hace copia de respaldo del ``.env`` antes de modificarlo.
  * No imprime valores en claro (solo longitudes y estado).
  * Si no hay clave Fernet disponible, aborta sin escribir nada.

Uso (invocado por setup_aws_credentials.ps1):
    python encrypt_aws_into_env.py --env-file <ruta.env> [--region us-east-1]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Ubicacion del hub que contiene el gestor de secretos y la clave Fernet.
DEFAULT_HUB_ROOT = Path(r"C:\ahk-Autohokey")


def load_crypto(hub_root: Path):
    """Importa el modulo de cifrado del hub. Devuelve None si no esta."""
    module_dir = hub_root / "src" / "secrets_manager"
    if not (module_dir / "secrets_crypto.py").exists():
        print(f"[encrypt] ERROR: no encuentro el gestor de secretos en {module_dir}")
        return None
    if str(hub_root) not in sys.path:
        sys.path.insert(0, str(hub_root))
    try:
        from src.secrets_manager import secrets_crypto as sc  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[encrypt] ERROR importando el gestor: {exc.__class__.__name__}: {exc}")
        return None
    return sc


def set_env_value(lines: list[str], key: str, value: str) -> list[str]:
    """Reemplaza (o agrega) ``key=value`` conservando el resto del archivo."""
    prefix = key + "="
    replaced = False
    out: list[str] = []
    for line in lines:
        if line.strip().startswith(prefix) and not replaced:
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="encrypt_aws_into_env",
        description="Cifra las credenciales AWS dentro de un .env del hub.",
    )
    parser.add_argument("--env-file", required=True, help="Ruta del .env a actualizar.")
    parser.add_argument("--region", default="us-east-1", help="Region de AWS (se guarda en claro).")
    parser.add_argument("--hub-root", default=str(DEFAULT_HUB_ROOT),
                        help="Raiz del proyecto que contiene secret.key y el gestor.")
    args = parser.parse_args(argv)

    access_key = os.environ.get("AULATEX_TMP_AKID", "").strip()
    secret_key = os.environ.get("AULATEX_TMP_SECRET", "").strip()
    if not access_key or not secret_key:
        print("[encrypt] ERROR: faltan las variables temporales con las credenciales.")
        print("          Este script lo invoca setup_aws_credentials.ps1.")
        return 2

    env_path = Path(args.env_file).resolve()
    if not env_path.exists():
        print(f"[encrypt] ERROR: no existe {env_path}")
        return 2

    sc = load_crypto(Path(args.hub_root).resolve())
    if sc is None:
        return 2

    fernet = sc.resolve_data_fernet(create_key=False)
    if fernet is None:
        print("[encrypt] ERROR: no hay clave Fernet disponible.")
        print("          Define AULATEX_MASTER_PIN o asegura que exista secret.key.")
        return 2

    # Respaldo antes de tocar el archivo.
    backup = env_path.with_suffix(env_path.suffix + ".bak-aws-setup")
    if not backup.exists():
        shutil.copy2(env_path, backup)
        print(f"[encrypt] respaldo creado: {backup.name}")

    lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines()
    enc_access = sc.encrypt_value(access_key, fernet)
    enc_secret = sc.encrypt_value(secret_key, fernet)

    lines = set_env_value(lines, "AWS_ACCESS_KEY_ID", enc_access)
    lines = set_env_value(lines, "AWS_SECRET_ACCESS_KEY", enc_secret)
    lines = set_env_value(lines, "AWS_REGION", args.region)

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[encrypt] credenciales cifradas en {env_path.name}")
    print(f"[encrypt]   AWS_ACCESS_KEY_ID     -> enc: ({len(enc_access)} chars)")
    print(f"[encrypt]   AWS_SECRET_ACCESS_KEY -> enc: ({len(enc_secret)} chars)")

    # Verificacion inmediata del ciclo cifrar -> descifrar.
    ok_access = sc.decrypt_value(enc_access) == access_key
    ok_secret = sc.decrypt_value(enc_secret) == secret_key
    print(f"[encrypt] verificacion de descifrado: "
          f"access={'OK' if ok_access else 'FALLO'}  secret={'OK' if ok_secret else 'FALLO'}")
    return 0 if (ok_access and ok_secret) else 1


if __name__ == "__main__":
    sys.exit(main())
