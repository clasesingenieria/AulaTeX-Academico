# Responsabilidad Social y Desarrollo Sustentable

UANL, Facultad de Agronomía, Ingeniero Agrónomo.

## Ubicación curricular

- Institución: Universidad Autónoma de Nuevo León.
- Facultad: Agronomía.
- Programa: Ingeniero Agrónomo.
- Semestre, créditos y clave: no confirmados en los insumos disponibles.
- [Ficha analítica de la materia](programa-analitico-responsabilidad-social-y-desarrollo-sustentable.md): alcance documentado de la fase 1, no programa oficial completo.
- [Inventario AulaTeX](estructura-aulatex.json).

## Actividad 1

- [Reporte PDF: cuadro comparativo](reporte-responsabilidad-social-y-desarrollo-sustentable-Actividad-1.pdf): seis páginas.
- [Presentación PDF](presentacion-responsabilidad-social-y-desarrollo-sustentable-Actividad-1.pdf): tres diapositivas, una por práctica.
- [Consigna revisada](planeaciones-responsabilidad-social-y-desarrollo-sustentable/consigna-Actividad-1.md).
- [Bibliografía APA](responsabilidad-social-y-desarrollo-sustentable.bib).
- [Contenido editable del reporte](contenido-actividad-1.tex).
- [Verificación técnica y hashes de los PDF](retroalimentacion-aulatex/verificacion-actividad-1.json).

**Antes de entregar:** completar estudiante, matrícula, grupo y docente en los
cuatro campos editables de la portada del PDF, o incorporar los datos confirmados
al TEX. No se inventaron datos ni se reutilizaron los de otras instituciones.
Revisar y asumir o ajustar la reflexión personal. No se cargaron archivos a
NEXUS ni se respondió el examen de la fase.

## Contenido y verificación

El cuadro mantiene dos columnas, México y otro país, y tres pares de prácticas:
agua de riego frente a reúso seguro en Israel; generación eléctrica fósil frente
a expansión renovable en Alemania; descarte mezclado de envases frente al
depósito y devolución alemán. Se incorporan condiciones de adaptación a México,
límites de los casos e indicadores ODS 6.3.1, 6.4.1, 6.4.2, 7.2.1, 7.3.1 y 12.5.1.

Validación del 11 de septiembre de 2026: latexmk, XeLaTeX y Biber finalizaron con
éxito. Los registros finales no contienen errores, citas indefinidas ni desbordes
de cajas. Se renderizaron y revisaron las páginas del reporte. La portada usa
Arial a 14 pt y las celdas Arial a 12 pt con interlineado sencillo. Las referencias
se componen con `biblatex-apa`. El contenido no debe reducirse para forzar las
tres prácticas en una sola página ilegible.

La portada retoma la composición editorial de UnADM: identidad centrada, título
y subtítulo separados, líneas de acento y datos agrupados sobre un fondo claro.
Se conservan los cuatro campos editables y la identidad UANL, con acentos azules
y dorados. El cuerpo se organiza en introducción, comparación temática con tres
subsecciones y conclusión, sin cambiar los argumentos ni las fuentes.

## Uso de realizar-actividad

Se ejecutó la acción real `realizar-actividad`, con cinco roles, el router
configurado, una pasada de monitor y una de optimización. Se desactivaron el
extractor del agente y el transformador de foros.

La corrida inicial **no aprobó**. El generador no incorporó correctamente la
consigna y propuso una comparación genérica; además, la plantilla anterior tenía
problemas de compilación. Su salida no se aceptó como entrega terminada.

El diagnóstico quedó en
[la corrida 20260911-075416](../../../retroalimentacion-editorial/aulatex/runs/20260911-075416-realizar-actividad/reporte-aulatex.md).
Después se corrigieron directamente los documentos contra los originales
docentes y las fuentes verificadas, y se recompilaron con el comando local.
No se atribuye a la corrida fallida la validación técnica posterior, ni se
presenta la puntuación heurística del motor como calificación académica.

## Organización

Se aplica el patrón de carpetas observado en las materias de UnADM, conservando
la identidad UANL y las particularidades de la consigna de Agronomía.

