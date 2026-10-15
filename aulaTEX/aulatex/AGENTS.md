# AulaTeX agentic architecture

## Purpose

AulaTeX is a local multimodule editorial agent for institutional LaTeX work.
It adapts useful production patterns from the local reference project:

`D:\Documentos\t-books\proyectos-traducidos\30-Agents-Every-AI-Engineer-Must-Build-main_es_semantic-safe`

The app does not import that project at runtime. The patterns are implemented
inside AulaTeX so the suite remains autonomous.

## Integrated patterns

- Chapter 05: planning agent and memory-augmented agent.
- Chapter 07: tool-using agent, safe invocation, stateful workflow and audit trail.
- Chapter 08: verification and validation agent.
- Chapter 15: collective intelligence, weighted consensus and adversarial critic.

## AulaTeX roles

- Planificador editorial: turns the target into an executable editorial plan.
- Investigador documental: detects institutional context, bibliography and gaps.
- Arquitecto de plantillas: proposes report, presentation and activity structures.
- Verificador y validador: checks evidence, compilation and acceptance criteria.
- Critico adversarial: finds blockers before applying changes.

## Subject delivery layout

- Every subject has `entregas-<subject-slug>/`; obtain its path from `subject_layout()`.
- The subject slug removes the program suffix `-lde`, `-lad`, `-mga`, `-isc` or `-imtc`.
- Use `subject_artifact_contract()` in new planning models and structure inventories.
- Preserve existing delivery files and indexes. Do not create generic `Entregas/` or `entregas/` folders.
- Editable source files keep their editorial location; the delivery directory contains the files selected for submission.
- Full specification: [CONTRATO-ESTRUCTURA-MATERIAS.md](CONTRATO-ESTRUCTURA-MATERIAS.md).

## Runtime outputs

Each agent run writes:

- `stage-*.md`: one LLM role output per stage.
- `workflow-trace.md`: state-machine audit.
- `shared-memory.md`: memory accumulated during the cycle.
- `agentic-patterns.md`: pattern catalog for the run.
- `manifest.json`: machine-readable run contract.
- `reporte-aulatex.md`: editorial report.

## Safety

- Never commit `aulaTEX/aulatex.env`.
- Never hardcode credentials.
- Keep LLM calls routed through `AulaTeXLLMClient`.
- Keep fragile tools wrapped through `safe_invoke` or `graceful_fallback`.
- Never copy credentials, encrypted secrets, PII or private document contents into notebooks, model cards, manifests or logs.
- Keep real datasets, checkpoints and model weights outside Git; version only code, configuration, tests and small manifests.
- Split training/evaluation by target or subject, never by related rows, to prevent leakage.
- Reject learned judges below their documented validation threshold.
- When the AulaTeX template is loaded, generate `\insertimage` or `images`/`\addimage`; do not emit manual `figure` + `\includegraphics`.
