"""Construye corpus de entrenamiento a partir del material editorial YA EXISTENTE.

Complementa ``build_reward_corpus.py`` en lugar de reemplazarlo. Aquel exige
corridas de ``activity-optimize`` (``manifest.json`` + ``proposal.json``); este
no espera a que existan y aprovecha lo que el repositorio ya contiene:

1. ``reward.jsonl``     — regresion (texto -> score de calidad).
   Fuente: todos los TEX de actividad del workspace, puntuados con el MISMO
   ``_quality_score`` determinista que usa el optimizador. No hay LLM ni costo:
   el score sale de contar citas, secciones tematicas, conectores y estructura.

2. ``preference.jsonl`` — pares (chosen, rejected) para DPO.
   Fuentes, en orden de confiabilidad:
     a) respaldos ``*.tex.activity-optimize.bak`` frente al TEX actual;
     b) revisiones consecutivas del historial de git del mismo archivo.
   Solo se conserva el par si el score MEJORA: una revision posterior que
   empeora la calidad no es una preferencia, es un retroceso.

Honestidad sobre los limites
----------------------------
* El score es un proxy heuristico, no juicio humano. Entrenar un reward model
  contra el proxy reproduce sus sesgos: sirve para ACELERAR la busqueda, no
  para redefinir que es calidad. Por eso ``--min-gain`` descarta ruido.
* Las revisiones de git incluyen cambios no editoriales (renombres, arreglos de
  compilacion). El filtro de ganancia minima los descarta en su mayoria, pero
  el corpus resultante es mas ruidoso que el de ``activity-optimize``.
* Se deduplica por (texto normalizado) para no inflar el dataset con copias.

Uso:
    python aulaTEX/aulatex_training/build_corpus_from_repo.py
    python aulaTEX/aulatex_training/build_corpus_from_repo.py --no-git
    python aulaTEX/aulatex_training/build_corpus_from_repo.py --min-gain 2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Un TEX mas corto que esto es un esqueleto sin contenido evaluable.
MIN_TEX_CHARS = 400
# Ganancia minima de score para aceptar un par de preferencia. Por debajo, el
# cambio suele ser cosmetico (typo, espaciado) y mete ruido en el DPO.
DEFAULT_MIN_GAIN = 1.0
# Carpetas que no contienen trabajo del alumno.
EXCLUDED_PARTS = {".git", ".venv", "base", "node_modules", "__pycache__"}


def load_scorer():
    """Devuelve la funcion de score determinista del optimizador.

    Se instancia sin ``__init__`` a proposito: el constructor real levanta
    workspace y cliente LLM, y aqui solo hace falta el metodo de scoring.
    """
    sys.path.insert(0, str(REPO_ROOT / "aulaTEX"))
    from aulatex.activity_optimizer import ActivityOptimizer

    optimizer = ActivityOptimizer.__new__(ActivityOptimizer)
    optimizer._current_concepts = None
    return optimizer._quality_score


def is_relevant(path: Path) -> bool:
    if EXCLUDED_PARTS.intersection(path.parts):
        return False
    name = path.name.lower()
    return name.startswith(("reporte-", "presentacion-")) and name.endswith(".tex")


def iter_activity_tex(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.tex")):
        if is_relevant(path):
            yield path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def evaluable_body(text: str) -> str:
    """Cuerpo del documento sin preambulo ni comentarios.

    Con ``--max-length`` el modelo solo ve el inicio del texto. Sin esta poda,
    ese inicio es el preambulo de la plantilla (identico en cientos de archivos)
    y el corpus queda 40% duplicado en la ventana visible. El scorer ya ignora
    los comentarios, asi que esto alinea la entrada del modelo con lo que el
    score realmente mide.
    """
    match = re.search(r"\\begin\{document\}", text)
    body = text[match.end():] if match else text
    body = re.sub(r"\\end\{document\}.*", "", body, flags=re.DOTALL)
    lines = [line for line in body.splitlines() if not line.lstrip().startswith("%")]
    body = "\n".join(lines)
    # Andamiaje de la plantilla: portada, indices y macros de maquetado son
    # identicos en cientos de archivos y no aportan senal de calidad.
    body = re.sub(
        r"^\s*\\(insertcoverwatermark|template\w+|onehalfspacing|clearpage|newpage|"
        r"tableofcontents|listoffigures|listoftables|maketitle|selectlanguage\{[^}]*\})\s*$",
        "", body, flags=re.MULTILINE)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def fingerprint(text: str) -> str:
    """Hash del texto normalizado, para deduplicar sin depender de espacios."""
    return hashlib.sha1(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


def institution_of(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        return ""


# ------------------------------------------------------------------ reward set
def build_reward_rows(root: Path, score_of: Any,
                      min_score: float = 0.0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for path in iter_activity_tex(root):
        text = read_text(path)
        if len(text) < MIN_TEX_CHARS or "POR DEFINIR" in text:
            continue
        score = float(score_of(text))
        if score < min_score:
            continue
        # El score se mide sobre el documento completo; el modelo recibe solo el
        # cuerpo, que es donde vive la señal de calidad.
        body = evaluable_body(text)
        if len(body) < MIN_TEX_CHARS:
            continue
        key = fingerprint(body)
        if key in seen:
            continue
        seen.add(key)
        rel = path.relative_to(root).as_posix()
        activity = re.search(r"Actividad-(\d+)", path.name)
        rows.append({
            "text": body,
            "score": round(score, 2),
            "source": "workspace-validated" if min_score > 0 else "workspace",
            "target": rel,
            "institution": institution_of(path, root),
            "activity_number": int(activity.group(1)) if activity else 0,
            "kind": "presentacion" if path.name.startswith("presentacion-") else "reporte",
        })
    return rows


# -------------------------------------------------------------- preference set
def git_revisions(root: Path, rel_path: str) -> list[str]:
    """Commits que tocaron el archivo, del mas antiguo al mas reciente."""
    result = subprocess.run(
        ["git", "log", "--reverse", "--format=%H", "--", rel_path],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_show(root: Path, commit: str, rel_path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{rel_path}"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    return result.stdout if result.returncode == 0 else ""


PREFERENCE_PROMPT = (
    "Mejora el siguiente fragmento LaTeX academico elevando rigor, fuentes citadas "
    "y densidad argumentativa, conservando la tecnica didactica."
)


def make_pair(before: str, after: str, score_of: Any, min_gain: float,
              origin: str, target: str) -> dict[str, Any] | None:
    if len(before) < MIN_TEX_CHARS or len(after) < MIN_TEX_CHARS:
        return None
    gain = float(score_of(after)) - float(score_of(before))
    if gain < min_gain:
        return None
    chosen, rejected = evaluable_body(after), evaluable_body(before)
    if len(chosen) < MIN_TEX_CHARS or len(rejected) < MIN_TEX_CHARS:
        return None
    if fingerprint(chosen) == fingerprint(rejected):
        return None
    return {
        "prompt": PREFERENCE_PROMPT,
        "chosen": chosen,
        "rejected": rejected,
        "quality_gain": round(gain, 2),
        "source": origin,
        "target": target,
    }


def extract_tex_document(text: str) -> str:
    """Devuelve el documento LaTeX completo contenido en una respuesta del arquitecto."""
    if not text:
        return ""
    candidates: list[str] = [m.group(1) for m in
                             re.finditer(r"```(?:la)?tex\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)]
    if not candidates:
        candidates = [m.group(1) for m in re.finditer(r"```\s*\n(.*?)```", text, re.DOTALL)]
    if not candidates:
        candidates = [text]
    for body in sorted(candidates, key=len, reverse=True):
        if r"\begin{document}" in body and r"\end{document}" in body and "\\documentclass" in body:
            start = body.index("\\documentclass")
            end = body.index(r"\end{document}") + len(r"\end{document}")
            return body[start:end].strip()
    return ""


def iter_agent_proposal_pairs(root: Path, score_of: Any, min_gain: float):
    """Pares (propuesta del arquitecto -> TEX final) de las corridas realizar-actividad."""
    runs_dir = root / "retroalimentacion-editorial" / "aulatex" / "runs"
    if not runs_dir.is_dir():
        return
    for run in sorted(runs_dir.glob("*realizar-actividad*")):
        manifests = list(run.rglob("manifest.json"))
        if not manifests:
            continue
        try:
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        targets = [c.get("tex") for c in (manifest.get("compile_results") or [])
                   if isinstance(c, dict) and str(c.get("tex", "")).find("reporte-") >= 0]
        if not targets:
            continue
        final_path = root / str(targets[0])
        if not final_path.exists():
            continue
        final_tex = read_text(final_path)
        for stage in run.rglob("stage-*generar*.md"):
            proposal = extract_tex_document(read_text(stage))
            if not proposal:
                continue
            yield make_pair(proposal, final_tex, score_of, min_gain,
                            "agent-proposal", str(targets[0]))


def iter_optimizer_block_pairs(root: Path):
    """Pares a nivel de bloque desde los proposal.json del optimizador.

    No se filtran por ganancia de score global: la mejora es local y el score
    mide el documento completo. La justificación del motor acompaña al par.
    """
    base = root / "retroalimentacion-editorial" / "aulatex"
    # El optimizador escribe en activity-optimize/runs; el agente en runs.
    runs_dirs = [base / "activity-optimize" / "runs", base / "runs"]
    for runs_dir in runs_dirs:
        if not runs_dir.is_dir():
            continue
        for proposal_path in sorted(runs_dir.rglob("proposal.json")):
            try:
                data = json.loads(proposal_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            before = str(data.get("original_block", "")).strip()
            after = str(data.get("improved_block", "")).strip()
            if len(before) < 40 or len(after) < 40 or before == after:
                continue
            yield {
                "prompt": PREFERENCE_PROMPT,
                "chosen": after,
                "rejected": before,
                "quality_gain": 0.0,
                "source": "optimizer-block",
                "target": data.get("improvement_kind", ""),
                "justification": str(data.get("justification", ""))[:300],
            }


def build_preference_rows(root: Path, score_of: Any, min_gain: float,
                          use_git: bool) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    stats = {"bak": 0, "agent": 0, "blocks": 0, "git": 0, "git_files": 0, "discarded": 0}
    seen: set[tuple[str, str]] = set()

    def add(pair: dict[str, Any] | None) -> bool:
        if pair is None:
            stats["discarded"] += 1
            return False
        key = (fingerprint(pair["rejected"]), fingerprint(pair["chosen"]))
        if key in seen:
            return False
        seen.add(key)
        rows.append(pair)
        return True

    # (a) Respaldos del optimizador: la evidencia mas directa.
    for bak in sorted(root.rglob("*.tex.activity-optimize.bak")):
        if EXCLUDED_PARTS.intersection(bak.parts):
            continue
        current = bak.with_name(bak.name.replace(".activity-optimize.bak", ""))
        if not current.exists():
            continue
        if add(make_pair(read_text(bak), read_text(current), score_of, min_gain,
                         "backup", current.relative_to(root).as_posix())):
            stats["bak"] += 1

    # (a2) Propuestas del arquitecto en corridas de realizar-actividad frente al
    # TEX final validado: enseñan a corregir los fallos reales del motor
    # (plantilla equivocada, biblatex en vez de natbib, técnica mal detectada).
    for pair in iter_agent_proposal_pairs(root, score_of, min_gain):
        if add(pair):
            stats["agent"] += 1

    # (a3) Bloques del optimizador: cada proposal.json es una mejora quirúrgica
    # (original_block -> improved_block) sobre un punto concreto del texto. Son
    # la señal más limpia porque aíslan QUÉ cambió y por qué.
    for pair in iter_optimizer_block_pairs(root):
        if add(pair):
            stats["blocks"] += 1

    if not use_git:
        return rows, stats

    # (b) Revisiones consecutivas en git del mismo archivo.
    for path in iter_activity_tex(root):
        rel = path.relative_to(root).as_posix()
        commits = git_revisions(root, rel)
        if len(commits) < 2:
            continue
        stats["git_files"] += 1
        previous = git_show(root, commits[0], rel)
        for commit in commits[1:]:
            current = git_show(root, commit, rel)
            if not current:
                continue
            if add(make_pair(previous, current, score_of, min_gain, "git", rel)):
                stats["git"] += 1
            previous = current

    return rows, stats


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="build_corpus_from_repo",
        description="Genera reward.jsonl y preference.jsonl desde el material editorial existente.",
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help="Raiz del workspace a recorrer.")
    parser.add_argument("--out-dir", default="", help="Carpeta de salida del corpus.")
    parser.add_argument("--min-gain", type=float, default=DEFAULT_MIN_GAIN,
                        help="Ganancia minima de score para aceptar un par de preferencia.")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Score editorial minimo del TEX; usa 95 para actividades validadas.")
    parser.add_argument("--no-git", action="store_true",
                        help="Omite el historial de git (mas rapido, menos pares).")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (
        root / "retroalimentacion-editorial" / "aulatex" / "training")

    score_of = load_scorer()

    print("[corpus] recorriendo TEX del workspace...")
    reward_rows = build_reward_rows(root, score_of, args.min_score)
    print(f"[corpus] ejemplos reward        : {len(reward_rows)}")

    print("[corpus] extrayendo pares de preferencia"
          f"{' (sin git)' if args.no_git else ' (incluye historial git)'}...")
    preference_rows, stats = build_preference_rows(root, score_of, args.min_gain, not args.no_git)

    reward_path = out_dir / "reward.jsonl"
    preference_path = out_dir / "preference.jsonl"
    write_jsonl(reward_path, reward_rows)
    write_jsonl(preference_path, preference_rows)

    print()
    print(f"[corpus] reward.jsonl           : {len(reward_rows)}  -> {reward_path}")
    print(f"[corpus] preference.jsonl       : {len(preference_rows)}  -> {preference_path}")
    print(f"[corpus]   desde respaldos .bak : {stats['bak']}")
    print(f"[corpus]   desde el arquitecto  : {stats['agent']}")
    print(f"[corpus]   bloques del optimizador: {stats['blocks']}")
    print(f"[corpus]   desde historial git  : {stats['git']} (en {stats['git_files']} archivos)")
    print(f"[corpus]   descartados          : {stats['discarded']} (sin ganancia o muy cortos)")

    if not reward_rows:
        print("\n[corpus] ABORTA: no se encontro ningun TEX de actividad puntuable.")
        return 1

    scores = [row["score"] for row in reward_rows]
    stdev = statistics.pstdev(scores) if len(scores) > 1 else 0.0
    print()
    print(f"[corpus] score min/media/max    : {min(scores):.1f} / "
          f"{statistics.mean(scores):.1f} / {max(scores):.1f}")
    print(f"[corpus] desviacion (std)       : {stdev:.2f}")

    # Con --max-length el modelo solo ve el inicio; si ahi todo se parece, no aprende.
    prefixes = {fingerprint(row["text"][:1000]) for row in reward_rows}
    duplication = 100.0 * (1 - len(prefixes) / len(reward_rows))
    print(f"[corpus] duplicacion en 1000 ch : {duplication:.1f}% "
          f"({len(prefixes)} prefijos unicos)")
    if duplication > 20.0:
        print("[corpus] AVISO: mucha duplicacion en la ventana visible del modelo;"
              " sube --max-length al entrenar.")

    # Mismos umbrales que exige train_reward_model.py, para avisar antes de entrenar.
    ok_examples = len(reward_rows) >= 50
    ok_variance = stdev >= 2.0
    print(f"[corpus] minimo 50 ejemplos     : {'CUMPLE' if ok_examples else 'NO CUMPLE'}")
    print(f"[corpus] desviacion minima 2.0  : {'CUMPLE' if ok_variance else 'NO CUMPLE'}")

    if not (ok_examples and ok_variance):
        print("\n[corpus] AVISO: el corpus no alcanza los minimos de train_reward_model.py.")
        return 1

    print("\n[corpus] Corpus listo. Siguiente paso:")
    print(f"    python aulaTEX/aulatex_training/train_reward_model.py --train-file {reward_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
