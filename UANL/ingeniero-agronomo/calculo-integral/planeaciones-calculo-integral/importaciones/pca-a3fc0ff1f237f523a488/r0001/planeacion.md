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

## Actividad source-01cad240123aabc2: consigna-Actividad-4

### Consigna importada

[document]
# Actividad 4 — Actividad ponderada 2.2

## Datos de la consigna

- **Valor:** 6 puntos.
- **Indicación original:** resolver adecuadamente y entregar en hoja de máquina.
- **Fuente original:** `Actividad-ponderada-2.2-6-puntos.docx`.
- **Tema:** ecuaciones diferenciales separables aplicadas a la ganancia de peso de becerros.

## Ejercicio 63 — Ganancia de peso

Un becerro pesa 60 libras al nacer y gana peso conforme a

$$
\frac{dw}{dt}=k(1200-w),
$$

donde $w$ es el peso en libras y $t$ el tiempo en años.

1. Resolver la ecuación diferencial.
2. Para $k=0.8$, $0.9$ y $1$, obtener y representar las tres soluciones.
3. Si el animal se vende al alcanzar 800 libras, determinar el tiempo de venta para cada modelo.
4. Determinar el peso máximo del animal en cada modelo.

## Ejercicio 64 — Ganancia de peso

Un becerro que pesa $w_0$ libras al nacer gana peso conforme a

$$
\frac{dw}{dt}=1200-w,
$$

donde $w$ es el peso en libras y $t$ el tiempo en años. Resolver la ecuación diferencial aplicando la condición inicial $w(0)=w_0$.

## Alcance obligatorio del reporte

- Incluir separación de variables, integración, despeje de $w(t)$ y aplicación de condiciones iniciales.
- Resolver todos los incisos de los ejercicios 63 y 64.
- Incluir una gráfica comparativa de los tres modelos del ejercicio 63.
- Interpretar físicamente el límite de peso y los tiempos de venta.
- Presentar cada ejercicio e inciso en cajas de actividad AulaTeX.


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
    "title": "consigna-Actividad-4.md",
    "url": null,
    "path": "planeaciones-calculo-integral/consigna-Actividad-4.md",
    "sha256": "01cad240123aabc2b1fdbecda26ed7662e2860d89abe32e4c9c56352e95988e3",
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
        "quoted_text": "[document]\n# Actividad 4 — Actividad ponderada 2.2\n\n## Datos de la consigna\n\n- **Valor:** 6 puntos.\n- **Indicación original:** resolver adecuadamente y entregar en hoja de máquina.\n- **Fuente original:** `Actividad-ponderada-2.2-6-puntos.docx`.\n- **Tema:** ecuaciones diferenciales separables aplicadas a la ganancia de peso de becerros.\n\n## Ejercicio 63 — Ganancia de peso\n\nUn becerro pesa 60 libras al nacer y gana peso conforme a\n\n$$\n\\frac{dw}{dt}=k(1200-w),\n$$\n\ndonde $w$ es el peso en libras y $t$ el tiempo en años.\n\n1. Resolver la ecuación diferencial.\n2. Para $k=0.8$, $0.9$ y $1$, obtener y representar las tres soluciones.\n3. Si el animal se vende al alcanzar 800 libras, determinar el tiempo de venta para cada modelo.\n4. Determinar el peso máximo del animal en cada modelo.\n\n## Ejercicio 64 — Ganancia de peso\n\nUn becerro que pesa $w_0$ libras al nacer gana peso conforme a\n\n$$\n\\frac{dw}{dt}=1200-w,\n$$\n\ndonde $w$ es el peso en libras y $t$ el tiempo en años. Resolver la ecuación diferencial aplicando la condición inicial $w(0)=w_0$.\n\n## Alcance obligatorio del reporte\n\n- Incluir separación de variables, integración, despeje de $w(t)$ y aplicación de condiciones iniciales.\n- Resolver todos los incisos de los ejercicios 63 y 64.\n- Incluir una gráfica comparativa de los tres modelos del ejercicio 63.\n- Interpretar físicamente el límite de peso y los tiempos de venta.\n- Presentar cada ejercicio e inciso en cajas de actividad AulaTeX.\n"
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
    "source_sha256": "01cad240123aabc2b1fdbecda26ed7662e2860d89abe32e4c9c56352e95988e3",
    "source_payload": null,
    "source_blocks": [
      {
        "locator": "document",
        "text": "# Actividad 4 — Actividad ponderada 2.2\n\n## Datos de la consigna\n\n- **Valor:** 6 puntos.\n- **Indicación original:** resolver adecuadamente y entregar en hoja de máquina.\n- **Fuente original:** `Actividad-ponderada-2.2-6-puntos.docx`.\n- **Tema:** ecuaciones diferenciales separables aplicadas a la ganancia de peso de becerros.\n\n## Ejercicio 63 — Ganancia de peso\n\nUn becerro pesa 60 libras al nacer y gana peso conforme a\n\n$$\n\\frac{dw}{dt}=k(1200-w),\n$$\n\ndonde $w$ es el peso en libras y $t$ el tiempo en años.\n\n1. Resolver la ecuación diferencial.\n2. Para $k=0.8$, $0.9$ y $1$, obtener y representar las tres soluciones.\n3. Si el animal se vende al alcanzar 800 libras, determinar el tiempo de venta para cada modelo.\n4. Determinar el peso máximo del animal en cada modelo.\n\n## Ejercicio 64 — Ganancia de peso\n\nUn becerro que pesa $w_0$ libras al nacer gana peso conforme a\n\n$$\n\\frac{dw}{dt}=1200-w,\n$$\n\ndonde $w$ es el peso en libras y $t$ el tiempo en años. Resolver la ecuación diferencial aplicando la condición inicial $w(0)=w_0$.\n\n## Alcance obligatorio del reporte\n\n- Incluir separación de variables, integración, despeje de $w(t)$ y aplicación de condiciones iniciales.\n- Resolver todos los incisos de los ejercicios 63 y 64.\n- Incluir una gráfica comparativa de los tres modelos del ejercicio 63.\n- Interpretar físicamente el límite de peso y los tiempos de venta.\n- Presentar cada ejercicio e inciso en cajas de actividad AulaTeX.\n"
      }
    ],
    "unsegmented_document": true,
    "period_pending": true,
    "activity_mapping": [
      {
        "activity_id": "source-01cad240123aabc2",
        "local_number": null,
        "source_locator": "document",
        "source_is_summary": false
      }
    ]
  }
}
```
