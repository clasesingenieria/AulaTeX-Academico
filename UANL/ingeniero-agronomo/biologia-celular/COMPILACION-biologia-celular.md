# Compilación y Generación: Biología Celular (UANL / Agronomía)

## Comandos de compilación oficial

Desde la raíz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\biologia-celular\reporte-biologia-celular-Actividad-8.tex
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\biologia-celular\presentacion-biologia-celular-Actividad-8.tex
```

Para generar la versión en formato editable Word (`.docx`) exigida por la plataforma Nexus para retroalimentación:

```powershell
pandoc "UANL/ingeniero-agronomo/biologia-celular/contenido-Actividad-8.tex" -o "UANL/ingeniero-agronomo/biologia-celular/reporte-biologia-celular-Actividad-8.docx"
```

---

## Requisitos de entorno y motor tipográfico

- **Motor:** TeX Live con `latexmk`, XeLaTeX o pdfLaTeX según el documento, y Biber cuando la fuente usa `biblatex`.
- **Tipografía:** Se emplea XeLaTeX para la carga nativa de la tipografía institucional Arial / Times New Roman, cumpliendo estrictamente con la consigna del PIA de la UANL.
- **Bibliografía:** `biblatex` con motor `biber` y estilo `apa` (APA 7ma edición estricto).
- **Márgenes y formato:** Carta (*Letter*), márgenes exactos de 2.5 cm en los 4 extremos e interlineado sencillo (1.0).

---

## Entregables generados y validados

| Archivo | Formato | Rol en la entrega | Estado |
|---|:---:|---|:---:|
| [`reporte-biologia-celular-Actividad-8.pdf`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/reporte-biologia-celular-Actividad-8.pdf) | PDF | Manuscrito final tipográfico del artículo de revisión | **Compilado y verificado** |
| [`reporte-biologia-celular-Actividad-8.docx`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/reporte-biologia-celular-Actividad-8.docx) | Word | Archivo editable para revisión docente y Turnitin | **Generado y verificado** |
| [`presentacion-biologia-celular-Actividad-8.pdf`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/presentacion-biologia-celular-Actividad-8.pdf) | PDF | Diapositivas para la exposición de 15 min en MS Teams | **Compilado y verificado** |
| [`biologia-celular.bib`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/biologia-celular.bib) | BibTeX | Base de datos de citas bibliográficas APA 7 | **Resuelto y enlazado** |

---

## Estructura de directorios y trazabilidad

- `template.tex`: Hook de configuración que define márgenes de 2.5 cm, interlineado sencillo y carpetas de logos.
- `contenido-Actividad-8.tex`: Cuerpo del artículo científico con desarrollo exhaustivo de los 9 apartados temáticos.
- `planeaciones-biologia-celular/`: Consignas, inventario del curso y textos originales de Nexus.
- `referencias-biologia-celular/`: Catálogos de libros, fichas conceptuales de notas y referencias APA 7.
- `.build/latex/`: Auxiliares aislados por ruta y nombre del documento; los PDF finales se copian junto a sus fuentes.


