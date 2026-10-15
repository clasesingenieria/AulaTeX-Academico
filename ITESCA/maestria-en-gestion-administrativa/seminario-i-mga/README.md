# Seminario I — Maestría en Gestión Administrativa

Espacio de trabajo para construir el anteproyecto de titulación de la MGA del ITESCA.

## Datos del curso

- **Docente:** Dra. Carla Olimpya Zapuche Moreno
- **Atención:** jueves, 19:00–20:00, previa cita; acompañamiento asíncrono por canales digitales
- **Correo:** czapuche@itesca.edu.mx
- **Ubicación:** Edificio 5, planta alta, Subdirección de Posgrado e Investigación
- **Propósito:** conocer el marco normativo de titulación y elaborar un anteproyecto alineado con una LGAC para presentarlo ante el Consejo de Posgrado.

## Organización

- [Reporte T12](reporte-seminario-i-Actividad-12.tex) y [PDF académico de raíz](reporte-seminario-i-Actividad-12.pdf).
- [Word acumulativo T12 para entrega](entregas-seminario-i/Tarea12_DeLaCruzMunoz.docx); [PDF de consulta del Word](entregas-seminario-i/Tarea12_DeLaCruzMunoz.pdf). El aula solicita un solo Word, no el reporte auxiliar.
- [Notas de T12](referencias-seminario-i/notas-seminario-i/actividad-12-hipotesis/README.md): consignas, fuentes, pasajes, generador, respaldo y comprobaciones. No son el reporte ni el archivo de entrega.
- [Contrato de compilación y plantillas](COMPILACION-seminario-i.md).
- [Estado de entregables y revisión estructural](ESTADO-ENTREGABLES.md).
- [Planeaciones normalizadas por módulo](planeaciones-seminario-i/INDICE-GENERADAS.md): trece fichas, sin reemplazar las planeaciones por unidad.
- `programa-analitico-seminario-i.md`: objetivo, temario, evaluación y calendario.
- `planeaciones-seminario-i/`: control de las 18 actividades.
- [Notas por actividad](referencias-seminario-i/notas-seminario-i/README.md): materiales docentes, formatos, consignas y revisiones; apuntes transversales en materiales generales y versiones historicas identificadas.
- `anteproyecto/`: matrices, capítulos y evidencias del producto integrador.
- `referencias-seminario-i/`: fuentes incorporadas y organizadas por tipo.
- `investigacion-aulatex/`: bitácora de búsqueda y base de conocimiento.
- `extractor-aulatex/`: conceptos y trazabilidad generados por actividad.
- `entregas-seminario-i/`: copias finales destinadas al aula; las fuentes permanecen en la raíz.
- `assets-seminario-i/`: figuras y recursos visuales propios o con licencia compatible.
- `reporte-seminario-i-mga.tex` y `presentacion-seminario-i-mga.tex`: entradas LaTeX canónicas.
- `reporte-seminario-i-Actividad-N.tex`: fuente de cada actividad materializada.
- `COMPILACION-seminario-i.md`: comandos y contrato de compilación.
- `seminario-i.bib`: bibliografía de la materia.
- [Plantilla de materia](reporte-seminario-i-plantilla-actividad.tex): metadatos y contenido; delega en la maestra MGA, que incluye el diseño institucional ITESCA y el núcleo compartido. Se carga desde un reporte, no se compila sola.
- La entrada anterior en `assets-seminario-i/plantilla/` delega en la plantilla de raíz por compatibilidad; ya no abre otro documento ni carga su copia local del núcleo. Las copias históricas se conservan, pero no gobiernan T12.

Los reportes 1, 2, 3 y 6 cargan explícitamente el núcleo local; la Actividad 4 y la presentación son autocontenidas y conservan sus formatos. El reporte base usa la nueva plantilla reutilizable. Los emblemas oficiales se comparten desde `ITESCA/assets-itesca/`; no hay dependencia de una biblioteca personal externa.

El reporte base anterior se conserva, sin alterar su contenido, en `referencias-seminario-i/notas-seminario-i/historico/`. Es material histórico con instrucciones editoriales, no un entregable vigente.

## Corrección contractual del 13 de octubre de 2026

Se materializó T12 en la raíz y se corrigió la plantilla reutilizable para pasar por la maestra de carrera. Cadena verificada en el registro de compilación: reporte T12 → plantilla Seminario I → maestra MGA con identidad ITESCA → núcleo compartido AulaTeX. El Word acumulativo conserva la portada y estructura pedidas por el aula; no se transforma automáticamente en el reporte LaTeX. Ambos productos tienen propósitos diferentes.

Corrección posterior de correspondencia: el reporte de raíz ya no es un auxiliar reducido. Se sincronizó el cuerpo completo del Word, referencias y tres tablas; 130 párrafos cotejados en el PDF. La raíz tiene 25 páginas y el Word 31 por maquetación diferente. El Word es la fuente acumulativa y el conversor documentado permite regenerar el reporte sin resumirlo. La interpretación anterior de productos con contenido distinto queda sustituida por esta equivalencia.

T12 compiló con portada identificada, matrícula, GGS102, docente y fecha; T11 se compiló en un directorio aislado por la entrada compatible sin sustituir su PDF anterior. No se migraron aquí todas las actividades autocontenidas ni se modificaron los Word históricos. No se realizaron envíos.

## Flujo de trabajo

1. Registrar cada consigna y rúbrica en su planeación.
2. Verificar autoría, año, editorial, DOI/ISBN y procedencia de cada fuente.
3. Elaborar fichas en `referencias-seminario-i/notas-seminario-i/` con páginas y procedencia verificables.
4. Actualizar primero las matrices y después los capítulos del anteproyecto.
5. Conservar cada PDF compilado junto a su `.tex` y colocar en `entregas-seminario-i/` únicamente la copia nombrada para el aula.

> Toda fuente utilizada debe estar incorporada en `referencias-seminario-i/`; no se mantienen dependencias de rutas externas.

## Reorganizacion del 10 de octubre de 2026

Absorcion posterior: las carpetas de Tarea 6 y planeaciones generadas se retiraron de la raiz tras redistribuir 69 archivos en [notas por actividad](referencias-seminario-i/notas-seminario-i/README.md). Elaboracion de Tarea 6 conserva scripts, fuentes y validacion dentro de su actividad; las fichas MD/JSON generadas se agrupan por producto y fecha. Se actualizaron rutas de LaTeX, scripts y documentos. El Word de Tarea 6 paso su validador y el reporte recompilo; no hubo nuevos envios.

Se trasladaron 31 archivos aplicando el criterio de Antecedentes: libros con nombres legibles, materiales en notas de actividades 1, 2, 3, 4, 6 y 10, y apuntes comunes separados. Las planeaciones permanecen en sus carpetas. Se conservaron el anteproyecto acumulativo, sus evidencias de entrega y los scripts operativos; sus rutas de consulta se actualizaron cuando fue necesario. Validadores de Tareas 6 y 10 aprobados; no hubo nuevos envios. En Windows, el validador de Tarea 6 requiere `PYTHONUTF8=1` para interpretar la salida de Poppler.