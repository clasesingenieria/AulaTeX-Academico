# Busqueda de grabaciones ITESCA

## Estado actual: 12 de octubre de 2026

**Dos grabaciones de Plan de Negocios con MP4 y SRT verificados: arranque y S1.**
**Revision de Plan de Negocios cerrada con pendientes documentados:** S2 y S3
tienen accesos directos en lugar de copias locales del video; sus SRT siguen
pendientes. Esto no equivale a tener todas las grabaciones y transcripciones.

| Materia / grabacion | Estado | Pendiente |
| --- | --- | --- |
| Plan de Negocios: Sesion de arranque | MP4 y SRT homonimos, 429.25 segundos (7:09), 92 segmentos | Revision humana; fecha de sesion no indicada en la fuente |
| Plan de Negocios: S1 | MP4 de 88.498.641 bytes, 1153.033 segundos (19:13) y SRT de 267 segmentos | Revision humana; fecha de sesion no confirmada |
| Plan de Negocios: S2 | Acceso directo .url al visor; fecha en nombre 2026-09-22; video no descargado | Descarga denegada y transcripcion no recuperada en el visor actual |
| Plan de Negocios: S3 | Acceso directo .url al visor; fecha en nombre 2026-09-29; video no descargado | Descarga denegada y transcripcion no recuperada en el visor actual |
| Plan de Negocios: S4 | El campo del enlace contiene texto de retroalimentacion, no una URL de grabacion | Solicitar enlace correcto o confirmacion de que no hubo grabacion; no es reparable por decodificacion |
| Seminario I | Revision ampliada: 52 paginas HTML accesibles; sin grabaciones ni enlaces multimedia candidatos identificados | No acredita ausencia en adjuntos, reuniones privadas o recursos restringidos |
| Fundamentos de Gestion Administrativa, GGFG02 | Tres sesiones localizadas (2, 3 y 4), con accesos directos .url | MP4 y SRT pendientes: S2/S3 con descarga denegada y S4 con acceso al archivo denegado |

La sesion de arranque estaba incrustada mediante `video/source` en Moodle y
no aparecia en el detector anterior de enlaces rotulados como grabacion.
Dos referencias al mismo medio se deduplicaron. Se conservaron aparte, como
apoyos o instrucciones y no como sesiones confirmadas, tres videos de Moodle
y un tutorial de Google Forms en YouTube.

La [carpeta de grabaciones](../maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios/grabaciones-plan-de-negocios/)
es plana y contiene dos MP4, sus dos SRT y dos accesos directos .url. No se encontraron pistas de
subtitulos publicadas en el reproductor de arranque. Se uso Purfview Faster
Whisper XXL, large-v3, Spanish, CUDA y `--standard`; codigo de salida 0 y marcador
de finalizacion confirmados. Se validaron numeracion, texto, orden, tiempos,
duracion, pistas, hashes y decodificacion integral del MP4 con FFmpeg.
La reutilizacion de los archivos se probo sin acceso al navegador ni ejecucion
adicional de Whisper. Original del motor, log, procedencia y verificacion estan
en `notas-plan-de-negocios/materiales-generales/control-grabaciones/`.

S1 se obtuvo mediante la descarga original de SharePoint. Aunque la herramienta
no recibio el evento de descarga, el archivo aparecio en Descargas con el tamano
exacto anunciado por el servidor. Se copio al proyecto, conservando ese original
con el mismo SHA256. No se guardaron URLs firmadas ni credenciales en el proyecto.
La pista Shaka observada estaba vacia y no se recuperaron subtitulos publicados;
no se afirma que sean inexistentes. Se transcribio con large-v3, Spanish, CUDA
y `--standard`. El motor devolvio **3221226505**, no cero, despues de escribir
la salida y el marcador de fin. Se revisaron las 188 lineas del log, la duracion
completa del audio, los 267 segmentos y el MP4 completo. No se presenta la
incidencia como un codigo de salida normal. El SRT sigue pendiente de revision.

