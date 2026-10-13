from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = REPO_ROOT / ".aulatex-temp" / "ciclo-a-pdf-batches"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_materialization_results() -> Path:
    candidates = sorted(
        REPO_ROOT.glob(".aulatex-temp/ciclo-a-editorial/*/ciclo-a-materialization-results.json"),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("No se encontró ciclo-a-materialization-results.json.")
    return candidates[0]


def unique_tex_from_results(results_path: Path, *, only_changed: bool) -> list[Path]:
    payload = read_json(results_path)
    tex_paths: list[Path] = []
    seen: set[str] = set()
    for item in payload:
        if only_changed and not item.get("changed"):
            continue
        tex_ref = item.get("tex_path") or ""
        if not tex_ref:
            continue
        tex_path = (REPO_ROOT / tex_ref).resolve()
        if not tex_path.exists() or not tex_path.is_file():
            continue
        key = str(tex_path).lower()
        if key in seen:
            continue
        seen.add(key)
        tex_paths.append(tex_path)
    return tex_paths


def repair_bibtex_style_conflict(tex_path: Path) -> dict:
    text = tex_path.read_text(encoding="utf-8")
    if "\\input{template}" not in text and "\\input{aulaTEX/base/Plantilla-Informe/template}" not in text:
        return {"changed": False, "reason": "sin plantilla AulaTeX"}
    repaired = []
    removed = 0
    for line in text.splitlines():
        if line.lstrip().startswith("\\bibliographystyle"):
            repaired.append("% Ciclo PDF: bibliographystyle omitido; la plantilla AulaTeX ya define el estilo bibliográfico")
            removed += 1
        else:
            repaired.append(line)
    if removed == 0:
        return {"changed": False, "reason": "sin bibliographystyle local"}
    tex_path.write_text("\n".join(repaired) + "\n", encoding="utf-8")
    return {"changed": True, "removed_bibliographystyle": removed, "reason": "bibliographystyle duplicado corregido"}


def compile_tex(tex_path: Path, *, timeout_seconds: int, repair_bibtex: bool) -> dict:
    repair = repair_bibtex_style_conflict(tex_path) if repair_bibtex else {"changed": False, "reason": "reparación desactivada"}
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REPO_ROOT / "aulaTEX" / "latexmk-build.ps1"),
        str(tex_path.relative_to(REPO_ROOT)),
        "-CleanMode",
        "safe",
    ]
    started = time.time()
    proc = subprocess.Popen(command, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=max(30, int(timeout_seconds)))
        timeout = False
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
        stdout, stderr = proc.communicate()
        timeout = True
        rc = "timeout"
    pdf_path = tex_path.with_suffix(".pdf")
    salvaged = False
    if not pdf_path.exists():
        build_pdf = REPO_ROOT / ".build" / "latex" / f"{tex_path.stem}.pdf"
        aux_pdf = REPO_ROOT / ".build" / "latex" / "aux-files" / f"{tex_path.stem}.pdf"
        source_pdf = build_pdf if build_pdf.exists() else aux_pdf if aux_pdf.exists() else None
        if source_pdf:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            source_pdf.replace(pdf_path)
            salvaged = True
    return {
        "tex_path": tex_path.relative_to(REPO_ROOT).as_posix(),
        "pdf_path": pdf_path.relative_to(REPO_ROOT).as_posix(),
        "ok": pdf_path.exists(),
        "returncode": rc,
        "timeout": timeout,
        "salvaged_pdf": salvaged,
        "bibtex_repair": repair,
        "elapsed_seconds": round(time.time() - started, 3),
        "pdf_exists": pdf_path.exists(),
        "stdout_tail": (stdout or "")[-2000:],
        "stderr_tail": (stderr or "")[-2000:],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compila PDFs por lotes para TEX materializados por Ciclo A.")
    parser.add_argument("--results", default="", help="Ruta a ciclo-a-materialization-results.json. Por defecto usa el más reciente.")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--batch-index", type=int, default=0, help="Índice de lote base 0.")
    parser.add_argument("--iterations", type=int, default=1, help="Iteraciones de compilación del lote.")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--repair-bibtex", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--only-changed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--skip-existing-pdf", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_path = (REPO_ROOT / args.results).resolve() if args.results else latest_materialization_results()
    tex_paths = unique_tex_from_results(results_path, only_changed=args.only_changed)
    if args.skip_existing_pdf:
        tex_paths = [path for path in tex_paths if not path.with_suffix(".pdf").exists()]

    start = max(0, args.batch_index) * max(1, args.batch_size)
    end = start + max(1, args.batch_size)
    batch = tex_paths[start:end]

    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = TEMP_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "pdf-batch-results.json"

    results: list[dict] = []
    for iteration in range(1, max(1, int(args.iterations)) + 1):
        for tex_path in batch:
            if args.skip_existing_pdf and tex_path.with_suffix(".pdf").exists() and iteration > 1:
                continue
            result = compile_tex(tex_path, timeout_seconds=args.timeout_seconds, repair_bibtex=args.repair_bibtex)
            result["iteration"] = iteration
            results.append(result)
            report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "ok": True,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "source_results": results_path.relative_to(REPO_ROOT).as_posix(),
        "total_queue_after_filter": len(tex_paths),
        "batch_index": args.batch_index,
        "batch_size": args.batch_size,
        "iterations": args.iterations,
        "processed": len(results),
        "compiled_ok": sum(1 for item in results if item.get("ok")),
        "bibtex_repairs": sum(1 for item in results if item.get("bibtex_repair", {}).get("changed")),
        "timeouts": sum(1 for item in results if item.get("timeout")),
        "failed": sum(1 for item in results if not item.get("ok")),
        "report": report_path.relative_to(REPO_ROOT).as_posix(),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
