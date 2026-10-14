"""Orquestador de mejora iterativa del mapa conceptual (Actividad 3).

En cada ciclo un motor LLM (rota entre los indicados) analiza el mapa actual
y los conceptos del extractor, y propone en JSON subconceptos NUEVOS (no
presentes). El orquestador los apila de forma segura debajo de la ultima hoja
de cada rama, compila y, si rompe la compilacion, revierte. Cae al extractor
cuando detecta estancamiento.

Uso:
  python aulaTEX/mejora_mapa_iterativa.py --cycles 100 \
    --tex <ruta.tex> --activity 3 \
    --engine GPT-5.6-SOL --engine GPT-5.6-Luna --engine GPT-5.6-Terra
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "aulaTEX"))

from aulatex.llm_bridge import AulaTeXLLMClient  # noqa: E402
from aulatex.config import load_aulatex_env  # noqa: E402

BEGIN = "% >>> MC-ENRIQUECIMIENTO-INICIO"
END = "% >>> MC-ENRIQUECIMIENTO-FIN"
TEXLIVE_BIN = r"C:\texlive\2026\bin\windows"

BRANCHES = {
    "hist": "1.1 Antecedentes históricos",
    "gen": "1.2 Generaciones de los derechos",
    "concepto": "1.3 Concepto de derecho humano",
    "princ": "1.4 Principios (art. 1.º constitucional)",
    "gar": "1.5 Concepto de garantía",
}
BASE_TAIL = {"hist": "hist4", "gen": "gen4", "concepto": "con4", "princ": "pr5", "gar": "ga4"}
MAX_PER_BRANCH = 4


def latex_escape(text: str) -> str:
    repl = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def read_managed_block(tex: str) -> str:
    start = tex.index(BEGIN) + len(BEGIN)
    end = tex.index(END)
    return tex[start:end]


def write_managed_block(tex: str, body: str) -> str:
    start = tex.index(BEGIN) + len(BEGIN)
    end = tex.index(END)
    return tex[:start] + "\n" + body.rstrip() + "\n" + tex[end:]


def base_concepts(tex: str) -> list[str]:
    texts = re.findall(r"\\node\[(?:mcleaf|mcsub|mcbranch|mcroot)[^\]]*\]\s*\([a-zA-Z0-9]+\)\s*\{([^}]*)\}", tex)
    return [re.sub(r"\\[a-zA-Z]+|\{|\}", "", t).strip() for t in texts]


def load_extractor_ideas(subject_dir: Path) -> list[dict]:
    path = subject_dir / "extractor-aulatex" / "ideas_detectadas.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def build_prompt(base_terms, added, extractor_ideas, per_branch, cycle, total) -> str:
    ideas_txt = "\n".join(
        f"- {i.get('concepto','')}: {str(i.get('idea_base',''))[:200]} (fuente: {i.get('fuente','')})"
        for i in extractor_ideas[:11]
    )
    base_txt = "\n".join(f"- {t}" for t in base_terms if t)
    added_txt = "\n".join(f"- [{r}] {t}" for r, t in added[-50:]) or "(ninguno aún)"
    capacity = ", ".join(f"{r}:{MAX_PER_BRANCH - per_branch.get(r,0)}" for r in BRANCHES)
    return f"""Eres jurista experto en derecho constitucional mexicano y en mapas conceptuales.
Enriqueces el mapa del Tema 1 "Marco teórico de los derechos humanos y sus principios"
(Garantías Constitucionales, UnADM). Ciclo {cycle}/{total}.

Ramas (identificador -> título):
  hist -> 1.1 Antecedentes históricos
  gen  -> 1.2 Generaciones de los derechos
  concepto -> 1.3 Concepto de derecho humano
  princ -> 1.4 Principios (art. 1.º constitucional)
  gar  -> 1.5 Concepto de garantía

Cupo restante por rama (no lo excedas): {capacity}

CONCEPTOS YA PRESENTES (NO repitas ni parafrasees):
{base_txt}

SUBCONCEPTOS YA AGREGADOS (NO repitas):
{added_txt}

Ideas extraídas de los libros del curso (fuente de verdad):
{ideas_txt}

TAREA: propón 1 a 2 subconceptos NUEVOS y RELEVANTES que aporten profundidad real
(no sinónimos de lo presente): matices, subtipos, ejemplos jurídicos, fundamentos
normativos o consecuencias. Cada subconcepto <= 80 caracteres, jurídicamente correcto,
anclado al Tema 1 y a las fuentes.

