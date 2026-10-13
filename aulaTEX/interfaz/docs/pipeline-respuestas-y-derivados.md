# Pipeline de respuestas y derivados

## Objetivo

Separar claramente:

- Nota local (rica, completa, versionable).
- Markdown enviado a Telegram (filtrado para lectura).
- Texto visible en Telegram (resumen útil).
- Texto copiado al portapapeles (ultralimpio).
- Audio (versión hablada optimizada).

## Regla principal

La nota limpia debe entregarse inmediatamente.

No se debe esperar a:

- Explicar
- Sugerencias
- Investigar
- Dialéctica

## Pipeline

1. Entrada (texto/audio/documento).
2. Generar nota limpia.
3. Guardar nota local.
4. Enviar nota limpia a Telegram.
5. Enviar Markdown filtrado de la nota.
6. Mostrar botones.
7. Encolar derivados.
8. Generar derivados en segundo plano.
9. Actualizar enlaces locales.

## Perfiles de salida

### Local

Incluye:

- Frontmatter.
- Conceptos clave.
- Términos relacionados.
- Enlaces entre nota y derivados.
- Metadatos de versionado.

### Telegram Markdown

Incluye:

- Título.
- Contenido principal.
- Secciones útiles.

Excluye:

- Frontmatter.
- IDs.
- Metadatos.
- Procesamientos derivados.

### Portapapeles

Incluye únicamente:

- Redacción limpia.

Excluye:

- Conceptos clave.
- Términos relacionados.
- Metadatos.
- Enlaces.

### Audio

Incluye:

- Título.
- Redacción limpia.

Opcional:

- Resumen corto de conceptos.

## Cola de trabajo

Una sola cola secuencial.

Prioridad:

1. Nota limpia.
2. Play solicitado por usuario.
3. Explicar.
4. Sugerencias.
5. Investigar.
6. Dialéctica.

## Reglas de concurrencia

Si entra una nueva nota:

- Se coloca en cola.
- No interrumpe derivaciones activas.

Si el usuario pulsa Play:

- Tiene prioridad sobre derivados pendientes.

## Estado visible

Pendiente.
Procesando.
Completado.
Error.

Cada derivado debe tener estado independiente.