- `planeaciones-responsabilidad-social-y-desarrollo-sustentable/`: los dos DOCX, la guía PPSX y la consigna depurada.
- `referencias-responsabilidad-social-y-desarrollo-sustentable/`: informes OCDE México 2013 y 2024, OCDE Israel 2023 y SEMARNAT 2020.
- `img/departamentos/`: logotipos oficiales de UANL y de la Facultad de Agronomía.
- `retroalimentacion-aulatex/`: verificación de PDF, borradores y extracciones previas; no forman parte de la entrega académica.
- `responsabilidad-social-y-desarrollo-sustentable.bib`: bibliografía canónica de la materia.
- `estructura-aulatex.json`: inventario de documentos y carpetas actuales.
- `programa-analitico-responsabilidad-social-y-desarrollo-sustentable.md`: ficha del alcance curricular conocido y datos por confirmar.
- `COMPILACION-responsabilidad-social-y-desarrollo-sustentable.md`: guía de compilación reproducible.
- `.memoria-aulatex/` y `extractor-aulatex/`: registros y salidas auxiliares generados por el motor; no sustituyen las fuentes verificadas. El planificador también actualizó índices de memoria de UANL y de la carrera.
- Los TEX, la bibliografía y los PDF finales permanecen en la raíz de la materia.
- Auxiliares y renders de revisión: `.build/latex/uanl-rsds/`, en la raíz del repositorio.

Los movimientos de archivos y carpetas se verificaron mediante SHA-256.
No se borraron originales; las extracciones antiguas se conservan como archivo,
no como evidencia académica.

## Trazabilidad de fuentes

- `ocdeMexico2013`: páginas impresas 28 y 71 (páginas 30 y 73 del PDF), sobre eficiencia, subsidios al bombeo y presión sobre acuíferos. Antecedente histórico, no estadística de 2026.
- `ocdeIsrael2023`: resumen ejecutivo, apartado sobre logros en gestión de agua y contaminación persistente. Sustenta el reúso agrícola y sus límites.
- `ocdeMexico2024` y `eiaMexico2023`: transición energética y perfil de generación de México; no se calcula una comparación numérica entre años distintos.
- `uba2026`: actualización del 10 de marzo de 2026, datos de 2025. Se distingue 55.1% de consumo eléctrico bruto y 23.8% de consumo final bruto bajo RED; ninguno se etiqueta automáticamente como indicador ONU 7.2.1.
- `semarnat2020`: secciones 2.2.1.3 y 2.2.3.2; también página impresa 13 sobre las limitaciones de información de recuperación mediante pepena. No se inventa una tasa nacional de reciclaje.
- `dpgProceso`: explicación del sistema DPG y depósito de 0.25 euros; se distingue retorno de reciclaje y reutilización.
- `onuIndicadores`: repositorio oficial UNSD, consultado el 11 de septiembre de 2026, para denominadores y definiciones de los indicadores.

URLs, títulos, fechas y DOI de las fuentes académicas están en la bibliografía.

## Logotipos oficiales

- UANL: [escudo del repositorio oficial](https://www.uanl.mx/wp-content/uploads/2025/04/logo-uanl-escudo.png), publicado el 9 de abril de 2025; PNG transparente de 500 × 500 píxeles.
- Agronomía: [archivo original del emblema](https://agronomia.uanl.mx/wp-content/uploads/2023/11/agronomia_logo.png), visible en el [portal oficial de la facultad](https://agronomia.uanl.mx/); PNG transparente de 313 × 300 píxeles.

Estos originales sustituyen las capturas reducidas anteriores. La fecha de
publicación del archivo UANL no acredita por sí sola un rediseño del escudo.
No se confirmó un rediseño posterior del emblema de Agronomía en las fuentes
públicas consultadas; se usa la versión que muestra su sitio actual.
Las capturas sustituidas se conservan en `retroalimentacion-aulatex/borradores/`.
Las URLs, dimensiones y hashes están en la verificación técnica.

## Compilación reproducible

Consultar [la guía de compilación de la materia](COMPILACION-responsabilidad-social-y-desarrollo-sustentable.md).
Desde esta carpeta:

```powershell
.\compilar.ps1
```

Usar `-Documento reporte` o `-Documento presentacion` para compilar solo uno.
También está disponible la tarea de VS Code **Compilar entrega UANL RSDS**.
