from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .llm_bridge import DEFAULT_MAX_TOKENS, AulaTeXLLMClient


_RISK_MARKERS = re.compile(
    r"\b(?:clasific|correspon|pertenec|modelo|tipo|r[eé]gimen|financi|causa|"
    r"implica|depende|art(?:[íi]culo)?\.?|fracci[oó]n|porcentaje|mayor|menor|"
    r"obligatorio|voluntario|facultativo|germano|latino|contributivo|"
    r"no contributivo)\b|\d",
    re.IGNORECASE,
)

_LABEL_GROUPS = (
    ("germano", "latino"),
    ("contributivo", "no contributivo"),
    ("obligatorio", "voluntario"),
    ("publico", "privado"),
    ("centralizado", "descentralizado"),
    ("permitido", "prohibido"),
    ("valido", "invalido"),
)


@dataclass(frozen=True)
class SemanticEvidence:
    source: str
    location: str
    quote: str


@dataclass(frozen=True)
class SemanticFinding:
    kind: str
    severity: str
    claim: str
    explanation: str
    evidence: tuple[SemanticEvidence, ...] = ()
    suggested_fix: str = ""
    origin: str = "llm"


@dataclass(frozen=True)
class SemanticAuditResult:
    ok: bool
    audit_available: bool
    claims_checked: int
    evidence_count: int
    findings: tuple[SemanticFinding, ...] = ()
    error: str = ""

    @property
    def blocking_findings(self) -> tuple[SemanticFinding, ...]:
        return tuple(item for item in self.findings if item.severity == "blocking")

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocking_count"] = len(self.blocking_findings)
        return payload


