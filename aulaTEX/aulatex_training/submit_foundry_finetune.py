"""Sube el corpus DPO y lanza el fine-tuning de preferencias en Azure OpenAI.

Via B: no requiere cuota de VM GPU (H100/A100 siguen en tramite). Foundry pone
la infraestructura; aqui solo se suben los archivos y se crea el job.

Modos
-----
``--check``   (por defecto) Verifica credenciales, archivos y modelo. NO sube nada.
``--submit``  Sube los .jsonl y crea el job. GENERA COSTO; exige ``--yes``.

Credenciales: ``AZURE_OPENAI_ENDPOINT`` y ``AZURE_OPENAI_API_KEY``. Se pueden
recuperar con ``az cognitiveservices account keys list``.

Uso:
    python aulaTEX/aulatex_training/submit_foundry_finetune.py --check
    python aulaTEX/aulatex_training/submit_foundry_finetune.py --submit --yes
    python aulaTEX/aulatex_training/submit_foundry_finetune.py --status <job_id>
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# El parametro `method` (DPO) solo viaja en versiones preview >= 2025-04-01;
# con versiones GA el servicio lo ignora y exige formato supervisado.
API_VERSION = "2025-04-01-preview"
# o4-mini solo admite fine-tuning por refuerzo, no DPO.
DEFAULT_MODEL = "gpt-4.1-mini"


def make_client(endpoint: str, api_key: str):
    from openai import AzureOpenAI

    return AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=API_VERSION)


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    base = REPO_ROOT / "retroalimentacion-editorial" / "aulatex" / "training" / "foundry"
    train = Path(args.train_file).resolve() if args.train_file else base / "dpo-train.jsonl"
    validation = (Path(args.validation_file).resolve() if args.validation_file
                  else base / "dpo-validation.jsonl")
    return train, validation


def check(args: argparse.Namespace, endpoint: str, api_key: str) -> int:
    print("\n=== Azure OpenAI fine-tuning: verificacion (read-only) ===")
    print(f"  endpoint : {endpoint or 'FALTA'}")
    print(f"  api key  : {'OK' if api_key else 'FALTA'}")
    print(f"  modelo   : {args.model}")

    train, validation = resolve_paths(args)
    ok = True
    for label, path in (("train", train), ("validation", validation)):
        if path.exists():
            lines = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            print(f"  {label:11s}: {lines} ejemplos  ({path.name})")
        else:
            print(f"  {label:11s}: NO EXISTE {path}")
            ok = False
    if not ok:
        print("\n  Genera el corpus: python aulaTEX/aulatex_training/build_foundry_dpo.py")
        return 1
    if not (endpoint and api_key):
        print("\n  Faltan credenciales. Exporta AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_API_KEY.")
        return 2

    try:
        client = make_client(endpoint, api_key)
        jobs = client.fine_tuning.jobs.list(limit=5)
        print("\n  Conexion OK. Jobs recientes:")
        found = False
        for job in jobs.data:
            found = True
            print(f"    - {job.id}  {job.status:12s} modelo={job.model}")
        if not found:
            print("    (ninguno todavia)")
    except Exception as exc:  # noqa: BLE001 - reportar causa al usuario
        print(f"\n  ERROR al conectar: {exc.__class__.__name__}: {exc}")
        return 2

    print("\n  Todo listo. Para lanzar: --submit --yes")
    return 0


def submit(args: argparse.Namespace, endpoint: str, api_key: str) -> int:
    train, validation = resolve_paths(args)
    if not train.exists() or not validation.exists():
        print("[foundry] Faltan los archivos de corpus. Ejecuta build_foundry_dpo.py")
        return 1

    client = make_client(endpoint, api_key)

    print("[foundry] subiendo archivos...")
    with train.open("rb") as handle:
        train_file = client.files.create(file=handle, purpose="fine-tune")
    with validation.open("rb") as handle:
        val_file = client.files.create(file=handle, purpose="fine-tune")
    print(f"[foundry]   train      : {train_file.id}")
    print(f"[foundry]   validation : {val_file.id}")

    # Azure procesa el archivo antes de aceptarlo en un job.
    for file_id in (train_file.id, val_file.id):
        for _ in range(60):
            status = client.files.retrieve(file_id).status
            if status in ("processed", "error"):
                break
            time.sleep(5)
        print(f"[foundry]   {file_id} -> {status}")
        if status == "error":
            print("[foundry] ABORTA: Azure rechazo el archivo. Revisa el formato JSONL.")
            return 1

    print(f"[foundry] creando job de preference fine-tuning sobre {args.model}...")
    job = client.fine_tuning.jobs.create(
        training_file=train_file.id,
        validation_file=val_file.id,
        model=args.model,
        method={"type": "dpo", "dpo": {"hyperparameters": {"n_epochs": args.epochs}}},
        suffix="aulatex-editorial",
    )
    print(f"[foundry] job creado : {job.id}")
    print(f"[foundry] estado     : {job.status}")
    print(f"\n[foundry] Seguimiento:\n    python {Path(__file__).name} --status {job.id}")
    return 0


def status(job_id: str, endpoint: str, api_key: str) -> int:
    client = make_client(endpoint, api_key)
    job = client.fine_tuning.jobs.retrieve(job_id)
    print(f"[foundry] job     : {job.id}")
    print(f"[foundry] estado  : {job.status}")
    print(f"[foundry] modelo  : {job.model}")
    if getattr(job, "fine_tuned_model", None):
        print(f"[foundry] afinado : {job.fine_tuned_model}")
    if getattr(job, "error", None):
        print(f"[foundry] error   : {job.error}")
    try:
        events = client.fine_tuning.jobs.list_events(job_id, limit=8)
        print("\n[foundry] eventos recientes:")
        for event in events.data:
            print(f"    {event.created_at}  {event.message}")
    except Exception:  # noqa: BLE001 - los eventos son informativos
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="submit_foundry_finetune")
    parser.add_argument("--check", action="store_true", help="Solo verifica (por defecto).")
    parser.add_argument("--submit", action="store_true", help="Crea el job (GENERA COSTO).")
    parser.add_argument("--yes", action="store_true", help="Confirma el envio.")
    parser.add_argument("--status", default="", help="Consulta el estado de un job.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--train-file", default="")
    parser.add_argument("--validation-file", default="")
    args = parser.parse_args(argv)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()

    if args.status:
        if not (endpoint and api_key):
            print("[foundry] Faltan AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY")
            return 2
        return status(args.status, endpoint, api_key)

    if args.submit:
        if not args.yes:
            print("[foundry] --submit crea un job que GENERA COSTO. Repite con --yes.")
            return 1
        if not (endpoint and api_key):
            print("[foundry] Faltan AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY")
            return 2
        return submit(args, endpoint, api_key)

    return check(args, endpoint, api_key)


if __name__ == "__main__":
    sys.exit(main())
