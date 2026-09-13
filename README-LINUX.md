# AulaTeX en Ubuntu 24.04 (CPU / Remote SSH)

Esta adaptación es local: no crea VMs, no despliega servicios y no configura
credenciales. Está orientada a Ubuntu 24.04 x86_64, Python 3.12 del sistema y
TeX Live **completo de la distribución**, no al instalador upstream de TeX Live.
La estación r7i.4xlarge actual es CPU, no GPU. Reserva el volumen persistente de 200 GiB para
el repositorio, el entorno y los datos; no dependas del NVMe efímero para conservarlos.
TeX Live ocupa varios GB y la generación de formatos puede tardar bastante.
Los modelos/datasets opcionales consumen espacio adicional; comprobar espacio libre.

## Instalación

Desde la raíz del repositorio, con acceso a los repositorios Ubuntu/PyPI:

```bash
df -h . /
bash setup.sh --help
bash setup.sh --no-shell --skip-llm
```

Para instalar todos los perfiles Linux de extracción, multimedia, IA, entrenamiento
CPU y notebooks, sin descargar modelos ni configurar proveedores:

```bash
bash setup.sh --all --no-shell
```

El bootstrap instala mediante apt: texlive-full, latexmk, biber, perl,
ghostscript, poppler-utils, Python/venv/Tk, compiladores, git/git-lfs, fuentes,
certificados y shellcheck. Puede pedir sudo para apt; **no ejecutes todo el
setup con sudo**, para no crear archivos del repositorio propiedad de root.
No configura Git LFS ni descarga objetos LFS automáticamente.

Si la VM ya tiene apt preparado:

```bash
bash setup.sh --skip-system --no-shell --skip-llm
```

`--skip-system` no instala ni comprueba todos los paquetes apt: su preparación
queda a cargo del administrador. Deben existir al menos Python >=3.12 con venv
y pip; para compilar, TeX Live completo y latexmk. La receta VS Code usa `python`,
por lo que se necesita `python-is-python3` o Python en el PATH de VS Code remoto.

Reejecutar el setup reutiliza .venv-linux sin borrarlo. pip puede actualizar
herramientas y resolver versiones dentro de los rangos declarados; no es un
lockfile reproducible bit a bit. .venv y sus dos archivos versionados de Windows
no se modifican. `--no-shell` evita abrir una consola; sin esa opción solo se abre
en una terminal interactiva, sin modificar perfiles Bash del usuario.

## Núcleo y perfiles opcionales

- [scripts/requirements-linux-cli.txt](scripts/requirements-linux-cli.txt):
  requests y los tres adaptadores LangChain importados obligatoriamente por la
  arquitectura actual. Aunque sean SDKs de IA, instalarlos no configura ni llama
  modelos. No incluye audio, GUI de terceros, PyWin32, CUDA ni entrenamiento.
- [scripts/requirements-linux-llm.txt](scripts/requirements-linux-llm.txt):
  integraciones opcionales LangChain/LangGraph/deepagents, cifrado y tokenizador.
- [scripts/requirements-linux-training.txt](scripts/requirements-linux-training.txt):
  preparación/entrenamiento local; PyTorch se instala antes desde el índice CPU.
  No usa los requisitos Windows/interfaz ni instala SDKs de despliegue de nube.
- [scripts/requirements-linux-documents.txt](scripts/requirements-linux-documents.txt):
  reutiliza los requisitos del extractor (PyMuPDF, DOCX, pandas, NumPy,
  OpenPyXL y scikit-learn) y añade pypdf y Pillow.
- [scripts/requirements-linux-notebooks.txt](scripts/requirements-linux-notebooks.txt):
  JupyterLab, ipykernel, ipywidgets y cliente Jupyter. Registra el kernel de usuario
  `aulatex-linux` con el intérprete de este entorno; no inicia un servidor Jupyter.
- `--with-media`: instala FFmpeg/FFprobe, Inkscape y Pandoc desde Ubuntu. Con
  `--skip-system` comprueba que los ejecutables existan y falla si falta alguno.

```bash
bash setup.sh --skip-system --no-shell --with-llm
bash setup.sh --skip-system --no-shell --skip-llm --with-training
bash setup.sh --no-shell --with-documents --with-media --with-notebooks
```

