# Artefactos del motor inteligente

Git conserva únicamente esta documentación y los manifiestos pequeños de `aulaTEX/models/manifests/`.

Los pesos base se obtienen del proveedor original. Los adaptadores LoRA y modelos fusionados se guardan temporalmente en `aulaTEX/models/local/`; los checkpoints quedan en `checkpoints/`. Ambos destinos están ignorados por Git. La copia canónica debe publicarse en un bucket S3 con versionado, cifrado y acceso privado.

Un modelo no realiza peticiones por sí mismo. La inferencia requiere: modelo base + adaptador + tokenizer/configuración + código que los cargue (por ejemplo, una API o el motor AulaTeX).
