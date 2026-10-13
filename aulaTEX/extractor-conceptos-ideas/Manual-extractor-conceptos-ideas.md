# Especificación funcional del motor de extracción de conceptos e ideas

## 1. Propósito del documento

Este documento describe la estructura funcional, la lógica conceptual y el plan de adaptación de un motor de extracción de conceptos e ideas a partir de planeaciones académicas. Su finalidad es definir una base técnica y editorial suficientemente clara para reutilizar el flujo ya implementado en `D:\Documentos\proyecto_2_fichador_azure` y adaptarlo al contexto de `Template-Informe`.

## 2. Alcance general

Se han de obtener los conceptos necesarios para realizar las actividades de cada una de las planeaciones, así como las ideas que se puedan derivar de ellas. La lógica del sistema debe partir de una entrada concreta y controlable, no de una búsqueda abierta. En este proyecto, la entrada del motor se compone de tres elementos:

1. La \textbf{planeación} de la semana o actividad.
2. La \textbf{carpeta de libros o fuentes base de la materia}.
3. La \textbf{carpeta de salida} donde se colocarán las fichas de conceptos e ideas.

A partir de esa entrada, el proceso general debe seguir estos pasos:

1. Leer la planeación y extraer de ella el contenido temático, el objetivo, la técnica didáctica, la bibliografía y la consigna operativa.
2. Revisar la carpeta de libros de la materia y localizar en esos materiales los conceptos y las ideas que respondan directamente a lo solicitado por la planeación.
3. Organizar los conceptos e ideas obtenidos en una estructura lógica y coherente, que permita su fácil comprensión y aplicación en las actividades propuestas.
4. Validar los conceptos e ideas obtenidos para asegurar su precisión y relevancia en el contexto de las planeaciones.
5. Documentar los conceptos e ideas de manera clara y concisa dentro de la carpeta de salida, para facilitar su consulta y uso en la elaboración de actividades y en la retroalimentación editorial.

## 3. Definición general del motor de extracción

El motor de extracción de conceptos e ideas debe entenderse como un flujo de trabajo documental y semántico. Su función no es resumir libros completos, sino detectar qué conceptos y qué ideas sirven específicamente para resolver una planeación concreta.

### 3.1 Entradas del motor

### 1. Planeación
Documento fuente que define:
- contenido temático;
- objetivo específico;
- técnica didáctica;
- bibliografía sugerida;
- actividad solicitada;
- criterios de entrega.

### 2. Carpeta de libros de la materia
Conjunto de materiales base desde donde se extraerán conceptos e ideas. Esta carpeta puede incluir:
- libros en PDF;
- apuntes;
- textos convertidos a `.txt` o `.md`;
- documentos normativos o institucionales asociados a la materia.

### 3. Carpeta de salida de fichas
Directorio donde el motor colocará las fichas resultantes. La salida no debe ser texto suelto, sino fichas reutilizables por tema, semana, actividad o concepto.

### 3.2 Funcionamiento esperado

El motor puede ser implementado con técnicas de procesamiento de lenguaje natural (PLN) y, si conviene, con apoyo limitado de aprendizaje automático. Sin embargo, el núcleo del sistema debe ser controlable y trazable. Primero debe analizar la planeación para detectar qué pide realmente; después debe recorrer la carpeta de libros para localizar definiciones, ideas explicativas, relaciones conceptuales, ejemplos útiles y citas relevantes.

El motor puede apoyarse en:
- extracción de palabras clave;
- reconocimiento de entidades y conceptos recurrentes;
- extracción de relaciones entre conceptos;
- detección de oraciones definicionales, comparativas, causales y conclusivas;
- clasificación por utilidad de redacción: introducción, desarrollo, conclusión, ejemplo o fundamento normativo.

## 4. Organización y salida de conceptos e ideas

Los conceptos e ideas obtenidos deben organizarse en una estructura lógica y coherente. La unidad mínima de salida debe ser una \textbf{ficha temática}. Cada ficha debería contener, como mínimo:

- nombre del concepto o idea;
- definición operativa o idea central;
- explicación breve en lenguaje claro;
- cita con fuente y punto de origen;
- utilidad dentro de la actividad;
- relación con otros conceptos;
- observaciones o límites de uso.

