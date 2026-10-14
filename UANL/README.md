# Universidad Autónoma de Nuevo León (UANL) - Entorno AulaTeX

Este directorio contiene la arquitectura institucional de plantillas, recursos gráficos, bibliografía y asignaturas de la **Universidad Autónoma de Nuevo León (UANL)** en el sistema AulaTeX Académico.

---

## 1. Suite de Plantillas Maestras Institucionales

Siguiendo el contrato y patrón institucional establecido en AulaTeX (homólogo a UnADM y UCNL), la raíz de `UANL/` provee:

| Archivo Fuente | Rol | Salida Verificada | Motor / Estilo |
| :--- | :--- | :--- | :--- |
| [`reporte-uanl.tex`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/reporte-uanl.tex) | Plantilla Maestra de Reporte Académico / PIA | `reporte-uanl.pdf` | Plantilla-Informe / Helvetica / APA 7 |
| [`presentacion-uanl.tex`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/presentacion-uanl.tex) | Plantilla Maestra de Defensa Oral Beamer (16:9) | `presentacion-uanl.pdf` | Beamer / XeLaTeX / TikZ |
| [`plantilla-actividad-uanl.tex`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/plantilla-actividad-uanl.tex) | Plantilla Unificada de Actividad Formativa | Salida PDF | XeLaTeX / BibLaTeX APA |
| [`maqueta.tex`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/maqueta.tex) | Entrada fundacional descendente del nodo | `maqueta.pdf` | Article / AulaTeX Contract |
| [`bibliografia-uanl.bib`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/bibliografia-uanl.bib) | Repositorio bibliográfico institucional | N/A | BibTeX / Biber / Natbib |

---

## 2. Identidad Gráfica y Paleta Institucional

Las plantillas integran la identidad cromática y visual oficial de la UANL y sus facultades:
- **Azul UANL:** `#00376C` / `RGB(0, 55, 108)` (Color primario institucional).
- **Azul UANL Profundo:** `#002855` (Fondos y encabezados de contraste).
- **Oro Universitario:** `#D4AF37` / `#F0A500` (Acentos dorados y filetes de separación).
- **Verde Facultad de Agronomía:** `#1B5E20` / `#2E7D32` (Acento específico para programas agropecuarios).

### Recursos de Logotipos (`assets-uanl/` e `img/departamentos/`)
- `logo-uanl.png`: Escudo oficial de la Universidad Autónoma de Nuevo León.
- `logo-agronomia.png`: Escudo heráldico oficial de la Facultad de Agronomía (*Scientia Agricolis Vita*).
- `logo-fime.png`: Logotipo de la Facultad de Ingeniería Mecánica y Eléctrica.
- `logos-institucionales.pdf`: Escudos institucionales combinados en alta resolución vectorial.

---

## 3. Comandos de Compilación

Para compilar las plantillas institucionales desde la raíz del repositorio:

```powershell
# 1. Compilación del Reporte Maestro UANL
$env:TEXINPUTS = '.;./aulaTEX/base/Plantilla-Informe//;'
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\reporte-uanl.tex

# 2. Compilación de la Presentación Maestra Beamer UANL
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\presentacion-uanl.tex

# 3. Compilación de la Maqueta Fundacional
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\maqueta.tex
```
