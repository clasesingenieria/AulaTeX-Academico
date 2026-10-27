# Planeacion: calculo-integral

Estado: needs_review. Conversion local, no aprobacion docente ni autorizacion de envio.

## Identificacion

```json
{
  "institution": "UANL",
  "program": "ingeniero-agronomo",
  "subject_id": "calculo-integral",
  "subject_title": "calculo-integral",
  "offering_id": "oferta-f7c524166f48fd47",
  "period": null,
  "modality": null
}
```

## Actividad source-d880c652d26d4a36: consigna-Actividad-1

### Consigna importada

[document]
# Actividad 1 — Actividad ponderada: integración por partes

## Datos de la consigna

- **Valor:** 6 puntos.
- **Indicación original:** resolver adecuadamente y entregar a mano en hoja de máquina.
- **Fuente oficial:** `Actividad-ponderada-1.md`.
- **Tema:** integración por partes.

## Ejercicios

7. $\int x^{3}\ln x\,dx$, con $u=\ln x$ y $dv=x^{3}\,dx$.
8. $\int(4x+7)e^{x}\,dx$, con $u=4x+7$ y $dv=e^{x}\,dx$.
9. $\int x\operatorname{sen}(3x)\,dx$, con $u=x$ y $dv=\operatorname{sen}(3x)\,dx$.
10. $\int x\cos(4x)\,dx$, con $u=x$ y $dv=\cos(4x)\,dx$.

## Alcance obligatorio del reporte

- Resolver los cuatro ejercicios.
- Incorporar la fórmula $\int u\,dv=uv-\int v\,du$ y el procedimiento resumido.
- Mostrar $u$, $dv$, $du$, $v$, sustitución, simplificación, resultado y constante $C$.
- Verificar cada resultado mediante diferenciación.
- Presentar cada ejercicio en una caja de actividad AulaTeX.


### Requisitos


### questions

```json
[]
```

### cognitive

```json
{
  "taxonomy": null,
  "level": null,
  "verb": null,
  "object": null,
  "conditions": null,
  "observable_evidence": null,
  "justification": null
}
```

### sequence

```json
[]
```

### products

```json
[]
```

### assessment

```json
{
  "kind": null,
  "scale_total": null,
  "weight": null,
  "weight_unit": null,
  "criteria": [],
  "editorial_checks": []
}
```

### calendar

```json
{
  "opens_at": null,
  "expected_at": null,
  "due_at": null,
  "closes_at": null,
  "timezone": null,
  "literal": null
}
```

### policies

```json
{
  "ai": null,
  "integrity": null,
  "collaboration": null,
  "citation": null,
  "attempts": null,
  "late_submission": null,
  "accessibility": null,
  "privacy": null,
  "exceptions": []
}
```

### resources

```json
[]
```

## sources

```json
[
  {
    "id": "src-local",
    "kind": "other",
    "authority": "unknown",
    "title": "consigna-Actividad-1.md",
    "url": null,
    "path": "planeaciones-calculo-integral/consigna-Actividad-1.md",
    "sha256": "d880c652d26d4a369521b00067af13fd86609fda589f01bf9ada63698de8c037",
    "captured_at": null,
    "media_type": "text/plain"
  }
]
```

## field_status

