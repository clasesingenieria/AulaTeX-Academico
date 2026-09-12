from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
import wave

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "verify_linux_flows.py"


@pytest.fixture
def flows(monkeypatch):
    specification = importlib.util.spec_from_file_location("verify_linux_flows_under_test", SCRIPT)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    monkeypatch.setattr(module, "load_dependency", Mock(side_effect=ModuleNotFoundError("synthetic dependency")))
    monkeypatch.setattr(module, "package_version", Mock(return_value="1.2.3"))
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=AssertionError("real subprocess forbidden")))
    monkeypatch.setattr(socket, "create_connection", Mock(side_effect=AssertionError("network forbidden")))
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("network forbidden")))
    monkeypatch.setattr(socket.socket, "connect_ex", Mock(side_effect=AssertionError("network forbidden")))
    return module


@pytest.mark.parametrize("arguments", [[], ["--unknown"], ["--doc"], ["--media", "synthetic-secret"]])
def test_invalid_arguments_are_json_and_fail(flows, capsys, arguments):
    assert flows.main(arguments) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["checks"]["cli"]["arguments"]["status"] == "failed"
    assert "use_help" in report["checks"]["cli"]["arguments"]["reason"]
    assert "synthetic-secret" not in captured.out
    assert captured.err == ""
    flows.load_dependency.assert_not_called()


def test_help_lists_all_profiles_without_imports(flows, capsys):
    with pytest.raises(SystemExit) as stopped:
        flows.main(["--help"])
    assert stopped.value.code == 0
    output = capsys.readouterr().out
    assert all(f"--{name}" in output for name in (*flows.PROFILE_PACKAGES, "all", "help"))
    flows.load_dependency.assert_not_called()


@pytest.mark.parametrize("arguments,expected", [
    (["--documents"], ["documents"]),
    (["--media"], ["media"]),
    (["--training"], ["training"]),
    (["--notebooks"], ["notebooks"]),
    (["--documents", "--training"], ["documents", "training"]),
    (["--all"], ["documents", "media", "training", "notebooks"]),
    (["--all", "--documents", "--documents"], ["documents", "media", "training", "notebooks"]),
])
def test_dispatch_is_unique_and_temporary(flows, monkeypatch, capsys, arguments, expected):
    visited = []
    workspaces = []

    def verifier_for(profile):
        def verify(workspace, checks):
            assert workspace.is_dir()
            (workspace / "synthetic.txt").write_text("temporary", encoding="utf-8")
            workspaces.append(workspace)
            visited.append(profile)
            checks["synthetic"] = {"status": "ok"}
        return verify

    for profile in flows.PROFILE_PACKAGES:
        monkeypatch.setattr(flows, f"verify_{profile}", verifier_for(profile))
    assert flows.main(arguments) == 0
    report = json.loads(capsys.readouterr().out)
    assert visited == expected
    assert list(report["checks"]) == expected
    assert set(report) == {"versions", "checks"}
    assert len(set(workspaces)) == len(expected)
    assert all(not workspace.exists() for workspace in workspaces)
    expected_packages = {package for profile in expected for package in flows.PROFILE_PACKAGES[profile]}
    assert set(report["versions"]) == {"python", *expected_packages}


