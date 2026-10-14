# Compilación y Generación: Biología Celular (UANL / Agronomía)

## Comandos de compilación oficial

Desde la carpeta de la materia:

```powershell
.\compilar.ps1
```

O para compilar un único entregable:

```powershell
.\compilar.ps1 -Documento reporte
.\compilar.ps1 -Documento presentacion
```

Desde la raíz del repositorio:

```powershell
.\UANL\ingeniero-agronomo\biologia-celular\compilar.ps1
```

Para generar la versión en formato editable Word (`.docx`) exigida por la plataforma Nexus para retroalimentación:

```powershell
pandoc "UANL/ingeniero-agronomo/biologia-celular/contenido-PIA.tex" -o "UANL/ingeniero-agronomo/biologia-celular/reporte-biologia-celular-PIA.docx"
```

---

## Requisitos de entorno y motor tipográfico

- **Motor:** TeX Live con `latexmk`, `xelatex` y `biber`.
- **Tipografía:** Se emplea XeLaTeX para la carga nativa de la tipografía institucional Arial / Times New Roman, cumpliendo estrictamente con la consigna del PIA de la UANL.
- **Bibliografía:** `biblatex` con motor `biber` y estilo `apa` (APA 7ma edición estricto).
- **Márgenes y formato:** Carta (*Letter*), márgenes exactos de 2.5 cm en los 4 extremos e interlineado sencillo (1.0).

---

## Entregables generados y validados

| Archivo | Formato | Rol en la entrega | Estado |
|---|:---:|---|:---:|
| [`reporte-biologia-celular-PIA.pdf`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/reporte-biologia-celular-PIA.pdf) | PDF | Manuscrito final tipográfico del artículo de revisión | **Compilado y verificado** |
| [`reporte-biologia-celular-PIA.docx`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/reporte-biologia-celular-PIA.docx) | Word | Archivo editable para revisión docente y Turnitin | **Generado y verificado** |
| [`presentacion-biologia-celular-PIA.pdf`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/presentacion-biologia-celular-PIA.pdf) | PDF | Diapositivas para la exposición de 15 min en MS Teams | **Compilado y verificado** |
| [`biologia-celular.bib`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/ingeniero-agronomo/biologia-celular/biologia-celular.bib) | BibTeX | Base de datos de citas bibliográficas APA 7 | **Resuelto y enlazado** |

---

## Estructura de directorios y trazabilidad

- `template.tex`: Hook de configuración que define márgenes de 2.5 cm, interlineado sencillo y carpetas de logos.
- `contenido-PIA.tex`: Cuerpo del artículo científico con desarrollo exhaustivo de los 9 apartados temáticos.
- `planeaciones-biologia-celular/`: Consignas, inventario del curso y textos originales de Nexus.
- `referencias-biologia-celular/`: Catálogos de libros, fichas conceptuales de notas y referencias APA 7.
- `.build/latex/uanl-biologia-celular/`: Artefactos auxiliares de compilación de TeX Live.

