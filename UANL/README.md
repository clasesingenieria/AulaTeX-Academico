# Universidad Autónoma de Nuevo León (UANL) - Entorno AulaTeX

Este directorio contiene la arquitectura institucional de plantillas, recursos gráficos, bibliografía y asignaturas de la **Universidad Autónoma de Nuevo León (UANL)** en el sistema AulaTeX Académico.

---

## 1. Suite de Plantillas Maestras Institucionales y por Carrera

Siguiendo el contrato y patrón institucional establecido en AulaTeX (homólogo a ITESCA, UnADM y UCNL), la arquitectura de UANL provee:

### Plantillas Maestras Institucionales (Raíz)
| Archivo Fuente | Rol | Salida Verificada | Motor / Estilo |
| :--- | :--- | :--- | :--- |
| [`reporte-uanl.tex`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/reporte-uanl.tex) | Plantilla Maestra de Reporte Académico / PIA | `reporte-uanl.pdf` | Plantilla-Informe / Helvetica / APA 7 |
| [`presentacion-uanl.tex`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/presentacion-uanl.tex) | Plantilla Maestra de Defensa Oral Beamer (16:9) | `presentacion-uanl.pdf` | Beamer / XeLaTeX / TikZ |
| [`bibliografia-uanl.bib`](file:///c:/Users/Sysx/Documents/AulaTeX-Academico/UANL/bibliografia-uanl.bib) | Repositorio bibliográfico institucional | N/A | BibTeX / Biber / Natbib |

### Plantillas Canónicas por Carrera
| Carrera | Reporte Técnico | Presentación Oral | Compilación |
| :--- | :--- | :--- | :--- |
| **Ingeniero Agrónomo** (FAGRO) | `reporte-ingeniero-agronomo.tex` | `presentacion-ingeniero-agronomo.tex` | `aulaTEX/latexmk-build.ps1` |
| **Ing. en Administración y Sistemas** (FIME) | `reporte-ingenieria-en-administracion-y-sistemas.tex` | `presentacion-ingenieria-en-administracion-y-sistemas.tex` | `aulaTEX/latexmk-build.ps1` |
| **Ing. en Mecatrónica** (FIME) | `reporte-ingenieria-en-mecatronica.tex` | `presentacion-ingenieria-en-mecatronica.tex` | `aulaTEX/latexmk-build.ps1` |

---

## 2. Identidad Gráfica y Paleta Institucional

Las plantillas integran la identidad cromática y visual oficial de la UANL y sus facultades:
- **Azul UANL:** `#00376C` / `RGB(0, 55, 108)` (Color primario institucional).
- **Azul UANL Profundo:** `#002855` (Fondos y encabezados de contraste).
- **Oro Universitario:** `#D4AF37` / `#F0A500` (Acentos dorados y filetes de separación).
- **Verde Facultad de Agronomía:** `#1B5E20` / `#2E7D32` (Acento específico para programas agropecuarios).
- **Verde FIME:** `#005A36` (Identidad gráfica para programas de la Facultad de Ingeniería Mecánica y Eléctrica).

### Recursos de Logotipos (`assets-uanl/`)
- `logo-uanl.png`: Escudo oficial de la Universidad Autónoma de Nuevo León.
- `logo-agronomia.png`: Escudo heráldico oficial de la Facultad de Agronomía (*Scientia Agricolis Vita*).
- `logo-fime.png`: Logotipo de la Facultad de Ingeniería Mecánica y Eléctrica.
- `logos-institucionales.pdf`: Escudos institucionales combinados en alta resolución vectorial.

---

## 3. Comandos de Compilación Oficial

Para compilar desde la raíz del repositorio con auxiliares aislados por documento en `.build/latex/`:

```powershell
# Compilación institucional general
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\reporte-uanl.tex
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\presentacion-uanl.tex

# Compilación canónica por carrera
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\reporte-ingeniero-agronomo.tex
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingenieria-en-administracion-y-sistemas\reporte-ingenieria-en-administracion-y-sistemas.tex
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingenieria-en-mecatronica\reporte-ingenieria-en-mecatronica.tex
```