S2 y S3 devolvieron HTTP 200 con `text/html` tras redireccionar a
`AccessDenied.aspx`, no un archivo MP4. No se confundio ese HTTP 200 con descarga
exitosa ni se intentaron rutas alternativas para eludir el permiso.
Los nombres contienen fechas de las grabaciones, mientras que la creacion de
los archivos aparece al dia siguiente en UTC; se conservaron esas distinciones.
Resultado y detalles en `control-grabaciones/resultado-sharepoint-2026-10-12.json`
y `control-grabaciones/S1-procedencia.json`.

## Accesos directos y transcripciones pendientes

Los accesos S2 y S3 guardan direcciones estables del visor de SharePoint con
unicamente el parametro `id` del archivo. No contienen contrasenas, cookies,
firmas ni parametros temporales de comparticion. Se abrieron ambos destinos y
se comprobaron sus titulos. Necesitan la cuenta institucional y no conceden
permisos nuevos ni garantizan que el reproductor funcione en todos los navegadores.

En la consulta actual, ambos visores muestran un error de carga y no exponen
controles de transcripcion ni pistas de texto recuperables. **No se obtuvieron
SRT de S2/S3 y no se afirma que no existan transcripciones.** Si el organizador
comparte un SRT/VTT o texto publicado accesible, puede recuperarse; con audio o
video autorizado tambien puede ejecutarse el motor local. No se extrajo audio
por otras rutas para sortear la restriccion ni se crearon SRT vacios.

No se creo un acceso S4 que simule una grabacion: falta un destino real. El
enlace del curso, conservado en los registros, permite volver a comprobarlo.

## Seminario I: continuacion realizada

Se ejecuto `buscar-grabaciones.py --seminario-only` con la boveda AulaTeX.
El recorrido incluye curso, paginas, recursos, enlaces URL y discusiones:
**52 respuestas HTML, todas HTTP 200**, sin alcanzar el limite de recorrido.
Una segunda inspeccion de enlaces y elementos de audio/video, incluidos
proveedores multimedia aunque no estuvieran rotulados como grabaciones,
tampoco encontro candidatos. No se abrieron evaluaciones, reuniones ni envios.

Evidencia en `referencias-seminario-i/notas-seminario-i/materiales-generales/control-grabaciones/`:
inventario de busqueda fechado y `revision-multimedia-2026-10-12.json`.
No se crearon carpetas multimedia vacias ni accesos a sesiones no localizadas.
La busqueda queda limitada al HTML accesible: no certifica que no existan
grabaciones dentro de adjuntos o canales privados que no se hayan facilitado.

## Fundamentos de Gestion Administrativa: revision realizada

Se comprobo el curso **372, GGFG02** de forma independiente con
`buscar-grabaciones.py --fundamentos-only`. El recorrido incluyo 71 entradas:
66 respuestas HTML y 5 redirecciones opacas no inspeccionadas; no se alcanzo
el limite. No se abrieron evaluaciones, reuniones ni envios.

| Sesion rotulada en el aula | Fecha en el nombre del archivo | Resultado |
| --- | --- | --- |
| 2 | 2026-08-19 | Metadatos accesibles, 45.463.243 bytes; descarga redirige a AccessDenied.aspx. Acceso .url creado |
| 3 | 2026-08-26 | Metadatos accesibles, 144.660.844 bytes; descarga redirige a AccessDenied.aspx. Acceso .url creado |
| 4 | 2026-09-02 | Resumen Teams con referencia explicita fileUrl a un MP4 de SharePoint; acceso al archivo denegado. Acceso .url creado |

La sesion 4 de Fundamentos **no tiene el mismo error que la S4 de Plan de
Negocios**: su enlace de Teams si referencia un archivo real. Se uso esa
referencia publicada, sin inventar un destino ni entrar a una reunion.
El archivo menciona semana 3 aunque el aula lo rotula sesion 4; se preservan
ambos datos. Las fechas indicadas proceden de los nombres de los archivos,
no de convertir sus fechas de creacion UTC en fechas locales.

Se guardaron tres accesos estables al visor, con solo el parametro id, sin
firmas, contrasenas ni cookies, en la
[carpeta de grabaciones de Fundamentos](../maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/referencias-fundamentos-de-gestion-administrativa/grabaciones-fundamentos-de-gestion-administrativa/).
**No hay MP4 ni SRT locales de esas tres sesiones.** Los accesos no conceden
permisos ni garantizan reproduccion con la cuenta actual. No se recuperaron
controles o pistas de transcripcion accesibles; no se afirma que no existan.

