#!/usr/bin/env bash
# Plantilla compartida UAS; Arial real mediante LuaLaTeX y APA mediante Biber.
set -euo pipefail
subject_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$subject_dir/../../.." && pwd -P)"
stem='reporte-actividad-final-materialidad-operaciones-facturadas'
build_dir="$repo_root/.build/latex/$stem-uas"
for executable in latexmk lualatex biber; do
    command -v "$executable" >/dev/null || { printf 'Falta %s\n' "$executable" >&2; exit 127; }
done
mkdir -p -- "$build_dir"
export TEXINPUTS="$subject_dir//:${TEXINPUTS:-}"
export BIBINPUTS="$subject_dir//:${BIBINPUTS:-}"
cd -- "$repo_root"
latexmk -norc -r "$repo_root/.latexmkrc" -lualatex \
    -interaction=nonstopmode -file-line-error -halt-on-error \
    "-outdir=$build_dir" "-auxdir=$build_dir" "$subject_dir/$stem.tex"
test -s "$build_dir/$stem.pdf"
cp -- "$build_dir/$stem.pdf" "$subject_dir/$stem.pdf"
# Mantener vigente el enlace al PDF que se entregó anteriormente.
mkdir -p -- "$subject_dir/.build"
cp -- "$build_dir/$stem.pdf" "$subject_dir/.build/$stem.pdf"
printf '\nPDF final: %s\n' "$subject_dir/$stem.pdf"