def test_profile_failure_cleans_and_continues_without_leaking(flows, monkeypatch, capsys):
    workspaces = []

    def fail(workspace, checks):
        workspaces.append(workspace)
        print("synthetic-sensitive-stdout")
        print("synthetic-sensitive-stderr", file=sys.stderr)
        os.write(1, b"synthetic-native-output")
        raise RuntimeError("synthetic-sensitive-exception")

    def succeed(workspace, checks):
        workspaces.append(workspace)
        checks["synthetic"] = {"status": "ok"}

    monkeypatch.setattr(flows, "verify_documents", fail)
    monkeypatch.setattr(flows, "verify_media", succeed)
    assert flows.main(["--documents", "--media"]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["checks"]["documents"]["profile"]["status"] == "failed"
    assert report["checks"]["media"]["synthetic"]["status"] == "ok"
    assert "sensitive" not in captured.out and "native-output" not in captured.out
    assert captured.err == ""
    assert all(not workspace.exists() for workspace in workspaces)


def test_empty_profile_cannot_succeed(flows, monkeypatch, capsys):
    monkeypatch.setattr(flows, "verify_media", lambda workspace, checks: None)
    assert flows.main(["--media"]) == 1
    assert json.loads(capsys.readouterr().out)["checks"]["media"]["profile"]["status"] == "failed"


@pytest.mark.parametrize("failure,reason", [
    (ModuleNotFoundError("synthetic-sensitive"), "dependency_missing_or_incompatible"),
    (RuntimeError("synthetic-sensitive"), "verification_failed"),
    (subprocess.TimeoutExpired("synthetic-sensitive", 30, output="synthetic-sensitive"), "command_timeout"),
])
def test_exception_messages_are_not_reported(flows, failure, reason):
    checks = {}
    flows.record_check(checks, "sample", Mock(side_effect=failure))
    assert checks["sample"] == {"status": "failed", "reason": reason}


def test_package_versions_use_only_metadata(flows, monkeypatch):
    metadata_version = Mock(return_value="9.8.7")
    monkeypatch.setattr(flows.metadata, "version", metadata_version)
    original_specification = importlib.util.spec_from_file_location("verify_versions_under_test", SCRIPT)
    original = importlib.util.module_from_spec(original_specification)
    original_specification.loader.exec_module(original)
    assert original.package_version("torch") == "9.8.7"
    metadata_version.assert_called_once_with("torch")
    metadata_version.side_effect = original.metadata.PackageNotFoundError("torch")
    assert original.package_version("torch") is None


@pytest.mark.parametrize("failure", [False, True])
def test_environment_is_offline_temporary_and_restored(flows, monkeypatch, tmp_path, failure):
    monkeypatch.setenv("HF_HUB_OFFLINE", "previous-offline-value")
    monkeypatch.delenv("HF_DATASETS_OFFLINE", raising=False)
    original_home = os.environ.get("HOME")
    try:
        with flows.isolated_environment(tmp_path):
            assert os.environ["HF_HUB_OFFLINE"] == "1"
            assert os.environ["HF_DATASETS_OFFLINE"] == "1"
            assert os.environ["HOME"] == str(tmp_path)
            assert os.environ["HF_HOME"] == str(tmp_path / "huggingface")
            assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
            if failure:
                raise RuntimeError("synthetic")
    except RuntimeError:
        pass
    assert os.environ["HF_HUB_OFFLINE"] == "previous-offline-value"
    assert "HF_DATASETS_OFFLINE" not in os.environ
    assert os.environ.get("HOME") == original_home


def test_child_environment_is_allowlisted(flows, monkeypatch, tmp_path):
    for name in ("SYNTHETIC_SECRET", "PYTHONPATH", "DISPLAY", "WAYLAND_DISPLAY", "JUPYTER_PATH"):
        monkeypatch.setenv(name, "synthetic-value")
    environment = flows.child_environment(tmp_path)
    assert all(name not in environment for name in
               ("SYNTHETIC_SECRET", "PYTHONPATH", "DISPLAY", "WAYLAND_DISPLAY", "JUPYTER_PATH"))
    assert environment["HOME"] == str(tmp_path)
    assert environment["QT_QPA_PLATFORM"] == "offscreen"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert environment["PYTHONNOUSERSITE"] == "1"


@pytest.mark.parametrize("name", ["ffmpeg", "ffprobe", "inkscape", "pandoc"])
def test_missing_binary_is_safe_failure(flows, monkeypatch, tmp_path, name):
    monkeypatch.setattr(flows.shutil, "which", Mock(return_value=None))
    checks = {}
    flows.record_check(checks, name, lambda: flows.run_binary(name, [], tmp_path))
    assert checks[name] == {"status": "failed", "reason": "missing_binary"}
    subprocess.run.assert_not_called()


@pytest.mark.parametrize("outcome,reason", [
    (SimpleNamespace(returncode=0, stdout="captured", stderr="captured"), None),
    (SimpleNamespace(returncode=2, stdout="synthetic-sensitive", stderr="synthetic-sensitive"), "command_failed"),
    (subprocess.TimeoutExpired("synthetic-sensitive", 30), "command_timeout"),
])
def test_binary_execution_is_bounded_and_captured(flows, monkeypatch, tmp_path, outcome, reason):
    monkeypatch.setattr(flows.shutil, "which", Mock(return_value=str(tmp_path / "binary")))
    runner = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    monkeypatch.setattr(subprocess, "run", runner)
    checks = {}
    flows.record_check(checks, "binary", lambda: flows.run_binary("binary", ["--sample"], tmp_path))
    options = runner.call_args.kwargs
    assert options["capture_output"] and options["timeout"] == 30
    assert options["shell"] is False and options["cwd"] == tmp_path
    assert options["stdin"] == subprocess.DEVNULL
    assert options["env"]["HOME"] == str(tmp_path)
    if reason is None:
        assert checks["binary"]["status"] == "ok"
    else:
        assert checks["binary"]["reason"] == reason


def test_media_synthetic_pipeline(flows, monkeypatch, tmp_path):
    calls = []

    def run_binary(name, arguments, workspace):
        assert workspace == tmp_path
        calls.append(name)
        if name == "ffmpeg":
            assert "lavfi" in arguments and "-nostdin" in arguments
            assert "sine=frequency=440:sample_rate=8000:duration=0.1" in arguments
            with wave.open(arguments[-1], "wb") as audio:
                audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 800)
        elif name == "ffprobe":
            return SimpleNamespace(stdout=json.dumps({"streams": [
                {"codec_name": "pcm_s16le", "sample_rate": "8000", "channels": 1},
            ]}))
        elif name == "inkscape":
            assert "--batch-process" in arguments
            assert Path(arguments[-1]).parent == workspace
            destination = next(argument.split("=", 1)[1] for argument in arguments
                               if argument.startswith("--export-filename="))
            Path(destination).write_bytes(b"\x89PNG\r\n\x1a\nsynthetic")
        elif name == "pandoc":
            assert Path(arguments[-1]).read_text(encoding="utf-8").startswith("# Synthetic heading")
            Path(arguments[arguments.index("--output") + 1]).write_text(
                "<h1>Synthetic heading</h1>\n<p>Offline paragraph.</p>", encoding="utf-8",
            )
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(flows, "run_binary", run_binary)
    checks = {}
    flows.verify_media(tmp_path, checks)
    assert calls == ["ffmpeg", "ffprobe", "inkscape", "pandoc"]
    assert all(check["status"] == "ok" for check in checks.values())