Los perfiles pueden combinarse; `--all` activa los cinco perfiles opcionales.
`--skip-llm` es incompatible con `--with-llm` y con `--all`. Omitir un perfil no desinstala
paquetes que se hayan instalado previamente. `--skip-llm` es una opción de
instalación, **no un cortafuegos** que desactive los subcomandos IA del programa.
IA requiere credenciales válidas, no configuradas por este bootstrap. No copies
secretos a Git ni los imprimas para diagnosticar. El entrenamiento de modelos
grandes en CPU puede ser impráctico; no se garantiza QLoRA/CUDA ni se descarga
ningún modelo automáticamente.

PyTorch se obtiene exclusivamente del índice CPU oficial. El bootstrap verifica
que no esté compilado para CUDA/ROCm y escribe una restricción de su versión exacta
en `.venv-linux/torch-cpu-constraints.txt` para la resolución conjunta de los demás
paquetes. Si otro requisito no es compatible, pip falla en lugar de sustituirlo
silenciosamente por una variante GPU. Esto no fija todas las versiones del entorno.
No se instalan controladores, CUDA, bitsandbytes ni servicios públicos.

El perfil notebooks puede usarse sin entrenamiento. En VS Code, instala la
extensión Jupyter en el host remoto y selecciona **AulaTeX Linux (CPU)**. Cambiar
la ubicación del repositorio exige volver a ejecutar el perfil para actualizar
la ruta registrada del kernel.

## Pruebas funcionales de los perfiles

```bash
.venv-linux/bin/python scripts/verify_linux_flows.py --all
.venv-linux/bin/python scripts/verify_linux_flows.py --documents --media
```

El verificador genera archivos sintéticos en directorios temporales: PDF, DOCX,
XLSX, PNG, audio WAV, SVG y Markdown. Comprueba lectura/exportación y TF-IDF.
El entrenamiento crea un GPT-2 diminuto desde configuración, hace un paso de
backpropagation CPU y guarda/recarga sus pesos; no usa `from_pretrained` ni
descarga modelos. Notebooks comprueba el intérprete registrado y ejecuta `6 * 7`
en un kernel temporal limitado a localhost, que se cierra al terminar.
No se crean notebooks `.ipynb`, se leen secretos ni se modifican documentos reales.
La salida JSON informa versiones y comprobaciones; un fallo devuelve código 1.

Las pruebas usan cachés temporales y modo offline de Hugging Face; esos ajustes
no equivalen a un cortafuegos del sistema. No prueban credenciales ni flujos de
proveedores, todos los scripts PowerShell, ni rendimiento de modelos grandes.
Instalar Inkscape no convierte automáticamente la receta TikZ Windows a Linux.

## CLI sin interfaz gráfica

```bash
bash scripts/aulatex.sh
bash scripts/aulatex.sh --help
bash scripts/aulatex.sh agent-patterns
bash scripts/aulatex.sh compile reporte-AulaTeX-Academico.tex
```

El lanzador usa [scripts/aulatex_agent.py](scripts/aulatex_agent.py), reenvía
argumentos sin perder espacios y ejecuta desde la raíz. Sin argumentos muestra
ayuda; no abre GUI. La GUI se importa únicamente al pedirla explícitamente
(el comportamiento predeterminado Windows se conserva). No uses `gui` en una
sesión SSH sin servidor gráfico; Remote SSH no proporciona escritorio remoto.
No se ha adaptado toda la automatización PowerShell, extractores, exportación
TikZ ni entrenamiento/cloud a Linux.

### Validar y configurar model-router

La carga del archivo de configuración no demuestra que la API key sea válida.
Para validar el LLM y corregir su configuración si falla, sin PowerShell ni GUI:

```bash
bash scripts/aulatex.sh llm-config
```

El asistente primero prueba `Auto (model-router)`. Si falla, permite introducir
**endpoint HTTPS, deployment y API key**, desbloquear las claves actuales mediante
el PIN maestro, reintentar o cancelar. El PIN y la API key se solicitan con entrada
oculta; nunca se pasan como argumentos ni se imprimen. No pegues secretos en el chat.

Los datos nuevos se prueban en memoria y solo se guardan cuando el LLM devuelve
el marcador esperado. La API key se cifra **antes** de escribir, con reemplazo
atómico y permisos `0600`. Se preservan los otros perfiles y comentarios. Si hay
otros secretos cifrados que deban conservarse, el PIN debe poder descifrarlos; el
asistente no rota ni sustituye su salt. Una clave antigua de model-router dañada
sí puede reemplazarse. Si el archivo cambia durante la edición, se aborta el
guardado para no sobrescribir esa modificación.

