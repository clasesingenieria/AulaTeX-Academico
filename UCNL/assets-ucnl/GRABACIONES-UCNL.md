# Grabaciones UCNL

## Comprobacion tecnica finalizada: 12 de octubre de 2026

Lote ejecutado con Deno y la sesion iniciada del Firefox convencional.
Treinta y un pares MP4/SRT verificados, en carpetas planas de las seis materias.
Este cierre permite pasar a la comprobacion de referencias. No significa que
esten publicadas todas las sesiones del tetramestre ni que se haya realizado
una revision humana integral de las transcripciones.

| Materia | Medios conservados | Pendiente real |
| --- | --- | --- |
| Administracion II, 20297 | Cinco: bienvenida y capitulos 11, 12, 13 y 14-15 | Un bloque con enlace vacio/autorreferente, sin destino de grabacion |
| Macroeconomia, 20322 | Cinco: bienvenida y sesiones 1, 2, 3 y 4 | `7DmSRMPqQ3A` seguia anunciado como emision futura; una referencia interna UCNL sin archivo de video identificado pasa a la fase de referencias |
| Matematicas II, 20328 | Cinco: video de presentacion del tetra, sesion 2 y semanas 3, 4 y 5 | El enlace rotulado Grabacion en Teams coincide con un acceso a reunion, no con un archivo de grabacion |
| Contabilidad II, 20308 | Cuatro: semanas 2, 3, 4 y 5 | En semana 6 se encontro acceso Zoom, no una grabacion adicional publicada |
| Derecho Constitucional, 20311 | Ocho archivos: partes 1 y 2 de las semanas 2, 3, 4 y 5 | Son cuatro sesiones divididas en dos, no ocho sesiones; semana 6 muestra acceso Zoom |
| Ingles II, 20336 | Cuatro: bienvenida de semana 2 y clases de semanas 3, 4 y 5 | Semana 6 muestra acceso Zoom, no una grabacion adicional publicada |

En esta ampliacion se preservaron los trece pares anteriores y se agregaron
dieciocho: dos bienvenidas y dieciseis archivos de Contabilidad, Derecho e Ingles.
En total, veintiocho SRT proceden de subtitulos automaticos de YouTube y tres
de Faster Whisper XXL. Todos siguen pendientes de revision humana. No se
repitieron las transcripciones previas ni se sobrescribieron sus contenidos.

Se comprobaron 110 entradas de lectura entre los seis cursos: 82 devolvieron
HTML y 28 devolvieron redireccion opaca (estado 0 de fetch con redirect manual).
No se alcanzo el limite de recorrido. Los destinos de esas redirecciones y los
adjuntos no se consideran revisados por esta auditoria de grabaciones.
Los registros `auditoria-recursos-*.json` de cada materia detallan el alcance.

### Aclaracion sobre Teams

Se verifico el destino, no solo el rotulo: en el aula, "Grabacion" y "Entrar a
la videollamada" apuntan al mismo acceso de Teams. Los destinos inspeccionados
son de tipo `/meet/` o `/l/meetup-join/`. No hay en ellos un archivo concreto que
pueda descargarse como grabacion, y no se iniciaron reuniones.
Esto NO significa que las grabaciones de Teams sean indescargables: un archivo
real de grabacion, normalmente en SharePoint/OneDrive, puede permitir descarga
segun la cuenta y los permisos. No se acredito ese archivo mediante este enlace.

### Orden de comprobacion

| Fase | Estado | Alcance siguiente |
| --- | --- | --- |
| Grabaciones | Comprobacion tecnica finalizada con pendientes externos documentados | 31 MP4 y 31 SRT verificados; no se certifica literalidad de los SRT |
| Referencias | Siguiente fase; aun no se declara comprobada | Contrastar documentos y videos de apoyo con el aula, verificar archivos, procedencia y referencias internas pendientes |
| Actividades | Estado de Moodle comprobado el 12/10; revision documental pendiente | [Notas, entregas y plazos actualizados](../REPORTE-ACTIVIDADES-2026-10-12.md); falta cotejar fuentes y calidad de entregables. No se enviaron tareas, mensajes ni intentos |