También se pueden organizar en mapas conceptuales o esquemas de relaciones, pero la salida principal debe seguir siendo documental y reutilizable. Cada concepto o idea debe incluir cita indicando la fuente y el punto exacto de donde se obtuvo, para facilitar su validación y referencia en la elaboración de las actividades y la retroalimentación editorial.

## 5. Esquema funcional derivado de `proyecto_2_fichador_azure`

A partir del proyecto funcional ubicado en `D:\Documentos\proyecto_2_fichador_azure`, el motor puede entenderse como una cadena de módulos especializados. No parte de una sola rutina monolítica, sino de un flujo por etapas donde cada bloque cumple una función bien delimitada.

## 1. Capa de entrada

### Entrada 1: planeación
Se carga como archivo de texto, PDF o DOCX mediante el lector documental. En el proyecto funcional, esta responsabilidad está cubierta por `document_reader.py`, especialmente a través de `read_any_text_file()`.

### Entrada 2: carpeta de libros o fuentes base de la materia
Se recorre como conjunto de fuentes heterogéneas. En el proyecto funcional, `discover_source_files()` y `extract_pages_from_sources()` resuelven esta parte. Aquí se detectan archivos `pdf`, `docx`, `txt`, `md` y `markdown`, además de permitir exploración recursiva.

### Entrada 3: carpeta de salida de fichas
Se usa como destino de exportación documental. En el proyecto funcional esta salida es atendida por `exporters.py`, que genera formatos `md`, `xlsx`, `csv`, `json` y `docx`.

## 2. Capa de lectura documental

Esta capa convierte documentos heterogéneos en texto estructurado. En el proyecto funcional se divide así:

- `pdf_reader.py`: extracción de páginas o bloques desde PDF.
- `document_reader.py`: lectura unificada de PDF, DOCX, TXT y MD.
- `extract_docx_blocks()` y `extract_plain_text_blocks()`: normalización por bloques citables.

Su salida no es todavía una ficha, sino un corpus con metadatos:
- fuente;
- tipo de archivo;
- página o bloque;
- ruta;
- texto bruto.

## 3. Capa de preprocesamiento

Una vez leído el corpus, el texto se limpia y se divide en fragmentos utilizables. En el proyecto funcional esto se resuelve con `preprocessing.py` y la llamada central `build_fragments()` desde `cli.py`.

Aquí ocurre lo siguiente:
- normalización de espacios;
- limpieza de ruido de marcado;
- división en fragmentos citables;
- control de tamaño mínimo y máximo;
- deduplicación parcial de conceptos o líneas repetidas.

Esta etapa es decisiva porque el motor no debe trabajar con libros completos como una sola masa textual, sino con fragmentos que puedan citarse y reutilizarse.

## 4. Capa de interpretación de la planeación

La planeación no se usa solo como referencia temática; se usa como guía de búsqueda. En el proyecto funcional esto aparece en `cli.py` mediante `_load_concepts()` y `extract_candidate_concepts_from_text()`.

La lógica es:
1. leer la planeación;
2. dividirla en bloques significativos;
3. extraer candidatos conceptuales;
4. combinarlos con un archivo opcional de conceptos semilla;
5. normalizar y depurar la lista final de búsqueda.

En términos funcionales, esta capa traduce la consigna académica a una lista operativa de conceptos rastreables.

## 5. Capa de extracción de conceptos

En el proyecto funcional la extracción conceptual se concentra en `concept_extractor.py`. Ahí se observa un enfoque híbrido y controlable:

- limpieza léxica;
- tokenización y n-gramas;
- `TF-IDF` sobre bloques de texto;
- listas de conceptos genéricos a excluir;
- filtros de utilidad conceptual;
- eliminación de redundancias;
- ranking por relevancia.

Este bloque no devuelve aún ideas completas, sino candidatos conceptuales ordenados por utilidad. Es el primer filtro semántico serio del sistema.

## 6. Capa de búsqueda semántica o léxica

Una vez definidos los conceptos, el sistema busca citas y fragmentos asociados. En el proyecto funcional esta capa se distribuye en varios motores:

