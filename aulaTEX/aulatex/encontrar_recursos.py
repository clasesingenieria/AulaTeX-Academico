"""Agente ``encontrar-recursos`` para localizar, descargar y organizar recursos académicos.

A partir de la planeación canónica generada por ``realizar-planeación``, este agente:
1. Localiza y descarga adjuntos docentes y materiales de unidad desde ITESCA Virtual
   mediante ``navegación-itesca`` (verificando MIME real, tamaño y SHA-256).
2. Organiza los materiales docentes en ``referencias-<slug>/notas-<slug>/<actividad>/material-docente/``
   y extrae su texto con localizadores de página (``Pagina N``).
3. Vincula la biblioteca verificada de la materia (``libros-<slug>/``, ``institucionales/``,
   ``fuentes-web/``, archivos ``.bib`` y entregables acumulativos previos).
4. Consolida ``corpus-extractor/`` dentro de la carpeta de notas de la actividad y
   registra ``recursos-actividad.json`` sin exponer credenciales.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.parse import unquote, urlsplit

from .mcp_lex import McpLexClient, get_lex_client
from .navegacion_itesca import DownloadedPlatformFile, NavegacionItescaAgent
from .navegacion_unadm import NavegacionUnadmAgent
from .navegacion_plataforma import assert_no_credential_leak
from .node_planning import PEDAGOGICAL_SCHEMA_PATH, validate_schema
from .planning_layout import subject_layout
from .planning_validation import validate_pedagogical
from .workspace import AulaTeXWorkspace

AGENT_ID_ENCONTRAR_RECURSOS = "encontrar-recursos"


@dataclass(frozen=True)
class EncontrarRecursosRequest:
    target: str
    activity_number: int
    plan_json_path: str | Path = ""
    extra_platform_urls: tuple[str, ...] = ()
    download_from_platform: bool = True


@dataclass(frozen=True)
class EncontrarRecursosResult:
    agent_id: str
    activity_number: int
    subject_root: Path
    notes_dir: Path
    material_docente_dir: Path
    corpus_dir: Path
    manifest_path: Path
    downloaded_count: int
    organized_files_count: int
    missing_or_blocked: tuple[str, ...]

    @property
    def total_resources(self) -> int:
        return self.organized_files_count + self.downloaded_count

    @property
    def ok(self) -> bool:
        return self.organized_files_count > 0 or self.downloaded_count > 0


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_document_text(path: Path) -> str:
    """Extrae texto UTF-8 con marcadores ``Pagina N`` para PDF o párrafos/tablas para DOCX."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pymupdf

        chunks: list[str] = []
        with pymupdf.open(path) as doc:
            for idx, page in enumerate(doc, start=1):
                txt = (page.get_text("text") or "").strip()
                chunks.append(f"Pagina {idx}\n{txt}")
        return "\n\n".join(chunks).strip() + "\n"
    if suffix == ".docx":
        from docx import Document

        doc = Document(path)
        lines: list[str] = ["Pagina 1"]
        for p in doc.paragraphs:
            if p.text.strip():
                lines.append(p.text.strip())
        for tbl in doc.tables:
            for row in tbl.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells if c.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))
        return "\n".join(lines).strip() + "\n"
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