[Resultado por video, hashes y procedencia](resultado-grabaciones-2026-10-12.json).
En cada materia, `notas-<slug>/materiales-generales/control-grabaciones/`
conserva originales de subtitulos, verificaciones e historial. No se guardan
cookies, contrasenas ni URLs firmadas en esos registros.

Se verificaron pistas, duracion, SHA256, numeracion y texto no vacio del SRT,
orden y tiempos dentro del medio, y decodificacion integral con FFmpeg.
Administracion II usa semana, tema, fecha de sesion y materia en el nombre.
Las otras materias conservan los nombres anteriores; donde la fecha de clase
no esta confirmada, no se sustituye por la fecha de publicacion de YouTube.
Los dos nombres historicos de Macroeconomia se conservaron.

## Nombres de Administracion II

Semanas y fechas cotejadas el 12 de octubre de 2026 en el bloque de sesion
sincrona que contiene cada video del curso 20297. La numeracion empieza en
semana 2 para estas cuatro grabaciones: no se renumero como semana 1.

| Semana | Fecha anunciada de la sesion | Tema |
| --- | --- | --- |
| 02 | 2026-09-14 | Administracion y seleccion de recursos humanos |
| 03 | 2026-09-21 | Evaluacion de desempeno y plan de carrera |
| 04 | 2026-09-28 | Cambio y desarrollo de administradores y organizacion |
| 05 | 2026-10-05 | Factores humanos, motivacion y liderazgo |

Formato: `Semana NN - Tema - AAAA-MM-DD - UCNL ADM2`, con MP4 y SRT homonimos.
El tema completo de la semana 4 se conserva en los metadatos; solo se abrevia
en el nombre para facilitar su lectura en el explorador.

[Metadatos de semana, fecha y tema](../licenciatura-en-administracion/administracion-ii-lad/referencias-administracion-ii/notas-administracion-ii/materiales-generales/control-grabaciones/sesiones-por-semana.json).
Los inventarios vigentes contienen las rutas nuevas, el titulo academico y
el ID/titulo original de YouTube. Los controles asociados se renombraron
sin alterar su contenido. El registro de equivalencias
`control-grabaciones/renombrado-semanas-2026-10-12.json` permite resolver los
nombres de inventarios historicos, que no se reescribieron.
Renombrado verificado mediante SHA256: los cuatro MP4 y cuatro SRT conservan
exactamente sus bytes. No se modificaron etiquetas internas del MP4 ni se
repitieron descargas, recodificaciones o transcripciones.

## Configuracion verificada

- Subtitle Edit: `yt-dlp.exe` localizado en `%APPDATA%\Subtitle Edit`, carpeta ya incluida en el PATH de usuario.
- Deno 2.9.7 instalado; `%APPDATA%\yt-dlp\config` ya contiene `--js-runtimes "deno:RUTA_A_DENO.exe"` con su ruta real.
- yt-dlp 2026.8.19 y yt-dlp-ejs 0.8.0; dependencia EJS exacta comprobada.
- El script Python aplica Deno explicitamente: la API no lee automaticamente la configuracion de la CLI.
- Firefox convencional activo: `C:\Program Files\Mozilla Firefox\firefox.exe`, sin argumento de perfil alternativo; unico predeterminado declarado `Profiles/ehmfttic.default-release`. Se uso solo ese perfil, no Tor.
- Edge Default contenia la cuenta autorizada, pero su base de cookies estaba bloqueada por el navegador abierto. No se forzo su lectura.

Reanudacion desde la raiz del repositorio:

```powershell
& .\.venv\Scripts\python.exe .\UCNL\assets-ucnl\descargar-transcribir-grabaciones.py --browser firefox --profile "$env:APPDATA\Mozilla\Firefox\Profiles\ehmfttic.default-release"
```

El script conserva pares existentes antes de consultar YouTube. Prioriza
subtitulos accesibles del autor y luego automaticos en el idioma original
identificado; si no puede
obtenerlos y existe audio autorizado, utiliza Purfview Faster Whisper XXL,
large-v3, el idioma identificado (espanol por defecto), CUDA y `--standard`.
La opcion `--deep-audit` revisa tambien recursos y avisos de solo lectura;
`--audit-only` no descarga ni transcribe. El detector incluye bloques de
Grabacion, enlaces Clase grabada y partes de sesiones, no solo el rotulo
Ver la sesion grabada. Dependencias del entorno: yt-dlp con
su extra `default`, srt, playwright y beautifulsoup4, ademas de FFmpeg.
Si cambia el perfil activo, confirmarlo antes de reutilizar el comando.

