#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf '%s\n' 'Uso: bash scripts/latexmk-build.sh DOCUMENTO[.tex] [--clean-mode none|safe|full]'
}
if (($# == 0)); then
    usage >&2
    exit 2
fi
if [[ "$1" == --help || "$1" == -h ]]; then
    usage
    exit 0
fi
tex_input="$1"
shift
clean_mode=safe
while (($#)); do
    case "$1" in
        --clean-mode)
            if (($# < 2)); then usage >&2; exit 2; fi
            clean_mode="$2"
            shift 2
            ;;
        *) printf 'Opción desconocida: %s\n' "$1" >&2; exit 2 ;;
    esac
done
case "$clean_mode" in
    none|safe|full) ;;
    *) printf 'Modo de limpieza inválido: %s\n' "$clean_mode" >&2; exit 2 ;;
esac

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ "$tex_input" != *.tex ]]; then tex_input+=.tex; fi
if [[ -f "$tex_input" ]]; then
    tex="$(realpath -- "$tex_input")"
elif [[ -f "$repo_root/$tex_input" ]]; then
    tex="$(realpath -- "$repo_root/$tex_input")"
else
    printf 'No existe el documento: %s\n' "$tex_input" >&2
    exit 2
fi
case "$tex" in
    "$repo_root"/*) ;;
    *) printf '%s\n' 'El documento debe estar dentro del repositorio.' >&2; exit 2 ;;
esac
command -v latexmk >/dev/null || { printf '%s\n' 'Falta latexmk; instala TeX Live y latexmk.' >&2; exit 127; }
relative="${tex#"$repo_root/"}"
digest="$(printf '%s' "$relative" | sha256sum)"
digest="${digest:0:16}"
filename="${tex##*/}"
stem="${filename%.tex}"
build_dir="$repo_root/.build/latex/$stem-$digest"
mkdir -p -- "$build_dir"
if [[ "$clean_mode" == full ]]; then
    find "$build_dir" -maxdepth 1 -type f -delete
fi
source_dir="$(dirname -- "$tex")"
export TEXINPUTS="$source_dir//:${TEXINPUTS:-}"
export BIBINPUTS="$source_dir//:${BIBINPUTS:-}"
cd -- "$repo_root"
status=0
latexmk -norc -r "$repo_root/.latexmkrc" -cd- -pdf \
    -interaction=nonstopmode -file-line-error -halt-on-error \
    "-outdir=$build_dir" "-auxdir=$build_dir" "$tex" || status=$?
if ((status != 0)); then exit "$status"; fi
pdf="$build_dir/$stem.pdf"
if [[ ! -f "$pdf" ]]; then
    printf 'latexmk terminó sin generar el PDF esperado: %s\n' "$pdf" >&2
    exit 1
fi
cp -- "$pdf" "$source_dir/$stem.pdf"
printf 'PDF final: %s\n' "$source_dir/$stem.pdf"