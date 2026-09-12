from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash") or ("C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else None)
HAS_BASH = bool(BASH and Path(BASH).is_file())


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def workspace_module():
    return load_module("linux_test_workspace", "scripts/aulatex/workspace.py")


@pytest.fixture
def dispatcher():
    return load_module("linux_test_dispatcher", "scripts/latexmk_build.py")


@pytest.mark.parametrize("platform,executable,script", [("nt", "powershell", "latexmk-build.ps1"), ("posix", "bash", "latexmk-build.sh")])
def test_workspace_dispatch(workspace_module, monkeypatch, tmp_path, platform, executable, script):
    workspace = workspace_module.AulaTeXWorkspace(tmp_path)
    monkeypatch.setattr(workspace_module, "os", SimpleNamespace(name=platform))
    proc = Mock(returncode=17)
    proc.communicate.return_value = ("salida", "error")
    popen = Mock(return_value=proc)
    monkeypatch.setattr(workspace_module.subprocess, "Popen", popen)
    result = workspace.compile_tex("materia con espacios/main.tex", clean_mode="none", timeout_seconds=9)
    args, kwargs = popen.call_args
    assert args[0][0] == executable
    assert any(arg.endswith(script) for arg in args[0])
    assert str(tmp_path / "materia con espacios/main.tex") in args[0]
    assert args[0][-1] == "none"
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs.get("start_new_session", False) is (platform == "posix")
    assert not result.ok and result.returncode == 17
    assert result.stdout == "salida" and result.stderr == "error"
    proc.communicate.assert_called_once_with(timeout=9)


def test_workspace_missing_launcher(workspace_module, monkeypatch, tmp_path):
    workspace = workspace_module.AulaTeXWorkspace(tmp_path)
    monkeypatch.setattr(workspace_module, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(workspace_module.subprocess, "Popen", Mock(side_effect=FileNotFoundError("bash")))
    result = workspace.compile_tex("main.tex")
    assert not result.ok and result.returncode == 127
    assert "latexmk-build.sh" in result.stderr


@pytest.mark.parametrize("leader_exited", [False, True])
def test_timeout_kills_linux_process_group(workspace_module, monkeypatch, tmp_path, leader_exited):
    workspace = workspace_module.AulaTeXWorkspace(tmp_path)
    killpg = Mock()
    monkeypatch.setattr(workspace_module, "os", SimpleNamespace(name="posix", killpg=killpg))
    monkeypatch.setattr(workspace_module, "signal", SimpleNamespace(SIGKILL=9))
    proc = Mock(pid=234)
    proc.poll.return_value = 0 if leader_exited else None
    proc.communicate.side_effect = [subprocess.TimeoutExpired("bash", 1), ("parcial", "diagnóstico")]
    monkeypatch.setattr(workspace_module.subprocess, "Popen", Mock(return_value=proc))
    result = workspace.compile_tex("main.tex", timeout_seconds=1)
    killpg.assert_called_once_with(234, 9)
    assert result.returncode == 124
    assert "parcial" in result.stdout and "latexmk-build.sh" in result.stdout
    assert result.stderr == "diagnóstico"


def test_exited_process_group_is_harmless(workspace_module, monkeypatch, tmp_path):
    monkeypatch.setattr(workspace_module, "os", SimpleNamespace(name="posix", killpg=Mock(side_effect=ProcessLookupError)))
    monkeypatch.setattr(workspace_module, "signal", SimpleNamespace(SIGKILL=9))
    workspace_module.AulaTeXWorkspace(tmp_path)._terminate_process_tree(Mock(pid=234))


def test_linux_venv_is_not_scanned(workspace_module, tmp_path):
    (tmp_path / ".venv-linux").mkdir()
    (tmp_path / ".venv-linux/hidden.tex").touch()
    (tmp_path / "visible.tex").touch()
    assert workspace_module.AulaTeXWorkspace(tmp_path).find_tex_files() == [tmp_path / "visible.tex"]


@pytest.mark.parametrize("platform,tikz,script", [("nt", False, "latexmk-build.ps1"), ("nt", True, "tikz-export.ps1"), ("posix", False, "latexmk-build.sh")])
def test_portable_recipe(dispatcher, monkeypatch, platform, tikz, script):
    monkeypatch.setattr(dispatcher, "os", SimpleNamespace(name=platform))
    run = Mock(return_value=SimpleNamespace(returncode=13))
    monkeypatch.setattr(dispatcher.subprocess, "run", run)
    assert dispatcher.main(["materia/main"] + (["--tikz"] if tikz else [])) == 13
    command = run.call_args.args[0]
    assert any(arg.endswith(script) for arg in command)
    assert str(Path("materia/main.tex")) in command
    assert run.call_args.kwargs["cwd"] == ROOT
    if tikz:
        assert command[-2:] == ["-Format", "all"]


def test_linux_tikz_is_explicitly_unsupported(dispatcher, monkeypatch):
    monkeypatch.setattr(dispatcher, "os", SimpleNamespace(name="posix"))
    run = Mock()
    monkeypatch.setattr(dispatcher.subprocess, "run", run)
    assert dispatcher.main(["main.tex", "--tikz"]) == 2
    run.assert_not_called()


def test_dispatcher_missing_launcher(dispatcher, monkeypatch):
    monkeypatch.setattr(dispatcher.subprocess, "run", Mock(side_effect=FileNotFoundError("launcher")))
    assert dispatcher.main(["main.tex"]) == 127


def test_cli_imports_gui_only_on_demand():
    tree = ast.parse((ROOT / "scripts/aulatex/cli.py").read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.ImportFrom) and node.module == "gui" for node in tree.body)
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    module = ast.Module(body=[main], type_ignores=[])
    parser = Mock()
    parser.parse_args.return_value = SimpleNamespace(command=None)
    namespace = {"build_parser": lambda: parser, "os": SimpleNamespace(name="posix")}
    exec(compile(module, "cli-main", "exec"), namespace)
    namespace["main"]([])
    parser.print_help.assert_called_once()