Los seis videos de YouTube incrustados se cotejaron con sus titulos y autores
publicos: organizacion, teoria organizacional, toma de decisiones, liderazgo,
diversidad y estilos de liderazgo. No se acreditaron como grabaciones del
grupo. Tampoco se conto como clase un MP4 publicado en una discusion del foro.
No se identifico un enlace rotulado como grabacion de sesion 1 en esta consulta.

[Resultado y procedencia de Fundamentos](../maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/referencias-fundamentos-de-gestion-administrativa/notas-fundamentos-de-gestion-administrativa/materiales-generales/control-grabaciones/resultado-grabaciones-2026-10-12.json).
Los inventarios fechados conservan la primera busqueda; el resultado enlazado
incorpora la comprobacion posterior con la cuenta Microsoft autenticada.
Quedan pendientes permisos o copias autorizadas y las transcripciones.

## Vias revisadas para S2, S3 y S4 de Plan de Negocios

Se abrio la biblioteca oficial del curso, carpeta Recordings, en la sesion
institucional autenticada. Mostro dos archivos visibles, correspondientes a
S2 y S3, ambos con marca Solo lectura. Se inspeccionaron las opciones de
archivo y el menu contextual; no aparecio Descargar. La marca Solo lectura
por si sola no demuestra bloqueo de descarga, pero se conserva tambien el
rechazo AccessDenied.aspx observado en la descarga original.

Una nueva lectura de los metadatos de ambos archivos devolvio HTTP 200,
confirmando acceso de la cuenta a esos datos. La consulta acotada para buscar
otra copia MP4 en General devolvio HTTP 403; no se intentaron otras rutas para
eludirlo. No se afirma que no existan copias fuera del alcance autorizado.
El visor de S3 tambien muestra un error de carga; ese error tecnico no se uso
como prueba independiente de falta de permisos.

S4 no contiene una direccion de SharePoint ni siquiera tras decodificar el
valor publicado: contiene texto de retroalimentacion de otra actividad.
No se guardo ese texto ni se invento una direccion o fecha para sustituirlo.
No se identifico un cuarto archivo en la carpeta Recordings visible.

Vias autorizadas que quedan:

1. Pedir al propietario que habilite una descarga autorizada de S2/S3, si la politica institucional lo permite.
2. Pedir al organizador las copias MP4 por el canal institucional, o sus subtitulos SRT/VTT o transcripciones si existen.
3. Pedir a la docente que corrija el enlace S4 o confirme si esa sesion fue grabada.

[Registro de esta comprobacion](../maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios/notas-plan-de-negocios/materiales-generales/control-grabaciones/vias-s2-s3-s4-2026-10-12.json).
No se modificaron permisos ni se enviaron solicitudes o mensajes.

### Solicitud preparada, no enviada

Profesora: puedo acceder a la biblioteca de Plan de Negocios, pero las
grabaciones S2 y S3, identificadas en sus nombres con las fechas 22 y 29 de
septiembre, no muestran la opcion Descargar y la descarga devuelve acceso
denegado. ¿Podria habilitar una descarga autorizada o proporcionarme los MP4
y, si existen, sus subtitulos o transcripciones? Ademas, el enlace S4 contiene
texto de retroalimentacion en lugar de una direccion de video. ¿Podria
publicar el enlace correcto o confirmar si esa sesion no fue grabada? Gracias.

## Perfil Microsoft confirmado

El usuario identifico su perfil de trabajo mediante captura. La entrada unica
correspondiente es **Edge Profile 19, ITESCA Jonathan de la Cruz**, con dominio
institucional. No se inspeccionaron otros perfiles de usuario. La lectura normal de la sesion con
yt-dlp fallo porque Edge mantiene bloqueada la base de cookies. No se forzo el
acceso, no se cerraron ventanas y no se exportaron cookies.

Ese fallo no demostraba falta de permisos: solo impedia reutilizar las cookies
de Edge. Posteriormente, el usuario autorizo el inicio de sesion institucional
en el navegador accesible por las herramientas. Microsoft acepto el acceso y
se eligio no mantener la sesion iniciada permanentemente. Se pudo abrir S1 y
descargarla; el rechazo de S2/S3 se comprobo despues de autenticar la cuenta.

