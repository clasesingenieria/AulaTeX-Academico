# Médico Cirujano - UAdeC

Material, guías y planeaciones para la carrera de [Médico Cirujano en la UAdeC](https://www.uadec.mx/medicina/).

## Materias y Temarios

Actualmente, este directorio contiene ocho áreas de **preparación local para ingreso**, no las asignaturas de un plan curricular completo. No se ha cotejado una convocatoria, campus, ciclo de admisión ni temario oficial de UAdeC/CENEVAL. Los nombres históricos `examen-ingreso-*` se conservan como rutas, no como prueba de cobertura oficial:

- [Anatomía](./examen-ingreso-anatomia)
- [Bioquímica y Biología Molecular](./examen-ingreso-bioquimica)
- [Biología Celular y Microbiología](./examen-ingreso-biologia-celular)
- [Comprensión Lectora](./examen-ingreso-comprension-lectora)
- [Fisiología](./examen-ingreso-fisiologia)
- [Pensamiento Matemático](./examen-ingreso-pensamiento-matematico)
- [Redacción Indirecta](./examen-ingreso-redaccion-indirecta)
- [Salud Pública y Medicina Comunitaria](./examen-ingreso-salud-publica)

### Metodología de Trabajo
Para cada tema del temario del examen de ingreso, se realizarán dos actividades formativas principales:
1. **Actividades de Investigación**: Para profundizar en los conceptos teóricos.
2. **Cuestionarios / Evaluaciones**: Reactivos originales de práctica con soluciones justificadas; no son exámenes oficiales ni acreditan un intento personal.

## Productos y estructura vigente

Cada área cuenta con guía, dos consignas locales, reporte TEX/PDF, esquema o tabla y cuestionario resuelto. [Catálogo de productos](catalogo-productos.json) y [validación reproducible](validacion-productos.json).

- `referencias-<area>/libros-<area>/`: PDF originales con inventario SHA256; metadatos y lectura integral pendientes de cotejo.
- `referencias-<area>/notas-<area>/actividad-01-investigacion/`: fuentes y alcance de consulta.
- `referencias-<area>/notas-<area>/actividad-02-cuestionario/`: banco estructurado y soluciones.
- `materiales-generales/historico-2026-10-10/`, dentro de notas: originales anteriores preservados.
- `planeaciones-<area>/`: una consigna Markdown por actividad, sin formatos oficiales inventados.
- `assets-<area>/` y `extractor-aulatex/`: espacios de soporte; su existencia no acredita extracción ni investigación.
- `Entregas/`: reservado para el formato que exija una consigna real; no se han realizado envíos.

La [plantilla común](assets-medico-cirujano/plantilla/README.md) usa una portada local sin logos de otra universidad. La carpeta `plantilla/` anterior es un recurso genérico histórico con licencias propias, no identidad UAdeC.

## Calidad y límites

[Informe de calidad y pendientes](CALIDAD-PRODUCTOS.md): páginas, reactivos y alcance del muestreo visual.

Se completaron las tres áreas generales y se ampliaron las cinco científicas. Las revisiones corrigen fórmulas incompletas y simplificaciones sobre planos anatómicos, fíbula, transporte celular, meiosis, ATP e indicadores epidemiológicos. Las claves son propuestas para estudio, no calificaciones.

El control comprueba compilación, presencia de productos, referencias, cuatro opciones por reactivo, claves, enlaces y hashes. No certifica revisión científica integral, equivalencia psicométrica ni alineación oficial. Las consultas de OpenStax, RAE/ASALE y CDC están delimitadas en las notas de cada actividad. No se atribuye lectura íntegra de los libros locales ni se autoriza su redistribución.

Desde la raíz: ejecutar `./scripts/latexmk-build.ps1 <ruta-del-reporte.tex>` para cada área; después ejecutar `UAdeC/medico-cirujano/assets-medico-cirujano/validar_productos.py` con el entorno Python del repositorio. El organizador `organizar_productos.py` es una migración inicial con protección de respaldos: no debe repetirse sobre la estructura ya generada. Las correcciones posteriores de TEX se mantienen en los reportes; el validador sincroniza las claves científicas desde ellos.
