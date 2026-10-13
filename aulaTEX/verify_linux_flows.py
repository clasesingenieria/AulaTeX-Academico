from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Callable, Iterator
import wave


PROFILE_PACKAGES = {
    "documents": ("PyMuPDF", "pypdf", "python-docx", "pandas", "openpyxl", "scikit-learn", "Pillow"),
    "media": (),
    "training": ("torch", "transformers", "peft", "trl", "datasets"),
    "notebooks": ("ipykernel", "jupyterlab", "jupyter-client"),
}
OFFLINE_SETTINGS = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "DO_NOT_TRACK": "1",
    "WANDB_DISABLED": "true",
    "WANDB_MODE": "offline",
    "TOKENIZERS_PARALLELISM": "false",
    "CUDA_VISIBLE_DEVICES": "",
    "HIP_VISIBLE_DEVICES": "",
    "OMP_NUM_THREADS": "2",
    "MKL_NUM_THREADS": "2",
}
KERNEL_NAME = "aulatex-linux"
Checks = dict[str, dict[str, str]]


class VerificationFailure(Exception):
    pass


class ArgumentFailure(Exception):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ArgumentFailure


def load_dependency(name: str):
    return importlib.import_module(name)


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise VerificationFailure(reason)


def record_check(checks: Checks, name: str, operation: Callable[[], None]) -> None:
    try:
        operation()
    except VerificationFailure as failure:
        checks[name] = {"status": "failed", "reason": str(failure)}
    except ImportError:
        checks[name] = {"status": "failed", "reason": "dependency_missing_or_incompatible"}
    except subprocess.TimeoutExpired:
        checks[name] = {"status": "failed", "reason": "command_timeout"}
    except Exception:
        checks[name] = {"status": "failed", "reason": "verification_failed"}
    else:
        checks[name] = {"status": "ok"}


def environment_settings(workspace: Path) -> dict[str, str]:
    return {
        **OFFLINE_SETTINGS,
        "HOME": str(workspace),
        "USERPROFILE": str(workspace),
        "TMP": str(workspace),
        "TEMP": str(workspace),
        "TMPDIR": str(workspace),
        "XDG_CONFIG_HOME": str(workspace / "config"),
        "XDG_CACHE_HOME": str(workspace / "cache"),
        "XDG_DATA_HOME": str(workspace / "data"),
        "HF_HOME": str(workspace / "huggingface"),
        "HF_HUB_CACHE": str(workspace / "huggingface" / "hub"),
        "HF_DATASETS_CACHE": str(workspace / "huggingface" / "datasets"),
        "TORCH_HOME": str(workspace / "torch"),
        "MPLCONFIGDIR": str(workspace / "matplotlib"),
        "IPYTHONDIR": str(workspace / "ipython"),
        "JUPYTER_CONFIG_DIR": str(workspace / "jupyter-config"),
        "JUPYTER_DATA_DIR": str(workspace / "jupyter-data"),
        "JUPYTER_RUNTIME_DIR": str(workspace / "jupyter-runtime"),
    }


@contextmanager
def isolated_environment(workspace: Path) -> Iterator[None]:
    settings = environment_settings(workspace)
    previous = {name: os.environ.get(name) for name in settings}
    try:
        os.environ.update(settings)
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def child_environment(workspace: Path) -> dict[str, str]:
    allowed = ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT")
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment.update(environment_settings(workspace))
    environment["PYTHONNOUSERSITE"] = "1"
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["GSETTINGS_BACKEND"] = "memory"
    return environment


@contextmanager
def muted_output() -> Iterator[None]:
    saved_descriptors = []
    with open(os.devnull, "w", encoding="utf-8") as sink:
        try:
            for descriptor in (1, 2):
                saved_descriptors.append((descriptor, os.dup(descriptor)))
                os.dup2(sink.fileno(), descriptor)
            with redirect_stdout(sink), redirect_stderr(sink):
                yield
        finally:
            for descriptor, saved in reversed(saved_descriptors):
                os.dup2(saved, descriptor)
                os.close(saved)


def run_binary(name: str, arguments: list[str], workspace: Path) -> subprocess.CompletedProcess:
    executable = shutil.which(name)
    require(executable is not None, "missing_binary")
    completed = subprocess.run(
        [executable, *arguments],
        cwd=workspace,
        env=child_environment(workspace),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=30,
        check=False,
        shell=False,
    )
    require(completed.returncode == 0, "command_failed")
    return completed