Se admite la raíz del recurso Azure, `/openai/v1`, `/v1` o la URL completa de
`chat/completions`/`responses`. Una URL antigua de deployments conserva su
`api-version` y se actualiza con el deployment introducido.

**El PIN introducido en el asistente no se exporta a la terminal padre.** Para
usar las credenciales cifradas en otras ejecuciones desde la misma terminal,
define primero el PIN en Bash sin mostrarlo ni guardarlo en el historial:

```bash
read -r -s -p "PIN maestro de AulaTeX: " AULATEX_MASTER_PIN
printf '\n'
export AULATEX_MASTER_PIN
bash scripts/aulatex.sh llm-config
```

Para automatización o comprobación sin modificaciones:

```bash
bash scripts/aulatex.sh llm-config --non-interactive
bash scripts/aulatex.sh llm-validate
bash scripts/aulatex.sh llm-validate --configure-on-failure
```

`llm-validate` usa model-router por defecto y conserva `--engine` para los otros
motores. `--configure-on-failure` habilita el asistente solo para model-router.
Sin TTY o con `--non-interactive` no se solicitan datos. La salida final es JSON
sin secretos, con código `0` solo si la validación fue exitosa y `1` si falla o
se cancela. El asistente interactivo añade menús antes del JSON.

Estas pruebas **sí llaman al proveedor** y pueden consumir cuota: envían un prompt
mínimo, sin documentos del proyecto, en un único intento sin fallback ni
redirecciones, con 32 tokens de salida y timeout de 45 segundos por defecto.
Se pueden ajustar con `--max-tokens` (16–128) y `--timeout-seconds` (mínimo 5).
El bootstrap, la ayuda y la compilación siguen sin validar ni configurar LLM.

## Compilación y códigos de salida

```bash
bash scripts/latexmk-build.sh reporte-AulaTeX-Academico.tex
bash scripts/latexmk-build.sh "materia con espacios/main.tex" --clean-mode none
python3 scripts/latexmk_build.py reporte-AulaTeX-Academico.tex
```

El wrapper resuelve rutas desde el cwd de quien lo invoca o desde la raíz;
acepta rutas absolutas internas al repositorio y el nombre sin extensión que
envía LaTeX Workshop. Después cambia a la raíz y carga explícitamente
[.latexmkrc](.latexmkrc), sin cargar otros archivos rc del usuario.
Los paths TeX/Bib incluyen también el directorio del documento.

Cada documento usa un directorio propio bajo .build/latex, identificado por el
nombre y un hash de su ruta relativa; dos main.tex de materias distintas no
comparten auxiliares. Se copia el PDF junto al TeX **solo si latexmk termina
correctamente y existe el PDF generado**. Un fallo conserva el PDF final anterior:
su existencia no demuestra que la última compilación haya funcionado.

- `none` y `safe` conservan auxiliares/logs para compilación incremental y diagnóstico.
- `full` limpia solamente los archivos del directorio de build de ese documento.
- Nunca se barren otras materias ni se eliminan residuos junto a las fuentes.
- Se conserva el código de latexmk; argumentos/documento inválido: 2;
  ejecutable ausente: 127; éxito sin PDF: 1.
- `AulaTeXWorkspace.compile_tex()` limita el tiempo (360 segundos por defecto)
  y en POSIX mata el grupo del proceso y sus hijos al expirar; devuelve 124.
  El wrapper directo y la receta VS Code no añaden timeout propio.
- No ejecutes dos compilaciones simultáneas del **mismo** documento.
- Scripts antiguos que buscan logs en el directorio compartido Windows necesitan
  adaptación adicional. Los logs Linux están en el directorio aislado.
- Los scripts no habilitan shell-escape de forma global. Algunos documentos
  pueden necesitar fuentes externas, rutas corregidas por mayúsculas/minúsculas,
  o configuraciones especiales que TeX Live completo no resuelve por sí solo.

## VS Code Remote SSH

1. Conecta a la VM ya preparada usando la extensión Remote - SSH del equipo local.
2. Abre [AulaTeX-Linux.code-workspace](AulaTeX-Linux.code-workspace) en la ventana
   remota. Instala Python y LaTeX Workshop en el host remoto si VS Code lo solicita.
3. El workspace Linux selecciona .venv-linux. Si VS Code conserva una selección
   anterior, ejecuta **Python: Select Interpreter** y elige el Python de ese entorno.
   No cambies .venv de Windows. Para Windows sigue abriendo la carpeta habitual.