@pytest.mark.parametrize("pillow_installed", [False, True])
def test_documents_dispatch_and_optional_pillow(flows, monkeypatch, tmp_path, pillow_installed):
    operations = {}
    for name in ("check_pdf", "check_pypdf", "check_docx", "check_xlsx", "check_tfidf", "check_png"):
        operations[name] = Mock()
        monkeypatch.setattr(flows, name, operations[name])
    monkeypatch.setattr(flows, "package_version", Mock(return_value="1.0" if pillow_installed else None))
    checks = {}
    flows.verify_documents(tmp_path, checks)
    assert len(checks) == 6
    for name, operation in operations.items():
        if name == "check_png" and not pillow_installed:
            operation.assert_not_called()
        elif name == "check_tfidf":
            operation.assert_called_once_with()
        else:
            operation.assert_called_once_with(tmp_path)
    assert checks["png_roundtrip"]["status"] == ("ok" if pillow_installed else "skipped")


def test_missing_document_dependencies_fail_without_leak(flows, tmp_path):
    checks = {}
    flows.verify_documents(tmp_path, checks)
    assert all(check["status"] == "failed" for check in checks.values())
    assert checks["pymupdf_roundtrip"]["reason"] == "dependency_missing_or_incompatible"


@pytest.mark.parametrize("mismatch", [None, "pdf", "pypdf", "docx", "xlsx", "tfidf", "png"])
def test_document_roundtrips_with_mocked_libraries(flows, monkeypatch, tmp_path, mismatch):
    pdf_document = MagicMock()
    pdf_document.__enter__.return_value = pdf_document
    pdf_document.__getitem__.return_value.get_text.return_value = (
        "incorrect" if mismatch == "pdf" else "AulaTeX synthetic ASCII document"
    )
    pdf_document.save.side_effect = lambda destination: Path(destination).write_bytes(b"synthetic PDF")
    pymupdf = SimpleNamespace(open=Mock(return_value=pdf_document))
    pdf_reader = Mock()
    pdf_reader.pages = [Mock()]
    pdf_reader.pages[0].extract_text.return_value = (
        "incorrect" if mismatch == "pypdf" else "AulaTeX synthetic ASCII document"
    )
    pypdf = SimpleNamespace(PdfReader=Mock(return_value=pdf_reader))
    docx_document = Mock()
    docx_document.save.side_effect = lambda destination: Path(destination).write_bytes(b"synthetic DOCX")
    restored_docx = SimpleNamespace(paragraphs=[SimpleNamespace(
        text="incorrect" if mismatch == "docx" else "Synthetic DOCX roundtrip",
    )])
    docx = SimpleNamespace(Document=Mock(side_effect=[docx_document, restored_docx]))
    original_frame = Mock()
    original_frame.to_excel.side_effect = lambda destination, **options: destination.write_bytes(b"synthetic XLSX")
    restored_frame = Mock()
    compare_frames = Mock(side_effect=AssertionError("synthetic mismatch") if mismatch == "xlsx" else None)
    pandas = SimpleNamespace(
        DataFrame=Mock(return_value=original_frame), read_excel=Mock(return_value=restored_frame),
        testing=SimpleNamespace(assert_frame_equal=compare_frames),
    )
    vectorizer = Mock()
    vectorizer.fit_transform.return_value = SimpleNamespace(shape=(2, 4), nnz=0 if mismatch == "tfidf" else 6)
    extraction = SimpleNamespace(TfidfVectorizer=Mock(return_value=vectorizer))
    image = MagicMock()
    image.__enter__.return_value = image
    image.size = (3, 2)
    image.getpixel.return_value = (0, 0, 0) if mismatch == "png" else (12, 34, 56)
    image.save.side_effect = lambda destination, **options: destination.write_bytes(b"synthetic PNG")
    image_module = SimpleNamespace(new=Mock(return_value=image), open=Mock(return_value=image))
    dependencies = {"pymupdf": pymupdf, "pypdf": pypdf, "docx": docx, "pandas": pandas,
                    "openpyxl": SimpleNamespace(), "sklearn.feature_extraction.text": extraction,
                    "PIL.Image": image_module}
    monkeypatch.setattr(flows, "load_dependency", dependencies.__getitem__)
    checks = {}
    flows.verify_documents(tmp_path, checks)
    failed = [name for name, check in checks.items() if check["status"] == "failed"]
    expected_failure = {"pdf": "pymupdf_roundtrip", "pypdf": "pypdf_read", "docx": "docx_roundtrip",
                        "xlsx": "xlsx_roundtrip", "tfidf": "tfidf", "png": "png_roundtrip"}
    assert failed == ([] if mismatch is None else [expected_failure[mismatch]])
    pdf_document.new_page.return_value.insert_text.assert_called_once_with(
        (72, 72), "AulaTeX synthetic ASCII document",
    )
    pymupdf.open.assert_any_call(str(tmp_path / "synthetic.pdf"))
    assert pypdf.PdfReader.call_args.args[0].closed
    docx.Document.assert_any_call(str(tmp_path / "synthetic.docx"))
    original_frame.to_excel.assert_called_once_with(tmp_path / "synthetic.xlsx", index=False, engine="openpyxl")
    pandas.read_excel.assert_called_once_with(tmp_path / "synthetic.xlsx", engine="openpyxl")
    compare_frames.assert_called_once_with(original_frame, restored_frame)
    vectorizer.fit_transform.assert_called_once_with(["alpha beta document", "beta gamma document"])
    image.load.assert_called_once_with()
    assert image.__exit__.call_count == 2