- `search.py`: motor local `TF-IDF`.
- `tfhub_search.py`: embeddings locales con sentence-transformers.
- `api_search.py`: embeddings remotos con Azure u OpenAI.
- `api_client.py`: configuración del proveedor.

La decisión del motor se resuelve en `cli.py` mediante `_build_engine()` y `_build_engine_with_fallback()`.

Esto permite una arquitectura escalable:
- modo local y reproducible;
- modo semántico con embeddings;
- fallback automático a `tfidf` cuando falla un proveedor remoto.

## 7. Capa de construcción de fichas

La búsqueda devuelve citas o hits; todavía falta convertirlos en fichas comprensibles. En el proyecto funcional esto se atiende con `fichas.py` y su llamada desde `cli.py` mediante `build_fichas()`.

Aquí el sistema agrupa por concepto:
- fuentes relacionadas;
- ubicaciones;
- mejor similitud;
- similitud promedio;
- observación automática.

En otras palabras, esta capa convierte resultados de búsqueda en una unidad documental reutilizable.

## 8. Capa de exportación

El bloque final lo resuelve `exporters.py`. La lógica de salida ya está claramente definida:
- Markdown para lectura rápida;
- Excel para revisión tabular;
- CSV para procesamiento posterior;
- JSON para integraciones automáticas;
- Word para revisión o entrega más formal.

Esto es importante porque la ficha no debe depender de una sola interfaz. Debe poder usarse como insumo editorial, académico o técnico.

## 6. Maquetación conceptual del motor

La maquetación conceptual describe cómo se relacionan las piezas del sistema, no solo qué archivos existen.

```text
Planeación
  └─ define: tema, objetivo, técnica, bibliografía, actividad
        ↓
Interpretador de planeación
  └─ extrae conceptos semilla y criterios de búsqueda
        ↓
Carpeta de libros / fuentes de la materia
  └─ lector documental unificado
        ↓
Corpus estructurado por fuente, página o bloque
        ↓
Preprocesamiento
  └─ limpieza, fragmentación, normalización
        ↓
Extractor de conceptos
  └─ ranking, filtrado, deduplicación
        ↓
Motor de búsqueda
  ├─ tfidf local
  ├─ tfhub local
  ├─ azure embeddings
  └─ openai embeddings
        ↓
Agrupador de resultados
  └─ construye fichas por concepto
        ↓
Carpeta de salida
  ├─ fichas_conceptos.md
  ├─ fichas_conceptos.xlsx
  ├─ fichas_conceptos.csv
  ├─ fichas_conceptos.json
  └─ fichas_conceptos.docx
```

## 7. Lectura funcional del proyecto de referencia

Tomando el proyecto funcional como referencia, el motor puede resumirse así:

- `run.py`: punto de entrada.
- `cli.py`: orquestador general del flujo.
- `document_reader.py`: entrada documental.
- `preprocessing.py`: normalización y fragmentación.
- `concept_extractor.py`: extracción de conceptos.
- `search.py`, `tfhub_search.py`, `api_search.py`: recuperación de citas e ideas por concepto.
- `fichas.py`: agrupación conceptual.
- `exporters.py`: salida documental.

## 8. Adaptación al uso editorial de este repositorio

Si este motor se adapta al flujo de `Template-Informe`, la lectura correcta sería:

- la \textbf{planeación} determina qué conceptos hay que buscar;
- la \textbf{carpeta de libros} contiene el universo válido de extracción;
- la \textbf{carpeta de salida} concentra fichas reutilizables para redactar actividades, apoyar retroalimentación y construir mapas conceptuales o esquemas.

La ventaja del modelo ya implementado en `proyecto_2_fichador_azure` es que no trabaja con resúmenes inventados. Trabaja con fragmentos citables, motores intercambiables y salidas estructuradas. Eso lo vuelve una base adecuada para construir un motor editorial de extracción de conceptos e ideas dentro de este proyecto.

## 9. Estructura propuesta para la adaptación en `Template-Informe`

La adaptación del motor requiere una estructura de carpetas clara, estable y reutilizable. Como punto de partida, ya se preparó una carpeta específica dentro de `aulaTEX/`:

- `aulaTEX/extractor-conceptos-ideas/`

Esa carpeta funcionará como contenedor local del proyecto adaptado, es decir, como el lugar donde residirá el código del motor, su configuración de ejecución y sus utilidades internas.

Se propone la siguiente organización general:

```text
Template-Informe/
├─ planeaciones/
│  └─ <materia>/
│     ├─ semana-01.pdf
│     ├─ semana-01.txt
│     └─ ...
├─ fuentes/
│  └─ <materia>/
│     ├─ libros/
│     ├─ normas/
│     ├─ apuntes/
│     └─ textos-procesados/
├─ salidas/
│  └─ fichas/
│     └─ <materia>/
│        ├─ semana-01/
│        │  ├─ fichas_conceptos.md
│        │  ├─ fichas_conceptos.xlsx
│        │  ├─ fichas_conceptos.json
│        │  └─ resumen_planeacion.json
│        └─ ...
└─ aulaTEX/
   └─ extractor-conceptos-ideas/
      ├─ README.md
      ├─ src/
      ├─ config/
      ├─ runners/
      └─ output/
```

Esta estructura separa con claridad:
- la entrada académica (`planeaciones/`);
- el universo documental (`fuentes/`);
- las salidas reutilizables (`salidas/fichas/`);
- la lógica de automatización (`aulaTEX/extractor-conceptos-ideas/`).

### 9.1 Uso previsto dentro del repositorio de edición

La carpeta `aulaTEX/extractor-conceptos-ideas/` no se plantea como un lugar de almacenamiento pasivo, sino como un subsistema operativo dentro de `Template-Informe`.

Su uso esperado es el siguiente:

1. Seleccionar una planeación específica de una materia y semana.
2. Apuntar a la carpeta de libros o fuentes de esa misma materia.
3. Ejecutar el motor adaptado desde `aulaTEX/extractor-conceptos-ideas/`.
4. Generar fichas de conceptos e ideas con trazabilidad documental.
5. Publicar la salida útil en `salidas/fichas/<materia>/<semana>/`.
6. Reutilizar esas fichas como apoyo para:
   - redacción de actividades;
   - construcción de esquemas o mapas conceptuales;
   - preparación de retroalimentación editorial;
   - consolidación de notas de apoyo por materia.

La lógica editorial correcta es que `aulaTEX/extractor-conceptos-ideas/` contenga el motor, pero que la salida estable se consuma fuera de esa carpeta, en rutas reutilizables por materia y semana.
## 10. Convención de nombres

Para evitar ambigüedad, conviene fijar una convención simple y persistente.

### 10.1 Planeaciones
- `semana-01.pdf`
- `semana-01.txt`
- `semana-08.txt`

### 10.2 Fichas
- `fichas_conceptos.md`
- `fichas_conceptos.xlsx`
- `fichas_conceptos.csv`
- `fichas_conceptos.json`
- `fichas_conceptos.docx`

### 10.3 Archivos auxiliares
- `resumen_planeacion.json`
- `conceptos_detectados.json`
- `ideas_detectadas.json`
- `trazabilidad_fuentes.json`

### 10.4 Identificadores recomendados
- materia: `etica-y-moral-juridica`
- semana: `semana-08`
- concepto: `libertad-personal`
- ficha individual: `ficha-libertad-personal.json`

La regla debe ser: nombres en minúsculas, con guiones medios y sin espacios.

## 11. Formato mínimo de las salidas

### 11.1 Resumen estructurado de planeación

```json
{
  "materia": "etica-y-moral-juridica",
  "semana": 8,
  "contenido_tematico": "Principales leyes que resguardan los derechos en México",
  "objetivo": "...",
  "tecnica": "analisis de hechos",
  "bibliografia": ["Ronquillo", "Singer"],
  "actividad": ["registrar hecho", "identificar derechos", "localizar ley secundaria"]
}
```

### 11.2 Ficha de concepto o idea

