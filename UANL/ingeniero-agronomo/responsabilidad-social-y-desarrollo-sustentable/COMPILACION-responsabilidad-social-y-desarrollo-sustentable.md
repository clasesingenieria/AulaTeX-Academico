# Compilación: Responsabilidad Social y Desarrollo Sustentable

## Comando de la materia

Desde la carpeta de la materia:

```powershell
.\compilar.ps1
```

Desde la raíz del repositorio:

```powershell
.\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable\compilar.ps1
```

Para un solo documento, añadir `-Documento reporte` o `-Documento presentacion`.
La tarea de VS Code **Compilar entrega UANL RSDS** ejecuta el mismo script.

## Requisitos

TeX Live con latexmk, XeLaTeX, Biber, fontspec, biblatex-apa, csquotes,
pdflscape, xurl, titlesec y soporte de español. Arial debe estar instalada en Windows.
Se utiliza XeLaTeX para cumplir la tipografía de la consigna; no pdfLaTeX.

## Rutas y salidas

- Bibliografía: `responsabilidad-social-y-desarrollo-sustentable.bib`.
- Logotipos: `img/departamentos/`.
- Contenido del reporte: `contenido-actividad-1.tex`.
- PDF finales: junto a los TEX de la actividad, en la raíz de la materia.
- Auxiliares y registros: `.build/latex/uanl-rsds/`, desde la raíz del repositorio.
- Verificación: `retroalimentacion-aulatex/verificacion-actividad-1.json`.

El script usa `-norc` y rutas explícitas para evitar la configuración global
recursiva que interrumpía XeLaTeX. Los cambios de entorno son locales al proceso
y se restauran al terminar. No se eliminan fuentes ni respaldos.

## Criterios de validación

latexmk y Biber deben terminar sin errores. El PDF debe estar actualizado,
con bibliografía resuelta, logotipos visibles y sin cajas desbordadas. La
versión revisada consta de seis páginas de reporte y tres diapositivas.

Después de cambiar el contenido, revisar de nuevo el PDF y actualizar sus
hashes de verificación. Compilar correctamente no equivale a completar los
datos del estudiante o a enviar la evidencia a NEXUS.