La sesion Firefox resolvio los rechazos anteriores: incluso tres videos que
sin sesion respondian "This video is not available" se descargaron. Deno
resuelve la parte JavaScript; no sustituye autenticacion ni permisos.

## Capitulo 11: original conservado

ID `6cwxqJcswrY`, confirmado en el aula de Administracion II. MKV original de
196.422.734 bytes, H.264/Opus y 3162.001 segundos: preservado con SHA256
coincidente. MP4 H.264/AAC de 229.334.174 bytes y 3161.984 segundos; video sin
recodificacion y audio convertido a AAC para compatibilidad.

SRT de Faster Whisper XXL: 793 segmentos. El motor produjo 797 entradas;
tres tenian duracion cero en 32:18.820. Se agruparon las entradas originales
474-478 con los limites existentes 32:17.120-32:48.800, conservando todas las
palabras. Original, log completo y reparacion permanecen en control.
Ese tramo requiere revision temporal. El log contiene el marcador de fin;
el codigo de salida no se registro antes del fallo inicial de validacion,
por lo que no se certifica codigo cero. Se recupero la salida sin repetir
Whisper, y se verificaron el SRT y la decodificacion completa del MP4.

## Busqueda inicial: registro historico

Lo siguiente describe la consulta anterior a las descargas. No representa
el estado actual de la tabla superior.

Consulta autenticada del 12 de octubre de 2026, solo lectura de seis cursos.
No se iniciaron reuniones, examenes, SCORM ni H5P. No se descargaron videos
ni se ejecutaron motores de transcripcion.

| Materia | Hallazgos visibles | Alcance y pendiente |
| --- | --- | --- |
| Administracion II, 20297 | Cuatro enlaces Ver la sesion grabada; presentaciones de sesiones capitulos 11-16 | Destinos internos sin reproduccion confirmada; presentacion no equivale a grabacion |
| Macroeconomia, 20322 | Cinco enlaces rotulados Ver la sesion grabada dirigidos a YouTube | Comprobar titulo, fecha, acceso y duplicados antes de contar sesiones o descargar |
| Matematicas II, 20328 | Cinco enlaces rotulados como grabacion a YouTube, uno Teams y uno interno en la segunda consulta | Lista visible cambio entre consultas; no se acredita cantidad de sesiones unicas ni permisos Teams |
| Derecho Constitucional, 20311 | Enlace de reunion Zoom | No se identifico grabacion; enlace de acceso excluido de los registros |
| Contabilidad II, 20308 | Sin enlaces candidatos visibles | No prueba ausencia en avisos, recursos u otras secciones |
| Ingles II, 20336 | Sin enlaces candidatos visibles | No prueba ausencia en avisos, recursos u otras secciones |

[Primera busqueda saneada](busqueda-grabaciones-2026-10-12.json) y
[clasificacion de destinos](destinos-grabaciones-2026-10-12.json).
Los registros no conservan enlaces de reuniones con claves ni enlaces
privados de videos. Usar el curso como punto de entrada para nuevas consultas.

Macroeconomia y Matematicas II son los mejores candidatos para continuar
la verificacion. Un enlace a YouTube no acredita descarga autorizada ni que
sea una clase docente en lugar de material complementario. Teams puede
requerir cuenta institucional y permisos propios. No eludir restricciones.

Si posteriormente se obtienen archivos, conservarlos en cada materia bajo
`referencias-<materia>/grabaciones-<materia>/`, sin subcarpetas, con MP4 y
SRT homonimos identificados por materia, sesion, fecha y tema verificados.
Inventarios y procedencia en notas/materiales-generales/control-grabaciones.
No crear carpetas de medios vacias ni transcripciones ficticias. La autorizacion
actual del usuario incluye transcribir UCNL y sustituye la preferencia anterior
de no ejecutar Whisper. No sobrescribir SRT revisados por el usuario.