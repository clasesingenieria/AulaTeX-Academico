"""Pruebas locales de la bóveda con datos exclusivamente ficticios."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Cargar solo el servicio: __init__ importa otros componentes de la aplicación
# que no deben acceder a configuración ni secretos durante la colección.
_SPEC = importlib.util.spec_from_file_location(
    "platform_credentials_under_test",
    Path(__file__).resolve().parents[1] / "platform_credentials.py",
)
assert _SPEC is not None and _SPEC.loader is not None
credentials = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(credentials)


PIN = "pin-ficticio-exclusivo-de-pruebas-1234"
NEW_PIN = "otro-pin-ficticio-exclusivo-de-pruebas-5678"
OPERATIONS = ("list", "get", "save", "delete", "rotate")


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """No copiar os.environ: ni siquiera un fallo debe mostrar secretos reales."""
    monkeypatch.setattr(os, "environ", {})


@pytest.fixture
def vault(tmp_path):
    return credentials.PlatformCredentialVault(tmp_path / "local" / "test.vault.json")


@pytest.fixture
def account():
    return {
        "institution": "Institución Ficticia Alfa",
        "platform": "Campus Ficticio Uno",
        "url": "https://campus-alfa.example.invalid/acceso",
        "username": "usuario-ficticio-alfa",
        "password": "password-ficticio-alfa-ñ-1234",
    }


@pytest.fixture
def saved(vault, account):
    return vault.save(PIN, **account)


def envelope(vault):
    return json.loads(vault.path.read_bytes())


def independent_cipher(document, pin=PIN):
    """Verificar el formato real sin utilizar el derivador privado del servicio."""
    salt = base64.b64decode(document["salt"], validate=True)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        iterations=document["iterations"],
    )
    return Fernet(base64.urlsafe_b64encode(kdf.derive(pin.encode("utf-8"))))


def decrypted_records(document, pin=PIN):
    return json.loads(independent_cipher(document, pin).decrypt(document["token"].encode("ascii")))


def assert_clean(vault):
    assert not vault.path.with_name(vault.path.name + ".lock").exists()
    assert not list(vault.path.parent.glob(vault.path.name + ".*.tmp"))


def assert_no_plaintext(raw, record):
    for value in record.values():
        assert value.encode("utf-8") not in raw
        assert json.dumps(value, ensure_ascii=True).encode("ascii") not in raw
    for key in record:
        assert ('"' + key + '"').encode("ascii") not in raw
    assert PIN.encode("utf-8") not in raw
    assert NEW_PIN.encode("utf-8") not in raw


def operate(vault, operation, pin, account, account_id):
    if operation == "list":
        return vault.list_accounts(pin)
    if operation == "get":
        return vault.get_credentials(pin, account_id)
    if operation == "save":
        return vault.save(pin, account_id=account_id, **account)
    if operation == "delete":
        return vault.delete(pin, account_id)
    if operation == "rotate":
        return vault.rotate_pin(pin, NEW_PIN)
    raise AssertionError("Operación de prueba desconocida")


def test_crud_multiple_institutions_platforms_and_accounts(vault, account):
    entries = [
        account,
        {**account, "username": "usuario-ficticio-beta", "password": "password-ficticio-beta"},
        {**account, "platform": "Biblioteca Ficticia Dos"},
        {**account, "institution": "Institución Ficticia Beta"},
    ]
    ids = [vault.save(PIN, **entry) for entry in entries]
    assert len(set(ids)) == len(entries)
    reopened = credentials.PlatformCredentialVault(vault.path)
    assert {item["id"] for item in reopened.list_accounts(PIN)} == set(ids)
    for account_id, entry in zip(ids, entries):
        assert reopened.get_credentials(PIN, account_id) == {"id": account_id, **entry}

    edited = {
        "institution": "Institución Ficticia Gamma",
        "platform": "Portal Ficticio Tres",
        "url": "https://gamma.example.invalid/portal",
        "username": "usuario-ficticio-gamma",
        "password": "password-ficticio-gamma",
    }
    assert reopened.save(PIN, account_id=ids[0], **edited) == ids[0]
    assert reopened.get_credentials(PIN, ids[0]) == {"id": ids[0], **edited}
    for account_id, entry in zip(ids[1:], entries[1:]):
        assert reopened.get_credentials(PIN, account_id) == {"id": account_id, **entry}
    reopened.delete(PIN, ids[1])
    assert {item["id"] for item in reopened.list_accounts(PIN)} == set(ids) - {ids[1]}
    with pytest.raises(credentials.VaultError, match="ya no existe"):
        reopened.get_credentials(PIN, ids[1])
    for account_id in (ids[0], ids[2], ids[3]):
        reopened.delete(PIN, account_id)
    assert reopened.list_accounts(PIN) == []
    assert vault.path.is_file()
    assert_clean(vault)


def test_listing_exposes_only_public_fields(vault, account, saved):
    second = {**account, "username": "otro-usuario-ficticio", "password": "otra-password-ficticia"}
    second_id = vault.save(PIN, **second)
    listing = vault.list_accounts(PIN)
    assert listing == [
        {"id": account_id, **{key: entry[key] for key in ("institution", "platform", "url")}}
        for account_id, entry in ((saved, account), (second_id, second))
    ]
    serialized = json.dumps(listing, ensure_ascii=False)
    for entry in (account, second):
        assert entry["username"] not in serialized
        assert entry["password"] not in serialized
    assert "username" not in serialized
    assert "password" not in serialized


def test_all_metadata_and_secrets_are_encrypted(vault, account, saved):
    raw = vault.path.read_bytes()
    record = {"id": saved, **account}
    assert_no_plaintext(raw, record)
    document = json.loads(raw)
    assert set(document) == {"version", "kdf", "iterations", "salt", "token"}
    assert document["version"] == 1
    assert document["kdf"] == "pbkdf2-sha256"
    assert document["iterations"] == credentials.ITERATIONS == 600_000
    assert len(base64.b64decode(document["salt"], validate=True)) == 16
    assert decrypted_records(document) == [record]
    assert_clean(vault)


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("bad_pin", [None, "", " \t\n", 0, "pin-ficticio-equivocado"])
def test_missing_or_wrong_pin_never_changes_existing_file(vault, account, saved, operation, bad_pin):
    before = vault.path.read_bytes()
    with pytest.raises(credentials.VaultError):
        operate(vault, operation, bad_pin, account, saved)
    assert vault.path.read_bytes() == before
    assert_clean(vault)


@pytest.mark.parametrize("bad_pin", [None, "", " \t\n"])
def test_missing_pin_does_not_create_vault(vault, account, bad_pin):
    with pytest.raises(credentials.VaultError, match="AULATEX_MASTER_PIN"):
        vault.save(bad_pin, **account)
    assert not vault.path.exists()
    assert_clean(vault)


@pytest.mark.parametrize("new_pin", [None, "", " \t\n"])
def test_missing_new_pin_does_not_change_vault(vault, saved, new_pin):
    before = vault.path.read_bytes()
    with pytest.raises(credentials.VaultError, match="AULATEX_MASTER_PIN"):
        vault.rotate_pin(PIN, new_pin)
    assert vault.path.read_bytes() == before
    assert vault.get_credentials(PIN, saved)["id"] == saved
    assert_clean(vault)


@pytest.mark.parametrize("operation", ("list", "save", "delete", "rotate"))
@pytest.mark.parametrize("damage", [
    "invalid-json", "truncated", "missing-token", "invalid-token", "changed-token",
    "invalid-salt", "short-salt", "changed-salt", "version", "iterations", "kdf",
])
def test_corrupt_or_altered_envelope_is_rejected_without_writing(vault, account, saved, operation, damage):
    document = envelope(vault)
    if damage == "invalid-json":
        corrupted = b"not a vault document"
    elif damage == "truncated":
        corrupted = vault.path.read_bytes()[:32]
    else:
        if damage == "missing-token":
            del document["token"]
        elif damage == "invalid-token":
            document["token"] = "not-a-fernet-token"
        elif damage == "changed-token":
            token = bytearray(base64.urlsafe_b64decode(document["token"]))
            token[-1] ^= 1
            document["token"] = base64.urlsafe_b64encode(token).decode("ascii")
        elif damage == "invalid-salt":
            document["salt"] = "%%%invalid-base64%%%"
        elif damage == "short-salt":
            document["salt"] = base64.b64encode(b"short").decode("ascii")
        elif damage == "changed-salt":
            salt = bytearray(base64.b64decode(document["salt"]))
            salt[0] ^= 1
            document["salt"] = base64.b64encode(salt).decode("ascii")
        elif damage == "version":
            document["version"] = 2
        elif damage == "iterations":
            document["iterations"] += 1
        elif damage == "kdf":
            document["kdf"] = "unsupported-kdf"
        corrupted = json.dumps(document).encode("utf-8")
    vault.path.write_bytes(corrupted)
    with pytest.raises(credentials.VaultError, match="PIN incorrecto o bóveda dañada/incompatible"):
        operate(vault, operation, PIN, account, saved)
    assert vault.path.read_bytes() == corrupted
    assert_clean(vault)


@pytest.mark.parametrize("damage", ["json", "not-list", "not-record", "missing-field", "duplicate-id", "url"])
def test_authenticated_but_invalid_payload_is_rejected(vault, account, saved, damage):
    document = envelope(vault)
    record = {"id": saved, **account}
    if damage == "json":
        plaintext = b"not json"
    else:
        payload = [record]
        if damage == "not-list":
            payload = {"records": [record]}
        elif damage == "not-record":
            payload = ["not a record"]
        elif damage == "missing-field":
            del record["password"]
        elif damage == "duplicate-id":
            payload.append({**record, "username": "otro-usuario-ficticio"})
        elif damage == "url":
            record["url"] = "http://example.invalid"
        plaintext = json.dumps(payload).encode("utf-8")
    document["token"] = independent_cipher(document).encrypt(plaintext).decode("ascii")
    corrupted = json.dumps(document).encode("utf-8")
    vault.path.write_bytes(corrupted)
    for operation in ("list", "save"):
        with pytest.raises(credentials.VaultError, match="dañada/incompatible"):
            operate(vault, operation, PIN, account, saved)
        assert vault.path.read_bytes() == corrupted
        assert_clean(vault)


@pytest.mark.parametrize("url", [
    "http://example.invalid", "ftp://example.invalid", "javascript:alert(1)",
    "//example.invalid", "https://", "https:///missing-host",
    "https://usuario:password@example.invalid", "https://usuario@example.invalid",
    "https://example.invalid:bad", "https://example.invalid:99999",
    "https://exam ple.invalid", "https://example.invalid/path with space",
    "https://example.invalid/path\nfragment", "https://example.invalid/path\tfragment",
    "https://[invalid-ipv6]/", "",
])
def test_rejected_url_does_not_modify_file(vault, account, saved, url):
    before = vault.path.read_bytes()
    with pytest.raises(credentials.VaultError):
        vault.save(PIN, account_id=saved, **{**account, "url": url})
    assert vault.path.read_bytes() == before
    assert_clean(vault)


@pytest.mark.parametrize("empty_fields", [("username",), ("password",), ("username", "password")])
def test_edit_preserves_each_empty_secret(vault, account, saved, empty_fields):
    edited = {
        **account, "platform": "Campus Ficticio Editado",
        "username": "usuario-ficticio-nuevo", "password": "password-ficticio-nuevo",
    }
    for field in empty_fields:
        edited[field] = ""
    assert vault.save(PIN, account_id=saved, **edited) == saved
    expected = {**edited, **{field: account[field] for field in empty_fields}}
    assert vault.get_credentials(PIN, saved) == {"id": saved, **expected}
    assert len(vault.list_accounts(PIN)) == 1
    assert_clean(vault)


@pytest.mark.parametrize("field", ["username", "password"])
def test_new_account_requires_nonempty_secrets(vault, account, field):
    with pytest.raises(credentials.VaultError, match=field):
        vault.save(PIN, **{**account, field: ""})
    assert not vault.path.exists()
    assert_clean(vault)


@pytest.mark.parametrize("editing", [False, True])
def test_duplicate_account_rejected_even_with_case_and_whitespace_changes(vault, account, saved, editing):
    account_id = None
    if editing:
        account_id = vault.save(PIN, **{**account, "username": "segundo-usuario-ficticio"})
    duplicate = {
        **account,
        "institution": "  " + account["institution"].upper() + "  ",
        "platform": "  " + account["platform"].upper() + "  ",
        "password": "password-ficticio-distinto-no-evita-duplicado",
    }
    before = vault.path.read_bytes()
    with pytest.raises(credentials.VaultError, match="Esta cuenta ya existe"):
        vault.save(PIN, account_id=account_id, **duplicate)
    assert vault.path.read_bytes() == before
    assert_clean(vault)


@pytest.mark.parametrize("operation", ["get", "save", "delete"])
def test_unknown_account_id_never_modifies_file(vault, account, saved, operation):
    before = vault.path.read_bytes()
    with pytest.raises(credentials.VaultError, match="ya no existe"):
        operate(vault, operation, PIN, account, "id-ficticio-inexistente")
    assert vault.path.read_bytes() == before
    assert_clean(vault)


def test_pin_rotation_preserves_all_records_and_changes_salt(vault, account, saved):
    second_id = vault.save(PIN, **{**account, "institution": "Otra Institución Ficticia"})
    before_records = [vault.get_credentials(PIN, account_id) for account_id in (saved, second_id)]
    before_envelope = envelope(vault)
    vault.rotate_pin(PIN, NEW_PIN)
    after_envelope = envelope(vault)
    assert after_envelope["salt"] != before_envelope["salt"]
    assert after_envelope["token"] != before_envelope["token"]
    assert len(base64.b64decode(after_envelope["salt"], validate=True)) == 16
    reopened = credentials.PlatformCredentialVault(vault.path)
    assert [reopened.get_credentials(NEW_PIN, account_id) for account_id in (saved, second_id)] == before_records
    assert decrypted_records(after_envelope, NEW_PIN) == before_records
    after = vault.path.read_bytes()
    with pytest.raises(credentials.VaultError, match="PIN incorrecto"):
        reopened.list_accounts(PIN)
    assert vault.path.read_bytes() == after
    assert_clean(vault)


@pytest.mark.parametrize("operation", ["save", "delete", "rotate"])
def test_replace_failure_keeps_original_and_cleans_temp_and_lock(vault, account, saved, monkeypatch, operation):
    before = vault.path.read_bytes()
    temporary_paths = []

    def fail_replace(source, destination):
        temporary = Path(source)
        temporary_paths.append(temporary)
        assert Path(destination) == vault.path
        assert temporary.parent == vault.path.parent
        assert temporary.suffix == ".tmp"
        assert vault.path.with_name(vault.path.name + ".lock").is_file()
        assert vault.path.read_bytes() == before
        assert_no_plaintext(temporary.read_bytes(), {"id": saved, **account})
        raise OSError("fallo ficticio al reemplazar")

    monkeypatch.setattr(credentials.os, "replace", fail_replace)
    with pytest.raises(credentials.VaultError, match="se conserva la versión anterior") as caught:
        operate(vault, operation, PIN, account, saved)
    assert "fallo ficticio" not in str(caught.value)
    assert len(temporary_paths) == 1
    assert not temporary_paths[0].exists()
    assert vault.path.read_bytes() == before
    assert vault.get_credentials(PIN, saved) == {"id": saved, **account}
    assert_clean(vault)


def test_replace_failure_on_first_save_leaves_no_files(vault, account, monkeypatch):
    calls = []

    def fail_replace(source, destination):
        calls.append(Path(source))
        assert Path(source).is_file()
        assert Path(destination) == vault.path
        raise OSError("fallo ficticio en primera escritura")

    monkeypatch.setattr(credentials.os, "replace", fail_replace)
    with pytest.raises(credentials.VaultError, match="No se pudo guardar"):
        vault.save(PIN, **account)
    assert len(calls) == 1
    assert not vault.path.exists()
    assert list(vault.path.parent.iterdir()) == []
    assert_clean(vault)


@pytest.mark.parametrize("operation", ["save", "delete", "rotate"])
def test_concurrent_writer_is_rejected_without_removing_owner_lock(vault, account, saved, operation):
    competitor = credentials.PlatformCredentialVault(vault.path)
    before = vault.path.read_bytes()
    lock = vault.path.with_name(vault.path.name + ".lock")
    # Solapar los escritores de forma determinista, sin sleeps ni hilos frágiles.
    with vault._writer():
        assert lock.is_file()
        with pytest.raises(credentials.VaultError, match="Bóveda ocupada"):
            operate(competitor, operation, PIN, account, saved)
        assert lock.is_file()
        assert vault.path.read_bytes() == before
        assert not list(vault.path.parent.glob(vault.path.name + ".*.tmp"))
    assert_clean(vault)
    assert competitor.save(PIN, account_id=saved, **account) == saved
    assert_clean(vault)


def test_identical_saves_produce_different_ciphertext_without_duplicates(vault, account, saved):
    first = envelope(vault)
    assert vault.save(PIN, account_id=saved, **account) == saved
    second = envelope(vault)
    assert first["salt"] == second["salt"]
    assert first["token"] != second["token"]
    assert decrypted_records(first) == decrypted_records(second) == [{"id": saved, **account}]
    assert len(vault.list_accounts(PIN)) == 1
    assert_clean(vault)