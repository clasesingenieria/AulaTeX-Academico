#!/usr/bin/env bash
# Esta actividad exige Arial real y APA: no usar el wrapper general pdfLaTeX.
set -euo pipefail
materia_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$materia_dir/../../.." && pwd)"
build_dir="$repo_dir/.build/latex/fga-actividad-8-xelatex"
documento="reporte-fundamentos-de-gestion-administrativa-Actividad-8"

for herramienta in latexmk xelatex biber fc-match; do
  command -v "$herramienta" >/dev/null || {
    printf 'Falta la herramienta requerida: %s\n' "$herramienta" >&2
    exit 1
  }
done
if [[ "$(fc-match -f '%{family}' Arial)" != *Arial* ]]; then
  printf 'Se requiere Arial instalada; no se sustituye por Helvetica.\n' >&2
  exit 1
fi

mkdir -p -- "$build_dir"
cd -- "$materia_dir"
latexmk -norc -xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
  -outdir="$build_dir" -auxdir="$build_dir" "$documento.tex"
cp -- "$build_dir/$documento.pdf" "$materia_dir/$documento.pdf"
printf '\nPDF generado: %s/%s.pdf\n' "$materia_dir" "$documento"