def check_pdf(workspace: Path) -> None:
    pymupdf = load_dependency("pymupdf")
    text = "AulaTeX synthetic ASCII document"
    destination = workspace / "synthetic.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), text)
        document.save(str(destination))
    with pymupdf.open(str(destination)) as document:
        require(text in document[0].get_text(), "pdf_text_mismatch")


def check_pypdf(workspace: Path) -> None:
    pypdf = load_dependency("pypdf")
    with (workspace / "synthetic.pdf").open("rb") as source:
        reader = pypdf.PdfReader(source)
        require("AulaTeX synthetic ASCII document" in reader.pages[0].extract_text(), "pypdf_text_mismatch")


def check_docx(workspace: Path) -> None:
    docx = load_dependency("docx")
    destination = workspace / "synthetic.docx"
    document = docx.Document()
    document.add_paragraph("Synthetic DOCX roundtrip")
    document.save(str(destination))
    restored = docx.Document(str(destination))
    require(restored.paragraphs[0].text == "Synthetic DOCX roundtrip", "docx_text_mismatch")


def check_xlsx(workspace: Path) -> None:
    pandas = load_dependency("pandas")
    load_dependency("openpyxl")
    destination = workspace / "synthetic.xlsx"
    original = pandas.DataFrame({"document": ["alpha", "beta"], "count": [2, 3]})
    original.to_excel(destination, index=False, engine="openpyxl")
    restored = pandas.read_excel(destination, engine="openpyxl")
    pandas.testing.assert_frame_equal(original, restored)


def check_tfidf() -> None:
    extraction = load_dependency("sklearn.feature_extraction.text")
    vectorizer = extraction.TfidfVectorizer()
    matrix = vectorizer.fit_transform(["alpha beta document", "beta gamma document"])
    require(matrix.shape == (2, 4) and matrix.nnz == 6, "tfidf_mismatch")


def check_png(workspace: Path) -> None:
    image_module = load_dependency("PIL.Image")
    destination = workspace / "synthetic.png"
    with image_module.new("RGB", (3, 2), (12, 34, 56)) as image:
        image.save(destination, format="PNG")
    with image_module.open(destination) as image:
        image.load()
        require(image.size == (3, 2) and image.getpixel((1, 1)) == (12, 34, 56), "png_mismatch")


def verify_documents(workspace: Path, checks: Checks) -> None:
    with isolated_environment(workspace):
        record_check(checks, "pymupdf_roundtrip", lambda: check_pdf(workspace))
        record_check(checks, "pypdf_read", lambda: check_pypdf(workspace))
        record_check(checks, "docx_roundtrip", lambda: check_docx(workspace))
        record_check(checks, "xlsx_roundtrip", lambda: check_xlsx(workspace))
        record_check(checks, "tfidf", check_tfidf)
        if package_version("Pillow") is None:
            checks["png_roundtrip"] = {"status": "skipped", "reason": "optional_pillow_missing"}
        else:
            record_check(checks, "png_roundtrip", lambda: check_png(workspace))


def check_audio(workspace: Path) -> None:
    destination = workspace / "synthetic.wav"
    run_binary("ffmpeg", [
        "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=8000:duration=0.1",
        "-ac", "1", "-c:a", "pcm_s16le", str(destination),
    ], workspace)
    with wave.open(str(destination), "rb") as audio:
        require(audio.getnchannels() == 1 and audio.getframerate() == 8000, "wav_format_mismatch")
        require(0 < audio.getnframes() <= 1600, "wav_duration_mismatch")
    completed = run_binary("ffprobe", [
        "-v", "error", "-select_streams", "a:0", "-show_entries",
        "stream=codec_name,sample_rate,channels", "-of", "json", str(destination),
    ], workspace)
    streams = json.loads(completed.stdout)["streams"]
    require(len(streams) == 1, "ffprobe_stream_mismatch")
    require(streams[0]["codec_name"] == "pcm_s16le" and streams[0]["sample_rate"] == "8000"
            and streams[0]["channels"] == 1, "ffprobe_format_mismatch")


