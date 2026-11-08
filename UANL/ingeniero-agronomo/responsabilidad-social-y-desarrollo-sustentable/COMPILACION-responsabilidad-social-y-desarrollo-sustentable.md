# Compilación: Responsabilidad Social y Desarrollo Sustentable

## Comando de la materia

Desde la raíz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable\reporte-responsabilidad-social-y-desarrollo-sustentable-Actividad-1.tex
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable\presentacion-responsabilidad-social-y-desarrollo-sustentable-Actividad-1.tex
```

El motor se detecta desde la directiva `% !TeX program` o la presencia de
`fontspec`. Biber se ejecuta automáticamente mediante latexmk cuando el documento
usa `biblatex`.

## Requisitos

TeX Live con latexmk, XeLaTeX, Biber, fontspec, biblatex-apa, csquotes,
pdflscape, xurl, titlesec y soporte de español. Arial debe estar instalada en Windows.
Se utiliza XeLaTeX para cumplir la tipografía de la consigna; no pdfLaTeX.

## Rutas y salidas

- Bibliografía: `responsabilidad-social-y-desarrollo-sustentable.bib`.
- Logotipos: `img/departamentos/`.
- Contenido del reporte: `contenido-actividad-1.tex`.
- PDF finales: junto a los TEX de la actividad, en la raíz de la materia.
- Auxiliares y registros: `.build/latex/`, aislados por ruta y nombre del documento.
- Verificación: `retroalimentacion-aulatex/verificacion-actividad-1.json`.

El wrapper común carga la configuración del repositorio, prioriza la bibliografía
de la materia y deja los pasos de compilación y bibliografía a cargo de latexmk.
No se eliminan fuentes ni respaldos.

## Criterios de validación

latexmk y Biber deben terminar sin errores. El PDF debe estar actualizado,
con bibliografía resuelta, logotipos visibles y sin cajas desbordadas. La
versión revisada consta de seis páginas de reporte y tres diapositivas.

Después de cambiar el contenido, revisar de nuevo el PDF y actualizar sus
hashes de verificación. Compilar correctamente no equivale a completar los
datos del estudiante o a enviar la evidencia a NEXUS.
