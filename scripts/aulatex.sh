#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
python="$repo_root/.venv-linux/bin/python"
if [[ ! -x "$python" ]]; then
    printf '%s\n' 'Falta .venv-linux. Ejecuta bash setup.sh --no-shell --skip-llm.' >&2
    exit 127
fi
cd -- "$repo_root"
if (($# == 0)); then
    set -- --help
fi
exec "$python" "$repo_root/scripts/aulatex_agent.py" "$@"