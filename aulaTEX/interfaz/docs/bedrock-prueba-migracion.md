# Migracion de Bedrock-prueba

Esta carpeta resume lo que se rescato de `upgrade/Bedrock-prueba` para que ese proyecto pueda borrarse sin romper `notas-telegram`.

## Piezas migradas

- Cliente Azure OpenAI compatible con Foundry `openai/v1`: ahora vive en `src/azure_openai_client.py`.
- Carga de `credenciales.env` con prioridad sobre variables ya existentes: ahora vive en `src/config.py`.
- Alias `AZURE_OPENAI_DEPLOYMENT_NAME`: ahora se acepta junto con `AZURE_OPENAI_CHAT_DEPLOYMENT`.
- Payload de Responses API con `instructions`, `input`, `max_output_tokens`, `reasoning` y `text`: ahora vive en `src/azure_openai_client.py`.
- Extraccion de texto desde respuestas SDK (`output_text`, `output[].content[].text`) y respuestas legacy (`choices[0].message.content`).
- Reintento automatico quitando campos opcionales si el endpoint rechaza `temperature`, `reasoning` o `text`.

## Archivos raiz relacionados

- `src/azure_openai_client.py`: cliente Azure/OpenAI reusable.
- `src/analyze.py`: convierte texto en nota limpia + conceptos usando el cliente.
- `src/config.py`: carga `.env` y luego `credenciales.env` con `override=True`.
- `credenciales.env.example`: plantilla equivalente a la configuracion funcional.
- `.gitignore`: evita versionar `.env` y `credenciales.env`.

## Configuracion recomendada

Para Foundry Project v1:

```env
AZURE_OPENAI_ENDPOINT=https://TU-RECURSO.services.ai.azure.com/api/projects/TU-PROYECTO/openai/v1/responses
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.3-codex
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_REASONING_EFFORT=high
AZURE_OPENAI_TEXT_VERBOSITY=high
```

El bot tambien acepta la variable nueva:

```env
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.3-codex
```

Si ambas existen, `AZURE_OPENAI_CHAT_DEPLOYMENT` tiene prioridad.
