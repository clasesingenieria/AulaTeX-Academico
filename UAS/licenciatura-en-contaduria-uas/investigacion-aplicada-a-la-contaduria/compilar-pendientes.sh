#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for herramienta in latexmk lualatex biber pdfinfo pdffonts pdfdetach; do
    command -v "$herramienta" >/dev/null || {
        printf 'Falta la herramienta: %s\n' "$herramienta" >&2
        exit 127
    }
done

documentos=(
    TI_S2_MartinDelaCruz
    TI_S3_MartinDelaCruz
    TI_S4_MartinDelaCruz
    PI_MOD_MartinDelaCruz
    reporte-foro-S1
    reporte-foro-S2
    reporte-foro-S3
    reporte-foro-S4
)
salida=.build/pendientes
mkdir -p -- "$salida"

for documento in "${documentos[@]}"; do
    latexmk -norc -silent -lualatex -interaction=nonstopmode -halt-on-error \
        "-outdir=$salida" "$documento.tex"
    pdf="$salida/$documento.pdf"
    if grep -Eq 'Overfull|undefined|Fatal error|LaTeX Error' "$salida/$documento.log"; then
        printf 'Revisar advertencias en %s/%s.log\n' "$salida" "$documento" >&2
        exit 1
    fi
    bytes=$(stat -c '%s' "$pdf")
    if ((bytes > 2000000)); then
        printf 'PDF mayor a 2 MB: %s (%s bytes)\n' "$pdf" "$bytes" >&2
        exit 1
    fi
    if ! pdffonts "$pdf" | grep -q 'Arial'; then
        printf 'No se detectó Arial en %s\n' "$pdf" >&2
        exit 1
    fi
    if [[ "$documento" == reporte-foro-S* ]]; then
        semana="${documento##*-}"
        adjuntos="$salida/adjuntos-$semana"
        mkdir -p -- "$adjuntos"
        pdfdetach -list "$pdf" | grep -q '^2 embedded files$'
        pdfdetach -saveall -o "$adjuntos" "$pdf"
        cmp -- "foro-$semana-principal.txt" "$adjuntos/foro-$semana-principal.txt"
        cmp -- "foro-$semana-replica-modelo.txt" "$adjuntos/foro-$semana-replica-modelo.txt"
    fi
    cp -- "$pdf" "$documento.pdf"
    printf '\nVERIFICADO: %s.pdf (%s bytes)\n' "$documento" "$bytes"
    pdfinfo "$pdf" | grep -E '^Pages:|^Page size:'
done

printf '\nOcho PDF generados. La validación técnica no acredita entrega en Moodle.\n'