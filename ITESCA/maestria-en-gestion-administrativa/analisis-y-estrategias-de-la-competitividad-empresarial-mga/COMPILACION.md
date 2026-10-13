# Compilacion - Analisis y Estrategias de la Competitividad Empresarial

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\analisis-y-estrategias-de-la-competitividad-empresarial-mga\\reporte-analisis-y-estrategias-de-la-competitividad-empresarial-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\analisis-y-estrategias-de-la-competitividad-empresarial-mga\\presentacion-analisis-y-estrategias-de-la-competitividad-empresarial-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en analisis-y-estrategias-de-la-competitividad-empresarial.bib.
- Esta carpeta corresponde a la categoria LGAC gestion e innovacion de las organizaciones.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.

## Checklist editorial

- Definir la competitividad como decision estrategica, no como adjetivo generico.
- Vincular ventaja competitiva con evidencia: sector, mercado, procesos o talento.
- Explicar recursos, riesgos, indicadores y condiciones de implementacion.
- Evitar copiar modelos sin aplicacion: toda herramienta debe cerrar con una decision.
- La carpeta `referencias-analisis-y-estrategias-de-la-competitividad-empresarial/`
  resguarda fuentes, matrices, casos y evidencia auxiliar de la materia.