class EncontrarRecursosAgent:
    """Agente ``encontrar-recursos`` integrado al contrato de estructura de materias."""

    agent_id: str = AGENT_ID_ENCONTRAR_RECURSOS

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        nav_agent: Any | None = None,
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()
        self.nav_agent = nav_agent

    def _resolve_nav_agent(self, subject_root: Path, plan_doc: dict[str, Any]) -> Any:
        if self.nav_agent is not None:
            return self.nav_agent
        institution = str((plan_doc.get("identity") or {}).get("institution") or "")
        if institution.casefold() == "unadm" or "unadm" in subject_root.as_posix().lower():
            return NavegacionUnadmAgent(self.workspace)
        return NavegacionItescaAgent(self.workspace)

    def run(self, request: EncontrarRecursosRequest) -> EncontrarRecursosResult:
        subject_root = self.workspace.resolve_target(request.target)
        layout = subject_layout(subject_root)
        slug = subject_root.name
        for suffix in ("-mga", "-lde", "-lae", "-iias"):
            if slug.endswith(suffix):
                slug = slug[: -len(suffix)]
                break

        plan_path = (
            Path(request.plan_json_path).resolve()
            if str(request.plan_json_path).strip()
            else layout["plans"] / f"planeacion-{slug}-Actividad-{int(request.activity_number)}.json"
        )
        if not plan_path.is_file():
            raise FileNotFoundError(f"Planeación requerida no encontrada para encontrar-recursos: {plan_path}")

        plan_doc = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        active_nav = self._resolve_nav_agent(subject_root, plan_doc)
        act = plan_doc["activities"][0]
        notes_rel = act["bindings"].get("notes_directory")
        if not notes_rel:
            raise ValueError("La planeación no define bindings.notes_directory.")
        notes_dir = (subject_root / notes_rel).resolve()
        material_dir = notes_dir / "material-docente"
        corpus_dir = notes_dir / "corpus-extractor"
        material_dir.mkdir(parents=True, exist_ok=True)
        corpus_dir.mkdir(parents=True, exist_ok=True)

        ext_wf = (plan_doc.get("extensions") or {}).get("unadm_workflow") or (plan_doc.get("extensions") or {}).get("itesca_workflow") or {}
        mid = ext_wf.get("moodle_module_id") or ext_wf.get("course_id") or ""
        candidate_urls: list[dict[str, str]] = []
        for att in ext_wf.get("instructional_attachments") or []:
            if att.get("url"):
                candidate_urls.append({"url": att["url"], "prefix": str(mid)})
        for rel_link in ext_wf.get("related_links") or []:
            u = str(rel_link.get("url") or "")
            if any(k in u for k in ("/mod/resource/view.php", "/mod/folder/view.php", "/mod/page/view.php")):
                m_id = re.search(r"id=(\d+)", u)
                candidate_urls.append({"url": u, "prefix": m_id.group(1) if m_id else str(mid)})
        for extra_url in request.extra_platform_urls:
            if extra_url.strip():
                m_id = re.search(r"id=(\d+)", extra_url)
                candidate_urls.append({"url": extra_url.strip(), "prefix": m_id.group(1) if m_id else str(mid)})

        # Filtrar descargas cuyos nombres ya estén presentes y no vacíos en material-docente
        existing_names = {p.name.lower() for p in material_dir.iterdir() if p.is_file() and p.stat().st_size > 0}
        to_download: list[dict[str, str]] = []
        for item in candidate_urls:
            url_name = Path(unquote(urlsplit(item["url"]).path)).name.lower()
            prefixed_name = f"{item['prefix']}-{url_name}".lower() if item["prefix"] else url_name
            if url_name and url_name not in {"view.php", ""} and (url_name in existing_names or prefixed_name in existing_names):
                continue
            to_download.append(item)

        downloaded: list[Any] = []
        missing_or_blocked: list[str] = []
        if request.download_from_platform and to_download and active_nav is not None:
            try:
                downloaded = active_nav.download_resources(to_download, material_dir)
            except Exception as exc:
                missing_or_blocked.append(f"descarga_plataforma_fallida:{type(exc).__name__}")

        # Extraer texto de todos los PDF/DOCX docentes y copiarlos al corpus-extractor
        teacher_files_manifest: list[dict[str, Any]] = []
        for fpath in sorted(material_dir.iterdir()):
            if not fpath.is_file() or fpath.suffix.lower() not in {".pdf", ".docx"}:
                continue
            txt_companion = fpath.with_suffix(".txt")
            if not txt_companion.is_file() or txt_companion.stat().st_size == 0:
                extracted = extract_document_text(fpath)
                if extracted.strip():
                    txt_companion.write_text(extracted, encoding="utf-8")
            if txt_companion.is_file() and txt_companion.stat().st_size > 0:
                corpus_target = corpus_dir / f"docente-{txt_companion.name}"
                if not corpus_target.is_file():
                    shutil.copy2(txt_companion, corpus_target)
            teacher_files_manifest.append(
                {
                    "filename": fpath.name,
                    "relative_path": fpath.relative_to(subject_root).as_posix(),
                    "text_path": txt_companion.relative_to(subject_root).as_posix() if txt_companion.is_file() else None,
                    "sha256": _sha256_file(fpath),
                    "size_bytes": fpath.stat().st_size,
                }
            )

        # Incluir consigna y retroalimentación previa en el corpus-extractor
        for note_file in sorted(notes_dir.glob("consigna-*.txt")):
            shutil.copy2(note_file, corpus_dir / f"00-{note_file.name}")
        fb_json = notes_dir / "retroalimentacion-previa-itesca.json"
        if fb_json.is_file():
            fb_items = json.loads(fb_json.read_text(encoding="utf-8"))
            fb_lines = ["Pagina 1", "Retroalimentación docente previa verificada"]
            for entry in fb_items:
                fb_lines.append(f"=== {entry.get('title', '')} ({entry.get('grade', '')}) ===")
                fb_lines.append(entry.get("feedback", ""))
            (corpus_dir / "01-retroalimentacion-docente-previa.txt").write_text(
                "\n\n".join(fb_lines) + "\n",
                encoding="utf-8",
            )

        # Vincular biblioteca local verificada y documentos institucionales/acumulativos
        ref_root = layout["references"]
        local_library_manifest: list[dict[str, Any]] = []
        for sub_name in (f"libros-{slug}", "institucionales", "fuentes-web", "fuentes-oficiales-2026-10-11"):
            sub_dir = ref_root / sub_name
            if not sub_dir.is_dir():
                continue
            for item in sorted(sub_dir.rglob("*")):
                if not item.is_file() or item.suffix.lower() not in {".pdf", ".txt", ".md", ".docx"}:
                    continue
                local_library_manifest.append(
                    {
                        "category": sub_name,
                        "filename": item.name,
                        "relative_path": item.relative_to(subject_root).as_posix(),
                        "sha256": _sha256_file(item),
                        "size_bytes": item.stat().st_size,
                    }
                )
                # Si el corpus aún es pequeño, incorporar textos institucionales o extractos .txt/.md
                if item.suffix.lower() in {".txt", ".md"} and len(list(corpus_dir.glob("*.txt"))) < 18:
                    dest = corpus_dir / f"ref-{item.stem[:48]}.txt"
                    if not dest.is_file():
                        txt_body = item.read_text(encoding="utf-8", errors="replace")
                        if "Pagina " not in txt_body:
                            txt_body = "Pagina 1\n" + txt_body
                        dest.write_text(txt_body, encoding="utf-8")

        # Si el corpus sigue teniendo pocos textos y hay PDFs en institucionales o libros pequeños, extraer muestra
        if len(list(corpus_dir.glob("*.txt"))) < 6:
            inst_dir = ref_root / "institucionales"
            if inst_dir.is_dir():
                for pdf_item in sorted(inst_dir.glob("*.pdf"))[:4]:
                    dest = corpus_dir / f"inst-{pdf_item.stem[:48]}.txt"
                    if not dest.is_file():
                        txt = extract_document_text(pdf_item)
                        if txt.strip():
                            dest.write_text(txt, encoding="utf-8")

        # Detectar entregable acumulativo previo en Seminario I (ej. Tarea 14 -> Tarea 15)
        prior_deliverable: dict[str, Any] | None = None
        if int(request.activity_number) > 1:
            prev_num = int(request.activity_number) - 1
            prev_candidates = list(layout["deliveries"].glob(f"Tarea{prev_num}_*.docx"))
            if prev_candidates:
                prev_doc = prev_candidates[0]
                prior_deliverable = {
                    "filename": prev_doc.name,
                    "relative_path": prev_doc.relative_to(subject_root).as_posix(),
                    "sha256": _sha256_file(prev_doc),
                    "size_bytes": prev_doc.stat().st_size,
                }
                prev_txt_dest = corpus_dir / f"previo-acumulativo-tarea-{prev_num}.txt"
                if not prev_txt_dest.is_file():
                    prev_txt = extract_document_text(prev_doc)
                    if prev_txt.strip():
                        prev_txt_dest.write_text(prev_txt, encoding="utf-8")

        bib_files = [
            {
                "filename": b.name,
                "relative_path": b.relative_to(subject_root).as_posix(),
                "sha256": _sha256_file(b),
            }
            for b in sorted(subject_root.glob("*.bib")) + sorted(ref_root.glob("*.bib"))
            if b.is_file()
        ]

        # Actualizar fuentes verificadas en la planeación canónica
        existing_source_paths = {s.get("path") for s in plan_doc["sources"] if s.get("path")}
        now_iso = datetime.now(timezone.utc).isoformat()
        for idx, tf in enumerate(teacher_files_manifest, start=1):
            if tf["relative_path"] in existing_source_paths:
                continue
            src_id = f"src-docente-{idx:02d}"
            kind = "pdf" if tf["filename"].lower().endswith(".pdf") else ("docx" if tf["filename"].lower().endswith(".docx") else "other")
            plan_doc["sources"].append(
                {
                    "id": src_id,
                    "kind": kind,
                    "authority": "instructional",
                    "title": tf["filename"],
                    "url": None,
                    "path": tf["relative_path"],
                    "sha256": tf["sha256"],
                    "captured_at": now_iso,
                    "media_type": "application/pdf" if kind == "pdf" else "application/octet-stream",
                }
            )
            act["resources"].append(
                {
                    "id": f"res-docente-{idx:02d}",
                    "source_id": src_id,
                    "purpose": f"Material docente verificado ({tf['filename']})",
                    "required": True,
                    "access": "local",
                    "rights": f"Material docente institucional {plan_doc['identity'].get('institution', 'AulaTeX')}",
                }
            )

        validate_schema(plan_doc, PEDAGOGICAL_SCHEMA_PATH)
        sem_val = validate_pedagogical(plan_doc, subject_root)
        plan_doc["review"]["semantic_validation"] = "passed" if sem_val["passed"] else "failed"
        assert_no_credential_leak(plan_doc)
        plan_path.write_text(json.dumps(plan_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        corpus_files = [
            {
                "filename": cf.name,
                "relative_path": cf.relative_to(subject_root).as_posix(),
                "sha256": _sha256_file(cf),
                "size_bytes": cf.stat().st_size,
            }
            for cf in sorted(corpus_dir.glob("*.txt"))
            if cf.is_file()
        ]

        manifest = {
            "schema_version": "1.0.0",
            "agent_id": self.agent_id,
            "organized_at_utc": now_iso,
            "subject_id": subject_root.name,
            "activity_number": int(request.activity_number),
            "notes_directory": notes_dir.relative_to(subject_root).as_posix(),
            "material_docente_files": teacher_files_manifest,
            "downloaded_in_this_run": [
                {
                    "filename": d.filename,
                    "sha256": d.sha256,
                    "size_bytes": d.size_bytes,
                    "mime_hint": d.mime_hint,
                }
                for d in downloaded
            ],
            "bibliography_files": bib_files,
            "prior_cumulative_deliverable": prior_deliverable,
            "local_library_count": len(local_library_manifest),
            "local_library_sample": local_library_manifest[:25],
            "corpus_extractor_files": corpus_files,
            "missing_or_blocked": missing_or_blocked,
        }
        assert_no_credential_leak(manifest)
        manifest_path = notes_dir / "recursos-actividad.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        return EncontrarRecursosResult(
            agent_id=self.agent_id,
            activity_number=int(request.activity_number),
            subject_root=subject_root,
            notes_dir=notes_dir,
            material_docente_dir=material_dir,
            corpus_dir=corpus_dir,
            manifest_path=manifest_path,
            downloaded_count=len(downloaded),
            organized_files_count=len(corpus_files),
            missing_or_blocked=tuple(missing_or_blocked),
        )


__all__ = [
    "AGENT_ID_ENCONTRAR_RECURSOS",
    "EncontrarRecursosAgent",
    "EncontrarRecursosRequest",
    "EncontrarRecursosResult",
    "extract_document_text",
]