def check_svg(workspace: Path) -> None:
    source = workspace / "synthetic.svg"
    destination = workspace / "rendered.png"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
        '<rect width="8" height="8" fill="blue"/></svg>', encoding="utf-8",
    )
    run_binary("inkscape", [
        "--batch-process", "--export-type=png", f"--export-filename={destination}", str(source),
    ], workspace)
    with destination.open("rb") as image:
        require(image.read(8) == b"\x89PNG\r\n\x1a\n", "svg_export_invalid")


def check_markdown(workspace: Path) -> None:
    source = workspace / "synthetic.md"
    destination = workspace / "synthetic.html"
    source.write_text("# Synthetic heading\n\nOffline paragraph.\n", encoding="utf-8")
    run_binary("pandoc", [
        "--from=markdown", "--to=html", "--output", str(destination), str(source),
    ], workspace)
    rendered = destination.read_text(encoding="utf-8")
    require("Synthetic heading</h1>" in rendered and "<p>Offline paragraph.</p>" in rendered,
            "markdown_export_mismatch")


def verify_media(workspace: Path, checks: Checks) -> None:
    record_check(checks, "ffmpeg_ffprobe", lambda: check_audio(workspace))
    record_check(checks, "inkscape_headless", lambda: check_svg(workspace))
    record_check(checks, "pandoc_html", lambda: check_markdown(workspace))


def check_training(workspace: Path) -> None:
    torch = load_dependency("torch")
    require(torch.version.cuda is None and torch.version.hip is None, "cpu_only_torch_required")
    previous_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(2)
        transformers = load_dependency("transformers")
        for dependency in ("peft", "trl", "datasets"):
            load_dependency(dependency)
        configuration = transformers.GPT2Config(
            vocab_size=32, n_positions=8, n_ctx=8, n_embd=16, n_layer=1, n_head=2,
            bos_token_id=1, eos_token_id=2, use_cache=False,
            attn_pdrop=0.0, embd_pdrop=0.0, resid_pdrop=0.0,
        )
        with torch.device("cpu"):
            model = transformers.GPT2LMHeadModel(configuration).to("cpu")
        model.train()
        require(all(parameter.device.type == "cpu" for parameter in model.parameters()), "non_cpu_parameter")
        tokens = torch.tensor([[1, 3, 4, 5, 2]], dtype=torch.long, device="cpu")
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        before = model.transformer.wte.weight.detach().clone()
        optimizer.zero_grad(set_to_none=True)
        loss = model(input_ids=tokens, labels=tokens).loss
        require(bool(torch.isfinite(loss).item()), "nonfinite_loss")
        loss.backward()
        gradients = [parameter.grad for parameter in model.parameters() if parameter.grad is not None]
        require(bool(gradients) and all(bool(torch.isfinite(gradient).all().item()) for gradient in gradients),
                "invalid_gradients")
        optimizer.step()
        require(not torch.equal(before, model.transformer.wte.weight.detach()), "optimizer_did_not_update")
        destination = workspace / "tiny-cpu-state.pt"
        torch.save(model.state_dict(), destination)
        restored = torch.load(destination, map_location="cpu", weights_only=True)
        model.load_state_dict(restored, strict=True)
        require(destination.is_file() and destination.stat().st_size > 0, "checkpoint_missing")
    finally:
        torch.set_num_threads(previous_threads)


def verify_training(workspace: Path, checks: Checks) -> None:
    with isolated_environment(workspace):
        record_check(checks, "cpu_backprop_checkpoint", lambda: check_training(workspace))


def kernel_arguments(specification) -> list[str]:
    arguments = list(specification.argv)
    require(bool(arguments) and isinstance(arguments[0], str), "kernel_interpreter_mismatch")
    interpreter = arguments[0]
    require(Path(interpreter).is_absolute(), "kernel_interpreter_mismatch")
    require(os.path.normcase(os.path.abspath(interpreter)) == os.path.normcase(os.path.abspath(sys.executable)),
            "kernel_interpreter_mismatch")
    remaining = arguments[1:]
    if remaining[:1] == ["-Xfrozen_modules=off"]:
        remaining = remaining[1:]
    elif remaining[:2] == ["-X", "frozen_modules=off"]:
        remaining = remaining[2:]
    require(remaining == ["-m", "ipykernel_launcher", "-f", "{connection_file}"], "unsafe_kernel_arguments")
    return [sys.executable, "-I", "-m", "ipykernel_launcher", "-f", "{connection_file}"]