Responde SOLO JSON válido, sin markdown:
{{"nodos":[{{"rama":"hist|gen|concepto|princ|gar","texto":"..."}}]}}
Si el mapa ya cubre con suficiencia el Tema 1, responde: {{"nodos":[],"saturado":true}}
"""


def parse_json(text: str):
    m = re.search(r"\{.*\}", text.strip(), re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def compile_tex(tex_path: Path) -> tuple[bool, str]:
    env = dict(os.environ)
    env["PATH"] = TEXLIVE_BIN + os.pathsep + env.get("PATH", "")
    ps = REPO / "aulaTEX" / "latexmk-build.ps1"
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"& '{ps}' '{tex_path}'"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env, timeout=600,
    )
    ok = proc.returncode == 0 and tex_path.with_suffix(".pdf").exists()
    return ok, (proc.stdout[-1200:] + "\n" + proc.stderr[-600:])


def render_block(nodes_by_branch: dict[str, list[str]]) -> str:
    lines: list[str] = []
    counter = 0
    for br, tail in BASE_TAIL.items():
        prev = tail
        for txt in nodes_by_branch.get(br, []):
            counter += 1
            nid = f"mx{counter}"
            lines.append(f"\\node[mcsub, below=0.3cm of {prev}] ({nid}) {{{latex_escape(txt)}}};")
            lines.append(f"\\draw[mclink] ({prev}) -- ({nid});")
            prev = nid
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True)
    ap.add_argument("--activity", type=int, default=3)
    ap.add_argument("--cycles", type=int, default=100)
    ap.add_argument("--engine", action="append", default=[])
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    load_aulatex_env()
    tex_path = Path(args.tex)
    if not tex_path.is_absolute():
        tex_path = (REPO / args.tex).resolve()
    subject_dir = tex_path.parent
    engines = args.engine or ["GPT-5.6-SOL", "GPT-5.6-Luna", "GPT-5.6-Terra"]
    client = AulaTeXLLMClient()
    extractor_ideas = load_extractor_ideas(subject_dir)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = REPO / "aulaTEX" / "retroalimentacion-editorial" / "aulatex" / "mejora-mapa" / "runs" / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    base_terms = base_concepts(tex_path.read_text(encoding="utf-8"))
    base_norm = {norm(t) for t in base_terms}

    nodes_by_branch: dict[str, list[str]] = {b: [] for b in BRANCHES}
    added: list[tuple[str, str]] = []
    per_branch: dict[str, int] = {b: 0 for b in BRANCHES}
    saturation_streak = 0

    for cycle in range(1, args.cycles + 1):
        engine = engines[(cycle - 1) % len(engines)]
        prompt = build_prompt(base_terms, added, extractor_ideas, per_branch, cycle, args.cycles)

        t0 = time.time()
        try:
            res = client.call(engine, prompt, max_tokens=800, timeout_seconds=args.timeout)
            raw, err = (res.text, "") if res.ok else ("", res.error)
        except Exception as exc:  # noqa: BLE001
            raw, err = "", str(exc)
        dt = round(time.time() - t0, 1)

        data = parse_json(raw) if raw else None
        added_this: list[tuple[str, str]] = []

        if data and not data.get("saturado"):
            for node in (data.get("nodos") or [])[:2]:
                br = str(node.get("rama", "")).strip()
                txt = str(node.get("texto", "")).strip()
                if br not in BRANCHES or not txt or len(txt) > 90:
                    continue
                if norm(txt) in base_norm or any(norm(txt) == norm(a) for _, a in added):
                    continue
                if per_branch[br] >= MAX_PER_BRANCH:
                    continue
                nodes_by_branch[br].append(txt)
                per_branch[br] += 1
                added.append((br, txt))
                added_this.append((br, txt))

        applied = False
        compile_ok = None
        if added_this:
            tex = tex_path.read_text(encoding="utf-8")
            candidate = write_managed_block(tex, render_block(nodes_by_branch))
            backup = tex_path.with_suffix(tex_path.suffix + ".mejora.bak")
            backup.write_text(tex, encoding="utf-8")
            tex_path.write_text(candidate, encoding="utf-8")
            compile_ok, _log = compile_tex(tex_path)
            if compile_ok:
                applied = True
                saturation_streak = 0
            else:
                tex_path.write_text(tex, encoding="utf-8")
                for br, txt in added_this:
                    if nodes_by_branch[br] and nodes_by_branch[br][-1] == txt:
                        nodes_by_branch[br].pop()
                        per_branch[br] -= 1
                added = added[: len(added) - len(added_this)]
                added_this = []
        else:
            saturation_streak += 1

        checkpoint = {
            "cycle": cycle, "engine": engine, "elapsed_s": dt,
            "llm_ok": bool(raw), "llm_error": err,
            "added": [f"{b}: {t}" for b, t in added_this],
            "applied": applied, "compile_ok": compile_ok,
            "total_added": len(added), "per_branch": dict(per_branch),
            "saturation_streak": saturation_streak,
        }
        (run_dir / f"cycle-{cycle:03d}.json").write_text(
            json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({k: checkpoint[k] for k in ("cycle", "engine", "added", "applied", "compile_ok", "total_added")}, ensure_ascii=False), flush=True)

        if saturation_streak and saturation_streak % 8 == 0:
            extractor_ideas = load_extractor_ideas(subject_dir) or extractor_ideas
        if all(per_branch[b] >= MAX_PER_BRANCH for b in BRANCHES):
            print(json.dumps({"stop": "todas_las_ramas_llenas", "total_added": len(added)}), flush=True)
            break

    summary = {"run": ts, "total_added": len(added), "per_branch": per_branch,
               "nodes": [f"{b}: {t}" for b, t in added]}
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"done": True, "total_added": len(added), "run_dir": str(run_dir)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
