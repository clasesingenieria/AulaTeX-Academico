"""Lanzador de jobs de entrenamiento de AulaTeX a GPU en Azure ML o SageMaker.

Empaqueta ``train_reward_model.py`` + el dataset y lo envía a un cluster GPU.
Reutiliza el mecanismo de credenciales del proyecto: variables de entorno,
opcionalmente descifradas desde un ``.env`` con valores ``enc:`` (Fernet).

Modos
-----
``--check``   (por defecto) Verificación READ-ONLY: qué credenciales hay, si el
              SDK autentica y qué cómputo GPU está disponible. NO crea nada.
``--submit``  Envía el job de entrenamiento al cluster indicado.

Backends
--------
``azure``     Azure ML: requiere AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP y
              AZURE_ML_WORKSPACE. Autentica con DefaultAzureCredential
              (usa ``az login`` o un service principal).
``aws``       SageMaker: requiere AWS_ACCESS_KEY_ID/SECRET (o perfil) y un rol
              de ejecución (SAGEMAKER_ROLE_ARN).

Advertencia honesta: ``--submit`` CREA recursos que generan costo en la nube.
Por eso el modo por defecto es ``--check`` y el envío exige confirmación
explícita mediante ``--yes``.

Uso:
    python aulaTEX/aulatex_training/submit_cloud_job.py --backend azure --check
    python aulaTEX/aulatex_training/submit_cloud_job.py --backend aws --check
    python aulaTEX/aulatex_training/submit_cloud_job.py --backend azure --submit --yes \
        --compute gpu-cluster --train-file .../reward.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# --------------------------------------------------------------------- entorno
def hydrate_env(env_file: str) -> None:
    """Carga un .env y descifra valores ``enc:`` con la clave Fernet local.

    Reutiliza ``aulaTEX/secrets_local.py`` del proyecto si está disponible.
    Best-effort: si no hay clave, deja las variables como estén.
    """
    if not env_file:
        return
    path = Path(env_file).expanduser().resolve()
    if not path.exists():
        print(f"[env] AVISO: no existe {path}")
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=True)
        print(f"[env] cargado: {path}")
    except ImportError:
        print("[env] AVISO: python-dotenv no instalado; omito la carga del .env")
        return

    if not any(str(v).startswith("enc:") for v in os.environ.values()):
        return
    try:
        import importlib.util

        module_path = REPO_ROOT / "aulaTEX" / "secrets_local.py"
        if not module_path.exists():
            print("[env] AVISO: hay valores 'enc:' pero no encuentro secrets_local.py")
            return
        spec = importlib.util.spec_from_file_location("aulatex_secrets_local", module_path)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fernet = mod.resolve_fernet(create=False)
        if fernet is None:
            print("[env] AVISO: valores cifrados presentes pero no hay clave Fernet disponible.")
            return
        from cryptography.fernet import InvalidToken

        decrypted = 0
        for key, value in list(os.environ.items()):
            if isinstance(value, str) and value.startswith("enc:"):
                try:
                    os.environ[key] = fernet.decrypt(value[4:].encode("ascii")).decode("utf-8")
                    decrypted += 1
                except InvalidToken:
                    pass
        print(f"[env] secretos descifrados: {decrypted}")
    except Exception as exc:  # noqa: BLE001 - best-effort por diseño
        print(f"[env] AVISO: no se pudieron descifrar secretos ({exc.__class__.__name__})")


def _present(name: str) -> str:
    value = os.getenv(name, "")
    return "OK" if value else "FALTA"


# Cuotas EC2 On-Demand relevantes para entrenamiento (códigos estándar de AWS).
# Hallazgo verificado en los laboratorios del hub (2026-07-24): la cuota P
# aparece "aprobada" en 8 vCPU pero es INSERVIBLE, porque la instancia A100 más
# pequeña (p4d.24xlarge) exige 96 vCPU. La ruta real es la familia G.
EC2_QUOTAS = {
    "L-1216C47A": ("Standard (C/M/R/X) vCPU", 0),
    "L-DB2E81BA": ("G y VT vCPU (A10G/L4)", 8),
    "L-417A185B": ("P vCPU (A100/H100)", 96),
    "L-1945791B": ("Inf vCPU (Inferentia)", 0),
}

# vCPU que consume cada tipo de instancia de entrenamiento y su familia de cuota.
INSTANCE_REQUIREMENTS = {
    "ml.g5.xlarge": ("L-DB2E81BA", 4),
    "ml.g5.2xlarge": ("L-DB2E81BA", 8),
    "ml.g5.4xlarge": ("L-DB2E81BA", 16),
    "ml.g5.12xlarge": ("L-DB2E81BA", 48),
    "ml.p3.2xlarge": ("L-417A185B", 8),
    "ml.p4d.24xlarge": ("L-417A185B", 96),
}


def aws_quota_report(region: str) -> dict[str, float]:
    """Consulta las cuotas EC2 de GPU/CPU. Devuelve {quota_code: valor}."""
    try:
        import boto3
    except ImportError:
        return {}

    values: dict[str, float] = {}
    try:
        client = boto3.client("service-quotas", region_name=region)
    except Exception:  # noqa: BLE001
        return {}

    print("\n  Cuotas EC2 On-Demand:")
    for code, (label, min_useful) in EC2_QUOTAS.items():
        try:
            quota = client.get_service_quota(ServiceCode="ec2", QuotaCode=code)
            value = float(quota["Quota"]["Value"])
            values[code] = value
            note = ""
            if min_useful and value < min_useful:
                note = f"  <-- INSERVIBLE (requiere >= {min_useful} vCPU)"
            print(f"    {label:26s} = {value:6.0f}{note}")
        except Exception as exc:  # noqa: BLE001
            print(f"    {label:26s} = (no consultable: {exc.__class__.__name__})")
    return values


def advise_instance(quotas: dict[str, float], requested: str) -> None:
    """Advierte si la instancia solicitada no cabe en la cuota disponible."""
    if not quotas:
        return
    requirement = INSTANCE_REQUIREMENTS.get(requested)
    if requirement is None:
        print(f"\n  AVISO: no conozco los requisitos de '{requested}'; verifica su cuota manualmente.")
        return

    code, needed = requirement
    available = quotas.get(code)
    label = EC2_QUOTAS.get(code, (code, 0))[0]
    if available is None:
        return
    if available >= needed:
        print(f"\n  '{requested}' CABE en la cuota {label} ({needed} <= {available:.0f}).")
        return

    print(f"\n  '{requested}' NO CABE: necesita {needed} vCPU de {label}, hay {available:.0f}.")
    viable = [
        name for name, (c, n) in INSTANCE_REQUIREMENTS.items()
        if quotas.get(c, 0) >= n
    ]
    if viable:
        print(f"  Alternativas lanzables hoy: {', '.join(sorted(viable))}")
    else:
        print("  No hay instancias de GPU lanzables con las cuotas actuales.")
        print("  Solicita aumento en la consola: Service Quotas -> EC2 -> On-Demand vCPUs.")


# ----------------------------------------------------------------- Azure ML
def azure_check() -> int:
    print("\n=== Azure ML: verificación (read-only) ===")
    for var in ("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "AZURE_ML_WORKSPACE", "AZURE_LOCATION"):
        print(f"  {var:26s} {_present(var)}")

    subscription = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP", "")
    workspace = os.getenv("AZURE_ML_WORKSPACE", "")
    if not all((subscription, resource_group, workspace)):
        print("\n  Faltan variables para conectar al workspace de Azure ML.")
        print("  Define AZURE_RESOURCE_GROUP y AZURE_ML_WORKSPACE (además de AZURE_SUBSCRIPTION_ID).")
        print("  Si aún no tienes workspace ML, créalo o usa el backend 'aws'.")
        return 1

    try:
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential
    except ImportError:
        print("  ERROR: falta azure-ai-ml / azure-identity. Instala requirements-training.txt")
        return 2

    try:
        client = MLClient(DefaultAzureCredential(), subscription, resource_group, workspace)
        print(f"\n  Conectado al workspace: {workspace}")
        print("  Cómputos disponibles:")
        found_gpu = False
        for compute in client.compute.list():
            size = getattr(compute, "size", "") or ""
            is_gpu = any(tag in size.upper() for tag in ("NC", "ND", "NV"))
            if is_gpu:
                found_gpu = True
            print(f"    - {compute.name:24s} tipo={compute.type:16s} size={size} "
                  f"{'[GPU]' if is_gpu else ''}")
        if not found_gpu:
            print("    (no se detectó cómputo con SKU de GPU: NC/ND/NV)")
        return 0
    except Exception as exc:  # noqa: BLE001 - reportar causa al usuario
        print(f"\n  ERROR al conectar: {exc.__class__.__name__}: {exc}")
        print("  Sugerencia: ejecuta 'az login' o configura un service principal.")
        return 2


def azure_submit(args: argparse.Namespace) -> int:
    from azure.ai.ml import MLClient, command
    from azure.ai.ml.entities import Environment
    from azure.identity import DefaultAzureCredential

    subscription = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP", "")
    workspace = os.getenv("AZURE_ML_WORKSPACE", "")
    if not all((subscription, resource_group, workspace)):
        print("[azure] ERROR: faltan AZURE_SUBSCRIPTION_ID / AZURE_RESOURCE_GROUP / AZURE_ML_WORKSPACE")
        return 2

    client = MLClient(DefaultAzureCredential(), subscription, resource_group, workspace)
    environment = Environment(
        image="mcr.microsoft.com/azureml/curated/acpt-pytorch-2.2-cuda12.1:latest",
        name="aulatex-reward-env",
    )

    # El corpus se sube como input: la ruta local del host no existe en el contenedor.
    train_path = Path(args.train_file).expanduser().resolve()
    if not train_path.exists():
        print(f"[azure] ERROR: no existe el corpus {train_path}")
        print("        Genera primero: python aulaTEX/aulatex_training/build_corpus_from_repo.py")
        return 2

    from azure.ai.ml import Input, Output
    from azure.ai.ml.constants import AssetTypes

    job = command(
        code=str(HERE),  # sube esta carpeta (contiene train_reward_model.py)
        command=(
            "python train_reward_model.py "
            "--train-file ${{inputs.train_file}} "
            f"--model-name {args.model_name} "
            f"--epochs {args.epochs} "
            f"--max-length {getattr(args, 'max_length', 512)} "
            "--output-dir ${{outputs.model_dir}}"
        ),
        inputs={"train_file": Input(type=AssetTypes.URI_FILE, path=str(train_path))},
        outputs={"model_dir": Output(type=AssetTypes.URI_FOLDER)},
        environment=environment,
        compute=args.compute,
        display_name="aulatex-reward-model",
        experiment_name="aulatex-editorial-quality",
    )
    created = client.jobs.create_or_update(job)
    print(f"[azure] job enviado: {created.name}")
    print(f"[azure] seguimiento : {created.studio_url}")
    return 0


# ----------------------------------------------------------------- SageMaker
def aws_check(instance_type: str = "ml.g5.2xlarge") -> int:
    print("\n=== AWS SageMaker: verificación (read-only) ===")
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "SAGEMAKER_ROLE_ARN"):
        print(f"  {var:26s} {_present(var)}")

    try:
        import boto3
    except ImportError:
        print("  ERROR: falta boto3. Instala requirements-training.txt")
        return 2

    region = os.getenv("AWS_REGION", "us-east-1")
    try:
        sts = boto3.client("sts", region_name=region)
        identity = sts.get_caller_identity()
        # No imprimimos el Account completo por higiene; solo confirmamos identidad.
        arn = identity.get("Arn", "")
        print(f"\n  Autenticado. ARN: ...{arn[-40:]}" if arn else "\n  Autenticado.")
    except Exception as exc:  # noqa: BLE001
        print(f"\n  ERROR de autenticación: {exc.__class__.__name__}: {exc}")
        print("  Sugerencia: define AWS_ACCESS_KEY_ID/SECRET o ejecuta 'aws configure'.")
        return 2

    # Permisos de entrenamiento (read-only): listar training jobs.
    training_ok = False
    try:
        sm = boto3.client("sagemaker", region_name=region)
        jobs = sm.list_training_jobs(MaxResults=5)
        print(f"  Permiso SageMaker ListTrainingJobs: OK "
              f"({len(jobs.get('TrainingJobSummaries', []))} jobs recientes)")
        training_ok = True
    except Exception as exc:  # noqa: BLE001
        print(f"  SageMaker NO accesible: {exc.__class__.__name__}")
        print("  → Las credenciales probablemente NO tienen permisos de entrenamiento.")

    # Cuotas de GPU y viabilidad de la instancia solicitada.
    quotas = aws_quota_report(region)
    advise_instance(quotas, instance_type)

    # Rol de ejecución: si no está en el entorno, intentar descubrirlo.
    role = os.getenv("SAGEMAKER_ROLE_ARN", "")
    if not role:
        print("\n  SAGEMAKER_ROLE_ARN no definido; buscando roles candidatos...")
        try:
            iam = boto3.client("iam")
            candidates = [
                r["Arn"] for r in iam.list_roles().get("Roles", [])
                if "sagemaker" in r["RoleName"].lower()
            ]
            if candidates:
                print("  Roles encontrados (define uno como SAGEMAKER_ROLE_ARN):")
                for arn in candidates[:5]:
                    print(f"    - {arn}")
            else:
                print("  No hay roles de SageMaker. Crea uno con AmazonSageMakerFullAccess.")
        except Exception as exc:  # noqa: BLE001
            print(f"  No se pudieron listar roles IAM ({exc.__class__.__name__}).")
        return 1

    return 0 if training_ok else 1


def aws_submit(args: argparse.Namespace) -> int:
    from sagemaker.huggingface import HuggingFace

    role = os.getenv("SAGEMAKER_ROLE_ARN", "")
    if not role:
        print("[aws] ERROR: falta SAGEMAKER_ROLE_ARN")
        return 2

    estimator = HuggingFace(
        entry_point="train_reward_model.py",
        source_dir=str(HERE),
        role=role,
        instance_type=args.instance_type,
        instance_count=1,
        transformers_version="4.36",
        pytorch_version="2.1",
        py_version="py310",
        hyperparameters={
            "train-file": "/opt/ml/input/data/training/reward.jsonl",
            "model-name": args.model_name,
            "epochs": args.epochs,
        },
    )
    estimator.fit({"training": args.s3_input})
    print(f"[aws] job completado: {estimator.latest_training_job.name}")
    return 0


# --------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="submit_cloud_job",
        description="Verifica acceso a GPU o envía el job de entrenamiento a Azure ML / SageMaker.",
    )
    parser.add_argument("--backend", choices=("azure", "aws"), required=True)
    parser.add_argument("--check", action="store_true", help="Solo verificar (read-only). Por defecto.")
    parser.add_argument("--submit", action="store_true", help="Enviar el job (CREA recursos con costo).")
    parser.add_argument("--yes", action="store_true", help="Confirma el envío sin preguntar.")
    parser.add_argument("--env-file", default="", help="Ruta a un .env (admite valores 'enc:').")
    parser.add_argument("--compute", default="gpu-cluster", help="Nombre del cluster GPU (Azure ML).")
    parser.add_argument("--instance-type", default="ml.g5.2xlarge", help="Tipo de instancia (SageMaker).")
    parser.add_argument("--train-file", default="data/reward.jsonl", help="Dataset de entrenamiento.")
    parser.add_argument("--s3-input", default="", help="URI S3 del dataset (SageMaker).")
    parser.add_argument("--model-name", default="FacebookAI/xlm-roberta-base")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=512,
                        help="Ventana de contexto. No puede exceder el limite del modelo.")
    args = parser.parse_args(argv)

    hydrate_env(args.env_file)

    if args.submit:
        if not args.yes:
            print("[submit] ABORTA: enviar un job CREA recursos con costo en la nube.")
            print("         Vuelve a ejecutar con --yes para confirmar.")
            return 1
        if args.backend == "azure":
            return azure_submit(args)
        if not args.s3_input:
            print("[aws] ERROR: --s3-input es obligatorio para SageMaker.")
            return 2
        return aws_submit(args)

    # Modo por defecto: verificación read-only.
    return azure_check() if args.backend == "azure" else aws_check(args.instance_type)


if __name__ == "__main__":
    sys.exit(main())
