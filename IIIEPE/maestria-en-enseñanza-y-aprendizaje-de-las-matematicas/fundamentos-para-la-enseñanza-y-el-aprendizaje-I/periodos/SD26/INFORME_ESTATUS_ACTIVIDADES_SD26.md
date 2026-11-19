# Informe Consolidado de Estatus y Evaluación · PFM01 Fundamentos para la Enseñanza y el Aprendizaje I (SD26)

- **Curso Moodle:** [PFM01 Fundamentos para la enseñanza y el aprendizaje. (Ago-Nov 2026 Grupo A)](https://evaposgrados.iiiepe.edu.mx/aula/course/view.php?id=1048) (`course_id=1048`)
- **Institución / Programa:** IIIEPE · Maestría en Aprendizaje y Enseñanza de las Matemáticas (`MAEM`)
- **Periodo Académico:** 2do periodo, septiembre--diciembre de 2026 (`SD26`)
- **Estudiante:** Mtro. Martín Jonathan de la Cruz Muñoz (Matrícula: `00874` · `martin.delacruz@campus.iiiepe.edu.mx`)
- **Docente Titular Registrado:** Mtro. Oscar Zertuche Santos
- **Alcance completado:** Realización íntegra sin restricción de fechas de vencimiento de:
  1. Las **8 actividades oficiales con buzón (`mod/assign`)** de Moodle Curso `1048` (`actividad-01` a `actividad-08`).
  2. Las **6 actividades complementarias** correspondientes a la segunda infografía de Sesión 3 (Keith Sawyer), la Sesión 4 sin buzón (`SIETE HABILIDADES BÁSICAS`), la brecha curricular de Sesión 5 (*Escuela Tradicional vs. NEM + Tres Reportes de Lectura*), el Bloque I Tema 4 (*Scott 2015b*), el Bloque II (*Cuadro de 4 Metodologías Sociocríticas NEM*) y el recurso oficial `51784` (*50 innovaciones educativas para escuelas*, Rivas et al., 2017) (`actividad-09` a `actividad-14`).
  3. Los **6 subproductos separados en PDF independiente** y **4 documentos editables en Word (`.docx`)** + **1 presentación editable en PowerPoint (`.pptx`)**.
- **Política de Entrega (`Fail-Closed`):** **Todos los entregables permanecen retenidos y sellados localmente** para tu revisión humana antes de cualquier carga en Moodle. **No se realizó ningún envío automático a plataforma.**

---

## 1. Resumen Ejecutivo de Realización Integral

| Dimensión Verificada | Resultado Final | Respaldo y Evidencia |
| :--- | :--- | :--- |
| Actividades oficiales con buzón en Moodle (`1048`) | **8 / 8 (100 %)** | `cli.py monitor-iiiepe --period SD26`: `8/8` en `entregable_generado` |
| Actividades complementarias (Sesiones sin buzón y programa) | **6 / 6 (100 %)** | `actividad-09` a `actividad-14` completas con consola PCA + PDF + Beamer |
| Planeaciones canónicas PCA v1.0.0 | **14 / 14 válidas** (`schema_valid=True`, `suma_pts=100.0`) | [planeaciones-...-SD26](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/planeaciones-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/) |
| Compilación LaTeX (`cli.py latexmk`) | **34 / 34 (`rc=0`)** (14 reportes + 14 Beamer + 6 subproductos PDF) | Cero citas sin resolver (`?? = False` en los 34 PDFs) |
| Auditoría Editorial y Estilo (`cli.py audit`) | **20 / 20 con EMS = 100.0/100 (`MAESTRO`)** | **20 / 20 con Fidelidad de Estilo = 100.0/100 (`VÁLIDO [OK]`)** y `0` violaciones |
| Auditoría Bibliográfica (`cli.py bibcheck`) | **20 / 20 con `0` claves faltantes** | Validación cruzada con [referencias-sd26.bib](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/referencias-sd26.bib) |
| Formatos editables complementarios | **4 archivos `.docx` (OOXML válidos) + 1 `.pptx` (15 diapositivas)** | Validados con parser XML de `ElementTree` y OOXML PresentationML |
| Paquete de entregas sincronizado (`sincronizar_entregas_iiiepe.py`) | **30 archivos principales + 10 archivos en `subproductos-independientes/`** | [CHECKLIST_PRE_ENTREGA.md](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/entregas-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/CHECKLIST_PRE_ENTREGA.md) |
| Estado en Moodle Curso `1048` | `Todavía no se han realizado envíos` (retenido localmente) | En espera de autorización humana explícita para carga |

---

## 2. Bloque A · Las 8 Actividades Oficiales con Buzón en Moodle (Curso `1048`)

| Act | Módulo | Actividad y Contenido Desarrollado | Plan PCA | Reporte PDF | Presentación / Extras | `audit` (EMS / Estilo) | `bibcheck` | Estatus |
| :-: | :-: | :--- | :-: | :-: | :--- | :-: | :-: | :--- |
| **1** | [`50157`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=50157) | **Recursos sesión 1:** 4 ideas ampliadas y comentarios críticos de Scott (2015) + matriz didáctica + diagnóstico de 4 conceptos en TikZ | `PCA 1.0` | **9 p.** (`195.2 KB`) | Beamer **11 p.** (`163.7 KB`) + Subproductos `1A`, `1B` y `.docx` | `100.0` / `100.0` | `8/8` ok | Completa |
| **2** | [`50158`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=50158) | **¿Cómo soy como maestro?:** 5 preguntas + silueta docente TikZ situada + matriz formativa y bibliografía justificada | `PCA 1.0` | **10 p.** (`150.1 KB`) | Beamer **11 p.** (`131.4 KB`) | `100.0` / `100.0` | `14/14` ok | Completa |
| **3** | [`51440`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51440) | **Infografía Philippe Meirieu (2020):** Infografía apaisada TikZ sobre *«La escuela después»... ¿con la pedagogía de antes?* + transferencia matemática | `PCA 1.0` | **7 p.** (`213.6 KB`) | Beamer **11 p.** (`145.3 KB`) + `.docx` `Actividad_7` | `100.0` / `100.0` | `8/8` ok | Completa |
| **4** | [`51676`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51676) | **Investigación-acción educativa:** 5 preguntas (Restrepo Gómez, 2004) + espiral TikZ y 5 fases aplicadas a variación lineal | `PCA 1.0` | **8 p.** (`185.4 KB`) | Beamer **11 p.** (`145.6 KB`) | `100.0` / `100.0` | `10/10` ok | Completa |
| **5** | [`51707`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51707) | **El aprendizaje profundo:** 5 preguntas (Quiroga y Lara, 2022) + algoritmo vs comprensión + triada cognitiva--interpersonal--intrapersonal | `PCA 1.0` | **8 p.** (`186.4 KB`) | Beamer **11 p.** (`192.5 KB`) | `100.0` / `100.0` | `10/10` ok | Completa |
| **6** | [`51809`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51809) | **Tercer momento Bloque III:** Primer momento (síntesis), Segundo momento (diagnóstico 6 aspectos) y Tercer momento (propuesta *por realizar* en 7 elementos) | `PCA 1.0` | **9 p.** (`222.1 KB`) | Beamer **12 p.** (`156.2 KB`) + Subproductos `6A`, `6B`, `6C` | `100.0` / `100.0` | `13/13` ok | Completa |
| **7** | [`51813`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=51813) | **Modelo Bioecológico:** 6 preguntas (Bronfenbrenner y Morris, 2006) + procesos proximales + diagrama concéntrico y matriz de 5 sistemas | `PCA 1.0` | **8 p.** (`141.9 KB`) | Beamer **11 p.** (`136.4 KB`) | `100.0` / `100.0` | `9/9` ok | Completa |
| **8** | [`50172`](https://evaposgrados.iiiepe.edu.mx/aula/mod/assign/view.php?id=50172) | **Trabajo final integrador:** Proyecto *por realizar* «Calibrar para decidir» (10 apartados `50173`, STEAM NEM, Bronfenbrenner) + Autoevaluación 20 ítems (`50175`) | `PCA 1.0` | **12 p.** (`236.9 KB`) | Beamer **15 p.** (`200.8 KB`) + **`.pptx` (`313.6 KB`)** + Subp. `8A` | `100.0` / `100.0` | `16/16` ok | Completa |

---

## 3. Bloque B · Las 6 Actividades Complementarias (Sesiones sin Buzón, Segunda Infografía y Programa General)

| Act | Referencia Curricular | Actividad y Contenido Desarrollado | Plan PCA | Reporte PDF | Presentación / Extras | `audit` (EMS / Estilo) | `bibcheck` | Estatus |
| :-: | :--- | :--- | :-: | :-: | :--- | :-: | :-: | :--- |
| **9** | Sesión 3b (`51440` / `51436`) | **Segunda Infografía · R. Keith Sawyer (2008):** Infografía apaisada TikZ sobre *Mejorando el aprendizaje: ciencias del aprendizaje* (instruccionismo vs aprendizaje profundo, andamiaje, articulación y TIMSS) | `PCA 1.0` | **8 p.** (`232.3 KB`) | Beamer **8 p.** (`132.3 KB`) + `Actividad_7_Martin_Jonathan_de_la_Cruz_Munoz.docx` | `100.0` / `100.0` | `7/7` ok | Completa |
| **10** | Bloque I · Tema 4 (`47634`) | **Tipos de aprendizaje en el siglo XXI:** Análisis de *El futuro del aprendizaje 2* (Scott, 2015b) + diagrama de 4 pilares (Delors) y caso energético | `PCA 1.0` | **6 p.** (`156.3 KB`) | Beamer **5 p.** (`125.5 KB`) | `100.0` / `100.0` | `9/9` ok | Completa |
| **11** | Sesión 4 en Moodle 1048 (`47637`) | **Siete habilidades básicas (Tony Wagner):** Mapa mental radial en TikZ + estrategias para Matemáticas + caso térmico $T(t)=20+3t$ | `PCA 1.0` | **7 p.** (`167.1 KB`) | Beamer **5 p.** (`201.7 KB`) + **`.docx` (`4.4 KB`)** | `100.0` / `100.0` | `6/6` ok | Completa |
| **12** | Sesión 5 (`47636` + Programa) | **Escuela tradicional vs. NEM y Tres Reportes de Lectura:** Cuadro comparativo de 8 dimensiones (Scallon/SEP) + 3 reportes independientes (Meirieu 2020, Sawyer 2008, Martínez Rizo 2026 PISA 2025) | `PCA 1.0` | **8 p.** (`171.3 KB`) | Beamer **5 p.** (`155.0 KB`) | `100.0` / `100.0` | `7/7` ok | Completa |
| **13** | Bloque II (`47639` / `49058`) | **Cuadro de 4 entradas · Metodologías sociocríticas NEM:** Comparativo de ABPC, STEAM, ABP y Aprendizaje Servicio (fases, cómo se trabaja, palabras clave, roles y árbol TikZ) | `PCA 1.0` | **7 p.** (`140.5 KB`) | Beamer **5 p.** (`125.4 KB`) | `100.0` / `100.0` | `6/6` ok | Completa |
| **14** | Sesión 7b (`51784`) | **Análisis de «50 innovaciones educativas para escuelas» (Rivas et al., 2017):** 6 criterios CIPPEC + adaptación de casos 4, 7, 29, 39 y 41 a Matemáticas + piloto *por realizar* | `PCA 1.0` | **7 p.** (`190.0 KB`) | Beamer **5 p.** (`134.9 KB`) | `100.0` / `100.0` | `8/8` ok | Completa |

---

## 4. Bloque C · Subproductos Separados en PDF Independiente y Entregables Word (`.docx`)

Ubicados tanto dentro de `subproductos/` en sus actividades de origen como concentrados en [`subproductos-independientes/`](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/entregas-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/subproductos-independientes/):

### 4.1 Seis Subproductos Independientes en PDF (Plantilla IIIEPE + `EMS = 100.0 / Estilo = 100.0`)

| Archivo PDF | Origen | Alcance específico | Págs. | Tamaño | `audit` / `bibcheck` | SHA-256 |
| :--- | :---: | :--- | :-: | :-: | :-: | :--- |
| `subproducto-01A-evaluacion-diagnostica-4-conceptos.pdf` | Act 1 (`50157`) | Diagnóstico de *enseñanza, aprendizaje, paradigmas y matemáticas* + diagrama TikZ y 2 ejemplos | 6 p. | `177.0 KB` | `100/100` · `7/0` | `1d9a02f07fe9500678d6bacc84b1b55aee0b6c0626451a90d5bdaebf5f090c33` |
| `subproducto-01B-cuatro-ideas-cynthia-scott-2015.pdf` | Act 1 (`50157`) | Las 4 ideas textuales de Scott (2015) y su comentario crítico situado | 6 p. | `129.0 KB` | `100/100` · `7/0` | `87b400744063232b3ec1271b2b34ba3cd8e997ea94c67a01f5cb7dd32b43a27a` |
| `subproducto-06A-primer-momento-analisis-lectura-quiroga-lara.pdf` | Act 6 (`51705`) | Primer momento independiente (análisis de Quiroga y Lara, 2022) | 5 p. | `127.8 KB` | `100/100` · `7/0` | `ae0e07265ce62c62d88f771fdd497b6d0d8ad4c5e4ad72e7dfb869fd6464d8ad` |
| `subproducto-06B-segundo-momento-cuadro-diagnostico-practica.pdf` | Act 6 (`51705`) | Segundo momento independiente (cuadro de 6 aspectos con evidencias reales de cuadernos) | 5 p. | `172.9 KB` | `100/100` · `6/0` | `5117b99ec99f47997a9562ca2b231f9e67b1cb06b30e699f330a8eb218cf18db` |
| `subproducto-06C-tercer-momento-propuesta-innovacion-matematica.pdf` | Act 6 (`51809`) | Tercer momento independiente (propuesta de innovación *por realizar* con 7 elementos + secuencia TikZ) | 5 p. | `184.1 KB` | `100/100` · `9/0` | `229293b562efea01c78319a975a6a77d3ca232a8c9cbb37e458f3c62199148eb` |
| `subproducto-08A-instrumento-autoevaluacion-trabajo-final-50175.pdf` | Act 8 (`50175`) | Instrumento de autoevaluación oficial (20 afirmaciones marcadas + 2 preguntas de reflexión) | 6 p. | `199.0 KB` | `100/100` · `8/0` | `0a3786a57c37c910b509d8e97f4d8d2ab2ac9b68905057cc6bdd902775039e65` |

### 4.2 Cuatro Entregables Editables en Word (`.docx`) Validados en OOXML

| Archivo `.docx` | Referencia / Propósito | Estructura Verificada (`ElementTree`) | Tamaño | SHA-256 |
| :--- | :--- | :--- | :-: | :--- |
| `Actividad_1_Cuatro_Ideas_Scott_Martin_Jonathan_de_la_Cruz_Munoz.docx` | Formato Word de las 4 ideas comentadas de Scott (2015) (`50157`) | 5 partes XML · 38 párrafos · 1 tabla de síntesis | `4,701 B` | `15d66ddeb84f679d7f76f1538196c10f64dbabc980f4fb7824e4569705aede0c` |
| `Actividad_7_Martin_Jonathan_de_la_Cruz_Munoz.docx` | Entregable nominal exigido en `Rúbrica 3.docx` (Meirieu 2020 + Sawyer 2008) | 5 partes XML · 50 párrafos · 2 tablas comparativas | `4,447 B` | `0ad8913f8451c51e1ccdb075a7227d4d73764e18de1b47de7154941637bb3387` |
| `reporte-siete-habilidades-SD26.docx` (y copia sincronizada Act 11) | Escrito en Word exigido en Sesión 4 (`47637`) sobre las 7 habilidades en Matemáticas | 5 partes XML · 34 párrafos · 1 tabla de estrategias | `4,464 B` | `48fd4b53fdde33ef7e50528a2f2d1beb008487528c0a556f9c743179306e5cde` |
| `Instrumento_Autoevaluacion_50175_Martin_Jonathan_de_la_Cruz_Munoz.docx` | Lista de 20 afirmaciones (`Sí [X]`) y reflexión personal editable (`50175`) | 5 partes XML · 97 párrafos · 1 tabla de 20 ítems | `4,870 B` | `86273e19dc308690896f8299673a92e6723343d45f513af8097179f1b16a1abd` |

---

## 5. Evaluación Crítica de los Trabajos Desarrollados

1. **Cobertura Curricular Completa (`Curso 1048 + Programa General`):** Se cubrieron tanto las 8 tareas con buzón habilitado en Moodle (`actividad-01` a `actividad-08`) como las sesiones sin buzón (`Sesión 4: Siete Habilidades`, brecha `Sesión 5`), ambas infografías de la Sesión 3 (`Meirieu 2020` y `Sawyer 2008`), el compendio oficial `51784` (*50 innovaciones educativas para escuelas*), los marcos de la NEM (`47636`, `47639`, `49058`) y la separación explícita de los 6 subproductos PDF y 4 `.docx`.
2. **Coherencia con el Perfil Docente Real e Integridad Epistémica:** Todas las secuencias, diagnósticos y proyectos están situados en la enseñanza matemática de CONALEP, CECyTE (mantenimiento industrial y mecatrónica) e ingeniería universitaria, diferenciando con honestidad los **diseños didácticos por realizar** (`Calibrar y comparar para decidir`, `Calibrar para decidir`, piloto `Peer Instruction + Pensamiento Visible`, curva térmica $T(t)=20+3t$) y los **datos didácticos simulados** ($y = 1.05x + 0.2$) respecto de evidencia empírica futura en aula.
3. **Verificación Tipográfica, Bibliográfica y Visual Automatizada:**
   - **20 / 20** documentos reportan `EMS = 100.0/100 (MAESTRO)`, `Fidelidad de Estilo = 100.0/100 (VÁLIDO [OK])`, `0` violaciones, `0` signos `??` y `0` referencias faltantes.
   - Todos los diagramas vectoriales críticos (silueta docente Act 2, infografía apaisada de Meirieu Act 3, espiral de investigación-acción Act 4, tríada Act 5, elipses PPCT Act 7, gráfica de calibración Act 8, **infografía apaisada de Keith Sawyer Act 9**, 4 pilares Act 10, **mapa mental radial de 7 habilidades Act 11**, árbol de metodologías NEM Act 13 y portafolio de 5 innovaciones Act 14) fueron renderizados a PNG y verificados visualmente sin solapamientos ni cortes de texto.
4. **Resguardo de Seguridad y Compuerta de Envío (`Fail-Closed`):** Cero envíos ejecutados a Moodle y cero exposición de credenciales; todos los archivos están listos en [`entregas-fundamentos-para-la-enseñanza-y-el-aprendizaje-I-SD26`](file:///C:/Users/Sysx/Documents/AulaTeX-Academico/IIIEPE/maestria-en-ense%C3%B1anza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I/periodos/SD26/entregas-fundamentos-para-la-ense%C3%B1anza-y-el-aprendizaje-I-SD26/) para revisión humana previa a su carga.