def test_vscode_paths_and_shell_line_endings():
    settings = json.loads((ROOT / ".vscode/settings.json").read_text(encoding="utf-8"))
    linux = json.loads((ROOT / "AulaTeX-Linux.code-workspace").read_text(encoding="utf-8"))
    assert "python.defaultInterpreterPath" not in settings
    assert linux["settings"]["python.defaultInterpreterPath"].endswith("/.venv-linux")
    assert settings["latex-workshop.latex.outDir"] == "%DIR%"
    for tool in settings["latex-workshop.latex.tools"]:
        assert tool["command"] == "python"
        assert tool["args"][0].endswith("/scripts/latexmk_build.py")
    for rel in ("setup.sh", "scripts/aulatex.sh", "scripts/latexmk-build.sh"):
        assert b"\r" not in (ROOT / rel).read_bytes()


@pytest.fixture
def sandbox(tmp_path):
    if not HAS_BASH:
        pytest.skip("Bash no disponible")
    root = tmp_path / "repo con espacios"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for rel in ("setup.sh", "scripts/aulatex.sh", "scripts/latexmk-build.sh"):
        shutil.copyfile(ROOT / rel, root / rel)
    (root / ".latexmkrc").write_text("", encoding="utf-8")
    tools = tmp_path / "tools"
    tools.mkdir()
    fake_latex = tools / "latexmk"
    fake_latex.write_text(
        '#!/usr/bin/env bash\nset -eu\nprintf "%s\\n" "$PWD" "$@" > "$TEST_LOG"\n'
        'out=""\nfor arg in "$@"; do case "$arg" in -outdir=*) out="${arg#-outdir=}";; esac; done\n'
        'if [[ "${TEST_LATEX_EXIT:-0}" != 0 ]]; then exit "$TEST_LATEX_EXIT"; fi\n'
        'if [[ "${TEST_NO_PDF:-0}" == 1 ]]; then exit 0; fi\n'
        'tex="${!#}"\nname="${tex##*/}"\nprintf "PDF nuevo" > "$out/${name%.tex}.pdf"\n',
        encoding="utf-8",
    )
    fake_latex.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "COMSPEC", "PATHEXT"}}
    env.update({"PATH": str(tools) + os.pathsep + env.get("PATH", ""), "TEST_LOG": str(tmp_path / "calls.txt")})
    return root, tools, env


def shell(sandbox, script, *args, cwd=None, **extra_env):
    root, _, env = sandbox
    if os.name == "nt":
        args = tuple("/" + arg[0].lower() + arg[2:].replace("\\", "/") if len(arg) > 2 and arg[1] == ":" else arg for arg in args)
    return subprocess.run([BASH, str(root / script), *args], cwd=cwd or root.parent, env={**env, **extra_env}, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)


