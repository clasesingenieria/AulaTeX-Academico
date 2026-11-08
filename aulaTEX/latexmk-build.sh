#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf '%s\n' 'Uso: bash aulaTEX/latexmk-build.sh DOCUMENTO[.tex] [--engine auto|pdflatex|xelatex|lualatex] [--clean-mode none|safe|full]'
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
engine=auto
while (($#)); do
    case "$1" in
        --engine)
            if (($# < 2)); then usage >&2; exit 2; fi
            engine="$2"
            shift 2
            ;;
        --clean-mode)
            if (($# < 2)); then usage >&2; exit 2; fi
            clean_mode="$2"
            shift 2
            ;;
        *) printf 'Opción desconocida: %s\n' "$1" >&2; exit 2 ;;
    esac
done
case "$engine" in
    auto|pdflatex|xelatex|lualatex) ;;
    *) printf 'Motor TeX inválido: %s\n' "$engine" >&2; exit 2 ;;
esac
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
elif [[ "$clean_mode" == safe ]]; then
    find "$build_dir" -maxdepth 1 -type f -name '*.log' -size 0 -delete
fi
source_dir="$(dirname -- "$tex")"
source_dir_for_tex="$source_dir"
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) source_dir_for_tex="$(cygpath -w "$source_dir")" ;;
esac
export AULATEX_SOURCE_DIR="$source_dir_for_tex"
cd -- "$repo_root"
if [[ "$engine" == auto ]]; then
    directive="$(sed -nE 's/^[[:space:]]*%[[:space:]]*!TeX[[:space:]]+program[[:space:]]*=[[:space:]]*(xelatex|lualatex|pdflatex).*$/\1/ip' "$tex" | head -n 1)"
    if [[ -n "$directive" ]]; then
        engine="${directive,,}"
    elif grep -Eiq '\\usepackage(\[[^]]*\])?\{[^}]*fontspec|\\set(main|sans|mono)font' "$tex"; then
        engine=xelatex
    else
        engine=pdflatex
    fi
fi
case "$engine" in
    xelatex) engine_flag=-xelatex ;;
    lualatex) engine_flag=-lualatex ;;
    *) engine_flag=-pdf ;;
esac
printf 'Motor TeX: %s\n' "$engine"
status=0
latexmk -norc -r "$repo_root/.latexmkrc" "$engine_flag" \
    -interaction=nonstopmode -file-line-error -halt-on-error \
    "-outdir=$build_dir" "-auxdir=$build_dir" "$relative" || status=$?
if ((status != 0)); then exit "$status"; fi
pdf="$build_dir/$stem.pdf"
if [[ ! -s "$pdf" || "$pdf" -ot "$tex" ]]; then
    printf 'latexmk no generó un PDF válido y actualizado: %s\n' "$pdf" >&2
    exit 1
fi
bcf="$build_dir/$stem.bcf"
bbl="$build_dir/$stem.bbl"
if [[ -f "$bcf" && ( ! -s "$bbl" ) ]]; then
    printf 'latexmk no produjo una bibliografía Biber válida para %s\n' "$tex" >&2
    exit 1
fi
log="$build_dir/$stem.log"
if [[ -f "$log" ]] && grep -Eiq '^LaTeX Warning: Citation .+ undefined' "$log"; then
    printf 'El PDF conserva citas bibliográficas sin resolver; consulta %s\n' "$log" >&2
    exit 1
fi
cp -- "$pdf" "$source_dir/$stem.pdf"
printf 'PDF final: %s\n' "$source_dir/$stem.pdf"
if [[ "$clean_mode" == safe ]]; then
    find "$build_dir" -maxdepth 1 -type f \( \
        -name '*.aux' -o -name '*.bbl' -o -name '*.bcf' -o -name '*.blg' \
        -o -name '*.fdb_latexmk' -o -name '*.fls' -o -name '*.lof' \
        -o -name '*.lot' -o -name '*.nav' -o -name '*.out' \
        -o -name '*.run.xml' -o -name '*.snm' -o -name '*.synctex.gz' \
        -o -name '*.toc' -o -name '*.vrb' -o -name '*.xdv' \
    \) -delete
fi
if [[ "$clean_mode" != none ]]; then
    for extension in aux bbl bcf blg fdb_latexmk fls lof log lot nav out run.xml snm toc vrb xdv; do
        rm -f -- "$source_dir/$stem.$extension"
    done
    rm -f -- "$source_dir/$stem.synctex.gz"
fi