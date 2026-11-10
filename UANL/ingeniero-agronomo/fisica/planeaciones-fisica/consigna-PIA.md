# Consigna de Evaluación: Producto Integrador de Aprendizaje (PIA)
## Unidad de Aprendizaje: Física (REF#261013755808)
### Facultad de Agronomía — Universidad Autónoma de Nuevo León (UANL)

- **Actividad:** Producto Integrador de Aprendizaje (Actividad Integradora Final / Actividad 4.1)
- **Denominación en Plataforma Nexus:** *Producto Integrador de Aprendizaje: Prototipo casero sobre un tema específico de su disciplina de estudio*
- **Docente Titular:** Garza Valverde Elizabeth
- **Estudiante:** Diego de la Cruz Muñoz
- **Matrícula:** 1977875
- **Programa Académico:** Ingeniero Agrónomo
- **Ponderación Curricular:** 25% de la calificación semestral final (25 puntos sobre 100)
- **Modalidad:** Construcción física individual y validación experimental
- **Entregables:**
  1. **Prototipo Físico Tangible:** Maquinaria excavadora hidráulica articulada a escala funcional construida físicamente conforme al esquema de ensamble industrial ("Science Technology Project Teaching - Excavating machinery"), entregada de forma presencial para verificación operativa y defensa técnica ante la docente titular.
  2. **Reporte Técnico Formal Institucional:** Documento monográfico formal compilado bajo arquitectura AulaTeX (`reporte-fisica-PIA.pdf`), con apego a contratos editoriales UANL, deducciones físico-matemáticas, análisis de error experimental, memorias de cálculo de presiones y fuerzas, y transferencia agronómica.

---

## 1. Propósito y Justificación Formativa
Diseñar, construir físicamente, caracterizar cuantitativamente y documentar analíticamente un prototipo funcional de maquinaria excavadora accionada por fluidos (brazo hidráulico de 3 a 4 grados de libertad con pala/cuchara excavadora) aplicable al movimiento de tierras, zanjado parcelario para tendido de líneas de riego y drenaje agrícola, y manipulación de enmiendas en el sector agronómico.

El proyecto fundamenta su operación en la **mecánica de fluidos incompresibles** y la **estática y dinámica de cuerpos rígidos**:
1. **Principio de Pascal y Transmisión de Presión:**
   $$\Delta P = \frac{F_1}{A_1} = \frac{F_2}{A_2} \implies F_2 = F_1 \left(\frac{A_2}{A_1}\right) = F_1 \left(\frac{D_2}{D_1}\right)^2$$
2. **Conservación de Volumen y Continuidad Hidráulica:**
   $$\Delta V_1 = \Delta V_2 \implies A_1 \Delta x_1 = A_2 \Delta x_2 \implies \Delta x_2 = \Delta x_1 \left(\frac{A_1}{A_2}\right)$$
3. **Ventaja Mecánica y Rendimiento Energético:**
   $$VM_{\text{hid}} = \frac{F_2}{F_1}, \quad W_{\text{salida}} = \eta_{\text{mec}} W_{\text{entrada}}$$
4. **Equilibrio Estático y Momentos de Fuerza en Articulaciones de Pasador:**
   $$\sum \vec{F} = 0, \quad \sum \vec{\tau}_O = 0$$

---

## 2. Esquema Técnico y Especificaciones Físicas de Construcción
El prototipo toma como base rigurosa el esquema técnico industrial suministrado (`Documento_2026-11-10_000027.pdf`: *Science Technology Project Teaching - Excavating machinery*), integrando:
- **Chasis y Estructura Mecánica:** Tiras y bastidores de madera ranurada con longitudes de ensamble normalizadas: $10.5\text{ cm}$, $17.5\text{ cm}$, $26.0\text{ cm}$ y $36.0\text{ cm}$, acopladas con pasadores metálicos y tuercas autoblocantes.
- **Grados de Libertad Operativos:**
  1. *Rotación de base:* Giro azimutal sobre plataforma pivotante.
  2. *Elevación de pluma (boom):* Cilindro hidráulico primario para control de cota vertical.
  3. *Articulación de brazo (stick/dipper):* Cilindro secundario para alcance y penetración radial.
  4. *Accionamiento de cuchara (bucket):* Cilindro terciario para desgarre, carga y volteo de suelo agrícola.
