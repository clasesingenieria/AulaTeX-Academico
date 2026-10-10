from __future__ import annotations

import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.aulatex.activity_observer import ActivityObservationRequest, ActivityObserver
from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

ROOT = PROJECT_ROOT / "UnADM" / "licenciatura-en-derecho-unadm"
HOST = "aulavirtual.unadmexico.mx"
COURSES = {
    3432: "teoria-del-estado-y-constitucion",
    3482: "derecho-penal-especial-mexicano",
    3441: "antecedentes-de-los-derechos-humanos",
}
BOOKS = {
    "teoria-del-estado-y-constitucion": (
        "Eduardo Garcia Maynez/Introduccion al estudio del Derecho (39)/*.pdf",
        "Hans Kelsen/Teoria pura del derecho (59)/*.pdf",
        "Ignacio Campoy Cervera/En defensa del estado de derecho_ de (57)/*.pdf",
        "Camara de Diputados del H. Congreso/Constitucion Politica de los Estados (79)/*.pdf",
    ),
    "derecho-penal-especial-mexicano": (
        "Manuel Atienza/Curso de argumentacion juridica (6)/*.pdf",
        "Eduardo Garcia Maynez/Introduccion al estudio del Derecho (39)/*.pdf",
    ),
    "antecedentes-de-los-derechos-humanos": (
        "Ana Maria Ibarra Olguin/Curso de derechos humanos (68)/*.pdf",
        "Ricardo Rabinovich Berkman/_Como se hicieron los derechos human (62)/*.pdf",
        "Luis Manuel Marcano Salazar/Derechos humanos, teorias y doctrina (64)/*.pdf",
        "Emilio Alvarez Icaza Longoria/Los derechos humanos en Mexico (61)/*.pdf",
        "Camara de Diputados del H. Congreso/Constitucion Politica de los Estados (79)/*.pdf",
    ),
}


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def copy_books() -> None:
    library = Path.home() / "Documents" / "Libros" / "Derecho"
    for slug, patterns in BOOKS.items():
        destination = ROOT / f"{slug}-lde" / f"referencias-{slug}" / f"libros-{slug}"
        destination.mkdir(parents=True, exist_ok=True)
        records = []
        for pattern in patterns:
            matches = list(library.glob(pattern))
            if len(matches) != 1:
                raise RuntimeError(f"Seleccion bibliografica ambigua o ausente: {pattern}")
            source = matches[0]
            target = destination / source.name
            source_hash = digest(source)
            if target.exists() and digest(target) != source_hash:
                raise RuntimeError(f"No se sobrescribira una copia diferente: {target.name}")
            if not target.exists():
                shutil.copy2(source, target)
            if digest(target) != source_hash:
                raise RuntimeError(f"Copia no integra: {target.name}")
            records.append({"origen_relativo_biblioteca": source.relative_to(library).as_posix(),
                            "archivo": target.name, "sha256": source_hash,
                            "estado": "disponible para consulta; no acredita lectura ni cita",
                            "vigencia_normativa": "comprobar edicion antes de usar"})
        save_json(destination / "inventario-libros.json", records)
        print(f"{slug}: {len(records)} copias verificadas")


