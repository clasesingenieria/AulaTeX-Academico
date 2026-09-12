#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Uso: bash setup.sh [--skip-system] [--no-shell] [--skip-llm]
                     [--with-llm] [--with-documents] [--with-media]
                     [--with-training] [--with-notebooks] [--all] [--help]

Ubuntu 24.04: instala TeX Live COMPLETO y el CLI en .venv-linux.
Por defecto solo se instala el núcleo; no se configuran credenciales.
  --skip-system    No ejecutar apt (dependencias del sistema ya preparadas).
  --no-shell       Terminar sin abrir una consola con el entorno activado.
  --skip-llm       Omitir integraciones IA opcionales; incompatible con --with-llm.
  --with-llm       Añadir LangGraph/LangChain y herramientas IA opcionales.
    --with-documents Añadir extracción PDF/DOCX/Excel y análisis de texto.
    --with-media     Instalar FFmpeg, Inkscape y Pandoc mediante apt.
  --with-training  Añadir entrenamiento local CPU, sin SDKs de nube ni CUDA.
    --with-notebooks Añadir JupyterLab e instalar el kernel aulatex-linux del usuario.
    --all           Activar todos los perfiles Linux anteriores, sin descargar modelos.
  --help          Mostrar esta ayuda sin instalar nada.
EOF
}

skip_system=0
no_shell=0
skip_llm=0
with_llm=0
with_training=0
with_documents=0
with_media=0
with_notebooks=0
for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
        --skip-system) skip_system=1 ;;
        --no-shell) no_shell=1 ;;
        --skip-llm) skip_llm=1 ;;
        --with-llm) with_llm=1 ;;
        --with-training) with_training=1 ;;
        --with-documents) with_documents=1 ;;
        --with-media) with_media=1 ;;
        --with-notebooks) with_notebooks=1 ;;
        --all) with_llm=1; with_training=1; with_documents=1; with_media=1; with_notebooks=1 ;;
        *) printf 'Opción desconocida: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
    esac
done
if ((skip_llm && with_llm)); then
    printf '%s\n' '--skip-llm y --with-llm son incompatibles.' >&2
    exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$repo_root"
if ((!skip_system)); then
    if [[ ! -r /etc/os-release ]]; then
        printf '%s\n' 'Se requiere Ubuntu 24.04 o --skip-system con dependencias preparadas.' >&2
        exit 2
    fi
    if ! grep -Eq '^ID="?ubuntu"?$' /etc/os-release || ! grep -Eq '^VERSION_ID="?24\.04"?$' /etc/os-release; then
        printf '%s\n' 'El bootstrap apt está destinado a Ubuntu 24.04.' >&2
        exit 2
    fi
    elevate=()
    if ((EUID != 0)); then
        elevate=(sudo)
    fi
    "${elevate[@]}" apt-get update
    extra_packages=()
    if ((with_media)); then
        extra_packages=(ffmpeg inkscape pandoc)
    fi
    "${elevate[@]}" env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install -y \
        python3 python-is-python3 python3-venv python3-dev python3-tk \
        build-essential pkg-config libffi-dev libssl-dev \
        texlive-full latexmk biber perl ghostscript poppler-utils \
        git git-lfs curl ca-certificates unzip fontconfig \
        fonts-dejavu fonts-liberation shellcheck "${extra_packages[@]}"
fi

if ((with_media)); then
    for tool in ffmpeg inkscape pandoc; do
        command -v "$tool" >/dev/null || { printf 'Falta %s; vuelve a ejecutar sin --skip-system.\n' "$tool" >&2; exit 127; }
    done
fi

command -v python3 >/dev/null || { printf '%s\n' 'Falta python3.' >&2; exit 127; }
python3 -c 'import sys; assert sys.version_info >= (3, 12), "Se requiere Python >= 3.12"'
venv="$repo_root/.venv-linux"
if [[ ! -x "$venv/bin/python" ]]; then
    python3 -m venv "$venv"
fi
"$venv/bin/python" -m pip install --upgrade pip setuptools wheel
requirements=(-r "$repo_root/scripts/requirements-linux-cli.txt")
if ((with_llm)); then
    requirements+=(-r "$repo_root/scripts/requirements-linux-llm.txt")
fi
if ((with_documents)); then
    requirements+=(-r "$repo_root/scripts/requirements-linux-documents.txt")
fi
if ((with_notebooks)); then
    requirements+=(-r "$repo_root/scripts/requirements-linux-notebooks.txt")
fi
if ((with_training)); then
    "$venv/bin/python" -m pip install --upgrade 'torch>=2.4,<3' --index-url https://download.pytorch.org/whl/cpu
    "$venv/bin/python" - "$venv/torch-cpu-constraints.txt" <<'PY'
import importlib.metadata
from pathlib import Path
import sys
import torch

if torch.version.cuda is not None or getattr(torch.version, "hip", None) is not None:
    raise SystemExit("Se requiere PyTorch CPU; no se continuará con una instalación CUDA/ROCm.")
version = importlib.metadata.version("torch")
Path(sys.argv[1]).write_text(f"torch=={version}\n", encoding="utf-8")
PY
    requirements+=(-c "$venv/torch-cpu-constraints.txt")
    requirements+=(-r "$repo_root/scripts/requirements-linux-training.txt")
fi
"$venv/bin/python" -m pip install "${requirements[@]}"
"$venv/bin/python" -m pip check
if ((with_notebooks)); then
    "$venv/bin/python" -m ipykernel install --user --name aulatex-linux --display-name 'AulaTeX Linux (CPU)'
fi
"$venv/bin/python" "$repo_root/scripts/aulatex_agent.py" --help
printf '\n%s\n' 'Entorno listo. CLI: bash scripts/aulatex.sh --help'
if ((!no_shell)) && [[ -t 0 && -t 1 ]]; then
    export VIRTUAL_ENV="$venv"
    export PATH="$venv/bin:$PATH"
    exec bash --norc -i
fi