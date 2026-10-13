# Grabaciones locales para Subtitle Edit

Continuacion del 12 de octubre de 2026: las tres salas volvieron a mostrar
exactamente las cinco sesiones aqui inventariadas; no se repitieron descargas
ni transcripciones. Se cotejaron los diez hashes de MP4/SRT, estructura plana,
pistas, duraciones y subtitulos, y se decodificaron los cinco MP4 completos con
FFmpeg sin errores. Evidencia en `control-grabaciones/verificacion-integridad-2026-10-12.json`
de cada materia. El inspector ahora guarda sus consultas fechadas fuera de
grabaciones y no persiste enlaces privados de reproduccion.

Cinco sesiones recuperadas de los medios que el reproductor autenticado
ofrece al usuario. No se eludieron accesos ni se guardaron cookies, tokens,
URLs de medios o chats. Son componentes locales, no una exportacion oficial
completa de la presentacion interactiva de BigBlueButton.

## Ubicacion

En cada materia:
`referencias-<materia>/grabaciones-<materia>/`.
Una sola copia por sesion; enlazar desde notas de las actividades relacionadas.

Estructura plana: sin subcarpetas. Se generaron cinco MP4 con pantalla
compartida en panel izquierdo, camara a la derecha y audio de la sesion.
Nombres: `UnADM - <identificador> - <sesion> <fecha> - <tema>.mp4`.
TEC identifica Teoria del Estado, ADH Antecedentes y DPEM Derecho Penal.
[Inventario de MP4, nombres, duraciones y hashes](grabaciones-combinadas.json).
Limpieza autorizada del 12 de octubre: WEBM y M4A auxiliares eliminados tras
verificar los cinco MP4. En grabaciones quedan solo MP4 y SRT finales.
Inventarios, procedencia e instrucciones se conservan fuera de esa carpeta,
en `notas-<materia>/materiales-generales/control-grabaciones/`.
Para recomponer con otro diseno seria necesario recuperar las fuentes del
aula; los MP4 conservan el audio y la imagen combinada, no las pistas originales
por separado. [Registro de limpieza](limpieza-grabaciones-2026-10-12.json).

En Antecedentes, el componente original de pantalla esta en blanco en los
fotogramas revisados (15 segundos y 5 minutos). El MP4 conserva esa fuente;
no incluye las diapositivas interactivas que pudieran estar separadas en
BigBlueButton. Camara visible a los 5 minutos en ambas sesiones. No se
certifica visionado integral ni sincronizacion labial mediante revision manual.

| Materia | Sesiones locales | Duracion aproximada |
| --- | --- | --- |
| Teoria del Estado | TEC S1 2026-10-02 y TEC S2 2026-10-09 | 54 y 63 minutos |
| Antecedentes | ADH Presentacion 2026-09-29 y ADH S2 2026-10-06 | 54 y 65 minutos |
| Derecho Penal | DPEM Sesion 2026-10-06; semana no explicita en aula | 75 minutos |

Cada sesion utilizo dos WEBM: camara con audio y pantalla compartida.
El M4A auxiliar se elimino; el MP4 final contiene audio AAC a 128 kbit/s.
El servidor anunciaba MIME text/html para WEBM: se validaron firma EBML,
rangos completos y pistas con FFprobe, no solo el nombre del archivo.
Procedencia y SHA256 en los JSON fechados de control-grabaciones, fuera
de la carpeta de uso diario.

## Transcripcion

Lote realizado el 12 de octubre de 2026: cinco SRT guardados con el mismo
nombre base de sus MP4, en las carpetas planas de grabaciones. Motor local
Purfview Faster Whisper XXL r245.4, modelo large-v3, Spanish, transcribe,
CUDA y preset --standard. No se tradujo al ingles ni se envio audio a un
servicio remoto. El preset segmenta subtitulos; no se acredita equivalencia
con todos los ajustes de postprocesamiento de la GUI de Subtitle Edit.

[Registro de SRT, hashes y validacion](transcripciones-grabaciones.json).
TEC S1: 890 segmentos; TEC S2: 1001; ADH presentacion: 883; ADH S2: 1697;
DPEM: 941. Se comprobaron numeracion, estructura, tiempos positivos y dentro
de la duracion del MP4. Un segmento de Penal tenia duracion nula: se amplio
100 ms sin alterar texto ni invadir el siguiente; original y cambio en
[registro de reparacion](reparaciones-tiempos-srt.json).
La primera ejecucion del motor completo emitio salida y marcador de fin,
pero devolvio codigo no cero; el SRT se recupero tras validar archivo y audio
temporal de duracion completa. No se presenta esa incidencia como exito del
codigo de salida. Las ejecuciones posteriores finalizaron y se validaron.

Todos son transcripciones automaticas pendientes de revision humana: no
certifican literalidad, nombres propios, citas ni exactitud juridica.

1. Abrir en Subtitle Edit el MP4 combinado para transcribir y revisar video/audio juntos.
2. Elegir el motor de reconocimiento e idioma espanol; revisar su politica de privacidad antes de enviar audio a un servicio externo. Preferir motor local cuando existan voces o datos de participantes.
3. Guardar el SRT con el mismo nombre base del MP4 en la misma carpeta.
4. Revisar nombres, articulos, terminos juridicos, puntuacion y tiempos contra el audio; registrar motor, fecha y estado de revision. No incluir datos personales innecesarios.
5. Usar referencias de tiempo de la sesion para notas academicas; el SRT es un auxiliar derivado, no una consigna ni prueba de que el contenido sea juridicamente correcto.

No se generaron SRT vacios ni transcripciones ficticias. La descarga no
acredita visionado o apropiacion personal. Las diapositivas y el chat pueden
ser componentes separados del reproductor y no forman parte de estas copias;
mantener el enlace del aula para verificar el contexto visual completo.
No se modificaron entregas previas ni se publicaron nuevos trabajos.