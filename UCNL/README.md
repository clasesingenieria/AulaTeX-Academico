# UCNL: base de referencias y plantillas

Consulta autenticada del **23/09/2026** en la plataforma de licenciatura. Las seis materias siguientes están disponibles en la cuenta para el periodo **2026-3**; las demás carpetas curriculares no se consideran verificadas por esta consulta.

| Materia | Grupo | Base revisada |
| --- | --- | --- |
| Administración II | D | [Referencias, notas y plantillas](licenciatura-en-administracion/administracion-ii-lad/BASE-ACADEMICA-2026-3.md) |
| Contabilidad II | G | [Referencias, notas y plantillas](licenciatura-en-administracion/contabilidad-ii-lad/BASE-ACADEMICA-2026-3.md) |
| Derecho Constitucional | B | [Referencias, notas y plantillas](licenciatura-en-administracion/derecho-constitucional-lad/BASE-ACADEMICA-2026-3.md) |
| Inglés II | C | [Referencias, notas y plantillas](licenciatura-en-administracion/ingles-ii-lad/BASE-ACADEMICA-2026-3.md) |
| Macroeconomía | E | [Referencias, notas y plantillas](licenciatura-en-administracion/macroeconomia-lad/BASE-ACADEMICA-2026-3.md) |
| Matemáticas II | C | [Referencias, notas y plantillas](licenciatura-en-administracion/matematicas-ii-lad/BASE-ACADEMICA-2026-3.md) |

## Continuación del 24/09/2026

El acceso a la plataforma devolvió HTTP 500 antes del formulario de inicio de sesión. No se modificaron credenciales ni se considera revalidado el contenido del aula. Se prepararon [seis rutas documentales](SEGUIMIENTO-2026-3.md), con 17 bloques de práctica propuestos, fuentes y criterios de revisión, a partir de la base conservada del 23/09/2026.

Las rutas no son consignas oficiales, no asignan fechas de entrega y no acreditan actividades realizadas. Matemáticas II mantiene su temario pendiente; Inglés II incorpora una ficha local de pasado simple. Al restablecerse el servicio se deben cotejar consignas, rúbricas y calendario antes de convertir esta preparación en actividades específicas.

## Referencias conservadas

Se conservaron **14 PDF del aula**: ocho de Administración II y seis de Contabilidad II. Se extrajo su texto y se revisaron selectivamente títulos, créditos, índices e inicios; no se afirma lectura íntegra. El libro de Administración es de Koontz, Weihrich y Cannice, 14.ª edición, 2012, con datos comprobados en el ejemplar. La referencia Wals (2000) de Contabilidad se conserva como recomendación de eLibro, sin afirmar acceso al texto.

Se incorporaron dos PDF complementarios íntegros: la Constitución de la Cámara de Diputados con últimas reformas DOF 02-06-2026 y Principles of Macroeconomics 3e de OpenStax. De Algebra and Trigonometry 2e se conserva un extracto inicial de ocho páginas, con enlace y huella del original; el libro completo supera 100 MB y no se deja como archivo normal del repositorio. Para Inglés se registró una referencia gramatical del British Council. Son apoyos adicionales, no lecturas obligatorias atribuidas al docente. En Matemáticas el apoyo es provisional porque no hay temario disciplinar visible suficiente.

Cada materia conserva originales, inventario de consulta, bibliografía verificada, notas, extracciones y recursos gráficos. Las entradas antiguas de refuerzo editorial se mantienen en sus archivos históricos, pero no se utilizan en las bibliografías nuevas. Los materiales del aula no tienen autorización de redistribución pública acreditada; los apoyos abiertos conservan sus condiciones de licencia. No se efectuó commit ni publicación.

## Plantillas

Las nuevas entradas de cada materia usan [la base de reporte y ficha](plantilla-actividad-ucnl.tex) y [la base de presentación](plantilla-presentacion-ucnl.tex). Se generaron **18 entradas editables y sus PDF de muestra**: reporte, ficha de actividad y presentación por materia. Los documentos de muestra no son actividades resueltas.

Formato editorial de partida: Arial 12 en reportes, interlineado 1.5, citas y bibliografía APA con Biber, identidad UCNL y rutas explícitas. Se adapta a la consigna concreta; no se presenta como una norma institucional no verificada. Matrícula UCNL, docente y fecha de realización permanecen por confirmar. Grupo y periodo proceden del título del curso; no se copian datos de ITESCA o UAS.

Al elaborar una actividad, definir `ucnlfecha` explícitamente y usar `\parencite{clave}` o `\textcite{clave}`. Las notas de procedencia se guardan como `annotation` y en los catálogos, sin insertarse en las referencias APA impresas. No mezclar estas bases con comandos de BibTeX/natbib de las plantillas históricas.

Compilar desde la raíz del repositorio con `scripts/latexmk-build.ps1`, `-CleanMode none -xelatex`. Cada base de materia contiene los tres comandos exactos. Los auxiliares quedan en `.build/latex` y el PDF junto a su fuente. Los reportes y presentaciones anteriores se conservan, pero no se consideran validados de nuevo.

## Pendientes y límites

- Derecho Constitucional tiene doce módulos bajo una sección rotulada **solo docentes** y Macroeconomía uno. Se registraron, pero no se descargaron ni se intentó eludir la restricción.
- No se iniciaron exámenes, H5P, SCORM, videollamadas, foros ni entregas. Los recursos interactivos quedan inventariados, no ejecutados.
- Administración II, Macroeconomía y Matemáticas II contienen fechas de febrero o enero a abril que no se trasladan automáticamente al periodo 2026-3.
- Inglés II sólo muestra la presentación general; Matemáticas II tiene una programación con temas vacíos. Faltan materiales o instrucciones específicas para completar su cobertura curricular.
- El texto extraído de T4 de Contabilidad contiene caracteres dañados. Consultar el PDF y no citar esa transcripción sin cotejo.
- Confirmar matrícula, docentes, rúbricas y calendario antes de elaborar actividades. La fase actual establece la base; no inventa consignas ni fechas.

[Inventario de materias](INVENTARIO-BASE-2026-3.json) y [validación técnica y hashes](VALIDACION-BASE-2026-3.json).