4. Las terminales Linux nuevas usan Bash con el entorno Linux en PATH; los perfiles
   Windows no cambian. Estas terminales no cargan .bashrc (`--norc`).
5. Usa la receta **AulaTeX: latexmk -> PDF junto al tex**. El dispatcher estándar
   [scripts/latexmk_build.py](scripts/latexmk_build.py) elige PowerShell en Windows
   o Bash en Linux, sin importar el stack IA. VS Code abre el PDF junto al TeX.

La receta TikZ PDF/SVG/PNG conserva el script Windows; en Linux devuelve un error
explícito (2). Para un documento TikZ completo usa la receta PDF, no la exportación.
El dispatcher requiere Python en PATH también en Windows (disponible tras el
setup Windows; si VS Code estaba abierto, reinícialo para actualizar PATH).

## Verificación offline

```bash
python3 --version
latexmk -v
pdflatex --version
kpsewhich article.cls
perl -MFile::Spec -e 'print "Perl OK\n"'
pdftotext -v
git lfs version
bash -n setup.sh scripts/aulatex.sh scripts/latexmk-build.sh
shellcheck setup.sh scripts/aulatex.sh scripts/latexmk-build.sh
.venv-linux/bin/python -m pip check
bash scripts/aulatex.sh --help
.venv-linux/bin/python -m pip install 'pytest>=8,<10'
.venv-linux/bin/python -m pytest scripts/tests/test_linux_support.py -q -p no:cacheprovider --tb=short
bash scripts/latexmk-build.sh reporte-AulaTeX-Academico.tex
```

La instalación de pytest necesita PyPI o un wheelhouse preparado; la suite en sí
es offline. Usa documentos sintéticos en temporales, simula latexmk/pip y omite
apt para probar argumentos, códigos de error, aislamiento y reejecución. Los tests de
CLI real bloquean apertura de secretos, red y Tk. Los tests de proceso comprueban
el grupo POSIX con mocks; no sustituyen la prueba real en la VM. La comprobación
final con un documento del repositorio sí requiere TeX Live y sus recursos.

Validación inicial del 12 de septiembre de 2026: 33 pruebas enfocadas aprobadas tanto
en Windows/Git Bash como en Ubuntu 24.04/Python 3.12. ShellCheck, `pip check`
y la auditoría de dpkg pasan en Ubuntu. Se instaló `texlive-full` de Ubuntu
(TeX Live 2023), incluidos XeTeX, LuaTeX, fuentes extra y Biber.
Se compilaron el reporte raíz (5 páginas), `UnADM/reporte-unadm.tex` con la
plantilla compartida (4 páginas) y la presentación raíz (7 páginas).
El perfil `--with-llm` también se instaló y pasó `pip check` y la misma suite.
No se configuraron credenciales, invocaron proveedores ni instalaron modelos
de entrenamiento. La portada del reporte se renderizó y revisó visualmente.

### Perfiles completos instalados y comprobados

Validación posterior del mismo día en la VM Ubuntu: `bash setup.sh --all --no-shell`
terminó correctamente, al igual que su repetición con `--skip-system`.
Pasaron las **102 pruebas** del bootstrap/verificador y las 12 comprobaciones
funcionales reales del verificador. `pip check`, ShellCheck y auditoría dpkg sin errores.
Una compilación limpia posterior volvió a producir el reporte PDF de 5 páginas.

Versiones comprobadas (inventario de esa ejecución, no lockfile completo):

| Perfil | Versiones |
| --- | --- |
| Documentos | PyMuPDF 1.28.2, pypdf 6.18.1, python-docx 1.2.0, pandas 2.3.3, OpenPyXL 3.1.5, scikit-learn 1.9.1, Pillow 12.3.0 |
| Entrenamiento CPU | torch 2.14.0+cpu, transformers 4.57.6, peft 0.20.0, trl 0.29.1, datasets 5.0.1 |
| Notebooks | JupyterLab 4.6.3, ipykernel 7.3.0, jupyter-client 8.10.0 |
| Multimedia | FFmpeg 6.1.1, Inkscape 1.2.2, Pandoc 3.1.3 |

El kernel `aulatex-linux` ejecutó correctamente una celda temporal y fue cerrado.
Se instaló la extensión Jupyter en el VS Code remoto. Quedaron unos 171 GiB libres.
El entorno previo y los manifiestos se respaldaron en
`/home/ubuntu/.cache/aulatex-bootstrap-9jpJenpR` antes de instalar.
No se descargaron modelos preentrenados ni se configuraron credenciales de proveedores.