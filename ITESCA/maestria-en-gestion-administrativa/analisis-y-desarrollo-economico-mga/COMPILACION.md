# Compilacion - Analisis y Desarrollo Economico

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\analisis-y-desarrollo-economico-mga\\reporte-analisis-y-desarrollo-economico-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\analisis-y-desarrollo-economico-mga\\presentacion-analisis-y-desarrollo-economico-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en analisis-y-desarrollo-economico.bib.
- Esta carpeta corresponde a la categoria tronco comun MGA.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.

## Checklist editorial

- Usar indicadores oficiales con periodo, unidad de medida y cobertura territorial.
- Distinguir crecimiento, desarrollo, bienestar, productividad y competitividad.
- Traducir cada dato a una decision administrativa, sectorial o institucional.
- Evitar listados de cifras sin interpretacion: toda evidencia debe cerrar con implicacion.
- La carpeta `referencias-analisis-y-desarrollo-economico/` resguarda fuentes,
  tabulados y notas de lectura de la materia.
