# Seminario I — Maestría en Gestión Administrativa

Espacio de trabajo para construir el anteproyecto de titulación de la MGA del ITESCA.

## Datos del curso

- **Docente:** Dra. Carla Olimpya Zapuche Moreno
- **Atención:** jueves, 19:00–20:00, previa cita; acompañamiento asíncrono por canales digitales
- **Correo:** czapuche@itesca.edu.mx
- **Ubicación:** Edificio 5, planta alta, Subdirección de Posgrado e Investigación
- **Propósito:** conocer el marco normativo de titulación y elaborar un anteproyecto alineado con una LGAC para presentarlo ante el Consejo de Posgrado.

## Organización

- [Auditoria vigente de LaTeX y Entregas](referencias-seminario-i/notas-seminario-i/materiales-generales/AUDITORIA-LATEX-Y-ENTREGAS-2026-10-10.md): distingue revisiones locales, archivos recuperados de Moodle, complementos y plantillas no aptas. Carpeta `Entregas` normalizada; no se realizaron envios.
- [Estado de entregables y revision estructural](#estado-de-entregables).
- `planeaciones-seminario-i/`: una ficha Markdown por tarea (1-18) y una para el foro de presentacion; no hay PDF de planeaciones ni formato LaTeX aprobado. Los registros anteriores por modulo y unidad quedan en notas historicas.
- [Programa analitico](#programa-analítico--seminario-i): objetivo, temario, evaluacion y calendario integrados en este documento.
- `planeaciones-seminario-i/`: control de las 18 actividades.
- [Notas por actividad](#notas-seminario-i): materiales docentes, formatos, consignas y revisiones; apuntes transversales en materiales generales y versiones historicas identificadas.
- `referencias-seminario-i/notas-seminario-i/`: matrices, capitulos y evidencias distribuidos por actividad; componentes acumulativos en `materiales-generales/anteproyecto-acumulativo/`.
- `referencias-seminario-i/`: fuentes incorporadas y organizadas por tipo.
- Investigacion de objetivos en `referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/investigacion/`; notas de busqueda comunes en `referencias-seminario-i/notas-seminario-i/materiales-generales/investigacion/`.
- `extractor-aulatex/`: conceptos y trazabilidad generados por actividad.
- `Entregas/`: copias finales destinadas al aula; las fuentes permanecen en la raíz.
- `assets-seminario-i/`: figuras y recursos visuales propios o con licencia compatible.
- `referencias-seminario-i/notas-seminario-i/materiales-generales/encuadre/`: entradas base de materia, fuera de los productos por actividad de la raiz.
- `reporte-seminario-i-Actividad-N.tex`: fuente de cada actividad materializada.
- [Compilacion vigente](#compilacion-vigente): comandos y contrato unico.
- `seminario-i.bib`: bibliografía de la materia.
- `assets-seminario-i/plantilla/template.tex`: nucleo modular local, con manifiesto de procedencia.
- `assets-seminario-i/plantilla/reporte-seminario-i-plantilla-actividad.tex`: base reutilizable; dependencia de los reportes, no actividad independiente.

Los reportes 1, 2, 3 y 6 cargan explícitamente el núcleo local; la Actividad 4 y la presentación son autocontenidas y conservan sus formatos. El reporte base usa la nueva plantilla reutilizable. Los emblemas oficiales se comparten desde `ITESCA/assets-itesca/`; no hay dependencia de una biblioteca personal externa.

El reporte base anterior se conserva, sin alterar su contenido, en `referencias-seminario-i/notas-seminario-i/historico/`. Es material histórico con instrucciones editoriales, no un entregable vigente.

## Flujo de trabajo

1. Registrar cada consigna y rúbrica en su planeación.
2. Verificar autoría, año, editorial, DOI/ISBN y procedencia de cada fuente.
3. Elaborar fichas en `referencias-seminario-i/notas-seminario-i/` con páginas y procedencia verificables.
4. Actualizar primero las matrices y después los capítulos del anteproyecto.
5. Conservar cada PDF compilado junto a su `.tex` y colocar en `Entregas/` únicamente la copia nombrada para el aula.

> Toda fuente utilizada debe estar incorporada en `referencias-seminario-i/`; no se mantienen dependencias de rutas externas.

## Reorganizacion del 10 de octubre de 2026

Absorcion posterior: las carpetas de Tarea 6 y planeaciones generadas se retiraron de la raiz tras redistribuir 69 archivos en [notas por actividad](#notas-seminario-i). Elaboracion de Tarea 6 conserva scripts, fuentes y validacion dentro de su actividad; las fichas MD/JSON generadas se agrupan por producto y fecha. Se actualizaron rutas de LaTeX, scripts y documentos. El Word de Tarea 6 paso su validador y el reporte recompilo; no hubo nuevos envios.

Se trasladaron 31 archivos aplicando el criterio de Antecedentes: libros con nombres legibles, materiales en notas de actividades 1, 2, 3, 4, 6 y 10, y apuntes comunes separados. Las planeaciones permanecen en sus carpetas. Se conservaron el anteproyecto acumulativo, sus evidencias de entrega y los scripts operativos; sus rutas de consulta se actualizaron cuando fue necesario. Validadores de Tareas 6 y 10 aprobados; no hubo nuevos envios. En Windows, el validador de Tarea 6 requiere `PYTHONUTF8=1` para interpretar la salida de Poppler.

## Referencias de Seminario I

### Fuentes institucionales prioritarias

1. Lineamiento vigente para la operación de estudios de posgrado del Tecnológico Nacional de México.
2. Programa, perfil de egreso, objetivos y LGAC oficiales de la MGA del ITESCA.
3. Núcleo académico básico vigente.
4. Formato institucional para trabajos de titulación.
5. Rúbricas y materiales proporcionados en el aula virtual.

### Fuentes incorporadas al proyecto

#### Institucionales

| Archivo | Autoridad y contenido | Estado |
|---|---|---|
| `referencias-seminario-i/institucionales/tecnm-2023-lineamientos-operacion-posgrado.pdf` | Tecnológico Nacional de México; lineamientos de operación de posgrado | Copia local obtenida del sitio de ITESCA; verificar que siga siendo la versión aplicable |
| `referencias-seminario-i/institucionales/itesca-mga-oferta-academica-2026.html` | ITESCA; objetivo, perfil, LGAC y contactos de la MGA | Copia local del 29-08-2026 |

#### Metodología y apoyo

| Archivo | Datos verificados | Uso posible |
|---|---|---|
| `referencias-seminario-i/libros-seminario-i/Metodologia de la investigacion - Hernandez Sampieri y coautores - 2014.pdf` | Hernández Sampieri, Fernández Collado y Baptista Lucio; 2014; McGraw-Hill Education; ISBN 9781456223960 | Diseño, problema, objetivos y método |
| `referencias-seminario-i/libros-seminario-i/Epistemologia y metodologia de la investigacion - Navarro Chavez - 2014.pdf` | Navarro Chávez; 2014; Grupo Editorial Patria; ISBN 9786074388640 | Fundamentos epistemológicos |
| `referencias-seminario-i/libros-seminario-i/Los siete habitos de la gente altamente efectiva - Stephen Covey - 2014.pdf` | Covey; 2014; Planeta; ISBN 9786079377069 | Círculo de preocupación e influencia; verificar páginas |

La obra de Julio Pimienta no se incorporó porque sus metadatos editoriales estaban incompletos.

### Guía oficial APA incorporada

- [Reference Guide for Journal Articles, Books, and Edited Book Chapters](referencias-seminario-i/libros-seminario-i/Reference%20Guide%20for%20Journal%20Articles,%20Books,%20and%20Edited%20Book%20Chapters%20-%20APA%20-%202026.pdf): American Psychological Association, APA 7; actualización indicada en el documento: 23 de marzo de 2026.
- [Texto extraído](referencias-seminario-i/libros-seminario-i/Reference%20Guide%20for%20Journal%20Articles,%20Books,%20and%20Edited%20Book%20Chapters%20-%20APA%20-%202026.txt) y [procedencia con SHA-256](referencias-seminario-i/notas-seminario-i/actividad-2-normas-apa/procedencia-guia-APA.json). Descarga oficial del 22 de septiembre de 2026.
- Es una guía breve de referencias, no el manual completo ni una copia de la página web «References». No acredita por sí sola equivalencia con el recurso docente 2.1. Las notas históricas conservan el estado de consulta que tenían en su fecha.

### Notas y versiones históricas

Las [notas por actividad](#notas-seminario-i) contienen materiales docentes, formatos, consignas y revisiones; los apuntes transversales estan en materiales generales. Los libros y la guia APA, con nombres bibliograficos completos, estan en `referencias-seminario-i/libros-seminario-i/`; las fuentes institucionales permanecen en `referencias-seminario-i/institucionales/`. La subcarpeta `historico/` de notas resguarda el reporte base anterior y su PDF; no deben utilizarse como version vigente ni compilarse como una actividad. No se eliminaron versiones ni se reenviaron entregas durante esta reorganizacion.

### Política de archivos

- Toda fuente utilizada debe residir en esta carpeta y tener procedencia documentada.
- No conservar rutas dependientes de bibliotecas externas.
- Registrar notas propias, páginas consultadas y datos bibliográficos.
- Preferir fuentes primarias, artículos arbitrados, DOI y documentos institucionales.
- No citar una obra hasta verificar edición, año y pasaje usado.

## notas-seminario-i

Notas organizadas por actividad y materiales comunes. Distinguir interpretaciones propias de extractos de fuentes.

- [Unidad 1: consideraciones preliminares](referencias-seminario-i/notas-seminario-i/actividad-1-ruta-titulacion/consideraciones-preliminares.md).
- [Unidad 2: matriz de consistencia](referencias-seminario-i/notas-seminario-i/materiales-generales/coherencia-metodologica.md).
- [Unidad 2: revisión de la Actividad 4](referencias-seminario-i/notas-seminario-i/actividad-4-errores-circulo-covey/revision-actividad-04.md).
- [Unidad 3: anteproyecto](referencias-seminario-i/notas-seminario-i/materiales-generales/anteproyecto-acumulativo.md).

### Materiales por actividad

- Actividad 2, normas APA: [procedencia de la guia oficial](referencias-seminario-i/notas-seminario-i/actividad-2-normas-apa/procedencia-guia-APA.json); PDF y extraccion bibliografica en libros.
- Actividad 3, estado del arte: [formato DOCX](referencias-seminario-i/notas-seminario-i/actividad-3-estado-del-arte/materiales/Formato%2001%20-%20Matriz%20de%20estado%20del%20arte.docx) y [RTF](referencias-seminario-i/notas-seminario-i/actividad-3-estado-del-arte/materiales/Formato%2001%20-%20Matriz%20de%20estado%20del%20arte.rtf).
- Actividad 6, formato institucional: [material de ejemplo](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/materiales/Material%20para%20ejemplo.docx) y [portada docente](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/materiales/Portada.docx). La carpeta anterior de Tarea 6 se absorbio en [elaboracion](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/README.md): scripts, fuentes, contenido LaTeX, intermedios y validaciones, con dependencias actualizadas.
- Actividad 10, objetivos: [material docente](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/materiales/3.3%20-%20Formulacion%20de%20objetivos.pdf), [consigna](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/consigna-original-2026-09-28.txt), elaboracion en `referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/elaboracion-vtaxi-2026-09-28/` y comprobantes en `referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/comprobantes-envio/2026-10-04/`. Los componentes acumulativos compartidos permanecen en notas generales.

Las notas de alcance transversal estan en `referencias-seminario-i/notas-seminario-i/materiales-generales/`. [Registro de reorganizacion](referencias-seminario-i/notas-seminario-i/materiales-generales/registro-organizacion-2026-10-10.json): 31 archivos, procedencias y hashes previos al ajuste de rutas. `referencias-seminario-i/notas-seminario-i/historico/` resguarda el reporte base anterior y su PDF. Esos archivos no son productos vigentes ni deben compilarse como actividades actuales.

Material académico versionable dentro de la materia.

### Fichas generadas por actividad

Las trece parejas MD/JSON de la antigua carpeta de planeaciones generadas estan en `planeacion-generada/revision-2026-09-15/` de sus notas respectivas: actividades 0 a 11 y el registro de proyecto integrado en `referencias-seminario-i/notas-seminario-i/actividad-7-tema-titulo/registro-proyecto/`. El registro es un tramite complementario asociado al tema y titulo, no una actividad numerada adicional. Estas fichas son borradores historicos de requisitos, no planeaciones oficiales descargadas ni evidencia de una entrega. Las planeaciones por unidad permanecen en la carpeta propia de planeaciones.

[Registro de absorcion](referencias-seminario-i/notas-seminario-i/materiales-generales/absorcion-carpetas-2026-10-10.json): 69 archivos redistribuidos; binarios conservados, rutas locales actualizadas y carpetas originales retiradas. El Word de Tarea 6 mantiene su hash; su validador pasa desde elaboracion y el reporte LaTeX recompila. No se modificaron las entregas de Tarea 10.

## Consolidacion documental

El programa analitico se absorbio en la seccion siguiente y su archivo independiente se retiro. Se trasladaron 85 archivos de investigacion a notas: revision, scripts, versiones anteriores, registros de compilacion y capturas de Tarea 10 en su actividad; las dos notas generales de investigacion en materiales generales. [Registro de absorcion](referencias-seminario-i/notas-seminario-i/materiales-generales/absorcion-investigacion-2026-10-10.json). El validador de Tarea 10 paso desde la nueva ubicacion. No se modificaron documentos enviados ni se realizaron nuevas entregas.

Absorcion del anteproyecto y registro, 10 de octubre: 81 archivos distribuidos entre actividades 1, 2, 3, 4, 6, 7, 8, 9 y 10, segun su modulo y contenido. Las auditorias mixtas y el esquema acumulativo estan en materiales generales. [Registro de traslados](referencias-seminario-i/notas-seminario-i/materiales-generales/absorcion-anteproyecto-2026-10-10.json). Las entregas no se modificaron ni se reenviaron. Las copias de documentacion externa de vTaxi conservan enlaces historicos a su repositorio de origen que no estan disponibles localmente.

Los tres indices de materia, referencias y notas se integraron en este documento el 10 de octubre de 2026. Se conservaron sus contenidos y se recalcularon rutas. Las consignas, revisiones, notas academicas y README tecnicos por producto permanecen separados. No se modificaron entregas ni reportes.


## Programa analítico — Seminario I

### Objetivo general

Presentar el marco normativo del proceso de titulación y obtención del grado de Maestría, y guiar la elaboración de un anteproyecto alineado con una Línea de Generación y Aplicación del Conocimiento (LGAC), susceptible de evaluación por el Consejo de Posgrado y de asignación de Comité Tutorial.

### Unidad 1. Consideraciones preliminares (25 %)

**Resultado esperado:** reconocer el perfil, los objetivos, las LGAC y los requisitos de grado de la MGA.

1. Perfil de egreso.
2. Objetivos generales y específicos.
3. LGAC y núcleo académico básico.
4. Requisitos académicos para obtener el grado.

- Foro de presentación: 20 % de la unidad; vence 16-08-2026, 23:59.
- Tarea 1, ruta hacia la titulación: 80 %; 10-08-2026 a 30-08-2026, 23:59.

### Unidad 2. Elementos de la matriz de consistencia (25 %)

**Resultado esperado:** aplicar criterios de búsqueda, citación, escritura y coherencia metodológica.

1. Manual APA, 7.ª edición.
2. Búsqueda de información científica.
3. Matriz de estado del arte.
4. Matriz de consistencia.
5. Redacción académica.
6. Formato institucional.

- Tarea 2, normas APA: 20 %; vence 30-08-2026.
- Tarea 3, estado del arte: 25 %; vence 06-09-2026.
- Tarea 4, errores y Círculo de Covey: 25 %; vence 06-09-2026.
- Tarea 5, escritura científica: 15 %; vence 13-09-2026.
- Tarea 6, formato institucional: 15 %; vence 13-09-2026.

### Unidad 3. Propuesta de investigación (50 %)

**Resultado esperado:** integrar una propuesta pertinente, coherente y viable.

1. Antecedentes.
2. Planteamiento del problema.
3. Objetivos general y específicos.
4. Justificación.
5. Hipótesis de trabajo.
6. Alcances y limitaciones.
7. Marco teórico.
8. Métodos o procedimientos.
9. Cronograma.
10. Estrategias para la defensa.
11. Presentación ante el Consejo de Posgrado.

#### Productos integradores

- Matriz de consistencia actualizada.
- Anteproyecto completo.
- Presentación y video de defensa.

#### Hitos

| Actividad | Cierre |
|---|---:|
| Tarea 7: foro de tema y título | 20-09-2026, 08:00 |
| Registro del tema | 27-09-2026, 23:59 |
| Tarea 8: antecedentes | 27-09-2026, 23:59 |
| Tarea 9: problema | 27-09-2026, 23:59 |
| Tarea 10: objetivos | 04-10-2026, 23:59 |
| Tarea 11: justificación | 11-10-2026, 23:59 |
| Tarea 12: hipótesis | 18-10-2026, 23:59 |
| Tarea 13: alcances y limitaciones | 25-10-2026, 23:59 |
| Tarea 14: marco teórico | 01-11-2026, 23:59 |
| Tarea 15: métodos | 08-11-2026, 23:59 |
| Tarea 16: cronograma | 15-11-2026, 23:59 |
| Tarea 17: entrega y exposición | 22-11-2026, 23:59 |
| Tarea 18: retroalimentación del Comité | 29-11-2026, 23:59 |

### Vacíos por confirmar

- Código oficial, créditos, periodo y modalidad.
- Documento vigente de LGAC y relación de profesores.
- Lineamiento institucional y formato oficial de titulación.
- Rúbricas, extensiones y formatos de entrega de cada actividad.
- Fechas discrepantes del calendario del aula virtual.

El programa anterior se integra sin cambiar su calendario o porcentajes. Esta consolidacion no acredita una consulta nueva del aula ni actualiza su vigencia.


## Estado de entregables

### Actualizacion verificada del 10 de octubre

[Auditoria de LaTeX y Entregas](referencias-seminario-i/notas-seminario-i/materiales-generales/AUDITORIA-LATEX-Y-ENTREGAS-2026-10-10.md): ocho compilaciones correctas, sin equivalencia automatica con entregables oficiales. Carpeta normalizada a `Entregas`. PDF enviados de T1-T3 recuperados y cotejados por SHA256; difieren de las revisiones de la raiz y figuran enviados y calificados. T4 y T6 figuran sin envio, aunque el campo de calificacion indica Calificado; no se interpreta como entrega. T10 sigue enviada y sin calificar, con Word remoto identico al local. Esta consulta sustituye los estados historicos incompatibles siguientes, sin atribuir nuevas notas numericas ni envios.

### Actividad 10: revisión del 4 de octubre de 2026

[Word acumulativo revisado](Entregas/Tarea10_DeLaCruzMunoz_Revision-2026-10-04.docx) y [PDF de consulta](Entregas/Tarea10_DeLaCruzMunoz_Revision-2026-10-04.pdf), 21 páginas. Incorpora la retroalimentación docente de T1, T3 y T8: antecedentes específicos con alcance de lectura declarado, enfoque administrativo, objetivos precisados e indicadores propuestos. Conserva T9 original sin cambios y utiliza una copia de trabajo con cuatro ampliaciones identificadas. Un objetivo general, cuatro específicos, matriz, Covey e índice nativo actualizado con Microsoft Word. El Word es el archivo requerido; los complementos no lo sustituyen.

[Revisión contractual y mapa de fuentes](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/investigacion/revision-2026-10-04/revision-contractual.md). La versión anterior de T10 se conserva. La auditoría registra la preparación anterior al envío, no una aprobación docente.

**Envío confirmado:** 4 de octubre de 2026, 22:04, hora mostrada por Moodle, módulo 2910. Estado **Enviado para calificar**, todavía sin calificar; enviado 1 hora y 54 minutos antes del cierre. Se entregó únicamente el Word revisado. El archivo recuperado coincide por SHA-256 con el validado: `e17ff0bd89652fcefb190156037c76e2b11827044888d1decf62f246a3c95ff6`. [Recibo](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/comprobantes-envio/2026-10-04/2910-receipt.json), [estado del aula](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/comprobantes-envio/2026-10-04/2910-after-save.txt) y [captura](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/comprobantes-envio/2026-10-04/2910-after-save.png). Las menciones anteriores a «sin envío» describen la fase de preparación y quedan superadas por este comprobante.

Complementos: [reporte PDF](reporte-seminario-i-Actividad-10.pdf), 12 páginas, y [presentación PDF](presentacion-seminario-i-Actividad-10.pdf), 19 diapositivas. [Validación final](referencias-seminario-i/notas-seminario-i/actividad-10-objetivos/investigacion/revision-2026-10-04/validacion-final.json) aprobada para el alcance documental registrado. Se cotejaron los títulos de doce referencias con sus DOI; queda abierta la ampliación científica regional y reciente.

### Entregas del 27 de septiembre de 2026

- **Tarea 8:** [Word](Entregas/Tarea8_DeLaCruzMunoz.docx), 9 páginas, enviado para calificar en Moodle (módulo 2908).
- **Tarea 9:** [Word](Entregas/Tarea9_DeLaCruzMunoz.docx), 14 páginas, enviado para calificar en Moodle (módulo 2909).
- **Registro del tema:** [Word sin firmas](Entregas/RegistroTema_DeLaCruzMunoz.docx) y [PDF firmado](Entregas/RegistroTema_DeLaCruzMunoz_Firmado.pdf), enviados para calificar al módulo 2907 el 27/09/2026 a las 21:43, hora del aula. Ambos archivos recuperados y comprobados por SHA-256. El CVU permanece vacío en ambos documentos; el PDF escaneado se entregó exactamente como lo proporcionó el estudiante.
- Ambas tareas enviadas a las 14:32, hora mostrada por Moodle. Archivos recuperados y comprobados por SHA-256. [Evidencias y detalles](referencias-seminario-i/notas-seminario-i/materiales-generales/auditorias-anteproyecto/moodle-2026-09-27/README.md).

Tema tentativo: **Gestión del cumplimiento normativo para formalizar vTaxi como plataforma de taxis en Nuevo León**. No se afirma aprobación docente del tema.

Historial de revision estructural: 22 de septiembre de 2026. La tabla siguiente describe aquella revision local, no la identidad de los archivos enviados ni un estado vigente de plataforma. Preparación local no equivale a entrega en Moodle ni aprobación del anteproyecto.

| Documento | Fuente y producto | Alcance |
| --- | --- | --- |
| Encuadre de materia | [TEX](referencias-seminario-i/notas-seminario-i/materiales-generales/encuadre/reporte-seminario-i-mga.tex), [PDF](referencias-seminario-i/notas-seminario-i/materiales-generales/encuadre/reporte-seminario-i-mga.pdf) | Reporte base depurado, sin instrucciones de relleno ni citas de memoria editorial. |
| Actividad 1 | [TEX](reporte-seminario-i-Actividad-1.tex), [PDF](reporte-seminario-i-Actividad-1.pdf) | Contenido conservado; compilado con el núcleo local. |
| Actividad 2 | [TEX](reporte-seminario-i-Actividad-2.tex), [PDF](reporte-seminario-i-Actividad-2.pdf) | Contenido conservado; referencias manuales. |
| Actividad 3 | [TEX](reporte-seminario-i-Actividad-3.tex), [PDF](reporte-seminario-i-Actividad-3.pdf) | Contenido conservado; referencias manuales. |
| Actividad 4 | [TEX](reporte-seminario-i-Actividad-4.tex), [PDF](reporte-seminario-i-Actividad-4.pdf) | Infografía autocontenida. Se conserva su formato A4 horizontal, sin imponer formato de ensayo. |
| Actividad 6 | [TEX](reporte-seminario-i-Actividad-6.tex), [PDF](reporte-seminario-i-Actividad-6.pdf), [Word](Entregas/Tarea6_DeLaCruzMunoz.docx) | PDF complementario; el Word requerido por la consigna se conserva sin cambios. |

### Estructura corregida

- [Núcleo local](assets-seminario-i/plantilla/template.tex) y [manifiesto de los módulos replicados](assets-seminario-i/plantilla/manifest.json): derivados del núcleo modular actualizado del repositorio, conservando autoría y licencia.
- [Base reutilizable de actividad](assets-seminario-i/plantilla/reporte-seminario-i-plantilla-actividad.tex): portada ITESCA, marca de agua, pie institucional, metadatos y contenido parametrizable. No compilar directamente.
- [Notas unificadas](Readme%20-%20Seminario%20I.md): apuntes por unidad e histórico del reporte base anterior.
- [Referencias](Readme%20-%20Seminario%20I.md): materiales y guía breve oficial APA incorporados localmente.
- [Trece planeaciones normalizadas](referencias-seminario-i/notas-seminario-i/materiales-generales/historico-planeaciones-2026-10-10/INDICE-GENERADAS.md), sin reemplazar las fichas originales ni las planeaciones por unidad.
- [Inventario](estructura-aulatex.json) y [compilacion](#compilacion-vigente) actualizados.

### Límites académicos

Los datos personales o administrativos no aportados, la vigencia del calendario y la aprobación docente siguen pendientes; no se completan por inferencia. La guía APA descargada no es el manual completo ni sustituye automáticamente el recurso 2.1 del aula. Los originales históricos no se modifican para simular una revisión o entrega anterior.

### Historial de verificacion tecnica del 22 de septiembre de 2026

- Reporte base y actividades 1, 2, 3 y 6 compilados con `latexmk` y pdfLaTeX usando el núcleo local. Registros finales sin errores, citas indefinidas ni cajas desbordadas.
- Portada del reporte base renderizada y revisada visualmente: logotipo oficial, marca de agua, pie institucional y datos académicos legibles.
- Inventario JSON y enlaces Markdown locales comprobados. Materiales y documentos sin exclusiones de Git.
- Réplica de 19 módulos verificada por SHA-256 contra el núcleo modular actualizado. La distribución antigua incompatible no se conserva como plantilla activa.
- No se recompilaron la infografía de la Actividad 4 ni la presentación, cuyos formatos autocontenidos no fueron modificados.

## Compilacion vigente

Ejecutar desde la raiz del repositorio que contiene ITESCA. En Windows:

```powershell
$materia = '.\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga'
.\scripts\latexmk-build.ps1 "$materia\referencias-seminario-i\notas-seminario-i\materiales-generales\encuadre\reporte-seminario-i-mga.tex"
.\scripts\latexmk-build.ps1 "$materia\referencias-seminario-i\notas-seminario-i\materiales-generales\encuadre\presentacion-seminario-i-mga.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-1.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-2.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-3.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-4.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-6.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-seminario-i-Actividad-10.tex"
.\scripts\latexmk-build.ps1 "$materia\presentacion-seminario-i-Actividad-10.tex"
```

La presentacion base de materia es una entrada reutilizable, no una entrega especifica ni una compilacion comprobada en la auditoria del 10 de octubre. No confundir los comandos disponibles con ejecuciones verificadas.

En Linux, para la infografia y el complemento de Tarea 6:

```bash
bash scripts/latexmk-build.sh ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-Actividad-4.tex
bash scripts/latexmk-build.sh ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-Actividad-6.tex
```

### Contrato unico

- El unico argumento obligatorio del compilador es la ruta del TEX. El PDF final queda junto a su fuente; Entregas conserva los archivos destinados al aula y las copias recuperadas de lo enviado.
- El motor es pdfLaTeX mediante latexmk; el nucleo local no requiere fontspec. La bibliografia local es seminario-i.bib; varias actividades presentan referencias manuales.
- Los reportes 1, 2, 3 y 6 cargan assets-seminario-i/plantilla/template.tex. Tarea 2 no es autocontenida: tiene formato y referencias locales, pero depende de ese nucleo.
- El reporte base y Tarea 10 cargan assets-seminario-i/plantilla/reporte-seminario-i-plantilla-actividad.tex. La infografia 4 y la presentacion de Tarea 10 son autocontenidas; los emblemas residen en ITESCA/assets-itesca.
- El nucleo replicado contiene 19 modulos con manifiesto de procedencia. No asumir una dependencia de ITESCA/_shared si no existe.
- No compilar plantillas aisladas ni versiones historicas como entregables. Las entradas genericas con identidad UnADM no estan certificadas para ITESCA.
- Compilar sin errores no acredita cumplimiento de rubrica, formato oficial, envio o calificacion. Los PDF actuales de T1-T3 no son las copias exactas enviadas. T6 y T10 requieren Word; LaTeX es complementario.

### Particularidades de Tareas 4 y 6

Tarea 4 produce portada e infografia en dos paginas A4 horizontales con TikZ y bibliografia manual. El control 26130503 ya esta incorporado; semestre y fecha de entrega vigente requieren revision. [Revision de la actividad 4](referencias-seminario-i/notas-seminario-i/actividad-4-errores-circulo-covey/revision-actividad-04.md).

Tarea 6 carga el [contenido editable](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/contenido-actividad-6.tex) y dos imagenes locales; no necesita descargas para compilar. Cinco referencias manuales, indice, listas y referencias cruzadas se resuelven con las pasadas de latexmk. [Control LaTeX](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/validar_latex.py) y [resultado registrado](referencias-seminario-i/notas-seminario-i/actividad-6-formato-institucional/elaboracion/validacion/verificacion-latex.json). El resultado historico del control no sustituye una ejecucion nueva. El [Word preparado](Entregas/Tarea6_DeLaCruzMunoz.docx) no se reemplaza por el PDF. En Windows, el validador del Word requiere PYTHONUTF8=1 para leer la salida de Poppler.

## Discrepancias y regla de mantenimiento

Uniformizacion posterior del 10 de octubre: las planeaciones vigentes se consolidaron en 19 MD (tareas 1-18 y foro), sin JSON auxiliares ni indices paralelos en su carpeta. Se conservan las fichas previas en notas historicas, enlazadas para trazabilidad. Para T1-T4, T6 y T10 se incorporo la consigna cotejada el 10 de octubre; prevalece sobre requisitos locales incompatibles. Los pendientes historicos no describen automaticamente el estado actual. Las planeaciones de otras tareas conservan su alcance local y requieren cotejo antes de ejecutar o enviar.

La raiz contiene los productos LaTeX elaborados de T1, T2, T3, T4, T6 y T10, sus PDF y la presentacion auxiliar de T10. Las plantillas, encuadre e identidades genericas se retiraron a assets o notas. T8 y T9 tienen Word en Entregas y comprobantes; no se inventaron fuentes LaTeX equivalentes. T5, T7 y T11-T18 no se declaran completas por tener planeacion. T4 mantiene semestre pendiente y T2 requiere adecuacion al formato oficial: reorganizar no resuelve estos requisitos de contenido. La elaboracion de productos faltantes y las correcciones academicas requieren un trabajo posterior especifico, no copias de plantillas. Las seis fuentes de actividad recompilaron tras actualizar dependencias.

Las dos guias de compilacion eran versiones breve y ampliada del mismo procedimiento, actualizadas por separado. El estado de entregables mezclaba verificaciones historicas con consultas posteriores. Esto produjo instrucciones repetidas, rutas con capitalizacion antigua, una clasificacion incorrecta de Tarea 2 y pendientes de control que ya estaban resueltos.

Se consolida un unico contrato y control de estado en este Readme. Los estados se identifican por fecha y evidencia; la consulta del 10 de octubre prevalece sobre estados anteriores incompatibles. La evidencia historica se conserva como tal, sin atribuir nuevas consultas a T8/T9 ni aprobar requisitos pendientes. Actualizar aqui el estado vigente y sus enlaces cuando cambien archivos, requisitos o entregas; mantener comprobantes y auditorias especificas en notas, no crear otra guia paralela de compilacion. Esta consolidacion no modifica reportes, entregas ni publicaciones.