@pytest.mark.parametrize("cuda,hip", [("12.4", None), (None, "6.2"), ("12.4", "6.2")])
def test_training_rejects_accelerator_builds_before_imports(flows, monkeypatch, tmp_path, cuda, hip):
    torch = SimpleNamespace(version=SimpleNamespace(cuda=cuda, hip=hip))
    loader = Mock(return_value=torch)
    monkeypatch.setattr(flows, "load_dependency", loader)
    checks = {}
    flows.verify_training(tmp_path, checks)
    assert checks["cpu_backprop_checkpoint"] == {"status": "failed", "reason": "cpu_only_torch_required"}
    loader.assert_called_once_with("torch")


def training_dependencies():
    parameter = Mock(device=SimpleNamespace(type="cpu"), grad=Mock())
    model = Mock()
    model.to.return_value = model
    model.parameters.side_effect = lambda: iter([parameter])
    model.transformer.wte.weight.detach.side_effect = [Mock(), Mock()]
    loss = Mock()
    model.return_value = SimpleNamespace(loss=loss)
    tensor_finite = Mock()
    tensor_finite.item.return_value = True
    tensor_finite.all.return_value.item.return_value = True
    device_context = Mock()
    device_context.__enter__ = Mock()
    device_context.__exit__ = Mock(return_value=False)
    torch = SimpleNamespace(
        version=SimpleNamespace(cuda=None, hip=None), get_num_threads=Mock(return_value=8),
        set_num_threads=Mock(), device=Mock(return_value=device_context), tensor=Mock(), long="long",
        optim=SimpleNamespace(AdamW=Mock()), isfinite=Mock(return_value=tensor_finite),
        equal=Mock(return_value=False),
        save=Mock(side_effect=lambda state, destination: destination.write_bytes(b"synthetic state")),
        load=Mock(return_value={"synthetic": "state"}),
    )
    transformers = SimpleNamespace(GPT2Config=Mock(), GPT2LMHeadModel=Mock(return_value=model))
    return torch, transformers, model, loss


