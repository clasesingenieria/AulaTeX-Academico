# Compilación Canónica — Álgebra Lineal

La compilación y validación editorial de todos los reportes y presentaciones de Álgebra Lineal se realiza mediante el agente canónico **`latexmk`** integrado en AulaTeX y LEX, sin requerir scripts auxiliares locales (`compilar.ps1`).

---

## 1. Comandos de Compilación con el Agente `latexmk`

Desde la raíz de `c:\ahk-Autohokey` (o mediante la herramienta MCP `aulatex_latexmk`):

```powershell
# Compilar toda la materia (reportes y presentaciones con auto-detección de motor y aislamiento de auxiliares):
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal" --documento todos

# Compilar actividades individuales bajo numeración editorial secuencial (1..5):
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/reporte-algebra-lineal-Actividad-1.tex"
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/reporte-algebra-lineal-Actividad-2.tex"
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/reporte-algebra-lineal-Actividad-3.tex"
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/reporte-algebra-lineal-Actividad-4.tex"
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/reporte-algebra-lineal-Actividad-5.tex"
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/presentacion-algebra-lineal-Actividad-5.tex"
c:\ahk-Autohokey\.venv\Scripts\python.exe aulatex/cli.py latexmk "UANL/ingeniero-agronomo/algebra-lineal/reporte-algebra-lineal.tex"
```

---

## 2. Mapa de Actividades y Correspondencia Editorial Secuencial

| Núm. Editorial | Identificador Académico Original | Título y Propósito Formativo | Entregables Canónicos | Motor TeX | Puntos |
|:---:|:---|:---|:---|:---:|:---:|
| **Actividad 1** | Fase 1 / Evidencia 1 (Nexus 1.6) | Mapa cognitivo de telaraña sobre aplicaciones del álgebra lineal | `reporte-algebra-lineal-Actividad-1.tex` | `pdflatex` | 10 pts |
| **Actividad 2** | Fase 2 / Laboratorio 2 (Nexus 2.1) | Segundo Laboratorio de Álgebra Lineal (Gauss, Gauss-Jordan, Cramer) | `reporte-algebra-lineal-Actividad-2.tex` | `pdflatex` | 3 pts |
| **Actividad 3** | Fase 2 / Evidencia 2 (Nexus 2.6) | Mapa cognitivo de algoritmo: Solución del Sistema 11 | `reporte-algebra-lineal-Actividad-3.tex`<br>*(alias: Actividad-2-6)* | `pdflatex` | 10 pts |
| **Actividad 4** | Fase 3 / Evidencia 3 (Nexus 3.6) | Reporte de solución de un caso de valores y vectores propios (Sistema 11) | `reporte-algebra-lineal-Actividad-4.tex`<br>*(alias: Actividad-3-6)* | `pdflatex` | 10 pts |
| **Actividad 5** | Producto Integrador de Aprendizaje (PIA) | Modelación matricial y matrices de Leslie aplicadas a la dinámica poblacional | `reporte-algebra-lineal-Actividad-5.tex`<br>`presentacion-algebra-lineal-Actividad-5.tex` | `xelatex` | 25 pts |
| **Portafolio** | Cierre curricular global | Portafolio consolidado de evidencias de la materia | `reporte-algebra-lineal.tex` | `pdflatex` | — |

---

## 3. Garantías de Gobernanza y Aislamiento

1. **Aislamiento en `AHK-Trabajo`:** Todos los residuos de compilación (`.aux`, `.bcf`, `.bbl`, `.log`, `.toc`, `.fls`, `.fdb_latexmk`) se confinan en `AHK-Trabajo\latex\.build`, manteniendo la carpeta académica libre de efímeros.
2. **Detección Automática de Motor:** `latexmk` selecciona automáticamente `xelatex` para documentos con `fontspec` (como Actividad 5 y sus diapositivas Beamer) y `pdflatex` para los reportes 1 a 4 y el portafolio.
3. **Memoria de Reaprendizaje:** Las resoluciones se registran en `AHK-Trabajo\cache\aulatex\latexmk_learning.json`.
4. **Entregables Sincronizados:** Los PDFs finales y formatos Word oficiales se publican en `entregas-algebra-lineal/` con manifiesto SHA-256.
