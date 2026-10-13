"""Kernel de política de AulaTeX: aprende a elegir (motor, tipo de mejora).

Consume el ``dataset.jsonl`` producido por ``aulatex/training_dataset.py`` y
entrena dos modelos ligeros de scikit-learn (CPU, segundos):

1. ``accept_clf``  — clasificador: ¿esta propuesta será ACEPTADA?
   Permite filtrar acciones de bajo valor esperado ANTES de gastar una llamada
   LLM y un ciclo de compilación.

2. ``reward_reg``  — regresor: ¿cuánto Δcalidad aporta esta acción?
   Es la señal que un bandit contextual usa para enrutar motor/tipo según el
   estado del .tex, en lugar de la lista fija de motores.

Diseño deliberado (honesto sobre los límites):
  * Baseline explícito: se compara contra "aceptar siempre" (la política actual).
    Si el modelo no supera el baseline, se reporta y NO se recomienda usarlo.
  * Validación cruzada agrupada por ``target`` para no filtrar información entre
    ciclos del mismo documento (evita métricas infladas).
  * Se exige un mínimo de muestras y de ambas clases; si no, aborta con mensaje
    claro en lugar de producir un modelo inútil.

NO usa GPU ni nube: es el paso barato que valida si vale la pena entrenar algo
mayor. Sin dependencias del paquete ``aulatex`` (portable a un job remoto).

Uso:
    python aulaTEX/aulatex_training/train_policy.py \
        --dataset retroalimentacion-editorial/aulatex/training/dataset.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Mínimos para que el entrenamiento sea significativo y no ruido.
MIN_ROWS = 40
MIN_PER_CLASS = 8

# Features de ESTADO (conocidas ANTES de ejecutar la acción) + la acción misma.
# Nunca se incluyen campos *_after: serían fuga de información (leakage).
NUMERIC_FEATURES = (
    "quality_before",
    "contract_before",
    "semantic_blocking_before",
    "cycle",
    "activity_number",
    "quality_citas_before",
    "quality_estructura_before",
    "quality_base_conceptual_before",
    "quality_listas_before",
    "quality_conectores_before",
    "quality_extension_before",
    "quality_integridad_before",
)
CATEGORICAL_FEATURES = ("engine", "improvement_kind")


def load_rows(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise SystemExit(
            f"[policy] No existe el dataset: {dataset_path}\n"
            "         Ejecuta primero: python aulaTEX/aulatex/training_dataset.py"
        )
    rows: list[dict[str, Any]] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_matrices(rows: list[dict[str, Any]]):
    """Convierte filas en X (features), y_accept, y_reward y groups (target)."""
    import numpy as np

    numeric: list[list[float]] = []
    categorical: list[list[str]] = []
    y_accept: list[int] = []
    y_reward: list[float] = []
    groups: list[str] = []

    for row in rows:
        numeric.append([float(row.get(name, 0.0) or 0.0) for name in NUMERIC_FEATURES])
        categorical.append([str(row.get(name, "") or "(vacio)") for name in CATEGORICAL_FEATURES])
        y_accept.append(1 if row.get("accepted") else 0)
        y_reward.append(float(row.get("quality_delta", 0.0) or 0.0))
        groups.append(str(row.get("target", "") or "(sin-target)"))

    return (
        np.asarray(numeric, dtype=float),
        categorical,
        np.asarray(y_accept, dtype=int),
        np.asarray(y_reward, dtype=float),
        np.asarray(groups),
    )


def make_pipeline(kind: str):
    """Pipeline con one-hot para categóricas + modelo. kind: 'clf' | 'reg'."""
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    n_numeric = len(NUMERIC_FEATURES)
    n_total = n_numeric + len(CATEGORICAL_FEATURES)
    pre = ColumnTransformer(
        transformers=[
            ("num", "passthrough", list(range(n_numeric))),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(range(n_numeric, n_total)),
            ),
        ]
    )
    model = GradientBoostingClassifier(random_state=0) if kind == "clf" else GradientBoostingRegressor(random_state=0)
    return Pipeline([("pre", pre), ("model", model)])


def _stack(numeric, categorical):
    """Une numéricas y categóricas en una matriz de objetos para ColumnTransformer."""
    import numpy as np

    cat_array = np.asarray(categorical, dtype=object)
    return np.hstack([numeric.astype(object), cat_array])


def evaluate(dataset_path: Path, models_dir: Path) -> int:
    import numpy as np
    from sklearn.dummy import DummyClassifier
    from sklearn.model_selection import GroupKFold, cross_val_predict
    from sklearn.metrics import accuracy_score, mean_absolute_error, roc_auc_score

    rows = load_rows(dataset_path)
    print(f"[policy] filas leídas: {len(rows)}")

    if len(rows) < MIN_ROWS:
        print(
            f"[policy] ABORTA: se requieren >= {MIN_ROWS} ciclos para un modelo significativo.\n"
            f"         Con {len(rows)} filas el modelo sobreajustaría. Acumula más corridas de\n"
            "         activity-optimize y vuelve a ejecutar."
        )
        return 2

    numeric, categorical, y_accept, y_reward, groups = build_matrices(rows)
    X = _stack(numeric, categorical)

    n_pos = int(y_accept.sum())
    n_neg = int(len(y_accept) - n_pos)
    print(f"[policy] aceptados={n_pos}  rechazados={n_neg}")
    if min(n_pos, n_neg) < MIN_PER_CLASS:
        print(
            f"[policy] ABORTA: se requieren >= {MIN_PER_CLASS} ejemplos de CADA clase.\n"
            "         Sin ambas clases el clasificador no puede aprender a discriminar."
        )
        return 2

    n_groups = len(set(groups.tolist()))
    n_splits = max(2, min(5, n_groups))
    if n_groups < 2:
        print("[policy] AVISO: un solo 'target'; la validación no mide generalización entre documentos.")
    cv = GroupKFold(n_splits=n_splits)

    # ---------------------------------------------------------- clasificador
    clf = make_pipeline("clf")
    proba = cross_val_predict(clf, X, y_accept, cv=cv, groups=groups, method="predict_proba")[:, 1]
    pred = (proba >= 0.5).astype(int)
    acc = accuracy_score(y_accept, pred)
    try:
        auc = roc_auc_score(y_accept, proba)
    except ValueError:
        auc = float("nan")

    # Baseline honesto: la política actual = intentar SIEMPRE (aceptar todo).
    dummy = DummyClassifier(strategy="most_frequent")
    dummy_pred = cross_val_predict(dummy, X, y_accept, cv=cv, groups=groups)
    dummy_acc = accuracy_score(y_accept, dummy_pred)

    print("\n[policy] === Clasificador de aceptación ===")
    print(f"  accuracy modelo   : {acc:.3f}")
    print(f"  accuracy baseline : {dummy_acc:.3f}  (clase mayoritaria)")
    print(f"  ROC-AUC           : {auc:.3f}" if auc == auc else "  ROC-AUC           : n/d")
    beats_baseline = acc > dummy_acc + 0.02
    print(f"  ¿supera baseline? : {'SÍ' if beats_baseline else 'NO'}")

    # Ahorro estimado: ciclos rechazados que el modelo habría evitado.
    would_skip = int((proba < 0.5).sum())
    correctly_skipped = int(((proba < 0.5) & (y_accept == 0)).sum())
    wrongly_skipped = int(((proba < 0.5) & (y_accept == 1)).sum())
    print(f"  ciclos que evitaría: {would_skip} "
          f"(correctos: {correctly_skipped}, mejoras perdidas: {wrongly_skipped})")

    # --------------------------------------------------------------- regresor
    reg = make_pipeline("reg")
    reward_pred = cross_val_predict(reg, X, y_reward, cv=cv, groups=groups)
    mae = mean_absolute_error(y_reward, reward_pred)
    mae_baseline = mean_absolute_error(y_reward, np.full_like(y_reward, y_reward.mean()))
    print("\n[policy] === Regresor de recompensa (Δcalidad) ===")
    print(f"  MAE modelo   : {mae:.3f}")
    print(f"  MAE baseline : {mae_baseline:.3f}  (predecir la media)")
    print(f"  ¿supera baseline? : {'SÍ' if mae < mae_baseline * 0.98 else 'NO'}")

    # ------------------------------------------------------ ajuste final y guardado
    if not beats_baseline:
        print(
            "\n[policy] VEREDICTO: el modelo NO supera el baseline de forma clara.\n"
            "         Recomendación: NO enrutar con ML todavía. Usa el reporte de\n"
            "         training_dataset.py para recalibrar pesos a mano y acumula más datos."
        )
        return 1

    import joblib

    models_dir.mkdir(parents=True, exist_ok=True)
    clf.fit(X, y_accept)
    reg.fit(X, y_reward)
    joblib.dump({"pipeline": clf, "numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES},
                models_dir / "accept_clf.joblib")
    joblib.dump({"pipeline": reg, "numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES},
                models_dir / "reward_reg.joblib")

    metrics = {
        "rows": len(rows),
        "accepted": n_pos,
        "rejected": n_neg,
        "clf_accuracy": round(float(acc), 4),
        "clf_baseline_accuracy": round(float(dummy_acc), 4),
        "clf_roc_auc": (round(float(auc), 4) if auc == auc else None),
        "cycles_would_skip": would_skip,
        "correctly_skipped": correctly_skipped,
        "wrongly_skipped": wrongly_skipped,
        "reg_mae": round(float(mae), 4),
        "reg_baseline_mae": round(float(mae_baseline), 4),
        "beats_baseline": bool(beats_baseline),
    }
    (models_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[policy] modelos guardados en: {models_dir}")
    print(f"[policy] métricas           : {models_dir / 'metrics.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    default_dataset = repo_root / "retroalimentacion-editorial" / "aulatex" / "training" / "dataset.jsonl"
    default_models = repo_root / "retroalimentacion-editorial" / "aulatex" / "training" / "models"

    parser = argparse.ArgumentParser(
        prog="train_policy",
        description="Entrena el kernel de política (aceptación + recompensa) en CPU.",
    )
    parser.add_argument("--dataset", default=str(default_dataset), help="Ruta del dataset.jsonl.")
    parser.add_argument("--models-dir", default=str(default_models), help="Directorio de salida de modelos.")
    args = parser.parse_args(argv)

    return evaluate(Path(args.dataset).resolve(), Path(args.models_dir).resolve())


if __name__ == "__main__":
    sys.exit(main())
