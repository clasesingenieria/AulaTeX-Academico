# Ejecucion de actividades - Plan de Negocios

**Estado de esta carpeta: los reportes activos de 6534, 6545, 6546, 6547, 6548, 6549, 6550 y 6551 quedaron normalizados sobre la plantilla canónica MGA; siete módulos del lote original siguen sin ejecución directa mediante este ejecutor.**

Se solicito ejecutar `realizar-actividad` para las 14 [planeaciones del lote original](planeaciones-generadas/2026-II/revision-2026-09-20/README.md). El primer intento del modulo 6545 recibio HTTP 401 de `Auto (model-router)`. Tras el cambio de configuracion del usuario, se verifico el motor **GPT-5.6-SOL**, deployment **gpt-5.6-sol**, con una solicitud breve exitosa. El ejecutor ya no fuerza el motor anterior: respeta la seleccion vigente y la restriccion global cuando corresponda.

El reintento completo supero sus tres etapas de `AulaTeXAgent` y materializo el TEX. Después, los reportes activos de la materia se normalizaron para trabajar sobre `ITESCA/maestria-en-gestion-administrativa/reporte-itesca-mga.tex`, usando `reporte-plan-de-negocios-plantilla-actividad.tex` solo como adaptador de metadatos y contenido. Se exportaron los siguientes borradores:

- [Word del piloto 6545](reporte-plan-de-negocios-Actividad-6-Imagen-Empresa-NexoTeX.docx): formato solicitado por la consigna; caso hipotetico por confirmar.
- [PDF de revision, cinco paginas](reporte-plan-de-negocios-Actividad-6-Imagen-Empresa-NexoTeX.pdf): no sustituye el Word solicitado.
- [Fuente TEX](reporte-plan-de-negocios-Actividad-6-Imagen-Empresa-NexoTeX.tex): conserva la salida generada con la plantilla institucional aplicada.

La autenticacion y la exportacion estan verificadas, no la aprobacion academica. Los TEX activos de esta carpeta quedaron reorganizados al patrón visible de realizar-actividad, sin diagnosticos de etapas ni metadiscurso operativo. No se inventaron resultados de campo ni se publico el documento en Moodle.

La revisión posterior eligió AM Taller Autocentro como caso de referencia documentado. Se generaron los siguientes borradores adicionales:

- La variante AM Taller del modulo 6545 compilo con XeLaTeX, pero se retiro de esta carpeta durante cambios paralelos. No se recrea; el 6545 de esta carpeta conserva NexoTeX. Consultar los reportes canonicos de la materia antes de reutilizarlo.
- [Mercadotecnia y publicidad](reporte-plan-de-negocios-Actividad-8-Mercadotecnia-Publicidad.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-8-Mercadotecnia-Publicidad.pdf). No afirma precios, stock, clientes, demanda ni catálogo vendible.
- [Área geográfica de impacto](reporte-plan-de-negocios-Actividad-7-Area-Geografica.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-7-Area-Geografica.pdf). No asigna territorio, mercado potencial ni mercado meta sin estadística y trabajo de campo.
- [Preguntas para demanda y oferta](reporte-plan-de-negocios-Actividad-5-Preguntas-Demanda-Oferta.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-5-Preguntas-Demanda-Oferta.pdf). Contiene instrumentos de recolección; no contiene respuestas, muestras ni resultados de campo.
- [Resultados de investigación de mercados](reporte-plan-de-negocios-Actividad-10-Resultados-Mercados.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-10-Resultados-Mercados.pdf). Define cómo registrar y analizar resultados reales; no contiene encuesta aplicada, porcentajes ni competidores ficticios.
- [Diagrama de flujo de proceso](reporte-plan-de-negocios-Actividad-11-Diagrama-Flujo.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-11-Diagrama-Flujo.pdf). Incluye flujo y tabla de operaciones propuestas; tiempos, equipo, insumos y puestos deben medirse o confirmarse antes de una entrega final.
- [Puestos y funciones](reporte-plan-de-negocios-Actividad-12-Recursos-Humanos.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-12-Recursos-Humanos.pdf). Propone responsabilidades vinculadas al flujo; no acredita personal, contratos, nómina ni capacidad instalada.

## Preparacion validada