```json
{
  "concepto": "libertad personal",
  "tipo": "concepto",
  "definicion_operativa": "Condición jurídica que protege a la persona frente a privaciones arbitrarias de libertad.",
  "fuente": "constitucionCPEUM2026",
  "ubicacion": "art. 14 y 16",
  "cita_textual": "...",
  "utilidad_en_actividad": "Sirve para justificar por qué una detención ilegal vulnera derechos humanos.",
  "relaciones": ["debido proceso", "seguridad jurídica"],
  "observaciones": "Usar junto con acceso a la justicia y dignidad humana."
}
```

### 11.3 Ficha de idea redactable

```json
{
  "idea": "Una ley secundaria vuelve operativa la protección constitucional.",
  "tipo": "idea",
  "funcion": "desarrollo",
  "fuente": "lgv2026",
  "cita_textual": "...",
  "utilidad_en_actividad": "Permite conectar norma constitucional con mecanismo concreto de protección."
}
```

## 12. Plan de adaptación por fases

### Fase 1. Adaptación documental mínima
Objetivo: reutilizar el motor actual sin cambiar su arquitectura principal.

Tareas:
- definir rutas de entrada y salida para `Template-Informe`;
- normalizar nombres de planeaciones y fuentes;
- generar extracción textual previa de PDFs cuando sea necesario;
- producir fichas por semana y por materia.

Resultado esperado:
- un flujo funcional que tome una planeación, una carpeta de libros y produzca fichas documentales reutilizables.

### Fase 2. Adaptación semántica orientada a actividades
Objetivo: no extraer solo conceptos frecuentes, sino conceptos útiles para la consigna.

Tareas:
- reforzar el parser de planeación;
- clasificar conceptos por utilidad de redacción;
- separar conceptos, ideas, normas y ejemplos;
- priorizar resultados según técnica didáctica.

Resultado esperado:
- fichas más útiles para redactar actividades reales y menos ruido conceptual.

### Fase 3. Integración editorial
Objetivo: convertir las fichas en insumos directos de trabajo para este repositorio.

Tareas:
- conectar fichas con plantillas LaTeX;
- generar apoyos de redacción en `.md`;
- enlazar conceptos con bibliografía `.bib` local;
- permitir revisión y corrección manual de fichas.

Resultado esperado:
- un flujo mixto donde la automatización apoya la escritura, pero no reemplaza el criterio editorial.

### Fase 4. Validación y madurez operativa
Objetivo: asegurar consistencia, trazabilidad y reutilización real.

Tareas:
- validar una muestra de fichas por materia;
- depurar conceptos genéricos o poco útiles;
- medir precisión de citas y relaciones;
- documentar límites y casos problemáticos.

Resultado esperado:
- motor estable, reutilizable y alineado con las necesidades académicas y editoriales del proyecto.

## 13. Criterios de calidad del motor adaptado

El motor debería considerarse funcionalmente sólido cuando cumpla con lo siguiente:

- cada ficha pueda rastrearse a una fuente concreta;
- la planeación determine la búsqueda y no sólo el corpus;
- los conceptos genéricos se filtren de forma razonable;
- las ideas extraídas sean útiles para redactar, no sólo para listar;
- las salidas puedan reutilizarse en actividades, notas editoriales y retroalimentación;
- el sistema permita revisión manual sin romper la automatización.

## 14. Cierre operativo

La adaptación del motor de `proyecto_2_fichador_azure` a `Template-Informe` no requiere reinventar el flujo técnico, sino reorganizarlo con criterio editorial. El proyecto funcional ya resuelve lectura documental, preprocesamiento, extracción conceptual, búsqueda y exportación. Lo que este repositorio necesita es una capa adicional de estructura, convención y propósito académico para que la salida no sea solo una colección de coincidencias, sino una base útil para redactar, analizar y retroalimentar actividades de manera consistente.

En términos operativos, el punto de alojamiento del motor dentro de este repositorio queda definido así:

- `aulaTEX/extractor-conceptos-ideas/` para código, configuración y ejecución;
- `planeaciones/` como entrada académica primaria;
- `fuentes/` como universo documental por materia;
- `salidas/fichas/` como destino reutilizable de las fichas procesadas.

Con ello, el repositorio editorial no sólo documenta la idea del motor, sino también su lugar de implementación y su forma prevista de uso dentro del flujo real de trabajo.