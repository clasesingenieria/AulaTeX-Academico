from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from scripts import secrets_local
from scripts.aulatex import config, llm_bridge, llm_setup
from scripts.aulatex.config import MODEL_ROUTER_ENGINE
from scripts.aulatex.llm_bridge import AulaTeXLLMConfig, validate_llm_response


MARKER = "AULATEX_VALIDACION_OK"
FAKE_KEY = "fake-api-key-for-tests-only"


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Ni secretos reales, ni salt real, ni red en estas pruebas."""
    env = tmp_path / "aulatex.env"
    env.write_text("# Configuración ficticia\n", encoding="utf-8")
    monkeypatch.setattr(os, "environ", {"AULATEX_ENV_PATH": str(env)})
    monkeypatch.setattr(secrets_local, "SECRET_SALT_PATH", tmp_path / "secret.salt")
    monkeypatch.setattr(secrets_local, "SECRET_KEY_PATH", tmp_path / "secret.key")
    monkeypatch.setattr(config, "_secrets_module", lambda: secrets_local)
    monkeypatch.setattr(llm_setup, "_secrets_module", lambda: secrets_local)
    monkeypatch.setattr(requests, "post", Mock(side_effect=AssertionError("Red real bloqueada")))
    monkeypatch.setattr(llm_setup.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(llm_setup.sys.stdout, "isatty", lambda: True)
    return env


@pytest.fixture
def candidate():
    return AulaTeXLLMConfig(
        engine_label=MODEL_ROUTER_ENGINE,
        base_url="https://example.openai.azure.com/openai/v1/chat/completions",
        api_key=FAKE_KEY, deployment="model-router",
    )


def response(text=MARKER, status=200):
    return SimpleNamespace(
        status_code=status,
        json=lambda: {"choices": [{"message": {"content": text}}]},
    )


def input_answers(monkeypatch, *answers):
    entries = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _: next(entries))


def secret_answers(monkeypatch, *answers):
    entries = iter(answers)
    monkeypatch.setattr(llm_setup.getpass, "getpass", lambda _: next(entries))


def write_current(path, *, key=FAKE_KEY):
    path.write_text(
        "MODEL_ROUTER_BASE_URL=https://old.openai.azure.com/openai/v1/chat/completions\n"
        "MODEL_ROUTER_CHAT_DEPLOYMENT=model-router\n"
        f"MODEL_ROUTER_API_KEY={key}\n",
        encoding="utf-8",
    )


def test_validation_honors_limits_no_fallback_or_redirects(candidate, monkeypatch):
    post = Mock(return_value=response())
    monkeypatch.setattr(requests, "post", post)
    result = validate_llm_response(config=candidate, max_tokens=32, timeout_seconds=7)
    assert result["ok"] and result["marker_found"]
    assert result["engine"] == MODEL_ROUTER_ENGINE
    assert FAKE_KEY not in json.dumps(result)
    assert MARKER not in json.dumps(result)
    assert post.call_count == 1
    assert post.call_args.kwargs["json"]["max_tokens"] == 32
    assert post.call_args.kwargs["timeout"] == 7
    assert post.call_args.kwargs["allow_redirects"] is False
    assert post.call_args.kwargs["headers"]["api-key"] == FAKE_KEY


@pytest.mark.parametrize("status", [301, 302, 400, 401, 403, 404, 429, 500])
def test_http_failure_is_sanitized_and_not_retried(candidate, monkeypatch, status):
    post = Mock(return_value=response(FAKE_KEY, status))
    monkeypatch.setattr(requests, "post", post)
    result = validate_llm_response(config=candidate)
    assert not result["ok"]
    assert f"HTTP {status}" in result["error"]
    assert FAKE_KEY not in json.dumps(result)
    assert post.call_count == 1


@pytest.mark.parametrize("text", ["", "OK", "prefijo " + MARKER, MARKER + " extra"])
def test_empty_or_unexpected_response_fails(candidate, monkeypatch, text):
    monkeypatch.setattr(requests, "post", Mock(return_value=response(text)))
    result = validate_llm_response(config=candidate)
    assert not result["ok"] and result["error"]


@pytest.mark.parametrize("error", [requests.Timeout(FAKE_KEY), requests.ConnectionError(FAKE_KEY), ValueError(FAKE_KEY)])
def test_exceptions_do_not_leak_details(candidate, monkeypatch, error):
    monkeypatch.setattr(requests, "post", Mock(side_effect=error))
    result = validate_llm_response(config=candidate)
    assert not result["ok"] and result["error"]
    assert FAKE_KEY not in json.dumps(result)


def test_invalid_json_fails_without_leaking(candidate, monkeypatch):
    reply = response()
    reply.json = Mock(side_effect=ValueError(FAKE_KEY))
    monkeypatch.setattr(requests, "post", Mock(return_value=reply))
    assert not validate_llm_response(config=candidate)["ok"]


@pytest.mark.parametrize("base", ["https://example.azure.com", "https://example.azure.com/openai/v1/"])
def test_endpoint_normalization(base):
    assert llm_setup.normalize_router_endpoint(base, "model-router") == "https://example.azure.com/openai/v1/chat/completions"


def test_legacy_url_uses_edited_deployment():
    endpoint = "https://example.azure.com/openai/deployments/old/chat/completions?api-version=2024-10-21"
    normalized = llm_setup.normalize_router_endpoint(endpoint, "new-router")
    assert "/deployments/new-router/" in normalized
    assert normalized.endswith("?api-version=2024-10-21")


@pytest.mark.parametrize("endpoint", [
    "http://example.com", "https://user:password@example.com", "https://example.com#fragment",
    "https://example.com?api-key=secret", "https://example.com:bad", "https://example .com",
    "https://example.com/unknown", "https://example.com\nINJECT=value",
])
def test_unsafe_endpoint_rejected(endpoint):
    with pytest.raises(llm_setup.ConfigurationError):
        llm_setup.normalize_router_endpoint(endpoint, "model-router")


def test_deployment_injection_rejected():
    with pytest.raises(llm_setup.ConfigurationError):
        llm_setup.normalize_router_endpoint("https://example.com", "router\nAPI_KEY=value")


def test_missing_config_no_network():
    result = validate_llm_response()
    assert not result["ok"]
    requests.post.assert_not_called()


def test_encrypted_key_is_not_reported_usable(isolated_environment):
    write_current(isolated_environment, key="enc:locked")
    status = next(item for item in config.credential_status() if item.engine == MODEL_ROUTER_ENGINE)
    assert not status.ok
    assert "MODEL_ROUTER_API_KEY" in status.missing
    assert not validate_llm_response()["ok"]
    requests.post.assert_not_called()


def test_valid_current_configuration_never_prompts_or_writes(isolated_environment, monkeypatch):
    write_current(isolated_environment)
    before = isolated_environment.read_bytes()
    monkeypatch.setattr(requests, "post", Mock(return_value=response()))
    prompt = Mock(side_effect=AssertionError("No debe pedir datos"))
    monkeypatch.setattr("builtins.input", prompt)
    result = llm_setup.configure_model_router()
    assert result["ok"]
    assert isolated_environment.read_bytes() == before
    prompt.assert_not_called()


@pytest.mark.parametrize("non_interactive,tty", [(True, True), (False, False)])
def test_unattended_failure_never_prompts(isolated_environment, monkeypatch, non_interactive, tty):
    before = isolated_environment.read_bytes()
    monkeypatch.setattr(llm_setup.sys.stdin, "isatty", lambda: tty)
    prompt = Mock(side_effect=AssertionError("No debe pedir datos"))
    monkeypatch.setattr("builtins.input", prompt)
    assert not llm_setup.configure_model_router(non_interactive=non_interactive)["ok"]
    assert isolated_environment.read_bytes() == before
    prompt.assert_not_called()


def test_failed_validation_manual_repair_and_encrypted_save(isolated_environment, monkeypatch, capsys):
    # capsys sustituye stdout al comenzar la fase de ejecución del test.
    monkeypatch.setattr(llm_setup.sys.stdout, "isatty", lambda: True)
    write_current(isolated_environment, key="old-key")
    before = isolated_environment.read_bytes()
    input_answers(monkeypatch, "1", "https://new.openai.azure.com", "new-router")
    secret_answers(monkeypatch, FAKE_KEY, "test-pin")
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        # La clave candidata nunca se escribe antes de validarse.
        assert isolated_environment.read_bytes() == before
        if len(calls) == 1:
            return response(status=401)
        assert "new.openai.azure.com" in url
        assert kwargs["headers"]["api-key"] == FAKE_KEY
        assert kwargs["json"]["model"] == "new-router"
        return response()

    monkeypatch.setattr(requests, "post", post)
    result = llm_setup.configure_model_router()
    assert result["ok"] and result["configured"]
    assert len(calls) == 2
    stored = isolated_environment.read_text(encoding="utf-8")
    assert "MODEL_ROUTER_API_KEY=enc:" in stored
    assert FAKE_KEY not in stored
    assert "test-pin" not in stored
    assert isolated_environment.stat().st_mode & 0o777 == 0o600
    assert os.environ["MODEL_ROUTER_API_KEY"] == FAKE_KEY
    assert FAKE_KEY not in capsys.readouterr().out


def test_failed_candidate_leaves_configuration_unchanged(isolated_environment, monkeypatch):
    before = isolated_environment.read_bytes()
    input_answers(monkeypatch, "1", "https://example.azure.com", "", "0")
    secret_answers(monkeypatch, FAKE_KEY)
    monkeypatch.setattr(requests, "post", Mock(return_value=response(status=403)))
    result = llm_setup.configure_model_router()
    assert not result["ok"]
    assert isolated_environment.read_bytes() == before
    assert not secrets_local.SECRET_SALT_PATH.exists()


def test_pin_unlock_revalidates_existing_credentials(isolated_environment, monkeypatch):
    fernet = secrets_local.fernet_from_pin("existing-pin", create_salt=True)
    write_current(isolated_environment, key="enc:" + fernet.encrypt(FAKE_KEY.encode()).decode())
    before = isolated_environment.read_bytes()
    input_answers(monkeypatch, "2")
    secret_answers(monkeypatch, "existing-pin")
    monkeypatch.setattr(requests, "post", Mock(return_value=response()))
    assert llm_setup.configure_model_router()["ok"]
    assert isolated_environment.read_bytes() == before
    assert requests.post.call_count == 1


def test_wrong_pin_cannot_recipher_existing_secrets(isolated_environment, candidate, monkeypatch):
    fernet = secrets_local.fernet_from_pin("existing-pin", create_salt=True)
    write_current(isolated_environment, key="enc:" + fernet.encrypt(b"old-key").decode())
    with isolated_environment.open("a", encoding="utf-8") as stream:
        stream.write("OTHER_API_KEY=enc:" + fernet.encrypt(b"preserved-key").decode() + "\n")
    before = isolated_environment.read_bytes()
    salt = secrets_local.SECRET_SALT_PATH.read_bytes()
    secret_answers(monkeypatch, "wrong-pin")
    with pytest.raises(llm_setup.ConfigurationError, match="PIN"):
        llm_setup._save_candidate(candidate, isolated_environment)
    assert isolated_environment.read_bytes() == before
    assert secrets_local.SECRET_SALT_PATH.read_bytes() == salt


def test_missing_salt_is_not_replaced(isolated_environment, candidate, monkeypatch):
    write_current(isolated_environment, key="enc:existing-token")
    with isolated_environment.open("a", encoding="utf-8") as stream:
        stream.write("OTHER_API_KEY=enc:preserved-token\n")
    before = isolated_environment.read_bytes()
    secret_answers(monkeypatch, "new-pin")
    with pytest.raises(llm_setup.ConfigurationError):
        llm_setup._save_candidate(candidate, isolated_environment)
    assert not secrets_local.SECRET_SALT_PATH.exists()
    assert isolated_environment.read_bytes() == before


def test_duplicate_entries_replaced_and_other_lines_preserved(isolated_environment, candidate, monkeypatch):
    isolated_environment.write_text(
        "# Keep comment\nOTHER_SETTING=preserved\n"
        "export MODEL_ROUTER_API_KEY=old\nMODEL_ROUTER_API_KEY=another-old\n",
        encoding="utf-8",
    )
    secret_answers(monkeypatch, "test-pin")
    llm_setup._save_candidate(candidate, isolated_environment)
    stored = isolated_environment.read_text()
    assert stored.count("MODEL_ROUTER_API_KEY=") == 1
    assert "# Keep comment\nOTHER_SETTING=preserved\n" in stored
    assert FAKE_KEY not in stored


def test_corrupt_replaced_key_does_not_block_valid_candidate(isolated_environment, candidate, monkeypatch):
    fernet = secrets_local.fernet_from_pin("existing-pin", create_salt=True)
    other_token = "enc:" + fernet.encrypt(b"preserved-key").decode()
    isolated_environment.write_text(
        f"OTHER_API_KEY={other_token}\n"
        "MODEL_ROUTER_API_KEY=enc:damaged\nMODEL_ROUTER_API_KEY=enc:obsolete-duplicate\n",
        encoding="utf-8",
    )
    secret_answers(monkeypatch, "existing-pin")
    llm_setup._save_candidate(candidate, isolated_environment)
    stored = isolated_environment.read_text()
    assert f"OTHER_API_KEY={other_token}" in stored
    assert stored.count("MODEL_ROUTER_API_KEY=") == 1
    assert os.environ["MODEL_ROUTER_API_KEY"] == FAKE_KEY
    assert os.environ["OTHER_API_KEY"] == "preserved-key"


def test_edit_during_pin_entry_is_preserved(isolated_environment, candidate, monkeypatch):
    concurrent = "# Edición concurrente\nOTHER_SETTING=new-value\n"

    def pin_prompt(_):
        isolated_environment.write_text(concurrent, encoding="utf-8")
        return "test-pin"

    monkeypatch.setattr(llm_setup.getpass, "getpass", pin_prompt)
    with pytest.raises(llm_setup.ConfigurationError, match="cambió"):
        llm_setup._save_candidate(candidate, isolated_environment)
    assert isolated_environment.read_text() == concurrent
    assert set(path.name for path in isolated_environment.parent.iterdir()) == {"aulatex.env", "secret.salt"}


def test_atomic_write_failure_preserves_original(isolated_environment, candidate, monkeypatch):
    before = isolated_environment.read_bytes()
    secret_answers(monkeypatch, "test-pin")

    def fail_replace(source, target):
        assert FAKE_KEY not in Path(source).read_text()
        assert Path(source).stat().st_mode & 0o777 == 0o600
        raise OSError("Simulated write failure")

    monkeypatch.setattr(llm_setup.os, "replace", fail_replace)
    with pytest.raises(OSError):
        llm_setup._save_candidate(candidate, isolated_environment)
    assert isolated_environment.read_bytes() == before
    assert set(path.name for path in isolated_environment.parent.iterdir()) == {"aulatex.env", "secret.salt"}


def test_getpass_never_falls_back_to_echo(monkeypatch):
    import warnings

    def unsafe_getpass(_):
        warnings.warn("Echo might be enabled", llm_setup.getpass.GetPassWarning)
        pytest.fail("No debe leer un secreto con eco")

    monkeypatch.setattr(llm_setup.getpass, "getpass", unsafe_getpass)
    with pytest.raises(llm_setup.ConfigurationError, match="entrada oculta"):
        llm_setup._read_secret("PIN: ")


def test_retry_then_success(isolated_environment, monkeypatch):
    write_current(isolated_environment)
    input_answers(monkeypatch, "3")
    post = Mock(side_effect=[response(status=429), response()])
    monkeypatch.setattr(requests, "post", post)
    assert llm_setup.configure_model_router()["ok"]
    assert post.call_count == 2


def test_keyboard_interrupt_cancels_without_writes(isolated_environment, monkeypatch):
    before = isolated_environment.read_bytes()
    monkeypatch.setattr("builtins.input", Mock(side_effect=KeyboardInterrupt))
    result = llm_setup.configure_model_router()
    assert not result["ok"] and "cancelada" in result["error"]
    assert isolated_environment.read_bytes() == before


def test_cli_validate_defaults_to_router_and_returns_json_failure(capsys):
    from scripts.aulatex.cli import main

    with pytest.raises(SystemExit) as error:
        main(["llm-validate"])
    assert error.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["engine"] == MODEL_ROUTER_ENGINE
    assert not result["ok"]


def test_cli_config_non_interactive_success(isolated_environment, monkeypatch, capsys):
    from scripts.aulatex.cli import main

    write_current(isolated_environment)
    monkeypatch.setattr(requests, "post", Mock(return_value=response()))
    main(["llm-config", "--non-interactive"])
    assert json.loads(capsys.readouterr().out)["ok"]


def test_cli_validate_repair_flag(monkeypatch, capsys):
    from scripts.aulatex.cli import main

    repair = Mock(return_value={"ok": True})
    monkeypatch.setattr(llm_setup, "configure_model_router", repair)
    main(["llm-validate", "--configure-on-failure"])
    repair.assert_called_once()
    assert json.loads(capsys.readouterr().out)["ok"]


def test_cli_rejects_repair_of_non_router_engine():
    from scripts.aulatex.cli import main

    with pytest.raises(SystemExit) as error:
        main(["llm-validate", "--engine", "Codex", "--configure-on-failure"])
    assert error.value.code == 2