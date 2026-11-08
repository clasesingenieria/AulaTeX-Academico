# Ingeniero Agrónomo — UANL
## Facultad de Agronomía \textbar\ Universidad Autónoma de Nuevo León

Espacio académico curricular y suite de automatización integral para el programa educativo de **Ingeniero Agrónomo** de la Universidad Autónoma de Nuevo León (UANL), impartido por la Facultad de Agronomía en sus campus de General Escobedo y Marín, Nuevo León.

- **Estudiante:** Carlos Mauricio Carvajal Coronado
- **Matrícula:** 1977875
- **Ciclo Lectivo:** Agosto — Diciembre 2026 (Semestre Mixto / Competencias)
- **Plataforma Virtual:** Plataforma Nexus UANL / SIASE

---

## 1. Mapa Curricular y Estructura de Materias Activas

| Unidad de Aprendizaje | Código Ref. | Docente Titular | Fases | Actividades | Ponderación | Entregables Validados |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| [**Álgebra Lineal**](algebra-lineal/) | `REF#261013755137` | Miranda Vázquez José de Jesús | 4 | 19 | 100 pts | [`reporte-algebra-lineal-PIA.pdf`](algebra-lineal/reporte-algebra-lineal-PIA.pdf)<br>[`presentacion-algebra-lineal-PIA.pdf`](algebra-lineal/presentacion-algebra-lineal-PIA.pdf) |
| [**Biología Celular**](biologia-celular/) | `REF#261013755061` | Dr. Miguel Ángel Dector Carrillo | 5 | 16 | 100 pts | [`reporte-biologia-celular-PIA.pdf`](biologia-celular/reporte-biologia-celular-PIA.pdf)<br>[`presentacion-biologia-celular-PIA.pdf`](biologia-celular/presentacion-biologia-celular-PIA.pdf) |
| [**Cálculo Integral**](calculo-integral/) | `REF#261013755131` | Cátedra de Matemáticas Aplicadas | 2 | 9 | 100 pts | [`reporte-calculo-integral-PIA.pdf`](calculo-integral/reporte-calculo-integral-PIA.pdf)<br>[`presentacion-calculo-integral-PIA.pdf`](calculo-integral/presentacion-calculo-integral-PIA.pdf) |
| [**Ética y Cultura de la Legalidad**](etica-y-cultura-de-la-legalidad/) | `REF#261013755115` | Cátedra de FGU | 4 | 10 | 100 pts | [`reporte-etica-y-cultura-de-la-legalidad-PIA.pdf`](etica-y-cultura-de-la-legalidad/reporte-etica-y-cultura-de-la-legalidad-PIA.pdf)<br>[`presentacion-etica-y-cultura-de-la-legalidad-PIA.pdf`](etica-y-cultura-de-la-legalidad/presentacion-etica-y-cultura-de-la-legalidad-PIA.pdf) |
| [**Física**](fisica/) | `REF#261013755808` | Garza Valverde Elizabeth | 4 | 19 | 100 pts | [`reporte-fisica-PIA.pdf`](fisica/reporte-fisica-PIA.pdf)<br>[`presentacion-fisica-PIA.pdf`](fisica/presentacion-fisica-PIA.pdf) |
| [**Responsabilidad Social y Des. Sust.**](responsabilidad-social-y-desarrollo-sustentable/) | `REF#261013755032` | Cavazos Galindo Jaime Manuel | 4 | 12 | 100 pts | [`reporte-responsabilidad-social-y-desarrollo-sustentable-PIA.pdf`](responsabilidad-social-y-desarrollo-sustentable/reporte-responsabilidad-social-y-desarrollo-sustentable-PIA.pdf)<br>[`presentacion-responsabilidad-social-y-desarrollo-sustentable-PIA.pdf`](responsabilidad-social-y-desarrollo-sustentable/presentacion-responsabilidad-social-y-desarrollo-sustentable-PIA.pdf) |

---

## 2. Convenciones y Arquitectura de AulaTeX

### 2.1 Plantilla Unificada de Carrera
A nivel de carrera (`UANL/ingeniero-agronomo/`), se centraliza la maquetación y estructura de reportes:
- `template.tex`: Adaptación institucional que canaliza estilos al núcleo de AulaTeX (`aulaTEX/base/Plantilla-Informe/template.tex`), configurando paleta cromática (`uanlBlue`, `uanlGold`, `uanlGreenAgro`), márgenes de 2.5 cm, tipografía Arial/Helvetica y formato autor-año natbib (APA 7).
- `reporte-ingeniero-agronomo.tex`: Molde unificado oficial para evidencias y reportes técnicos de la carrera, que sintetiza:
  - **UnADM:** Desacoplamiento de metadatos, checklist didáctico y citas APA 7.
  - **IIIEPE:** Capa cromática formal e identidad visual de portada.
  - **ITESCA:** Eliminación rigurosa de metadatos operativos en entregables visibles.
- La compilación de reportes y presentaciones usa el wrapper común `aulaTEX/latexmk-build.ps1`, que detecta el motor declarado y aísla los auxiliares por documento en `.build/latex/`.

### 2.2 Estructura por Materia
Cada carpeta de materia implementa los contratos institucionales de AulaTeX:

```text
UANL/ingeniero-agronomo/
├── template.tex                                         # Adaptación institucional centralizada
├── reporte-ingeniero-agronomo.tex / .pdf                # Plantilla unificada de reportes
└── <materia>/
    ├── .aulatex-node.json                               # Contrato de metadatos de nodo curricular
    ├── estructura-aulatex.json                          # Estructura del curso (actividades, entregables, memoria)
    ├── README.md                                        # Dashboard académico de la materia
    ├── <materia>.bib                                    # Bibliografía especializada (APA 7 / BibLaTeX)
    ├── template.tex                                     # Hook modular de maquetación institucional
    ├── planeaciones-<materia>/
    │   ├── INVENTARIO.md                                # Desglose de ponderaciones, fases y criterios
    │   ├── consigna-PIA.md                              # Rúbrica y directrices oficiales del PIA
    │   ├── extraccion_nexus.json                        # Scraping exhaustivo crudo de plataforma
    │   └── recursos_listado.txt                         # Catálogo de recursos y enlaces de cátedra
    ├── referencias-<materia>/
    │   └── notas-<materia>/
    │       └── actividad-PIA/
    │           └── 01_fichas_conceptuales_*.md          # Fichas conceptuales y soporte técnico
    ├── recursos-<materia>/                              # Archivos y materiales descargados de Nexus
    ├── reporte-<materia>-PIA.tex / .pdf                 # Reporte técnico formal institucional
    └── presentacion-<materia>-PIA.tex / .pdf            # Presentación ejecutiva Beamer 16:9
```

---

## 3. Instrucciones de Compilación

### 3.1 Reporte Unificado de Carrera (`reporte-ingeniero-agronomo`)
Para compilar la plantilla unificada desde la raíz del repositorio:

```powershell
# Compilación común con detección automática del motor
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\reporte-ingeniero-agronomo.tex
```

O bien directamente mediante el comando `latexmk`:
```powershell
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\reporte-ingeniero-agronomo.tex
```

### 3.2 Compilación por Materia
Para compilar o regenerar los documentos de cualquiera de las materias desde la raíz del repositorio:

```powershell
# Compilar un reporte de materia (el motor se detecta desde el .tex)
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\<materia>\reporte-<materia>.tex

# Compilar una presentación Beamer
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\<materia>\presentacion-<materia>.tex
```