```json
[
  {
    "path": "/identity",
    "state": "inferred",
    "reason": "Identidad editorial del catalogo; oferta interna, periodo y modalidad no acreditados cuando faltan.",
    "evidence": [],
    "alternatives": []
  },
  {
    "path": "/sources",
    "state": "confirmed",
    "reason": "Archivo local preservado; su huella no acredita autoria ni vigencia docente.",
    "evidence": [
      {
        "source_id": "src-local",
        "locator": "local-file",
        "quoted_text": null
      }
    ],
    "alternatives": []
  },
  {
    "path": "/curriculum",
    "state": "unknown",
    "reason": "No se deducen competencias, resultados ni temario que no esten documentados.",
    "evidence": [],
    "alternatives": []
  },
  {
    "path": "/activities/0",
    "state": "unknown",
    "reason": "Campos sin datos no se completan por inferencia; la consigna puede estar resumida o sin segmentar.",
    "evidence": [],
    "alternatives": []
  },
  {
    "path": "/activities/0/role",
    "state": "inferred",
    "reason": "Clasificacion operativa provisional a partir del tipo original; no impone obligatoriedad.",
    "evidence": [],
    "alternatives": []
  },
  {
    "path": "/activities/0/instruction",
    "state": "inferred",
    "reason": "Texto completo importado o requisitos del modelo local; pendiente cotejo con consigna docente.",
    "evidence": [
      {
        "source_id": "src-local",
        "locator": "document",
        "quoted_text": "[document]\n# Actividad 1 — Actividad ponderada: integración por partes\n\n## Datos de la consigna\n\n- **Valor:** 6 puntos.\n- **Indicación original:** resolver adecuadamente y entregar a mano en hoja de máquina.\n- **Fuente oficial:** `Actividad-ponderada-1.md`.\n- **Tema:** integración por partes.\n\n## Ejercicios\n\n7. $\\int x^{3}\\ln x\\,dx$, con $u=\\ln x$ y $dv=x^{3}\\,dx$.\n8. $\\int(4x+7)e^{x}\\,dx$, con $u=4x+7$ y $dv=e^{x}\\,dx$.\n9. $\\int x\\operatorname{sen}(3x)\\,dx$, con $u=x$ y $dv=\\operatorname{sen}(3x)\\,dx$.\n10. $\\int x\\cos(4x)\\,dx$, con $u=x$ y $dv=\\cos(4x)\\,dx$.\n\n## Alcance obligatorio del reporte\n\n- Resolver los cuatro ejercicios.\n- Incorporar la fórmula $\\int u\\,dv=uv-\\int v\\,du$ y el procedimiento resumido.\n- Mostrar $u$, $dv$, $du$, $v$, sustitución, simplificación, resultado y constante $C$.\n- Verificar cada resultado mediante diferenciación.\n- Presentar cada ejercicio en una caja de actividad AulaTeX.\n"
      }
    ],
    "alternatives": []
  }
]
```

## review

```json
{
  "state": "needs_review",
  "reviewed_at": null,
  "reviewer_role": null,
  "critical_gaps": [
    "Cotejar consigna y procedencia docente; conversion local no equivale a aprobacion",
    "Documento sin segmentar: identificar actividades, requisitos, preguntas y rubrica antes de ejecutar"
  ],
  "semantic_validation": "failed"
}
```

## extensions

```json
{
  "conversion": {
    "version": "1.0",
    "source_format": ".md",
    "source_sha256": "d880c652d26d4a369521b00067af13fd86609fda589f01bf9ada63698de8c037",
    "source_payload": null,
    "source_blocks": [
      {
        "locator": "document",
        "text": "# Actividad 1 — Actividad ponderada: integración por partes\n\n## Datos de la consigna\n\n- **Valor:** 6 puntos.\n- **Indicación original:** resolver adecuadamente y entregar a mano en hoja de máquina.\n- **Fuente oficial:** `Actividad-ponderada-1.md`.\n- **Tema:** integración por partes.\n\n## Ejercicios\n\n7. $\\int x^{3}\\ln x\\,dx$, con $u=\\ln x$ y $dv=x^{3}\\,dx$.\n8. $\\int(4x+7)e^{x}\\,dx$, con $u=4x+7$ y $dv=e^{x}\\,dx$.\n9. $\\int x\\operatorname{sen}(3x)\\,dx$, con $u=x$ y $dv=\\operatorname{sen}(3x)\\,dx$.\n10. $\\int x\\cos(4x)\\,dx$, con $u=x$ y $dv=\\cos(4x)\\,dx$.\n\n## Alcance obligatorio del reporte\n\n- Resolver los cuatro ejercicios.\n- Incorporar la fórmula $\\int u\\,dv=uv-\\int v\\,du$ y el procedimiento resumido.\n- Mostrar $u$, $dv$, $du$, $v$, sustitución, simplificación, resultado y constante $C$.\n- Verificar cada resultado mediante diferenciación.\n- Presentar cada ejercicio en una caja de actividad AulaTeX.\n"
      }
    ],
    "unsegmented_document": true,
    "period_pending": true,
    "activity_mapping": [
      {
        "activity_id": "source-d880c652d26d4a36",
        "local_number": null,
        "source_locator": "document",
        "source_is_summary": false
      }
    ]
  }
}
```
