#!/usr/bin/env bash
# Compilación autónoma de 3.1 Propuesta de Modelo (Actividad 6 local).
set -euo pipefail

dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$dir/../../.." && pwd)"
out="$root/.build/latex/fga-actividad-6"
name="reporte-fundamentos-de-gestion-administrativa-Actividad-6"

for tool in latexmk xelatex biber fc-match; do
  command -v "$tool" >/dev/null || {
    printf 'Falta la herramienta requerida: %s\n' "$tool" >&2
    exit 1
  }
done

if [[ "$(fc-match --format '%{family}' Arial)" != 'Arial' ]]; then
  printf 'Se requiere Arial auténtica instalada; no se acepta una sustitución silenciosa.\n' >&2
  exit 1
fi

cd -- "$dir"
export TEXINPUTS="$dir:$root:$root/base/Plantilla-Informe//:${TEXINPUTS:-}"
export BIBINPUTS="$dir:$dir/..:${BIBINPUTS:-}"
latexmk -norc -xelatex -interaction=nonstopmode -halt-on-error \
  -file-line-error -outdir="$out" "$name.tex"
test -s "$out/$name.pdf"
# Publicar junto a la fuente solo después de una compilación exitosa.
cp -- "$out/$name.pdf" "$dir/$name.pdf"
printf '\nPDF generado: %s\n' "$dir/$name.pdf"