def platform_snapshot() -> None:
    from playwright.sync_api import sync_playwright

    load_aulatex_env()
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
    accounts = [account for account in vault.list_accounts(pin)
                if account["institution"].casefold() == "unadm"
                and urlsplit(account["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("Se requiere una unica cuenta UnADM para el sitio autorizado.")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path)
        del credentials
        for course_id, slug in COURSES.items():
            page.goto(f"https://{HOST}/course/view.php?id={course_id}", wait_until="domcontentloaded")
            links = page.locator('.course-content a[href*="/mod/"]').evaluate_all(
                "items => items.map(item => ({title: item.innerText, url: item.href}))")
            links = list({link["url"]: link for link in links
                          if urlsplit(link["url"]).hostname == HOST}.values())
            evidence = ROOT / f"{slug}-lde" / f"referencias-{slug}" / "auditoria-semana-2-2026-10-09"
            snapshot = {"fecha": "2026-10-09", "curso": course_id,
                        "solo_lectura": True, "enlaces": links, "actividades": []}
            for link in links:
                if course_id == 3441 and re.search(r"Cuadernillo|Presentaci.n de Clase", link["title"], re.I):
                    response = context.request.get(link["url"])
                    payload = response.body()
                    signature = payload[:4]
                    extension = ".pdf" if signature == b"%PDF" else ""
                    if signature[:2] == b"PK":
                        with zipfile.ZipFile(BytesIO(payload)) as archive:
                            names = archive.namelist()
                            extension = ".pptx" if "ppt/presentation.xml" in names else ".docx" if "word/document.xml" in names else ""
                    if not response.ok or not extension:
                        raise RuntimeError("No se pudo recuperar un material docente PDF/Office valido.")
                    module_id = urlsplit(link["url"]).query.split("=")[-1]
                    evidence.mkdir(parents=True, exist_ok=True)
                    target = evidence / f"material-docente-{module_id}{extension}"
                    target.write_bytes(payload)
                    obsolete = evidence / f"material-docente-{module_id}.docx"
                    if extension == ".pptx" and obsolete.exists() and digest(obsolete) == digest(target):
                        obsolete.unlink()
                    link["archivo_local"] = target.name
                    link["sha256"] = digest(target)
                is_assignment = "/mod/assign/view.php" in link["url"]
                is_current_forum = (course_id == 3441 and "/mod/forum/view.php" in link["url"]
                                    and re.search(r"actividad\s*2", link["title"], re.I))
                if not (is_assignment or is_current_forum):
                    continue
                page.goto(link["url"], wait_until="domcontentloaded")
                fragments = page.locator(".activity-description, #intro, .activity-dates, .submissionstatustable")
                record = dict(link, texto="\n\n".join(fragments.all_inner_texts()), adjuntos=[])
                attachments = page.locator('#region-main a[href*="pluginfile.php"]').evaluate_all(
                    "items => items.map(item => ({title:item.innerText,url:item.href}))")
                for attachment in attachments:
                    parsed = urlsplit(attachment["url"])
                    if parsed.hostname != HOST or not unquote(parsed.path).lower().endswith(".docx"):
                        continue
                    response = context.request.get(attachment["url"])
                    if not response.ok or response.body()[:2] != b"PK":
                        raise RuntimeError("No se pudo recuperar el formato DOCX docente.")
                    name = Path(unquote(parsed.path)).name
                    evidence.mkdir(parents=True, exist_ok=True)
                    target = evidence / name
                    target.write_bytes(response.body())
                    record["adjuntos"].append({"archivo": name, "sha256": digest(target)})
                snapshot["actividades"].append(record)
            save_json(evidence / "plataforma.json", snapshot)
            print(json.dumps(snapshot, ensure_ascii=True))
        context.close()
        browser.close()


def observe() -> None:
    observer = ActivityObserver()
    for slug, activity in ((COURSES[3432], 2), (COURSES[3482], 2), (COURSES[3441], 1)):
        target = ROOT / f"{slug}-lde"
        result = observer.observe(ActivityObservationRequest(
            target=str(target), activity_number=activity, compile_check=True,
            output=str(target / f"referencias-{slug}" / "auditoria-semana-2-2026-10-09")))
        print(json.dumps({"materia": slug, "passed": result.ok,
                          "evaluacion": result.evaluation_path.relative_to(PROJECT_ROOT).as_posix()}, ensure_ascii=True))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"platform", "books", "observe"}:
        raise SystemExit("Uso: unadm_semana2_auditar.py platform|books|observe")
    {"platform": platform_snapshot, "books": copy_books, "observe": observe}[sys.argv[1]]()