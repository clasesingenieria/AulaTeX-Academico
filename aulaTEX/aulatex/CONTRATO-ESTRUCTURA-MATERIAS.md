# Contrato de estructura de materias

Versión **1.1** · 14 de octubre de 2026.

Cada materia debe disponer de una carpeta `entregas-<slug>/` en su raíz. El slug conserva el nombre de la materia y elimina el sufijo de programa `-lde`, `-lad`, `-mga`, `-isc` o `-imtc`. Por ejemplo, `seminario-i-mga/entregas-seminario-i/`.

La implementación normativa está en `planning_layout.subject_layout()`. `subject_artifact_contract()` publica las rutas relativas, `deliverables_directory` y `source_directory`. Los generadores de planeaciones y de plantillas deben consumir esas funciones compartidas.

| Elemento | Regla |
|---|---|
| Entregas | `entregas-<slug>/`, obligatoria por materia. |
| Archivos para entregar | Conservar el formato y nombre exigidos por la consigna. |
| Fuentes editables y trabajo editorial | Conservan su ubicación; crear la carpeta no mueve ni duplica automáticamente los reportes. |
| Índice | Crear `README.md` si falta; conservar cualquier índice existente. |
| Inventario | Registrar la carpeta en `folders` y publicar el contrato en `artifact_contract`. |
| Detección de materias | Las carpetas `entregas-...` son de apoyo; no son materias ni carreras. |
| Preservación | Crear de forma idempotente, sin sobrescribir archivos o carpetas existentes. |
| Nombres anteriores | `Entregas/` y `entregas/` no se generan. Para migrarlas, conservar contenidos y actualizar sus rutas. |

`ensure_delivery_directory()` permite aplicar la convención a materias existentes. La carpeta y su índice forman parte del material académico versionable. La creación o preparación de archivos no modifica el estado de entrega en una plataforma.