class SemanticAuditor:
    """Audita afirmaciones contra evidencia local y coherencia interna.

    La auditoría combina reglas deterministas de alta precisión con un dictamen
    LLM limitado a los pasajes recuperados. Una falla del auditor se conserva
    como estado no disponible para que el llamador pueda aplicar fail-closed.
    """

    def __init__(self, llm: AulaTeXLLMClient | None = None) -> None:
        self.llm = llm or AulaTeXLLMClient()

    def audit(
        self,
        text: str,
        target_root: Path,
        *,
        engine: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        output_path: Path | None = None,
        feedback_path: Path | None = None,
    ) -> SemanticAuditResult:
        claims = self._extract_claims(text)
        evidence = self._retrieve_evidence(target_root, claims)
        external_feedback = self._load_feedback(feedback_path)
        motor_rules = self._load_motor_rules(target_root)
        if motor_rules:
            external_feedback = (
                external_feedback + "\n\nREGLAS PERSISTENTES DEL MOTOR:\n" + motor_rules
            ).strip()
        deterministic = self._detect_internal_contradictions(claims)
        deterministic.extend(self._detect_feedback_conflicts(text, external_feedback, evidence))
        if external_feedback:
            evidence.append(
                SemanticEvidence(
                    source="retroalimentación docente",
                    location="Actividad evaluada",
                    quote=external_feedback[:1200],
                )
            )
        prompt = self._build_prompt(claims, evidence, deterministic, external_feedback)
        # Auditoría con RED DE SEGURIDAD: si el motor elegido falla, opus entra
        # al quite (tarea 'razonamiento') para no quedar sin auditoría.
        response = self.llm.call_with_safety_net(
            prompt, task="razonamiento", engine=engine, max_tokens=min(max_tokens, 24_000)
        )
        if not response.ok or not response.text.strip():
            result = SemanticAuditResult(
                ok=False,
                audit_available=False,
                claims_checked=len(claims),
                evidence_count=len(evidence),
                findings=tuple(deterministic),
                error=response.error or "El auditor semántico no devolvió contenido.",
            )
            self._write_result(output_path, result, response.text)
            return result

        parsed = self._parse_response(response.text)
        if parsed is None:
            result = SemanticAuditResult(
                ok=False,
                audit_available=False,
                claims_checked=len(claims),
                evidence_count=len(evidence),
                findings=tuple(deterministic),
                error="El auditor semántico devolvió JSON inválido.",
            )
            self._write_result(output_path, result, response.text)
            return result

        llm_findings = self._normalize_findings(parsed.get("findings", []))
        findings = self._deduplicate_findings([*deterministic, *llm_findings])
        result = SemanticAuditResult(
            ok=not any(item.severity == "blocking" for item in findings),
            audit_available=True,
            claims_checked=max(len(claims), int(parsed.get("claims_checked") or 0)),
            evidence_count=len(evidence),
            findings=tuple(findings),
        )
        self._write_result(output_path, result, response.text)
        return result

    def _extract_claims(self, text: str, limit: int = 28) -> list[str]:
        plain = self._latex_to_text(text)
        candidates = re.split(r"(?<=[.!?])\s+|\n+", plain)
        claims: list[str] = []
        for candidate in candidates:
            claim = re.sub(r"\s+", " ", candidate).strip(" -")
            if len(claim) < 45 or not _RISK_MARKERS.search(claim):
                continue
            if claim not in claims:
                claims.append(claim[:900])
            if len(claims) >= limit:
                break
        return claims

    def _retrieve_evidence(
        self,
        target_root: Path,
        claims: list[str],
        limit: int = 36,
    ) -> list[SemanticEvidence]:
        records: list[SemanticEvidence] = []
        patterns = (
            "extractor-aulatex/**/fichas_conceptos.json",
            "extractor-aulatex/**/trazabilidad_fuentes.json",
            "extractor-aulatex/**/resumen_planeacion*.json",
        )
        paths: list[Path] = []
        for pattern in patterns:
            paths.extend(target_root.glob(pattern))
        for path in sorted(set(paths)):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            records.extend(self._evidence_from_payload(payload, path.name))

        if not records or not claims:
            return records[:limit]

        claim_tokens = [self._tokens(claim) for claim in claims]
        scored: list[tuple[float, SemanticEvidence]] = []
        for item in records:
            evidence_tokens = self._tokens(f"{item.quote} {item.source}")
            score = max(
                (len(tokens & evidence_tokens) / max(1, len(tokens)) for tokens in claim_tokens),
                default=0.0,
            )
            if score >= 0.08:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].source, pair[1].location))
        normalized_claims = [self._normalize(claim) for claim in claims]
        targeted = [
            item
            for item in records
            if any(
                ("facultativo" in claim and "facultativo" in self._normalize(item.quote)
                 and ("sustituy" in self._normalize(item.quote) or "salud" in self._normalize(item.quote)))
                or (
                    "sustituy" in claim
                    and "sustituy" in self._normalize(item.quote)
                    and "facultativo" in self._normalize(item.quote)
                )
                for claim in normalized_claims
            )
        ]
        ordered: list[SemanticEvidence] = []
        seen: set[tuple[str, str, str]] = set()
        for item in [*targeted, *(pair[1] for pair in scored)]:
            key = (item.source, item.location, item.quote)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(item)
            if len(ordered) >= limit:
                break
        return ordered

    def _evidence_from_payload(self, payload: Any, fallback_source: str) -> list[SemanticEvidence]:
        records: list[SemanticEvidence] = []
        if isinstance(payload, list):
            for item in payload:
                records.extend(self._evidence_from_payload(item, fallback_source))
            return records
        if not isinstance(payload, dict):
            return records

        quote = str(
            payload.get("cita_textual")
            or payload.get("fragmento")
            or payload.get("texto")
            or payload.get("resumen")
            or ""
        ).strip()
        if len(quote) >= 35:
            records.append(
                SemanticEvidence(
                    source=str(payload.get("fuente") or payload.get("archivo") or fallback_source),
                    location=str(payload.get("ubicacion") or payload.get("pagina_o_bloque") or ""),
                    quote=re.sub(r"\s+", " ", quote)[:1200],
                )
            )
        for value in payload.values():
            if isinstance(value, (dict, list)):
                records.extend(self._evidence_from_payload(value, fallback_source))
        return records

    def _detect_internal_contradictions(self, claims: list[str]) -> list[SemanticFinding]:
        assignments: dict[tuple[str, tuple[str, ...]], tuple[str, str]] = {}
        findings: list[SemanticFinding] = []
        for claim in claims:
            normalized = self._normalize(claim)
            for group in _LABEL_GROUPS:
                labels = []
                for label in group:
                    if label == "contributivo":
                        pattern = r"(?<!no\s)\bcontributivo\b"
                    else:
                        pattern = rf"\b{re.escape(label)}\b"
                    if re.search(pattern, normalized):
                        labels.append(label)
                if len(labels) != 1:
                    continue
                label = labels[0]
                subject_tokens = tuple(
                    token for token in self._tokens(normalized) if token not in set(group) and len(token) >= 5
                )
                key = ("|".join(group), subject_tokens[:8])
                previous = assignments.get(key)
                if previous is not None and previous[0] != label and previous[1] != claim:
                    findings.append(
                        SemanticFinding(
                            kind="internal_contradiction",
                            severity="blocking",
                            claim=f"{previous[1]} || {claim}",
                            explanation=(
                                f"El mismo sujeto recibe etiquetas incompatibles: "
                                f"'{previous[0]}' y '{label}'."
                            ),
                            suggested_fix="Resolver la clasificación con la fuente primaria y unificar todas sus apariciones.",
                            origin="deterministic",
                        )
                    )
                else:
                    assignments[key] = (label, claim)
        return findings

    def _detect_feedback_conflicts(
        self,
        text: str,
        external_feedback: str,
        evidence: list[SemanticEvidence],
    ) -> list[SemanticFinding]:
        if not external_feedback:
            return []
        feedback = self._normalize(external_feedback)
        plain = self._latex_to_text(text)
        findings: list[SemanticFinding] = []
        if "voluntario" in feedback and "germano" in feedback:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", plain):
                normalized = self._normalize(sentence)
                if re.search(r"voluntario.{0,160}latino|latino.{0,160}voluntario", normalized):
                    findings.append(
                        SemanticFinding(
                            kind="source_conflict",
                            severity="blocking",
                            claim=sentence.strip(),
                            explanation=(
                                "La retroalimentación docente aproxima el régimen voluntario "
                                "al modelo germano por el pago de cuotas o primas, pero esta "
                                "afirmación lo aproxima al modelo latino."
                            ),
                            suggested_fix=(
                                "Unificar esta aparición con la clasificación germana sustentada "
                                "en el pago de cuotas o primas."
                            ),
                            origin="deterministic-feedback",
                        )
                    )
        household_evidence = tuple(
            item for item in evidence
            if "hogar" in self._normalize(item.quote)
            and "obligatorio" in self._normalize(item.quote)
        )
        if household_evidence and "hogar" in plain.lower():
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", plain):
                normalized = self._normalize(sentence)
                if "hogar" in normalized and "volunt" in normalized:
                    findings.append(
                        SemanticFinding(
                            kind="source_conflict",
                            severity="blocking",
                            claim=sentence.strip(),
                            explanation=(
                                "El texto incluye a las personas trabajadoras del hogar en el "
                                "régimen voluntario, mientras los pasajes extraídos las ubican "
                                "en el régimen obligatorio."
                            ),
                            evidence=household_evidence[:2],
                            suggested_fix=(
                                "Eliminar esa inclusión o aclarar que corresponde a una regulación "
                                "histórica anterior al régimen obligatorio."
                            ),
                            origin="deterministic-source",
                        )
                    )
        return findings

    def _build_prompt(
        self,
        claims: list[str],
        evidence: list[SemanticEvidence],
        deterministic: list[SemanticFinding],
        external_feedback: str = "",
    ) -> str:
        evidence_payload = [asdict(item) for item in evidence]
        deterministic_payload = [asdict(item) for item in deterministic]
        return (
            "Actúa como auditor académico adversarial. Verifica las AFIRMACIONES contra los "
            "PASAJES LOCALES y busca contradicciones entre afirmaciones. No evalúes estilo. "
            "No uses conocimiento externo para declarar una afirmación respaldada; la evidencia "
            "debe estar en los pasajes. Marca como blocking únicamente: (a) contradicción interna "
            "clara, (b) conflicto claro con un pasaje, o (c) afirmación clasificatoria, causal, "
            "cuantitativa o jurídica importante sin pasaje que la respalde. Una cita adyacente no "
            "es respaldo si el pasaje no implica la afirmación. Conserva como warning las dudas "
            "menores. La RETROALIMENTACIÓN DOCENTE es autoridad evaluativa sobre el área señalada: "
            "si el documento contradice ese criterio, marca el conflicto; si el documento lo cumple, "
            "no lo marques como unsupported_claim únicamente porque el corpus local no repita la "
            "misma clasificación. No sustituye la necesidad de citar fuentes para otras afirmaciones. "
            "Devuelve SOLO JSON válido.\n\n"
            "Esquema:\n"
            '{"claims_checked": 0, "findings": [{"kind": "source_conflict|unsupported_claim|internal_contradiction", '
            '"severity": "blocking|warning", "claim": "cita exacta", "explanation": "razón", '
            '"evidence": [{"source": "", "location": "", "quote": ""}], "suggested_fix": ""}]}\n\n'
            f"AFIRMACIONES:\n{json.dumps(claims, ensure_ascii=False, indent=2)}\n\n"
            f"PASAJES LOCALES:\n{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}\n\n"
            f"HALLAZGOS DETERMINISTAS (debes conservarlos salvo falso positivo evidente):\n"
            f"{json.dumps(deterministic_payload, ensure_ascii=False, indent=2)}"
            + (
                "\n\nRETROALIMENTACIÓN EXTERNA DEL EVALUADOR (evidencia que debes verificar "
                "contra el documento y los pasajes; no la conviertas automáticamente en una "
                "orden de edición):\n"
                + external_feedback
                if external_feedback
                else ""
            )
        )

    def _load_feedback(self, path: Path | None) -> str:
        if path is None or not path.exists() or not path.is_file():
            return ""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        if path.suffix.lower() == ".json":
            try:
                return json.dumps(json.loads(raw), ensure_ascii=False, indent=2)[:12_000]
            except json.JSONDecodeError:
                pass
        return raw[:12_000]

    def _load_motor_rules(self, target_root: Path) -> str:
        candidates = [
            target_root / "retroalimentacion-editorial" / "aulatex" / "motor-calibration-rules.json",
            *(
                parent / "retroalimentacion-editorial" / "aulatex" / "motor-calibration-rules.json"
                for parent in [target_root, *target_root.parents]
            ),
        ]
        for candidate in candidates:
            if not candidate.exists() or not candidate.is_file():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rules = payload.get("rules", []) if isinstance(payload, dict) else []
            if isinstance(rules, list):
                return "\n".join(f"- {str(rule)}" for rule in rules if str(rule).strip())[:12_000]
        return ""

    def _parse_response(self, text: str) -> dict[str, Any] | None:
        candidate = text.strip()
        fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if fence:
            candidate = fence.group(1)
        else:
            start, end = candidate.find("{"), candidate.rfind("}")
            if start >= 0 and end > start:
                candidate = candidate[start : end + 1]
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _normalize_findings(self, payload: Any) -> list[SemanticFinding]:
        if not isinstance(payload, list):
            return []
        findings: list[SemanticFinding] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "unsupported_claim")
            severity = str(item.get("severity") or "warning").lower()
            if kind not in {"source_conflict", "unsupported_claim", "internal_contradiction"}:
                kind = "unsupported_claim"
            if severity not in {"blocking", "warning"}:
                severity = "warning"
            claim_text = str(item.get("claim") or "")
            normalized_claim = self._normalize(claim_text)
            if (
                kind == "unsupported_claim"
                and re.search(r"\b(se emplea aqui|se utiliza aqui|criterio comparativo|delimitacion metodologica)\b", normalized_claim)
            ):
                severity = "warning"
            evidence = tuple(
                SemanticEvidence(
                    source=str(ev.get("source") or ""),
                    location=str(ev.get("location") or ""),
                    quote=str(ev.get("quote") or "")[:1200],
                )
                for ev in item.get("evidence", [])
                if isinstance(ev, dict)
            )
            findings.append(
                SemanticFinding(
                    kind=kind,
                    severity=severity,
                    claim=claim_text[:1200],
                    explanation=str(item.get("explanation") or "")[:1600],
                    evidence=evidence,
                    suggested_fix=str(item.get("suggested_fix") or "")[:1200],
                )
            )
        return findings

    def _deduplicate_findings(self, findings: list[SemanticFinding]) -> list[SemanticFinding]:
        unique: list[SemanticFinding] = []
        seen: set[tuple[str, str]] = set()
        for item in findings:
            key = (item.kind, self._normalize(item.claim)[:240])
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _latex_to_text(self, text: str) -> str:
        active = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))
        active = re.sub(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{[^}]+\}", "", active)
        active = re.sub(r"\\(?:begin|end)\{[^}]+\}", "\n", active)
        active = re.sub(r"\\(?:section|subsection|subsubsection)\*?\{([^}]*)\}", r"\n\1. ", active)
        active = re.sub(r"\\[a-zA-Z@]+(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", active)
        active = re.sub(r"\\[a-zA-Z@]+|[{}&]", " ", active)
        return re.sub(r"\s+", " ", active)

    def _tokens(self, text: str) -> set[str]:
        stop = {"para", "como", "esta", "este", "desde", "entre", "sobre", "porque", "segun", "tambien"}
        return {token for token in re.findall(r"[a-z0-9]+", self._normalize(text)) if len(token) >= 4 and token not in stop}

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        return "".join(char for char in normalized if not unicodedata.combining(char))

    def _write_result(self, path: Path | None, result: SemanticAuditResult, raw: str) -> None:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        path.with_suffix(".raw.txt").write_text(raw, encoding="utf-8")