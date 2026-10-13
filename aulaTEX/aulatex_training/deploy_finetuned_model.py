"""Despliega el modelo afinado y lo registra para que AulaTeX pueda usarlo.

Un job de fine-tuning produce un modelo, pero ese modelo NO es invocable hasta
que se le crea un deployment. Este script cierra ese ultimo tramo:

    job terminado -> deployment -> variables del .env -> realizar-actividad

Modos
-----
``--check``   (por defecto) Muestra jobs terminados y deployments existentes.
``--deploy``  Crea el deployment. GENERA COSTO por hosting; exige ``--yes``.
``--test``    Invoca el deployment con un fragmento LaTeX real y compara el
              score de calidad antes/despues. Es la prueba que importa: si el
              modelo afinado no eleva el score, no sirve desplegarlo.

Credenciales: ``AZURE_OPENAI_ENDPOINT`` y ``AZURE_OPENAI_API_KEY``.

Uso:
    python aulaTEX/aulatex_training/deploy_finetuned_model.py --check
    python aulaTEX/aulatex_training/deploy_finetuned_model.py --deploy --yes
    python aulaTEX/aulatex_training/deploy_finetuned_model.py --test
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

API_VERSION = "2025-04-01-preview"
DEFAULT_DEPLOYMENT = "aulatex-editorial"
RESOURCE_GROUP = "maurygrupo"
ACCOUNT_NAME = "carlosmauriciocarvajalcoronado-4"

# Fragmento deliberadamente pobre: sin citas, sin conectores, con placeholder.
PROBE_FRAGMENT = r"""\section{Desarrollo}
Los seguros son importantes. Hay varios tipos de seguros.
El seguro de vida protege a la familia. El seguro de auto cubre accidentes.
\pendiente{Ampliar con fuentes}
"""

SYSTEM_PROMPT = (
    "Eres un asistente editorial academico de AulaTeX. Produces LaTeX para actividades "
    "universitarias en espanol. Respetas la tecnica didactica solicitada, estructuras el "
    "cuerpo en tres actos (introduccion, un unico desarrollo con titulo tematico y "
    "conclusiones), citas toda afirmacion con \\cite y evitas metadiscurso de ejecucion: "
    "hablas del tema, no de la actividad."
)


def make_client(endpoint: str, api_key: str):
    from openai import AzureOpenAI

    return AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=API_VERSION)


def load_scorer():
    sys.path.insert(0, str(REPO_ROOT / "aulaTEX"))
    from aulatex.activity_optimizer import ActivityOptimizer

    optimizer = ActivityOptimizer.__new__(ActivityOptimizer)
    optimizer._current_concepts = None
    return optimizer._quality_score


def check(endpoint: str, api_key: str) -> int:
    print("\n=== Modelos afinados y deployments ===")
    client = make_client(endpoint, api_key)

    ready: list[tuple[str, str]] = []
    for job in client.fine_tuning.jobs.list(limit=10).data:
        model = getattr(job, "fine_tuned_model", None) or "-"
        print(f"  {job.id}  {job.status:12s} {model}")
        if job.status == "succeeded" and model != "-":
            ready.append((job.id, model))

    if not ready:
        print("\n  Ningun job terminado todavia. Espera a que el estado sea 'succeeded'.")
        return 1

    print(f"\n  Modelos listos para desplegar: {len(ready)}")
    for _, model in ready:
        print(f"    {model}")

    result = subprocess.run(
        ["az", "cognitiveservices", "account", "deployment", "list",
         "--name", ACCOUNT_NAME, "--resource-group", RESOURCE_GROUP,
         "--query", "[].name", "-o", "tsv"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", shell=True)
    existing = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    print(f"\n  Deployments existentes: {len(existing)}")
    if DEFAULT_DEPLOYMENT in existing:
        print(f"    '{DEFAULT_DEPLOYMENT}' YA EXISTE")
    return 0


def deploy(args: argparse.Namespace, endpoint: str, api_key: str) -> int:
    client = make_client(endpoint, api_key)
    model = args.model
    if not model:
        for job in client.fine_tuning.jobs.list(limit=10).data:
            if job.status == "succeeded" and getattr(job, "fine_tuned_model", None):
                model = job.fine_tuned_model
                break
    if not model:
        print("[deploy] No hay ningun modelo afinado terminado. Espera al job.")
        return 1

    print(f"[deploy] modelo     : {model}")
    print(f"[deploy] deployment : {args.deployment_name}")
    result = subprocess.run(
        ["az", "cognitiveservices", "account", "deployment", "create",
         "--name", ACCOUNT_NAME, "--resource-group", RESOURCE_GROUP,
         "--deployment-name", args.deployment_name,
         "--model-name", model, "--model-version", "1",
         "--model-format", "OpenAI",
         "--sku-name", "standard", "--sku-capacity", str(args.capacity)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", shell=True)

    if result.returncode != 0:
        print(f"[deploy] ERROR:\n{result.stderr[-600:]}")
        return 1

    print("[deploy] deployment creado.")
    print("\n[deploy] Agrega a aulaTEX/aulatex.env:")
    print(f"    AULATEX_FINETUNED_DEPLOYMENT={args.deployment_name}")
    print(f"    AULATEX_FINETUNED_BASE_URL={endpoint}openai/v1/chat/completions")
    return 0


def test(args: argparse.Namespace, endpoint: str, api_key: str) -> int:
    client = make_client(endpoint, api_key)
    score_of = load_scorer()

    before = float(score_of(PROBE_FRAGMENT))
    print(f"[test] deployment      : {args.deployment_name}")
    print(f"[test] score ORIGINAL  : {before:.1f}")

    try:
        response = client.chat.completions.create(
            model=args.deployment_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content":
                    "Mejora el siguiente fragmento LaTeX academico elevando rigor, fuentes "
                    "citadas y densidad argumentativa, conservando la tecnica didactica.\n\n"
                    f"Fragmento actual:\n```latex\n{PROBE_FRAGMENT}\n```"},
            ],
            max_completion_tokens=2000,
        )
    except Exception as exc:  # noqa: BLE001 - reportar causa al usuario
        print(f"[test] ERROR al invocar: {exc.__class__.__name__}: {exc}")
        return 1

    improved = (response.choices[0].message.content or "").strip()
    if not improved:
        print("[test] El modelo no devolvio contenido.")
        return 1

    after = float(score_of(improved))
    print(f"[test] score MEJORADO  : {after:.1f}")
    print(f"[test] delta           : {after - before:+.1f}")
    print(f"\n[test] --- salida (600 chars) ---\n{improved[:600]}")

    if after > before:
        print("\n[test] El modelo afinado ELEVA la calidad medible.")
        return 0
    print("\n[test] AVISO: no elevo el score. Revisa el corpus antes de usarlo en produccion.")
    return 1


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="deploy_finetuned_model")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--deploy", action="store_true", help="Crea el deployment (GENERA COSTO).")
    parser.add_argument("--test", action="store_true", help="Prueba el deployment y mide el score.")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--model", default="", help="Modelo afinado; por defecto el ultimo exitoso.")
    parser.add_argument("--deployment-name", default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--capacity", type=int, default=1)
    args = parser.parse_args(argv)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    if not (endpoint and api_key):
        print("[deploy] Faltan AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY")
        return 2

    if args.test:
        return test(args, endpoint, api_key)
    if args.deploy:
        if not args.yes:
            print("[deploy] El deployment GENERA COSTO por hosting. Repite con --yes.")
            return 1
        return deploy(args, endpoint, api_key)
    return check(endpoint, api_key)


if __name__ == "__main__":
    sys.exit(main())