- [Plantilla canónica MGA](../reporte-itesca-mga.tex): base institucional vigente de carrera para los reportes de actividad de esta materia.
- [Adaptador de actividad](reporte-plan-de-negocios-plantilla-actividad.tex): resuelve metadatos locales y entrega el contenido al contenedor canónico con contractualización visible de realizar-actividad.
- Se revisaron el [ejemplo de Actividad 6](../fundamentos-de-gestion-administrativa-mga/reporte-fundamentos-de-gestion-administrativa-Actividad-6.tex), su [formato local](../fundamentos-de-gestion-administrativa-mga/formato-itesca-actividad-6.tex) y la [base reutilizable](../fundamentos-de-gestion-administrativa-mga/reporte-fundamentos-de-gestion-administrativa-plantilla-actividad.tex). No se copiaron materia, codigo GGFG02, fechas, pesos ni contenidos de esos productos.
- La [prueba minima de plantilla](../../../.aulatex-temp/realizar-plan-negocios-2026-09-20/prueba-plantilla.pdf) compilo en dos paginas con XeLaTeX. Portada y contenido se revisaron visualmente. Se resolvio una incompatibilidad local de pies de figura cargando `caption`.
- [Caso provisional NexoTeX](caso-provisional.json): servicio hipotetico de maquetacion y capacitacion LaTeX; no representa una empresa existente ni una eleccion confirmada del estudiante.
- [Marca grafica propuesta](marca-nexotex.svg) y [version PNG](marca-nexotex.png): propuesta asistida por IA para revisar, sin registro de marca ni validacion de mercado. No es una actividad entregada.
- La exportacion del piloto se verifico con Pandoc, python-docx y XeLaTeX: DOCX integro, dos imagenes, salto de portada y estilo normal Arial; PDF de cinco paginas con texto. Se corrigio el salto de pagina usando `WD_BREAK.PAGE`. La reanudacion reutilizo el TEX sin nuevas llamadas al modelo.

## Limites del lote

Los IDs son identificadores Moodle, no una numeracion institucional inventada. Las salidas futuras deben conservar el formato de la consigna: Word para el modulo 6545 y PDF para el integrador. Los PDF adicionales serian copias de revision, no sustitutos de Word ni del enlace de video.

| Modulos | Tratamiento previsto | Estado actual |
| --- | --- | --- |
| 6530, 6552, 6553 | Guias de preparacion; sin respuestas ni intentos | No ejecutados |
| 6539 | Caracterizacion hipotetica de apoyo al capitulo; sin acceder a seis reactivos | No ejecutado |
| 6534 | Pauta personalizable; sin empleo, experiencia, expectativas ni respuestas a companeros inventados | Normalizado manualmente sobre plantilla canónica |
| 6545 | Imagen propuesta con nombre, logotipo, lema y justificacion; Word | Generado y exportado; revision editorial pendiente |
| 6546 | Mercadotecnia y publicidad para AM Taller; sin precios, stock ni demanda afirmados | Generado y exportado; revisión editorial pendiente |
| 6547 | Área geográfica y diseño de investigación; territorio y mercado meta pendientes | Generado y exportado; revisión editorial pendiente |
| 6548 | Dos instrumentos para oferta y demanda, sin respuestas ni resultados | Generado y exportado; revisión editorial pendiente |
| 6549 | Estructura de análisis; requiere resultados reales de campo | Generado y exportado; revisión editorial pendiente |
| 6550 | Flujo y tabla de operación propuestos; recursos y tiempos por confirmar | Generado y exportado; revisión editorial pendiente |
| 6551 | Borrador AM Taller con datos pendientes claramente identificados | Generado y normalizado; revisión editorial pendiente |
| 6557 | Borrador integrador con las secciones exigidas; no afirmar viabilidad validada | No ejecutado |
| 6555 | Guion y apoyos; requiere grabacion y aparicion del estudiante | No ejecutado |

No se enviaron actividades, publicaron mensajes ni iniciaron cuestionarios. Se uso el nuevo motor configurado por el usuario sin modificar credenciales ni endpoints. El 401 queda registrado como antecedente.

## Reanudar

**Actualización 22/09/2026:** los reportes fueron [renumerados por vencimiento](ORDEN-ACTIVIDADES.md). Los comandos históricos siguientes usan IDs Moodle y pueden volver a producir nombres antiguos: no ejecutarlos sobre los entregables revisados sin adaptar antes sus rutas. Para recompilar las versiones actuales usar [COMPILACION.md](COMPILACION.md). El registro de generación conserva sus IDs; sólo se actualizaron las rutas de archivos disponibles.

Desde la raiz del repositorio, comprobar la seleccion efectiva sin llamar al modelo:

```powershell
.\.venv\Scripts\python.exe .\.aulatex-temp\realizar-plan-negocios-2026-09-20\ejecutar.py --module 6545 --check
```

La comprobacion muestra motor y deployment, nunca claves. No usar la contrasena de Moodle como clave del proveedor. El comando `llm-config` de la suite esta orientado a model-router; no ejecutarlo para cambiar inadvertidamente el proveedor SOL que ahora funciona.

El piloto puede reexportarse reutilizando el contenido ya generado:

```powershell
.\.venv\Scripts\python.exe .\.aulatex-temp\realizar-plan-negocios-2026-09-20\ejecutar.py --module 6545
```

La rutina temporal usa el agente real de AulaTeX con contexto aislado y tres etapas, sin bucles de optimizacion ilimitados. Rechaza reemplazar un TEX existente que difiera del generado. Reexportar actualiza PDF y DOCX: no usar ese comando sobre ediciones manuales de Word sin preservarlas antes. Validar el piloto y el caso empresarial antes de extenderlo al resto; los pendientes personales, de campo y de video necesitan intervencion del estudiante.

Registro sin secretos: [ejecucion.json](ejecucion.json). Las trazas tecnicas quedan en `.aulatex-temp/`, excluidas de Git.