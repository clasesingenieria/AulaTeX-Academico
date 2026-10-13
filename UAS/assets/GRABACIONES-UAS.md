# Busqueda de grabaciones UAS

## Comprobacion actual

Se repitio la consulta con la boveda AulaTeX el **12 de octubre de 2026**:
**99 paginas HTML accesibles**, 51 de Derecho mercantil y 48 de Investigacion,
todas con HTTP 200 y sin alcanzar el limite de recorrido. Se conservaron los
inventarios anteriores y se recuperaron los titulos completos de las paginas
Videos_S1/S2/S3/S4, que antes podian quedar vacios en el inspector.

Resultado: **17 videos de apoyo identificados y ninguna grabacion del grupo
confirmada**. No se trata de un rechazo de descarga como en SharePoint: en el
HTML revisado no se localizaron enlaces identificables de sesiones docentes.
No se descargaron los apoyos como si fueran clases ni se generaron SRT o
accesos directos ficticios. Los enlaces publicos de los apoyos quedan en el
inventario para la revision de referencias.

Se cotejaron nuevamente las descripciones de seis recursos del aula: cuatro
paginas de videos de Derecho, la pagina de fuentes de informacion y la lista
TEDx de Investigacion. Indican autores externos y fechas historicas; no son
evidencia de sesiones grabadas del grupo actual. Los archivos locales de UAS
inspeccionados tampoco aportaron MP4, audio, SRT o accesos a grabaciones; la
carpeta GRUPO 101 LCP - IAC contiene documentos, no medios de clase.

El panel consultado permitio identificar Derecho mercantil. Investigacion
tambien siguio accesible mediante su enlace conocido; esto no se presenta
como un inventario exhaustivo de matriculas o cursos archivados.

Evidencia actual:

- [Derecho mercantil: verificacion y descripciones](../licenciatura-en-contaduria-uas/derecho-mercantil/referencias-derecho-mercantil/notas-derecho-mercantil/materiales-generales/control-grabaciones/verificacion-grabaciones-2026-10-12.json).
- [Investigacion: verificacion y descripciones](../licenciatura-en-contaduria-uas/investigacion-aplicada-a-la-contaduria/referencias-investigacion-aplicada-a-la-contaduria/notas-investigacion-aplicada-a-la-contaduria/materiales-generales/control-grabaciones/verificacion-grabaciones-2026-10-12.json).

Para continuar con grabaciones del grupo hace falta localizar el enlace
publicado por la figura docente o facilitado en el canal de clase. No se
afirma que no existan en adjuntos, Teams, Zoom u otros espacios privados no
consultados. No se reutilizaron cuentas de ITESCA u otras instituciones.

## Alcance y clasificacion

Consulta autenticada del 12 de octubre de 2026 con el inspector existente
`aulaTEX/uas_course_inspect.py --recordings`. Recorrido de pestañas y enlaces
HTML accesibles de paginas, recursos, URL y foros; no se iniciaron reuniones,
evaluaciones ni envios.

| Materia | Alcance | Resultado |
| --- | --- | --- |
| Derecho mercantil, 632 | 51 paginas consultadas | 16 videos de apoyo externo; ninguna sesion del grupo confirmada |
| Investigacion aplicada a la contaduria, 634 | 48 paginas consultadas | Un video de apoyo y una lista de ponencias; ninguna sesion del grupo confirmada |

Las descripciones de Videos_S1/S2/S3/S4 identifican temas, autores externos y
publicaciones historicas. Derecho incluye historia, fuentes, normas, Estado,
sujetos, hechos/actos juridicos, obligaciones y contratos. Investigacion
identifica un video sobre fuentes de informacion de 2019 y una lista TEDx
como guia para ponencias. No se confundieron esos apoyos con grabaciones
docentes de las sesiones actuales. Tampoco se contaron PDFs incrustados ni
`videoseries` como videos individuales.

No se descargaron ni transcribieron esos apoyos como grabaciones del grupo.
La ausencia de sesiones confirmadas no demuestra que no existan en adjuntos,
avisos posteriores o recursos restringidos. Queda pendiente un enlace de
grabacion docente verificable.

En cada materia se conservaron los registros bajo
`referencias-<slug>/notas-<slug>/materiales-generales/control-grabaciones/`:

- `busqueda-grabaciones-2026-10-12-*.json`: paginas consultadas y candidatos.
- `clasificacion-grabaciones-2026-10-12.json`: clasificacion cotejada con las descripciones del aula.
- `verificacion-grabaciones-2026-10-12.json`: nueva consulta, titulos de recurso y descripciones de apoyo comprobadas.

No se crearon carpetas multimedia vacias ni se exportaron sesiones del navegador.