@pytest.mark.parametrize("stage", ["success", "import", "backward", "checkpoint"])
def test_training_cpu_offline_step_and_thread_cleanup(flows, monkeypatch, tmp_path, stage):
    torch, transformers, model, loss = training_dependencies()
    imported = []

    def load(name):
        imported.append(name)
        assert os.environ["HF_HUB_OFFLINE"] == "1"
        assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
        assert os.environ["HF_DATASETS_OFFLINE"] == "1"
        assert os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] == "1"
        assert os.environ["HOME"] == str(tmp_path)
        if name == "transformers" and stage == "import":
            raise ImportError("synthetic-sensitive")
        return {"torch": torch, "transformers": transformers}.get(name, SimpleNamespace())

    monkeypatch.setattr(flows, "load_dependency", load)
    if stage == "backward":
        loss.backward.side_effect = RuntimeError("synthetic-sensitive")
    if stage == "checkpoint":
        torch.load.side_effect = RuntimeError("synthetic-sensitive")
    checks = {}
    flows.verify_training(tmp_path, checks)
    assert checks["cpu_backprop_checkpoint"]["status"] == ("ok" if stage == "success" else "failed")
    assert [call.args for call in torch.set_num_threads.call_args_list] == [(2,), (8,)]
    if stage == "success":
        assert imported == ["torch", "transformers", "peft", "trl", "datasets"]
        torch.device.assert_called_once_with("cpu")
        assert torch.tensor.call_args.kwargs["device"] == "cpu"
        assert transformers.GPT2Config.call_args.kwargs["vocab_size"] == 32
        model.to.assert_called_once_with("cpu")
        loss.backward.assert_called_once_with()
        torch.optim.AdamW.return_value.step.assert_called_once_with()
        torch.load.assert_called_once_with(tmp_path / "tiny-cpu-state.pt", map_location="cpu", weights_only=True)
        model.load_state_dict.assert_called_once_with({"synthetic": "state"}, strict=True)


@pytest.mark.parametrize("option", [[], ["-Xfrozen_modules=off"], ["-X", "frozen_modules=off"]])
def test_kernel_arguments_match_current_interpreter(flows, option):
    registered = SimpleNamespace(argv=[sys.executable, *option, "-m", "ipykernel_launcher", "-f", "{connection_file}"])
    arguments = flows.kernel_arguments(registered)
    assert arguments == [sys.executable, "-I", "-m", "ipykernel_launcher", "-f", "{connection_file}"]


@pytest.mark.parametrize("arguments,reason", [
    (["python", "-m", "ipykernel_launcher", "-f", "{connection_file}"], "kernel_interpreter_mismatch"),
    ([sys.executable, "-c", "synthetic-sensitive"], "unsafe_kernel_arguments"),
    ([], "kernel_interpreter_mismatch"),
])
def test_unsafe_kernel_registration_is_rejected(flows, arguments, reason):
    with pytest.raises(flows.VerificationFailure, match=reason):
        flows.kernel_arguments(SimpleNamespace(argv=arguments))


