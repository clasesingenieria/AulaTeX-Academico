"""Corridas de entrenamiento supervisado del motor inteligente.

IDEA
====
Tomar actividades ya ENTREGADAS Y VALIDADAS como objetivo conocido, pedirle al
motor que rehaga esa misma actividad partiendo solo de la planeación y las
referencias, y medir cuánto se acerca al objetivo. Cada ciclo produce un par
(intento del motor, actividad validada) que alimenta el corpus de preferencia.

POR QUÉ ASÍ
===========
Sin un objetivo validado, los ciclos del motor solo generan variaciones sin
criterio externo: el motor se compara consigo mismo. Con la actividad aprobada
como referencia, cada ciclo tiene una señal de aprendizaje real.

HONESTIDAD DEL EXPERIMENTO
==========================
* La referencia se AÍSLA antes de cada ciclo: el motor no debe leer la respuesta
  que intenta reproducir. Sin ese aislamiento el resultado no valdría nada.
* Se registra la distancia al objetivo por ciclo, no solo el score heurístico:
  un texto puede sacar 100 en la métrica y seguir siendo distinto de la referencia.
* Si el motor no mejora a lo largo de los ciclos, se reporta. No se maquilla.

USO
---
    python aulaTEX/aulatex_training/run_supervised_cycles.py \
        --target UnADM/licenciatura-en-derecho-unadm/filosofia-del-derecho-lde \
        --activity 4 --cycles 10
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "aulaTEX"))


def quality_of(text: str) -> float:
    from aulatex.activity_optimizer import ActivityOptimizer

    optimizer = ActivityOptimizer.__new__(ActivityOptimizer)
    optimizer._current_concepts = None
    return float(optimizer._quality_score(text))


def body_of(text: str) -> str:
    """Cuerpo comparable: sin preámbulo ni comentarios."""
    start = text.find(r"\begin{document}")
    body = text[start:] if start >= 0 else text
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("%")]
    return "\n".join(lines)


def similarity(candidate: str, reference: str) -> float:
    return SequenceMatcher(None, body_of(candidate), body_of(reference)).ratio()


def resolve_report(target: Path, activity: int) -> Path | None:
    matches = sorted(target.glob(f"reporte-*Actividad-{activity}.tex"))
    return matches[0] if matches else None


def release_file(path: Path, attempts: int = 6) -> bool:
    """Borra el archivo reintentando ante bloqueos de Windows."""
    for attempt in range(attempts):
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return True
        except PermissionError:
            time.sleep(2 * (attempt + 1))
    return False


def run_engine(target: str, activity: int, engines: list[str], timeout_s: int) -> tuple[bool, str]:
    cmd = [
        str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m", "aulaTEX.aulatex.cli", "agent",
        "--target", target,
        "--level", "actividad",
        "--action", "realizar-actividad",
        "--activity", str(activity),
        "--no-detail-planner",
    ]
    for engine in engines:
        cmd += ["--engine", engine]
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout_s)
        return proc.returncode == 0, (proc.stdout or "")[-400:]
    except subprocess.TimeoutExpired:
        return False, "timeout"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser("run_supervised_cycles")
    parser.add_argument("--target", required=True, help="Carpeta de la materia.")
    parser.add_argument("--activity", type=int, required=True)
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--engine", action="append", default=[])
    parser.add_argument("--timeout-min", type=int, default=45)
    parser.add_argument("--out-dir", default="aulaTEX/retroalimentacion-editorial/aulatex/training/supervised")
    args = parser.parse_args(argv)

    target_dir = (REPO_ROOT / args.target).resolve()
    report = resolve_report(target_dir, args.activity)
    if report is None:
        print(f"[sup] No hay reporte de la actividad {args.activity} en {args.target}")
        return 1

    reference = report.read_text(encoding="utf-8", errors="replace")
    ref_score = quality_of(reference)
    print(f"[sup] Referencia: {report.name}  (calidad {ref_score:.2f}, {len(reference)} chars)")
    if ref_score < 90:
        print(f"[sup] AVISO: la referencia solo puntúa {ref_score:.0f}. Un objetivo débil "
              "enseña a producir trabajo débil; conviene usar actividades validadas al alza.")

    out_dir = (REPO_ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{target_dir.name}-A{args.activity}"
    pairs_path = out_dir / f"{slug}-pairs.jsonl"
    engines = args.engine or ["GPT-5.6-Luna", "GPT-5.6-Terra"]

    # La referencia se guarda fuera del árbol para que el motor no pueda leerla.
    vault = out_dir / f"{slug}-reference.tex"
    vault.write_text(reference, encoding="utf-8")

    records: list[dict[str, Any]] = []
    try:
        for cycle in range(1, args.cycles + 1):
            started = time.time()
            # Aislar la referencia: el motor parte de cero, no de la respuesta.
            # Un pdflatex colgado puede mantener el .tex abierto en Windows.
            if not release_file(report):
                print(f"[sup] ciclo {cycle}: {report.name} sigue bloqueado por otro proceso; se omite.")
                continue
            ok, tail = run_engine(args.target, args.activity, engines, args.timeout_min * 60)

            attempt = report.read_text(encoding="utf-8", errors="replace") if report.exists() else ""
            score = quality_of(attempt) if attempt else 0.0
            sim = similarity(attempt, reference) if attempt else 0.0
            elapsed = (time.time() - started) / 60

            records.append({
                "cycle": cycle, "ok": ok, "quality": round(score, 2),
                "similarity_to_reference": round(sim, 4),
                "chars": len(attempt), "minutes": round(elapsed, 1),
            })
            print(f"[sup] ciclo {cycle:>3}/{args.cycles}  calidad {score:6.2f}  "
                  f"similitud {sim:6.2%}  {elapsed:5.1f} min  {'ok' if ok else 'FALLO'}")

            if attempt:
                with pairs_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "prompt": f"Actividad {args.activity} de {target_dir.name}",
                        "rejected": attempt, "chosen": reference,
                        "quality_gain": round(ref_score - score, 2),
                        "similarity": round(sim, 4),
                        "source": "supervised-cycle",
                    }, ensure_ascii=False) + "\n")
    finally:
        # La referencia validada SIEMPRE vuelve a su sitio, incluso si algo falla.
        shutil.copyfile(vault, report)
        print(f"[sup] Referencia restaurada en {report.name}")

    if records:
        summary = out_dir / f"{slug}-summary.json"
        summary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        sims = [r["similarity_to_reference"] for r in records]
        print(f"\n[sup] === Resultado de {len(records)} ciclos ===")
        print(f"  similitud  min/media/max : {min(sims):.2%} / {sum(sims)/len(sims):.2%} / {max(sims):.2%}")
        mitad = len(sims) // 2
        if mitad:
            primera, segunda = sims[:mitad], sims[mitad:]
            delta = sum(segunda)/len(segunda) - sum(primera)/len(primera)
            print(f"  tendencia (2.ª mitad vs 1.ª): {delta:+.2%}")
            if delta <= 0.01:
                print("  VEREDICTO: sin evidencia de convergencia hacia la referencia.")
                print("  Los ciclos por sí solos no enseñan: el motor no acumula memoria entre corridas.")
            else:
                print("  VEREDICTO: hay tendencia de acercamiento a la referencia.")
        print(f"  pares para corpus        : {pairs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
