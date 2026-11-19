# Informe Consolidado de Estatus y Evaluación · PFM01 Fundamentos para la Enseñanza y el Aprendizaje I (SD26)

- **Curso Moodle:** [PFM01 Fundamentos para la enseñanza y el aprendizaje. (Ago-Nov 2026 Grupo A)](https://evaposgrados.iiiepe.edu.mx/aula/course/view.php?id=1048) (`course_id=1048`)
- **Institución / Programa:** IIIEPE · Maestría en Aprendizaje y Enseñanza de las Matemáticas (`MAEM`)
- **Periodo Académico:** 2do periodo, septiembre--diciembre de 2026 (`SD26`)
- **Estudiante:** Mtro. Martín Jonathan de la Cruz Muñoz (Matrícula: `00874` · `martin.delacruz@campus.iiiepe.edu.mx`)
- **Docente Titular Registrado:** Mtro. Oscar Zertuche Santos
- **Formato Canónico:** **100 % LaTeX $\to$ PDF** (`cli.py latexmk`, sin ningún archivo `.docx` generado; únicamente se conserva la presentación `.pptx` editable solicitada en la consigna oficial `50173` del Trabajo Final).
- **Política de Entrega (`Fail-Closed`):** **Todos los entregables permanecen retenidos y sellados localmente** para tu revisión humana antes de cualquier carga en Moodle. **No se realizó ningún envío automático a plataforma.**

---

## 1. Resumen Ejecutivo de Realización Integral

| Dimensión Verificada | Resultado Final | Respaldo y Evidencia |
| :--- | :--- | :--- |
| Actividades oficiales con buzón en Moodle (`1048`) | **8 / 8 (100 %)** | `cli.py monitor-iiiepe --period SD26`: `8/8` en `entregable_generado` |
| Actividades complementarias (Sesiones sin buzón, 2.ª infografía y programa) | **6 / 6 (100 %)** | `actividad-09` a `actividad-14` completas con PCA v1.0 + PDF + Beamer |
| Planeaciones canónicas PCA v1.0.0 | **14 / 14 válidas** (`schema_valid=True`, `suma_pts=100.0`) | [planeaciones-...-SD26](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/planeaciones-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/) |
| Compilación LaTeX (`cli.py latexmk`) | **37 / 37 (`rc=0`)** (14 reportes + 14 Beamer + 9 PDFs independientes) | Cero citas sin resolver (`?? = False` en todos los PDFs) |
| Auditoría Editorial y Estilo (`cli.py audit`) | **20 / 20 reportes completos con EMS = 100.0/100 (`MAESTRO`)** | **20 / 20 con Fidelidad de Estilo = 100.0/100 (`VÁLIDO [OK]`)** y `0` violaciones |
| Auditoría Bibliográfica (`cli.py bibcheck`) | **20 / 20 con `0` claves faltantes** | Validación cruzada con [referencias-sd26.bib](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/referencias-sd26.bib) |
| Rediseño visual de Infografías en LaTeX/TikZ | **3 láminas editoriales completas** (Meirieu, Sawyer y 3 Autores) | Retratos circulares, píldoras con medallones vectoriales, 12 mini-tarjetas de íconos por lámina y checks de práctica |
| Limpieza de archivos `.docx` generados | **0 archivos `.docx` generados restantes** | Validación automatizada `leftover_docx = []` |
| Paquete de entregas sincronizado | **29 archivos principales + 9 PDFs en `subproductos-independientes/`** | [CHECKLIST_PRE_ENTREGA.md](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/entregas-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/CHECKLIST_PRE_ENTREGA.md) |

---

## 2. Bloque A · Las 8 Actividades Oficiales con Buzón en Moodle (Curso `1048`)

| Act | Módulo | Actividad y Contenido Desarrollado | Plan PCA | Reporte PDF | Presentación / Subproductos PDF | `audit` (EMS / Estilo) | `bibcheck` | Estatus |
| :-: | :-: | :--- | :-: | :-: | :--- | :-: | :-: | :--- |
| **1** | [`50157`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=50157) | **Recursos sesión 1:** 4 ideas ampliadas y comentarios críticos de Scott (2015) + matriz didáctica + diagnóstico de 4 conceptos en TikZ | `PCA 1.0` | **9 p.** (`195.2 KB`) | Beamer **11 p.** (`163.7 KB`) + Subproductos `01A`, `01B` | `100.0` / `100.0` | `8/8` ok | Completa |
| **2** | [`50158`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=50158) | **¿Cómo soy como maestro?:** 5 preguntas + silueta docente TikZ situada + matriz formativa y bibliografía justificada | `PCA 1.0` | **10 p.** (`150.1 KB`) | Beamer **11 p.** (`131.4 KB`) | `100.0` / `100.0` | `14/14` ok | Completa |
| **3** | [`51440`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51440) | **Infografía Sesión 3 (Meirieu 2020 + 3 Autores):** 2 láminas visuales apaisadas en LaTeX/TikZ (Meirieu monográfico + comparativo Meirieu–Sawyer–Martínez Rizo) con retratos, 12 tarjetas c/u y transferencia matemática | `PCA 1.0` | **8 p.** (`1,009.8 KB`) | Beamer **6 p.** (`979.4 KB`) + Pósteres `03A`, `03B` | `100.0` / `100.0` | `9/9` ok | Completa |
| **4** | [`51676`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51676) | **Investigación-acción educativa:** 5 preguntas (Restrepo Gómez, 2004) + espiral TikZ y 5 fases aplicadas a variación lineal | `PCA 1.0` | **8 p.** (`185.4 KB`) | Beamer **11 p.** (`145.6 KB`) | `100.0` / `100.0` | `10/10` ok | Completa |
| **5** | [`51707`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51707) | **El aprendizaje profundo:** 5 preguntas (Quiroga y Lara, 2022) + algoritmo vs comprensión + triada cognitiva--interpersonal--intrapersonal | `PCA 1.0` | **8 p.** (`186.4 KB`) | Beamer **11 p.** (`192.5 KB`) | `100.0` / `100.0` | `10/10` ok | Completa |
| **6** | [`51809`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51809) | **Tercer momento Bloque III:** Primer momento (síntesis), Segundo momento (diagnóstico 6 aspectos) y Tercer momento (propuesta *por realizar* en 7 elementos) | `PCA 1.0` | **9 p.** (`222.1 KB`) | Beamer **12 p.** (`156.2 KB`) + Subproductos `06A`, `06B`, `06C` | `100.0` / `100.0` | `13/13` ok | Completa |
| **7** | [`51813`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51813) | **Modelo Bioecológico:** 6 preguntas (Bronfenbrenner y Morris, 2006) + procesos proximales + diagrama concéntrico y matriz de 5 sistemas | `PCA 1.0` | **8 p.** (`141.9 KB`) | Beamer **11 p.** (`136.4 KB`) | `100.0` / `100.0` | `9/9` ok | Completa |
| **8** | [`50172`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=50172) | **Trabajo final integrador:** Proyecto *por realizar* «Calibrar para decidir» (10 apartados `50173`, STEAM NEM, Bronfenbrenner) + Autoevaluación 20 ítems (`50175`) | `PCA 1.0` | **12 p.** (`236.9 KB`) | Beamer **15 p.** (`200.8 KB`) + **`.pptx` (`313.6 KB`)** + Subp. `08A` | `100.0` / `100.0` | `16/16` ok | Completa |

---

## 3. Bloque B · Las 6 Actividades Complementarias (100 % LaTeX $\to$ PDF)

| Act | Referencia Curricular | Actividad y Contenido Desarrollado | Plan PCA | Reporte PDF | Presentación / Subproducto | `audit` (EMS / Estilo) | `bibcheck` | Estatus |
| :-: | :--- | :--- | :-: | :-: | :--- | :-: | :-: | :--- |
| **9** | Sesión 3b (`51440` / `51436`) | **Infografía Monográfica · R. Keith Sawyer (2008):** Lámina editorial de 3 columnas en LaTeX/TikZ (instruccionismo vs economía creativa, hallazgos cognitivos y andamiaje, rediseño escolar y TIMSS) con retratos, 12 tarjetas de íconos y análisis | `PCA 1.0` | **8 p.** (`546.6 KB`) | Beamer **9 p.** (`562.5 KB`) + Póster `09A` | `100.0` / `100.0` | `7/7` ok | Completa |
| **10** | Bloque I · Tema 4 (`47634`) | **Tipos de aprendizaje en el siglo XXI:** Análisis de *El futuro del aprendizaje 2* (Scott, 2015b) + diagrama de 4 pilares (Delors) y caso energético | `PCA 1.0` | **6 p.** (`156.3 KB`) | Beamer **5 p.** (`125.5 KB`) | `100.0` / `100.0` | `9/9` ok | Completa |
| **11** | Sesión 4 en Moodle `1048` (`47637`) | **Siete habilidades básicas (Tony Wagner):** Mapa mental radial en TikZ + estrategias fundamentadas para la clase de Matemáticas + caso térmico $T(t)=20+3t$ | `PCA 1.0` | **7 p.** (`167.1 KB`) | Beamer **5 p.** (`201.7 KB`) | `100.0` / `100.0` | `6/6` ok | Completa |
| **12** | Sesión 5 (`47636` + Programa) | **Escuela tradicional vs. NEM, Infografía Comparada y Tres Reportes:** Cuadro de 8 dimensiones + lámina editorial de 3 columnas (`Meirieu | Sawyer | Martínez Rizo`) + 3 reportes independientes y contraste algebraico | `PCA 1.0` | **9 p.** (`839.6 KB`) | Beamer **6 p.** (`803.0 KB`) | `100.0` / `100.0` | `7/7` ok | Completa |
| **13** | Bloque II (`47639` / `49058`) | **Cuadro de 4 entradas · Metodologías sociocríticas NEM:** Comparativo de ABPC, STEAM, ABP y Aprendizaje Servicio (fases, cómo se trabaja, palabras clave, roles y árbol TikZ) | `PCA 1.0` | **7 p.** (`140.5 KB`) | Beamer **5 p.** (`125.4 KB`) | `100.0` / `100.0` | `6/6` ok | Completa |
| **14** | Sesión 7b (`51784`) | **Análisis de «50 innovaciones educativas para escuelas» (Rivas et al., 2017):** 6 criterios CIPPEC + adaptación de casos 4, 7, 29, 39 y 41 a Matemáticas + piloto *por realizar* | `PCA 1.0` | **7 p.** (`190.0 KB`) | Beamer **5 p.** (`134.9 KB`) | `100.0` / `100.0` | `8/8` ok | Completa |

---

## 4. Bloque C · Nueve Subproductos y Pósteres Infográficos Independientes en PDF

Concentrados en [`subproductos-independientes/`](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/entregas-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/subproductos-independientes/) (y en `subproductos/` de su actividad de origen):

| Archivo PDF | Origen | Descripción y Calidad Verificada | Págs. | Tamaño | SHA-256 |
| :--- | :---: | :--- | :-: | :-: | :--- |
| `subproducto-01A-evaluacion-diagnostica-4-conceptos.pdf` | Act 1 (`50157`) | Reporte diagnóstico de *enseñanza, aprendizaje, paradigmas y matemáticas* (`EMS=100`, `Estilo=100`, `7/0` bib) | 6 p. | `177.0 KB` | `1d9a02f07fe9500678d6bacc84b1b55aee0b6c0626451a90d5bdaebf5f090c33` |
| `subproducto-01B-cuatro-ideas-cynthia-scott-2015.pdf` | Act 1 (`50157`) | Las 4 ideas de Scott (2015) y comentario crítico situado (`EMS=100`, `Estilo=100`, `7/0` bib) | 6 p. | `129.0 KB` | `87b400744063232b3ec1271b2b34ba3cd8e997ea94c67a01f5cb7dd32b43a27a` |
| **`subproducto-03A-infografia-tres-autores-sesion-3.pdf`** | Act 3 (`51440`) | **Póster apaisado en LaTeX/TikZ · Comparativa 3 Autores** (*Philippe Meirieu 2020 | Keith Sawyer 2008 | Felipe Martínez Rizo 2026*) con retratos, 12 tarjetas de íconos y checks | 1 p. | `685.6 KB` | `ee17a31c1eeede6f13a59eb8cbafd0f07804730f4c3484006b5b1e057220429f` |
| **`subproducto-03B-infografia-philippe-meirieu-2020.pdf`** | Act 3 (`51440`) | **Póster apaisado en LaTeX/TikZ · Monografía Philippe Meirieu (2020)** en 3 ejes visuales con retratos, 12 mini-tarjetas y fuente APA 7 | 1 p. | `447.8 KB` | `6663823d6132df558e0eacb89cfa092d282c2390087e235b74f54e08cb94cc35` |
| `subproducto-06A-primer-momento-analisis-lectura-quiroga-lara.pdf` | Act 6 (`51705`) | Primer momento independiente (Quiroga y Lara, 2022) (`EMS=100`, `Estilo=100`, `7/0` bib) | 5 p. | `127.8 KB` | `ae0e07265ce62c62d88f771fdd497b6d0d8ad4c5e4ad72e7dfb869fd6464d8ad` |
| `subproducto-06B-segundo-momento-cuadro-diagnostico-practica.pdf` | Act 6 (`51705`) | Segundo momento independiente (diagnóstico de 6 aspectos) (`EMS=100`, `Estilo=100`, `6/0` bib) | 5 p. | `172.9 KB` | `5117b99ec99f47997a9562ca2b231f9e67b1cb06b30e699f330a8eb218cf18db` |
| `subproducto-06C-tercer-momento-propuesta-innovacion-matematica.pdf` | Act 6 (`51809`) | Tercer momento independiente (propuesta *por realizar* en 7 apartados) (`EMS=100`, `Estilo=100`, `9/0` bib) | 5 p. | `184.1 KB` | `229293b562efea01c78319a975a6a77d3ca232a8c9cbb37e458f3c62199148eb` |
| `subproducto-08A-instrumento-autoevaluacion-trabajo-final-50175.pdf` | Act 8 (`50175`) | Instrumento de autoevaluación oficial (20 afirmaciones y 2 reflexiones) (`EMS=100`, `Estilo=100`, `8/0` bib) | 6 p. | `199.0 KB` | `0a3786a57c37c910b509d8e97f4d8d2ab2ac9b68905057cc6bdd902775039e65` |
| **`subproducto-09A-infografia-keith-sawyer-2008.pdf`** | Act 9 (`51436`) | **Póster apaisado en LaTeX/TikZ · Monografía R. Keith Sawyer (2008)** en 3 ejes visuales con retratos, 12 mini-tarjetas e implicaciones en Matemáticas | 1 p. | `469.7 KB` | `d9a016600880a717142b7303b4800cf3fd3416a886c3007fd82c23e151dc56bf` |

---

## 5. Evaluación Crítica de la Corrección Visual y Entregables

1. **Eliminación Total de `.docx` Generados:** Se suprimieron los archivos Word previamente generados (`leftover_docx = []`) y las planeaciones `PCA 09` y `PCA 11` se actualizaron para declarar exclusivamente productos generados en LaTeX/PDF.
2. **Salto Cualitativo en las Infografías de Sesión 3 (LaTeX/TikZ):** Siguiendo el estilo editorial de tus dos láminas de referencia, se implementó un sistema nativo en TikZ (`infografia_components.tex`) con columnas de cabecera cromática (`#1A4F7A`, `#1E6B43`, `#C45522`), retratos circulares con aro blanco, barras tipo píldora con medallones circulares vectoriales (`target`, `key`, `bulb`, `gear`), 12 mini-tarjetas por lámina con pictogramas vectoriales propios (`personas`, `autonomia`, `dialogo`, `alerta`, `balanza`, `cerebro`, `construccion`, `grafica`, `lupa`, `escuela`, `andamio`, `doc`, `libro`), viñetas con círculos `✓` de implicaciones para la práctica docente y cintillo inferior integrador. Las tres láminas renderizadas a 200 DPI fueron inspeccionadas visualmente sin solapamientos ni cortes de texto.
3. **Verificación Integral (`any_error = False`):** Todos los reportes principales y subproductos compilados obtuvieron `rc=0`, `0` citas sin resolver (`?? = False`), `EMS = 100.0/100 (MAESTRO)`, `Fidelidad de Estilo = 100.0/100 (VÁLIDO [OK])` y `0` referencias faltantes en `cli.py bibcheck`.