@pytest.mark.parametrize("stage", ["success", "missing", "mismatch", "start", "ready", "execute", "wrong", "error", "shutdown"])
def test_notebook_execution_and_cleanup_with_private_registry(flows, monkeypatch, tmp_path, stage):
    class NoSuchKernel(Exception):
        pass

    registered = SimpleNamespace(
        argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        env={"SYNTHETIC_SECRET": "must-not-inherit"}, metadata={"synthetic": "not-copied"},
    )
    registry = Mock()
    registry.get_kernel_spec.return_value = registered
    if stage == "missing":
        registry.get_kernel_spec.side_effect = NoSuchKernel
    if stage == "mismatch":
        registered.argv[0] = str(tmp_path / "other-python")
    kernelspec = SimpleNamespace(KernelSpecManager=Mock(return_value=registry), NoSuchKernel=NoSuchKernel)
    manager = Mock()
    client = manager.client.return_value

    def execute(code, **options):
        assert code == "6 * 7"
        assert options["timeout"] == 30 and options["allow_stdin"] is False
        options["output_hook"]({"header": {"msg_type": "stream"}, "content": {"text": "synthetic-sensitive"}})
        options["output_hook"]({
            "header": {"msg_type": "execute_result"},
            "content": {"data": {"text/plain": "41" if stage == "wrong" else "42"}},
        })
        return {"content": {"status": "error" if stage == "error" else "ok"}}

    client.execute_interactive.side_effect = execute
    failures = {"start": manager.start_kernel, "ready": client.wait_for_ready,
                "execute": client.execute_interactive, "shutdown": manager.shutdown_kernel}
    if stage in failures:
        failures[stage].side_effect = TimeoutError("synthetic-sensitive")
    jupyter_client = SimpleNamespace(KernelManager=Mock(return_value=manager))
    dependencies = {"ipykernel": SimpleNamespace(), "jupyterlab": SimpleNamespace(),
                    "jupyter_client": jupyter_client, "jupyter_client.kernelspec": kernelspec}
    monkeypatch.setattr(flows, "load_dependency", dependencies.__getitem__)
    checks = {}
    flows.verify_notebooks(tmp_path, checks)
    assert checks["kernel_execution"]["status"] == ("ok" if stage == "success" else "failed")
    assert not list(tmp_path.rglob("*.ipynb"))
    if stage in ("missing", "mismatch"):
        jupyter_client.KernelManager.assert_not_called()
        return
    assert checks["kernel_registration"]["status"] == "ok"
    options = jupyter_client.KernelManager.call_args.kwargs
    assert options["kernel_name"] == "aulatex-linux" and options["ip"] == "127.0.0.1"
    assert options["transport"] == "tcp"
    assert Path(options["connection_file"]).parent == tmp_path
    kernel_json = json.loads((tmp_path / "kernels" / "aulatex-linux" / "kernel.json").read_text(encoding="utf-8"))
    assert kernel_json["env"] == {} and "metadata" not in kernel_json
    assert kernel_json["argv"][1] == "-I"
    assert manager.start_kernel.call_args.kwargs["cwd"] == str(tmp_path)
    assert "SYNTHETIC_SECRET" not in manager.start_kernel.call_args.kwargs["env"]
    manager.shutdown_kernel.assert_called_once_with(now=True)
    manager.cleanup_resources.assert_called_once_with()
    if stage != "start":
        client.stop_channels.assert_called_once_with()
        client.wait_for_ready.assert_called_once_with(timeout=30)


@pytest.mark.parametrize("source_path", [SCRIPT, Path(__file__)])
def test_sources_parse_as_python_312(flows, source_path):
    ast.parse(source_path.read_text(encoding="utf-8"), feature_version=(3, 12))


def test_verifier_has_no_pretrained_download_or_credentials_helpers(flows):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    forbidden = {"from_pretrained", "load_dataset", "snapshot_download", "hf_hub_download", "load_dotenv"}
    assert not any(isinstance(node, ast.Attribute) and node.attr in forbidden for node in ast.walk(tree))
    assert not any(isinstance(node, ast.Name) and node.id in forbidden for node in ast.walk(tree))