def tex_document(root, relative="materia con espacios/main.tex"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\documentclass{article}\\begin{document}Offline\\end{document}", encoding="utf-8")
    return path


def test_build_cwd_paths_and_isolation(sandbox):
    root, _, env = sandbox
    a = tex_document(root)
    b = tex_document(root, "otra materia/main.tex")
    for path in (a, b):
        result = shell(sandbox, "scripts/latexmk-build.sh", str(path))
        assert result.returncode == 0, result.stderr
        assert path.with_suffix(".pdf").read_text() == "PDF nuevo"
    builds = list((root / ".build/latex").glob("main-*"))
    assert len(builds) == 2
    assert all((build / "main.pdf").exists() for build in builds)
    log = Path(env["TEST_LOG"]).read_text()
    assert "repo con espacios\n-norc\n-r\n" in log
    assert "-cd-\n" in log
    assert "-auxdir=" in log and "-outdir=" in log


@pytest.mark.parametrize("mode", ["none", "safe", "full"])
def test_cleanup_preserves_other_documents_and_source(sandbox, mode):
    root, _, _ = sandbox
    a = tex_document(root)
    b = tex_document(root, "otra/main.tex")
    for path in (a, b):
        assert shell(sandbox, "scripts/latexmk-build.sh", str(path)).returncode == 0
    foreign = root / ".build/latex/unrelated.log"
    foreign.write_text("preservar")
    source_log = a.parent / "other.log"
    source_log.write_text("preservar")
    result = shell(sandbox, "scripts/latexmk-build.sh", str(a), "--clean-mode", mode)
    assert result.returncode == 0, result.stderr
    assert source_log.read_text() == foreign.read_text() == "preservar"
    assert b.with_suffix(".pdf").read_text() == "PDF nuevo"
    assert len(list((root / ".build/latex").glob("main-*/main.pdf"))) == 2


def test_build_preserves_failure_code_and_previous_final_pdf(sandbox):
    root, _, _ = sandbox
    tex = tex_document(root)
    tex.with_suffix(".pdf").write_text("anterior")
    result = shell(sandbox, "scripts/latexmk-build.sh", str(tex), TEST_LATEX_EXIT="23")
    assert result.returncode == 23
    assert tex.with_suffix(".pdf").read_text() == "anterior"


def test_success_without_pdf_is_failure(sandbox):
    root, _, _ = sandbox
    tex = tex_document(root)
    result = shell(sandbox, "scripts/latexmk-build.sh", str(tex), TEST_NO_PDF="1")
    assert result.returncode == 1
    assert "sin generar" in result.stderr


@pytest.mark.parametrize("args", [[], ["missing.tex"], ["main.tex", "--unknown"], ["main.tex", "--clean-mode"], ["main.tex", "--clean-mode", "invalid"]])
def test_build_invalid_arguments(sandbox, args):
    assert shell(sandbox, "scripts/latexmk-build.sh", *args).returncode == 2


def test_build_relative_cwd_and_extensionless_path(sandbox):
    root, _, _ = sandbox
    tex = tex_document(root)
    result = shell(sandbox, "scripts/latexmk-build.sh", "main", cwd=tex.parent)
    assert result.returncode == 0, result.stderr
    result = shell(sandbox, "scripts/latexmk-build.sh", "materia con espacios/main")
    assert result.returncode == 0, result.stderr


def test_setup_help_and_conflicting_options_do_not_install(sandbox):
    assert shell(sandbox, "setup.sh", "--help").returncode == 0
    assert shell(sandbox, "setup.sh", "--unknown").returncode == 2
    assert shell(sandbox, "setup.sh", "--skip-llm", "--with-llm").returncode == 2
    assert not (sandbox[0] / ".venv-linux").exists()


def test_launcher_missing_environment(sandbox):
    result = shell(sandbox, "scripts/aulatex.sh", "--help")
    assert result.returncode == 127
    assert "setup.sh" in result.stderr


def install_fake_python(sandbox):
    _, tools, _ = sandbox
    fake = tools / "python3"
    fake.write_text(
        '#!/usr/bin/env bash\nset -eu\nprintf "%s\\n" "$PWD" "$@" >> "$TEST_LOG"\n'
        'if [[ "${1:-}" == -m && "${2:-}" == venv ]]; then\n'
        'mkdir -p "$3/bin"\ncp "$0" "$3/bin/python"\nchmod +x "$3/bin/python"\nfi\n', encoding="utf-8"
    )
    fake.chmod(0o755)


def test_setup_skip_system_is_idempotent_and_preserves_windows(sandbox):
    root, _, env = sandbox
    install_fake_python(sandbox)
    win = root / ".venv"
    win.mkdir()
    (win / "install-venv.ps1").write_text("preservar")
    (win / ".gitignore").write_text("preservar")
    for _ in range(2):
        result = shell(sandbox, "setup.sh", "--skip-system", "--no-shell", "--skip-llm")
        assert result.returncode == 0, result.stderr
    log = Path(env["TEST_LOG"]).read_text()
    assert log.count("\nvenv\n") == 1
    assert "requirements-linux-cli.txt" in log
    assert "requirements-linux-llm.txt" not in log and "torch" not in log
    assert (win / "install-venv.ps1").read_text() == "preservar"
    assert (win / ".gitignore").read_text() == "preservar"


def test_optional_profiles_use_cpu_and_no_windows_requirements(sandbox):
    _, _, env = sandbox
    install_fake_python(sandbox)
    result = shell(sandbox, "setup.sh", "--skip-system", "--no-shell", "--with-llm", "--with-training")
    assert result.returncode == 0, result.stderr
    log = Path(env["TEST_LOG"]).read_text()
    assert "https://download.pytorch.org/whl/cpu" in log
    assert "requirements-linux-llm.txt" in log and "requirements-linux-training.txt" in log
    assert "requirements-training.txt" not in log and "interfaz/requirements.txt" not in log


@pytest.mark.parametrize("options", [("--all", "--skip-llm"), ("--skip-llm", "--all")])
def test_all_rejects_conflicting_skip_llm(sandbox, options):
    result = shell(sandbox, "setup.sh", *options)
    assert result.returncode == 2
    assert not (sandbox[0] / ".venv-linux").exists()


def test_documents_notebooks_do_not_install_training(sandbox):
    _, _, env = sandbox
    install_fake_python(sandbox)
    result = shell(sandbox, "setup.sh", "--skip-system", "--no-shell", "--with-documents", "--with-notebooks")
    assert result.returncode == 0, result.stderr
    log = Path(env["TEST_LOG"]).read_text()
    assert "requirements-linux-documents.txt" in log
    assert "requirements-linux-notebooks.txt" in log
    assert "\nipykernel\ninstall\n--user\n--name\naulatex-linux\n" in log
    assert "requirements-linux-training.txt" not in log and "download.pytorch.org" not in log


def test_all_selects_profiles_and_pins_cpu_torch(sandbox):
    _, tools, env = sandbox
    install_fake_python(sandbox)
    for tool in ("ffmpeg", "inkscape", "pandoc"):
        path = tools / tool
        path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    result = shell(sandbox, "setup.sh", "--skip-system", "--no-shell", "--all")
    assert result.returncode == 0, result.stderr
    log = Path(env["TEST_LOG"]).read_text()
    for profile in ("cli", "llm", "documents", "training", "notebooks"):
        assert f"requirements-linux-{profile}.txt" in log
    assert "https://download.pytorch.org/whl/cpu" in log
    assert "torch-cpu-constraints.txt" in log and "\n-c\n" in log
    assert "\nipykernel\ninstall\n" in log


def test_media_profile_uses_apt_and_validates_tools():
    script = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "extra_packages=(ffmpeg inkscape pandoc)" in script
    assert 'shellcheck "${extra_packages[@]}"' in script
    assert 'for tool in ffmpeg inkscape pandoc' in script


def test_launcher_defaults_to_help_and_preserves_arguments(sandbox):
    root, _, env = sandbox
    install_fake_python(sandbox)
    assert shell(sandbox, "setup.sh", "--skip-system", "--no-shell").returncode == 0
    Path(env["TEST_LOG"]).unlink()
    assert shell(sandbox, "scripts/aulatex.sh").returncode == 0
    assert shell(sandbox, "scripts/aulatex.sh", "compile", "materia con espacios/main.tex").returncode == 0
    log = Path(env["TEST_LOG"]).read_text()
    assert "aulatex_agent.py\n--help\n" in log
    assert "aulatex_agent.py\ncompile\nmateria con espacios/main.tex\n" in log
    assert root.name in log


@pytest.mark.parametrize("command", ["--help", "agent-patterns"])
def test_real_cli_offline_without_gui(command):
    if not all(importlib.util.find_spec(name) for name in ("langchain_core", "langchain_openai", "langchain_anthropic")):
        pytest.skip("Adaptadores CLI no instalados en este intérprete")
    code = r'''
import importlib.abc
from pathlib import Path
import runpy
import sys

def guard(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = str(args[0]).lower().replace("\\", "/").rsplit("/", 1)[-1]
        if name.endswith((".env", ".key", ".salt")):
            raise RuntimeError("Acceso a secretos bloqueado en pruebas")
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname"}:
        raise RuntimeError("Red bloqueada en pruebas")

class NoGUI(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"tkinter", "_tkinter"} or fullname == "aulatex.gui":
            raise RuntimeError("GUI bloqueada en pruebas CLI")

sys.addaudithook(guard)
sys.meta_path.insert(0, NoGUI())
script = Path(sys.argv[1])
sys.argv = [str(script), sys.argv[2]]
runpy.run_path(str(script), run_name="__main__")
'''
    result = subprocess.run([sys.executable, "-c", code, str(ROOT / "scripts/aulatex_agent.py"), command], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()