- **Circuito Hidráulico:** 4 pares de cilindros de émbolo (jeringas maestras de mando manual y jeringas esclavas actuadoras), líneas de conducción flexibles de infusión y fluido incompresible con tinte hidrodinámico.
- **Entrega Física y Pruebas Operativas:** Ensayo presencial de capacidad de levantamiento, ciclo de zanjado simulado en arena/sustrato y verificación de ausencia de fugas y cavitación.

---

## 3. Contratos Editoriales y Estructura del Reporte Técnico (AulaTeX)
1. **Portada Institucional UANL:** Cabecera institucional, logotipos de la UANL y Facultad de Agronomía, datos de identificación completos del estudiante y docente.
2. **Resumen y Palabras Clave:** Síntesis técnica con objetivos, parámetros físicos evaluados, ventaja mecánica medida y transferencia agronómica.
3. **Introducción y Relevancia Agronómica:** Problemática del manejo de suelos, drenajes y excavación en agricultura protegida y campo abierto.
4. **Marco Teórico y Deducciones Analíticas:** Desarrollo formal del principio de Pascal, hidrostática, trabajo mecánico, rozamiento en fluidos y balance de torques en los eslabones.
5. **Ingeniería del Prototipo y Memoria de Construcción:** Despiece detallado a partir del esquema técnico (dimensiones, lista de piezas, pasos de ensamble y fijación).
6. **Protocolo Experimental, Toma de Datos y Errores:** Calibración de presiones y fuerzas ($F_1$ vs $F_2$), cálculo de incertidumbres instrumentales y propagación de errores aleatorios y sistemáticos.
7. **Discusión de Resultados y Escalabilidad Agrícola:** Rendimiento mecánico real vs teórico, fuerza de desgarre en suelo y correlación con maquinaria agrícola comercial.
8. **Bitácora de Construcción y Entrega Presencial:** Registro de manufactura física, pruebas de estanqueidad y condiciones de entrega física.
9. **Conclusiones:** Síntesis de aprendizajes integradores.
10. **Bibliografía APA 7:** Citas rigurosas procesadas mediante BibLaTeX.

---

## 4. Rúbrica de Evaluación Curricular del PIA (100 Puntos = 25% Final)

| Criterio | Nivel Excelente (100-90%) | Nivel Satisfactorio (89-75%) | Nivel Básico (74-60%) | No Aprobatorio (<60%) | Ponderación |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Modelación Física y Deducción Matemática** | Deducción analítica rigurosa del principio de Pascal, relaciones de áreas, presiones hidrostáticas y momentos torsores con análisis dimensional impecable. | Planteamiento correcto de ecuaciones con leves omisiones en el balance de momentos o pérdidas de carga. | Fórmulas aisladas sin deducción analítica ni justificación física de los términos. | Formulación física errónea o incompleta. | **25%** |
| **Construcción y Funcionalidad del Prototipo Físico** | Prototipo físico tangible robusto, fiel al esquema técnico, con 4 grados de libertad plenamente operativos, sin fugas y con entrega física verificada. | Prototipo físico funcional con pequeños desajustes en el juego de pasadores o carrera de jeringas. | Prototipo con fallas de estanqueidad, rigidez precaria o grados de libertad bloqueados. | Prototipo no construido físicamente o inoperante. | **30%** |
| **Protocolo Experimental e Incertidumbres** | Tabulación exhaustiva de fuerzas ($F_1, F_2$) y presiones, determinación de ventaja mecánica empírica y propagación estricta de incertidumbres ($\delta F_2$). | Mediciones experimentales completas pero con tratamiento elemental de errores (solo promedios simples). | Datos experimentales incompletos o sin registro sistemático de instrumentos de medición. | Datos ficticios o ausencia de validación empírica. | **25%** |
| **Calidad Editorial UANL y Transferencia Agronómica** | Documento impecable bajo plantilla UANL/AulaTeX, redacción sobria de alto nivel, diagramas técnicos y clara vinculación con la agronomía moderna. | Buen formato institucional con detalles menores de espaciado o argumentación agronómica superficial. | Incumplimiento parcial de la plantilla o referencias bibliográficas deficientes. | Formato desestructurado o sin referencias normadas APA 7. | **20%** |
