import os
import subprocess
import time
import sys

PROMPT = (
    "Usa la siguiente planeación como contexto:\n\n"
    "# Actividad 10 — Formulación de objetivos\n- Cierre: 4 de octubre de 2026, 23:59.\n\n"
    "Producto previsto:\nObjetivo general y objetivos específicos coherentes con la pregunta, el alcance y la evidencia disponible.\n"
    "- Emplear verbos observables.\n- Evitar actividades administrativas como objetivos de conocimiento.\n"
    "- Verificar que los específicos produzcan el general.\n- Asociar cada objetivo con procedimiento y evidencia.\n\n"
    "Genera: 1) Un Objetivo general (una oración clara). 2) Cuatro objetivos específicos en infinitivo, observables y verificables."
    " 3) Para cada objetivo específico añade una breve línea con 'Evidencia:' y 'Procedimiento:'. Mantén un tono académico y conciso."
)

OUTDIR = os.path.join(
    "ITESCA",
    "maestria-en-gestion-administrativa",
    "seminario-i-mga",
    "planeaciones-seminario-i",
    "unidad-3",
)
OUTFILE = os.path.join(OUTDIR, "planeacion-actividad-10-grok.md")


def run_once(argv):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
        out = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        return out.strip()
    except subprocess.TimeoutExpired:
        return "Tiempo de espera agotado."


def main():
    attempts = 5
    delay = 6
    python = sys.executable
    for i in range(1, attempts + 1):
        print(f"=== attempt {i} ===")
        argv = [
            python,
            "-m",
            "scripts.aulatex.cli",
            "llm-prompt",
            PROMPT,
            "--engine",
            "Grok-Pensamiento-Libre",
            "--max-tokens",
            "512",
            "--timeout-seconds",
            "240",
        ]
        result = run_once(argv)
        # Save attempt log
        logdir = ".aulatex-temp"
        os.makedirs(logdir, exist_ok=True)
        open(os.path.join(logdir, f"attempt-{i}.txt"), "w", encoding="utf-8").write(result)

        if result and all(x not in result for x in ("Tiempo de espera", "HTTP 429", "Too Many Requests")):
            # ensure outdir exists
            os.makedirs(OUTDIR, exist_ok=True)
            with open(OUTFILE, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"SAVED: {OUTFILE}")
            return 0

        print(f"FAILED attempt {i}; sleeping {delay} s")
        time.sleep(delay)
        delay *= 2

    print("DONE without successful response")
    return 2


if __name__ == "__main__":
    sys.exit(main())