Los enlaces originales S1-S3 se trasladaron en memoria desde el aula mediante un
servidor local de lectura unica, cerrado al finalizar. Los nuevos accesos S2/S3
guardan solo la direccion estable del visor, sin firmas ni parametros de sesion.
El registro `control-grabaciones/acceso-sharepoint-2026-10-12.json` conserva
el bloqueo inicial; el resultado vigente es `resultado-sharepoint-2026-10-12.json`.
Para continuar hacen falta permisos de descarga para S2/S3 y el enlace correcto
de S4. No se solicitaron cambios de permisos ni se enviaron mensajes a docentes.

## Consulta anterior del 12 de octubre de 2026

La seccion siguiente conserva el alcance anterior, previo a recuperar la
sesion de arranque. Sus afirmaciones de ausencia de descargas son historicas.

Se ampliaron las consultas a 22 paginas de Plan de Negocios y 39 de Seminario I:
curso, paginas, recursos URL, avisos y discusiones accesibles, sin iniciar
evaluaciones ni reuniones. No se alcanzo el limite de recorrido. Los resultados
siguen siendo S1-S3 en SharePoint con login Microsoft, S4 malformado y ningun
enlace de grabacion identificado en las paginas consultadas de Seminario I.
No equivale a ausencia en adjuntos o recursos restringidos.

El acceso Microsoft queda pendiente de intervencion directa del usuario.
No se descargaron ni transcribieron medios ITESCA. Las nuevas consultas tienen
marca de hora en `control-grabaciones/inventario-busqueda-2026-10-12-*.json`;
se preservaron las anteriores. El inspector usa la conexion TLS validada de
Chromium y no imprime cabeceras de autenticacion en errores.

Incidencia de la continuacion: antes de ese ajuste, una excepcion TLS de
APIRequestContext incluyo cabeceras de sesion en la salida tecnica de la
herramienta. No se copiaron a los archivos del proyecto. Se sustituyo esa
consulta por fetch de mismo origen en Chromium y se suprimieron las trazas
externas en el manejador de errores; la nueva consulta finalizo correctamente.

Consulta autenticada Moodle: 12 de octubre de 2026. Solo lectura; no se
iniciaron reuniones, examenes, envios ni autenticacion externa de Microsoft.

| Materia | Resultado | Pendiente |
| --- | --- | --- |
| Plan de Negocios, curso 213 | Grabaciones S1, S2 y S3 enlazadas a SharePoint institucional; redirigen a inicio de sesion Microsoft | Acceder con cuenta institucional y comprobar permisos, reproductor y descarga |
| Plan de Negocios, S4 | Destino malformado; no se abrio | Solicitar enlace corregido a la docente; no adivinar URL |
| Seminario I, curso 215 | No se encontraron enlaces rotulados como grabaciones en contenido visible del curso | Consultar avisos o docente; no afirmar que no existen |

No se descargaron ni transcribieron archivos. Moodle autenticado no concede
automaticamente acceso a SharePoint. La busqueda inicial del panel solo
identifico estos dos cursos; no se certifica revision de todas las materias
ITESCA, incluidos cursos anteriores o Fundamentos.

Registros de consulta en cada materia:
`referencias-<materia>/notas-<materia>/materiales-generales/control-grabaciones/inventario-busqueda-2026-10-12.json`.
No contienen credenciales, cookies, enlaces privados de SharePoint ni tokens.
Para volver a los enlaces, abrir Plan de Negocios en Moodle y seleccionar
Grabacion S1, S2 o S3. No reutilizar credenciales Moodle en Microsoft sin
confirmar identidad de cuenta. Los secretos se introducen directamente en
el navegador, nunca en la conversacion.

Cuando se obtenga acceso y descarga permitida, destino previsto:
`referencias-<materia>/grabaciones-<materia>/`, sin subcarpetas; archivos
`ITESCA - <identificador> - <sesion> <fecha> - <tema>.mp4` y SRT homonimo.
Fecha y tema solo se completan con datos del aula/reproductor. Controles y
procedencia fuera de la carpeta multimedia; no crear videos ni SRT ficticios.