def check_notebooks(workspace: Path, checks: Checks) -> None:
    load_dependency("ipykernel")
    load_dependency("jupyterlab")
    jupyter_client = load_dependency("jupyter_client")
    kernelspec = load_dependency("jupyter_client.kernelspec")
    try:
        registered = kernelspec.KernelSpecManager().get_kernel_spec(KERNEL_NAME)
    except kernelspec.NoSuchKernel:
        raise VerificationFailure("kernel_not_registered") from None
    arguments = kernel_arguments(registered)
    checks["kernel_registration"] = {"status": "ok"}
    private_registry = workspace / "kernels"
    private_kernel = private_registry / KERNEL_NAME
    private_kernel.mkdir(parents=True)
    (private_kernel / "kernel.json").write_text(json.dumps({
        "argv": arguments, "display_name": KERNEL_NAME, "language": "python", "env": {},
    }), encoding="utf-8")
    with isolated_environment(workspace):
        registry = kernelspec.KernelSpecManager(kernel_dirs=[str(private_registry)], ensure_native_kernel=False)
        manager = jupyter_client.KernelManager(
            kernel_name=KERNEL_NAME, kernel_spec_manager=registry,
            ip="127.0.0.1", transport="tcp", connection_file=str(workspace / "connection.json"),
        )
        client = None
        answers = []

        def collect_output(message: dict) -> None:
            if message.get("header", {}).get("msg_type") == "execute_result":
                answers.append(message.get("content", {}).get("data", {}).get("text/plain"))

        try:
            manager.start_kernel(cwd=str(workspace), env=child_environment(workspace))
            client = manager.client()
            client.start_channels()
            client.wait_for_ready(timeout=30)
            reply = client.execute_interactive(
                "6 * 7", timeout=30, output_hook=collect_output, allow_stdin=False, stop_on_error=True,
            )
            require(reply.get("content", {}).get("status") == "ok" and answers == ["42"], "kernel_result_mismatch")
        finally:
            try:
                manager.shutdown_kernel(now=True)
            finally:
                try:
                    if client is not None:
                        client.stop_channels()
                finally:
                    manager.cleanup_resources()


def verify_notebooks(workspace: Path, checks: Checks) -> None:
    record_check(checks, "kernel_execution", lambda: check_notebooks(workspace, checks))


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description="Verifica flujos sintéticos locales sin descargas ni documentos de producción.",
                                allow_abbrev=False)
    for profile in PROFILE_PACKAGES:
        parser.add_argument(f"--{profile}", action="store_true", help=f"Verificar el perfil {profile}.")
    parser.add_argument("--all", action="store_true", help="Verificar todos los perfiles.")
    return parser


def main(arguments: list[str] | None = None) -> int:
    versions: dict[str, str | None] = {"python": platform.python_version()}
    checks: dict[str, Checks] = {}
    report = {"versions": versions, "checks": checks}
    try:
        options = build_parser().parse_args(arguments)
    except ArgumentFailure:
        checks["cli"] = {"arguments": {"status": "failed", "reason": "invalid_arguments_use_help"}}
        print(json.dumps(report, ensure_ascii=True))
        return 1
    selected = [profile for profile in PROFILE_PACKAGES if options.all or getattr(options, profile)]
    if not selected:
        checks["cli"] = {"arguments": {
            "status": "failed", "reason": "select_at_least_one_profile_or_all_use_help",
        }}
        print(json.dumps(report, ensure_ascii=True))
        return 1
    verifiers = {
        "documents": verify_documents, "media": verify_media,
        "training": verify_training, "notebooks": verify_notebooks,
    }
    with muted_output():
        for profile in selected:
            profile_checks: Checks = {}
            checks[profile] = profile_checks
            try:
                for distribution in PROFILE_PACKAGES[profile]:
                    versions[distribution] = package_version(distribution)
                with TemporaryDirectory(prefix=f"aulatex-verify-{profile}-") as temporary:
                    verifiers[profile](Path(temporary), profile_checks)
                require(bool(profile_checks), "no_checks_executed")
            except Exception:
                profile_checks["profile"] = {"status": "failed", "reason": "profile_failed"}
    print(json.dumps(report, ensure_ascii=True))
    return int(any(check["status"] == "failed" for profile_checks in checks.values() for check in profile_checks.values()))


if __name__ == "__main__":
    raise SystemExit(main())