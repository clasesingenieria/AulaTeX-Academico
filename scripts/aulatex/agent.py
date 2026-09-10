from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .agentic_patterns import (
    AgentTask,
    AgenticStateMachine,
    EditorialConsensusEngine,
    SharedMemory,
    build_editorial_tasks,
    pattern_catalog_markdown,
    safe_invoke,
)
from .activity_monitor import ActivityMonitor, ActivityMonitorRequest
from .activity_optimizer import ActivityOptimizeRequest, ActivityOptimizer
from .editorial_context import EditorialContextProvider
from .editorial_memory import EditorialMemoryStore
from .extractor_adapter import ExtractorAdapter, ExtractorRequest, ExtractorRunResult
from .incremental_detail_planner import DetailPlannerRequest, DetailPlannerResult, IncrementalDetailPlanner
from .langchain_adapter import AulaTeXLLMInterface, AulaTeXLangChainAdapter
from .llm_bridge import DEFAULT_MAX_TOKENS, LLM_ENGINES, AulaTeXLLMClient, LLMCallResult
from .config import MODEL_ROUTER_ENGINE, restrict_engines_to_available
from .template_materializer import MaterializationResult, TemplateMaterializer
from .workspace import AulaTeXWorkspace


@dataclass
class AgentRequest:
    target: str = "."
    level: str = "materia"
    action: str = "generar-plantilla"
    activity_number: int = 1
    generation_mode: str = "direct"
    parent_scope_key: str = ""
    child_level: str = ""
    child_name: str = ""
    engines: list[str] = field(default_factory=lambda: ["Codex", "Claude Foundry", "GPT-Pro", "Auto (model-router)"])
    iterations: int = 5
    cycle_mode: str = "stages"
    compile_tex: bool = True
    max_tokens: int = DEFAULT_MAX_TOKENS
    apply_feedback: bool = False
    run_extractor: bool = False
    skip_extractor: bool = False
    extractor_probe_only: bool = False
    extractor_fuentes: str = ""
    extractor_planeacion: str = ""
    extractor_conceptos: str = ""
    extractor_salida: str = ""
    extractor_motor: str = "anthropicfoundry"
    run_detail_planner: bool = True
    detail_planner_max_scopes: int = 6
    run_monitor: bool = True
    run_optimize: bool = True
    run_foro_producto: bool = True
    # Optimizador de layout TikZ para producto MAPA CONCEPTUAL: resuelve choques,
    # coloca las palabras de enlace sin empalmes y llena el alto de la pagina.
    # Se aplica automaticamente si el .tex contiene un mapa conceptual (mc*).
    run_mapa_layout: bool = True
    # Compilacion final con latexmk tras monitor/optimize (garantiza que el .tex
    # en su estado definitivo produce un PDF actualizado). Activada por defecto.
    run_final_compile: bool = True
    # Una pasada monitorizada por defecto; la optimizacion posterior conserva su
    # convergencia independiente hasta la calidad objetivo de 100.
    monitor_max_cycles: int = 1
    # 0 = modo convergencia (optimiza hasta calidad objetivo, ciclos necesarios).
    optimize_cycles: int = 0
    run_semantic_audit: bool = True
    semantic_fail_closed: bool = True
    semantic_feedback_path: str = ""


@dataclass
class AgentRunResult:
    run_id: str
    run_dir: Path
    ok: bool
    report_path: Path
    manifest_path: Path
    monitor_ok: bool | None = None
    optimize_ok: bool | None = None
    quality_before: float | None = None
    quality_after: float | None = None
    final_compile_ok: bool | None = None
    semantic_blocking_before: int | None = None
    semantic_blocking_after: int | None = None
    semantic_audit_available: bool | None = None
    optimize_plan_summary: dict[str, object] | None = None


@dataclass(frozen=True)
class AgentTargetContext:
    target_path: Path
    context_path: Path
    scope_key: str
    display_target: str
    generation_mode: str
    parent_scope_key: str = ""
    child_level: str = ""
    child_name: str = ""
    child_preview: str = ""


class AulaTeXAgent:
    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm_bridge: AulaTeXLLMInterface | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.llm = llm_bridge or AulaTeXLangChainAdapter(AulaTeXLLMClient())
        self.editorial_memory = EditorialMemoryStore(self.workspace)
        self.editorial_context = EditorialContextProvider(self.workspace, self.editorial_memory)
        self.template_materializer = TemplateMaterializer(self.workspace)
        self.extractor_adapter = ExtractorAdapter(self.workspace)
        self.detail_planner = IncrementalDetailPlanner(self.workspace, self.editorial_memory)
        self.activity_monitor = ActivityMonitor(self.workspace)
        self.activity_optimizer = ActivityOptimizer(self.workspace)

    def run(self, request: AgentRequest) -> AgentRunResult:
        target_ctx = self._resolve_target_context(request)
        target = target_ctx.target_path
        run_id = self.workspace.timestamp()
        safe_action = request.action.lower().replace(" ", "-")
        run_dir = self.workspace.feedback_root / "runs" / f"{run_id}-{safe_action}"
        run_dir.mkdir(parents=True, exist_ok=True)

        detail_plan_result: DetailPlannerResult | None = None
        if self._should_run_detail_planner(request, target_ctx):
            detail_plan_result = self.detail_planner.run(
                DetailPlannerRequest(
                    target=str(target_ctx.target_path),
                    activity_number=request.activity_number,
                    output=str(run_dir / "detail-planner"),
                    max_scopes=request.detail_planner_max_scopes,
                    persist_memory=True,
                )
            )

        workflow = AgenticStateMachine()
        memory = SharedMemory()
        context = self.workspace.context_summary(target_ctx.context_path)
        if detail_plan_result is not None:
            context += "\n\n" + self._detail_planner_context(detail_plan_result)
        if target_ctx.generation_mode == "downward":
            context += (
                "\n\n## Generacion descendente\n"
                f"- Padre seleccionado: {target_ctx.parent_scope_key}\n"
                f"- Nivel hijo: {target_ctx.child_level}\n"
                f"- Hijo solicitado: {target_ctx.child_name or f'Actividad {request.activity_number}'}\n"
                f"- Vista previa: {target_ctx.child_preview or 'Pendiente de definir'}\n"
                "- Regla: reutiliza memoria editorial ascendente del padre y genera hacia abajo sin asumir que el hijo exista ya.\n"
            )
        if target_ctx.scope_key:
            editorial_bundle = self.editorial_context.build_for_scope(target_ctx.scope_key, include_ancestors=True, max_chars=22000)
            if editorial_bundle.markdown.strip():
                context += "\n\n" + editorial_bundle.markdown
        base_tasks = build_editorial_tasks(request, context, memory)
        cycle_mode = self._normalize_cycle_mode(request.cycle_mode)
        selected_tasks = self._expand_tasks(base_tasks, request.iterations, cycle_mode)
        engines = self._normalize_engines(request.engines)
        stage_results: list[LLMCallResult] = []
        extractor_result: ExtractorRunResult | None = None
        materialization_result: MaterializationResult | None = None
        applied_tex: dict[str, object] = {}
        compile_results: list[dict[str, object]] = []
        artifacts_prepared = False

        for index, task in enumerate(selected_tasks, start=1):
            base_stage = self._base_stage(task.stage)
            if base_stage in {"validar", "criticar"} and not artifacts_prepared:
                materialization_result, applied_tex, compile_results = self._prepare_artifacts(
                    request, target_ctx, selected_tasks[:index - 1], stage_results, workflow, run_dir
                )
                artifacts_prepared = True
            prompt = self._build_stage_prompt(
                task, selected_tasks[:index - 1], stage_results, memory,
                target_ctx, request.activity_number, applied_tex, compile_results,
            )
            engine = engines[(index - 1) % len(engines)]
            workflow.record("llm-start", "ok", f"{task.stage}: {task.role} via {engine}")
            result = self.llm.call(engine, prompt, max_tokens=request.max_tokens)
            stage_results.append(result)
            if result.ok:
                memory.remember("proposal" if base_stage in {"planificar", "generar"} else "risk", result.text[:900])
                workflow.record("llm-end", "ok", f"{task.stage}: {len(result.text)} chars")
            else:
                memory.remember("risk", f"{task.stage} fallo con {result.engine}: {result.error}")
                workflow.record("llm-end", "error", f"{task.stage}: {result.error}")
            self._record_stage_transition(workflow, base_stage)
            if base_stage == "generar":
                artifacts_prepared = False
            if base_stage == "investigar" and extractor_result is None and self._should_run_extractor(request, target_ctx):
                extractor_result = self._run_extractor_tool(request, target_ctx, workflow, memory)

        if extractor_result is None and self._should_run_extractor(request, target_ctx):
            extractor_result = self._run_extractor_tool(request, target_ctx, workflow, memory)

        for index, (task, result) in enumerate(zip(selected_tasks, stage_results), start=1):
            stage_path = run_dir / f"stage-{index:02d}-{task.stage}.md"
            stage_path.write_text(self._format_stage(result, task), encoding="utf-8")

        if not artifacts_prepared:
            materialization_result, applied_tex, compile_results = self._prepare_artifacts(
                request, target_ctx, selected_tasks, stage_results, workflow, run_dir
            )

        consensus = EditorialConsensusEngine().evaluate(selected_tasks, stage_results)
        workflow.record("consensus", "ok" if consensus.passed else "warn", f"score={consensus.consensus_score:.2f}")
        if workflow.state in {"planned", "researched", "generated", "compiled"}:
            workflow.transition("evaluated", "validacion y consenso completados")
        workflow.transition("finalized", "ciclo agentico cerrado")

        workflow_path = run_dir / "workflow-trace.md"
        workflow_path.write_text(workflow.to_markdown(), encoding="utf-8")
        memory_path = run_dir / "shared-memory.md"
        memory_path.write_text("# Memoria compartida AulaTeX\n\n" + memory.summary(max_chars=12000), encoding="utf-8")
        patterns_path = run_dir / "agentic-patterns.md"
        patterns_path.write_text(pattern_catalog_markdown(), encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "target": self.workspace.relative(target),
            "display_target": target_ctx.display_target,
            "level": request.level,
            "action": request.action,
            "activity_number": request.activity_number,
            "cycle_mode": cycle_mode,
            "requested_iterations": int(request.iterations),
            "expanded_task_count": len(selected_tasks),
            "generation_mode": request.generation_mode,
            "parent_scope_key": request.parent_scope_key,
            "child_level": request.child_level,
            "child_name": request.child_name,
            "child_preview": target_ctx.child_preview,
            "engines": engines,
            "agentic_patterns": [
                "planning-memory",
                "tool-using-workflow",
                "verification-validation",
                "collective-consensus",
            ],
            "tasks": [
                {
                    "stage": task.stage,
                    "role": task.role,
                    "mission": task.mission,
                    "engine": stage_results[index].engine if index < len(stage_results) else "",
                }
                for index, task in enumerate(selected_tasks)
            ],
            "llm_results": [
                {"engine": r.engine, "ok": r.ok, "error": r.error, "chars": len(r.text)}
                for r in stage_results
            ],
            "compile_results": compile_results,
            "detail_planner": self._detail_planner_manifest(detail_plan_result),
            "extractor": self._extractor_manifest(extractor_result),
            "materialization": self._materialization_manifest(materialization_result),
            "generated_tex": applied_tex,
            "consensus": consensus.as_dict(),
            "workflow_events": workflow.as_dicts(),
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        report_path = run_dir / "reporte-aulatex.md"
        report_path.write_text(
            self._build_report(request, target_ctx, selected_tasks, stage_results, compile_results, consensus, extractor_result, detail_plan_result),
            encoding="utf-8",
        )
        if materialization_result is not None:
            report_path.write_text(
                report_path.read_text(encoding="utf-8")
                + "\n"
                + self._render_materialization_report(materialization_result),
                encoding="utf-8",
            )
        self.workspace.append_bitacora(run_id, request.action, manifest)

        if request.apply_feedback:
            self._write_target_feedback(target, report_path)

        ok = all(r.ok for r in stage_results) and all(item.get("ok") for item in compile_results or [{"ok": True}])
        ok = ok and consensus.passed
        if extractor_result is not None:
            ok = ok and extractor_result.ok
        if materialization_result is not None:
            ok = ok and materialization_result.ok
        if request.action.strip().lower() == "realizar-actividad":
            targets_after_generation = self._select_compile_targets(target_ctx, request.activity_number)
            unresolved_scaffold = any(
                "en construcción" in path.read_text(encoding="utf-8", errors="replace").lower()
                or path.read_text(encoding="utf-8", errors="replace").count(r"\begin{frame}") <= 2
                for path in targets_after_generation
                if path.name.startswith("presentacion-")
            )
            if applied_tex.get("reason") in {"arquitecto-sin-tex-completo", "propuesta-con-placeholders", "propuesta-no-es-presentacion"}:
                ok = False
            if unresolved_scaffold:
                ok = False

        # Post-procesamiento automático para realizar-actividad:
        # 1) monitor -> converger el contrato editorial del .tex (aplica parches reales).
        # 2) optimize -> elevar la calidad del .tex de forma verificada.
        (
            monitor_ok,
            optimize_ok,
            quality_before,
            quality_after,
            final_compile_ok,
            semantic_blocking_before,
            semantic_blocking_after,
            semantic_audit_available,
            optimize_plan_summary,
        ) = self._postprocess_activity(request, target_ctx, run_dir, report_path)
        if monitor_ok is False or optimize_ok is False:
            ok = False
        # Si la compilación final falló, el resultado global no puede reportar éxito.
        if final_compile_ok is False:
            ok = False

        manifest.update(
            {
                "ok": ok,
                "monitor_ok": monitor_ok,
                "optimize_ok": optimize_ok,
                "quality_before": quality_before,
                "quality_after": quality_after,
                "final_compile_ok": final_compile_ok,
                "semantic_blocking_before": semantic_blocking_before,
                "semantic_blocking_after": semantic_blocking_after,
                "semantic_audit_available": semantic_audit_available,
                "optimize_plan_summary": optimize_plan_summary,
            }
        )
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        return AgentRunResult(
            run_id, run_dir, ok, report_path, manifest_path,
            monitor_ok=monitor_ok, optimize_ok=optimize_ok,
            quality_before=quality_before, quality_after=quality_after,
            final_compile_ok=final_compile_ok,
            semantic_blocking_before=semantic_blocking_before,
            semantic_blocking_after=semantic_blocking_after,
            semantic_audit_available=semantic_audit_available,
            optimize_plan_summary=optimize_plan_summary,
        )

    def _build_stage_prompt(
        self,
        task: AgentTask,
        previous_tasks: list[AgentTask],
        results: list[LLMCallResult],
        memory: SharedMemory,
        target_ctx: AgentTargetContext,
        activity_number: int,
        applied_tex: dict[str, object],
        compile_results: list[dict[str, object]],
    ) -> str:
        sections = [task.prompt, "\n## Memoria actualizada\n" + memory.summary(max_chars=12000)]
        for previous, result in list(zip(previous_tasks, results))[-5:]:
            text = result.text if result.ok else result.error
            excerpt = text[:24000]
            if len(text) > len(excerpt):
                excerpt += "\n[Resultado truncado; no asumir cobertura completa.]"
            sections.append(f"\n## Resultado {previous.stage} ({'OK' if result.ok else 'ERROR'})\n{excerpt}")
        if self._base_stage(task.stage) in {"validar", "criticar"}:
            sections.append("\n## Aplicacion de la propuesta\n" + json.dumps(applied_tex, ensure_ascii=False))
            sections.append("\n## Compilacion observada\n" + json.dumps(compile_results, ensure_ascii=False))
            for tex in self._select_compile_targets(target_ctx, activity_number):
                text = tex.read_text(encoding="utf-8", errors="replace")
                excerpt = text[:60000]
                if len(text) > len(excerpt):
                    excerpt += "\n[Documento truncado; no asumir revision completa.]"
                sections.append(f"\n## TEX actual: {self.workspace.relative(tex)}\n```tex\n{excerpt}\n```")
            sections.append(
                "Evalua el TEX actual y la evidencia de compilacion, no solo la propuesta. "
                "Una compilacion ausente o fallida no demuestra que el documento sea compilable."
            )
        return "\n\n".join(sections)

    def _prepare_artifacts(
        self,
        request: AgentRequest,
        target_ctx: AgentTargetContext,
        tasks: list[AgentTask],
        results: list[LLMCallResult],
        workflow: AgenticStateMachine,
        run_dir: Path,
    ) -> tuple[MaterializationResult | None, dict[str, object], list[dict[str, object]]]:
        materialization: MaterializationResult | None = None
        if self._should_materialize_template(request, target_ctx):
            workflow.record("materialize-start", "ok", f"{request.action} materializara los archivos faltantes de la actividad")
            materialization = self.template_materializer.materialize_subject(
                target_ctx.target_path,
                activity_number=request.activity_number,
                force=request.action.strip().lower() == "generar-plantilla",
            )
            workflow.record(
                "materialize-end", "ok" if materialization.ok else "error",
                f"{len(materialization.artifacts)} artefactos procesados",
            )
        applied_tex = self._apply_generated_tex(request, target_ctx, tasks, results, workflow)
        compile_results: list[dict[str, object]] = []
        if request.compile_tex:
            workflow.record("tool-select", "ok", "latexmk-build.ps1 seleccionado para compilar objetivos canonicos")
            for tex in self._select_compile_targets(target_ctx, request.activity_number):
                invocation = safe_invoke(self.workspace.compile_tex, tex, clean_mode="safe")
                if invocation.ok:
                    build = invocation.result
                    ok = bool(build.ok) and build.returncode == 0
                    returncode = int(build.returncode)
                    stdout, stderr = build.stdout or "", build.stderr or ""
                else:
                    ok, returncode, stdout, stderr = False, 1, "", invocation.error
                compile_results.append({
                    "tex": self.workspace.relative(tex), "ok": ok, "returncode": returncode,
                    "stdout_tail": stdout[-3000:], "stderr_tail": stderr[-3000:],
                })
                (run_dir / f"compile-{tex.stem}.log.txt").write_text(stdout + "\n" + stderr, encoding="utf-8")
                workflow.record("tool-result", "ok" if ok else "error", f"{self.workspace.relative(tex)} rc={returncode}")
            if workflow.state == "generated":
                workflow.transition("compiled", "compilacion latexmk ejecutada")
        return materialization, applied_tex, compile_results

    def _postprocess_activity(
        self,
        request: AgentRequest,
        target_ctx: AgentTargetContext,
        run_dir: Path,
        report_path: Path,
    ) -> tuple[
        bool | None,
        bool | None,
        float | None,
        float | None,
        bool | None,
        int | None,
        int | None,
        bool | None,
        dict[str, object] | None,
    ]:
        """Encadena monitor + optimize + compilación final tras realizar-actividad.

        - Solo aplica a la acción realizar-actividad en nivel materia/actividad y
          modo de generación directo (no descendente).
        - El monitor converge el contrato editorial aplicando parches reales.
        - El optimizador eleva la calidad del .tex de forma verificada.
        - La compilación final con latexmk regenera el PDF sobre el .tex ya
          modificado por monitor/optimize (paso final por defecto).
        Cualquiera puede desactivarse con run_monitor / run_optimize /
        run_final_compile.
        """
        action = request.action.strip().lower()
        if action != "realizar-actividad" or request.level not in {"materia", "actividad"}:
            return None, None, None, None, None, None, None, None, None
        if target_ctx.generation_mode == "downward":
            return None, None, None, None, None, None, None, None, None

        monitor_ok: bool | None = None
        optimize_ok: bool | None = None
        quality_before: float | None = None
        quality_after: float | None = None
        final_compile_ok: bool | None = None
        semantic_blocking_before: int | None = None
        semantic_blocking_after: int | None = None
        semantic_audit_available: bool | None = None
        optimize_plan_summary: dict[str, object] | None = None
        report_lines: list[str] = []

        # 0) Producto FORO: si la actividad es un foro, aplicar el patrón editorial
        #    maduro (tcolorbox + botón de copia + 3 actos + footnote IA, sin
        #    metadiscurso) de forma determinista ANTES de monitor/optimize.
        if request.run_foro_producto:
            from .foro_producto import ForoProductoRequest, ForoProductoTransformer

            foro_invocation = safe_invoke(
                ForoProductoTransformer(self.workspace).run,
                ForoProductoRequest(
                    target=str(target_ctx.target_path),
                    activity_number=request.activity_number,
                    apply=True,
                ),
            )
            if foro_invocation.ok and foro_invocation.result.is_foro:
                res = foro_invocation.result
                report_lines.append(
                    f"- Producto foro: {'APLICADO' if res.applied else 'SIN CAMBIOS'} "
                    f"({len(res.changes)} cambios)"
                )
            elif not foro_invocation.ok:
                report_lines.append(f"- Producto foro: ERROR ({foro_invocation.error})")

        if request.run_monitor:
            monitor_invocation = safe_invoke(
                self.activity_monitor.run,
                ActivityMonitorRequest(
                    target=str(target_ctx.target_path),
                    activity_number=request.activity_number,
                    output=str(run_dir / "post-monitor"),
                    max_cycles=max(1, int(request.monitor_max_cycles)),
                    compile_check=True,
                    apply_bibliography_repair=True,
                    apply_revision_patches=True,
                    run_detail_planner=False,
                ),
            )
            if monitor_invocation.ok:
                monitor_ok = bool(monitor_invocation.result.ok)
                report_lines.append(
                    f"- Monitor: {'PASS' if monitor_ok else 'PENDIENTE'} "
                    f"(`{self.workspace.relative(monitor_invocation.result.manifest_path)}`)"
                )
            else:
                monitor_ok = False
                report_lines.append(f"- Monitor: ERROR ({monitor_invocation.error})")

        if request.run_optimize:
            # Por DEFECTO se optimiza hasta CONVERGER a calidad objetivo (cycles=0),
            # no un número fijo. Si el usuario fija optimize_cycles>0, se respeta.
            optimize_invocation = safe_invoke(
                self.activity_optimizer.optimize,
                ActivityOptimizeRequest(
                    target=str(target_ctx.target_path),
                    activity_number=request.activity_number,
                    output=str(run_dir / "post-optimize"),
                    cycles=max(0, int(request.optimize_cycles)),
                    engines=self._optimize_engines(request.engines),
                    # El monitor ya valida los checks requeridos del contrato.
                    # Permitir aquí reparar rangos no bloqueantes (p. ej.
                    # no_metadiscourse) sin aceptar una regresión del score.
                    require_contract_100=False,
                    run_semantic_audit=request.run_semantic_audit,
                    semantic_fail_closed=request.semantic_fail_closed,
                    semantic_feedback_path=request.semantic_feedback_path,
                ),
            )
            if optimize_invocation.ok:
                result = optimize_invocation.result
                optimize_ok = bool(result.ok)
                quality_before = result.quality_before
                quality_after = result.quality_after
                semantic_blocking_before = result.semantic_blocking_before
                semantic_blocking_after = result.semantic_blocking_after
                semantic_audit_available = result.semantic_audit_available
                optimize_plan_summary = self._load_planned_action_summary(result.manifest_path)
                report_lines.append(
                    f"- Optimización: {result.applied_cycles} ciclo(s) aplicados, "
                    f"calidad {result.quality_before}→{result.quality_after}; "
                    f"bloqueos semánticos "
                    f"{result.semantic_blocking_before}→{result.semantic_blocking_after} "
                    f"(`{self.workspace.relative(result.manifest_path)}`)"
                )
                summary_line = self._format_planned_action_summary(optimize_plan_summary)
                if summary_line:
                    report_lines.append(summary_line)
            else:
                optimize_ok = False
                report_lines.append(f"- Optimización: ERROR ({optimize_invocation.error})")

        # 2.5) Producto MAPA CONCEPTUAL: si el .tex contiene un mapa conceptual TikZ
        #      (estilos mc*), correr el optimizador de layout que resuelve choques,
        #      coloca las palabras de enlace sin empalmes (place_labels) y llena el
        #      alto de la página (estira Y / comprime X). Se ejecuta tras monitor/
        #      optimize para que las coordenadas absolutas sean el estado definitivo.
        if request.run_mapa_layout:
            mapa_note = self._optimize_mapa_layout(target_ctx.target_path)
            if mapa_note:
                report_lines.append(mapa_note)

        if request.run_final_compile:
            final_targets = self._select_compile_targets(target_ctx, request.activity_number)
            all_ok = bool(final_targets)
            for tex in final_targets:
                invocation = safe_invoke(self.workspace.compile_tex, tex, clean_mode="safe")
                pdf_path = tex.with_suffix(".pdf")
                pdf_fresh = pdf_path.is_file() and pdf_path.stat().st_mtime_ns >= tex.stat().st_mtime_ns
                if invocation.ok:
                    build = invocation.result
                    ok = bool(build.ok) and build.returncode == 0 and pdf_fresh
                    log_path = run_dir / f"final-compile-{tex.stem}.log.txt"
                    log_path.write_text(
                        (build.stdout or "") + "\n" + (build.stderr or ""), encoding="utf-8"
                    )
                else:
                    ok = False
                    (run_dir / f"final-compile-{tex.stem}.log.txt").write_text(
                        invocation.error or "", encoding="utf-8"
                    )
                all_ok = all_ok and ok
                report_lines.append(
                    f"- Compilación final (latexmk): {self.workspace.relative(tex)} "
                    f"{'OK' if ok else 'ERROR'}"
                    + ("" if ok else " (revisar log final-compile-*.log.txt)")
                )
            final_compile_ok = all_ok
            if not final_targets:
                report_lines.append("- Compilación final: ERROR (sin objetivos TEX).")

        if report_lines:
            report_path.write_text(
                report_path.read_text(encoding="utf-8")
                + "\n\n## Post-procesamiento automático (monitor + optimización + compilación final)\n\n"
                + "\n".join(report_lines)
                + "\n",
                encoding="utf-8",
            )

        return (
            monitor_ok,
            optimize_ok,
            quality_before,
            quality_after,
            final_compile_ok,
            semantic_blocking_before,
            semantic_blocking_after,
            semantic_audit_available,
            optimize_plan_summary,
        )

    def _load_planned_action_summary(self, manifest_path: Path) -> dict[str, object] | None:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        summary = payload.get("planned_action_summary")
        return summary if isinstance(summary, dict) else None

    def _format_planned_action_summary(self, summary: dict[str, object] | None) -> str | None:
        if not summary:
            return None
        policy_cycles = int(summary.get("policy_cycles") or 0)
        if policy_cycles <= 0:
            return "- Optimización (política): sin ciclos guiados por la política entrenada en esta corrida."
        return (
            "- Optimización (política): "
            f"uso {float(summary.get('policy_usage_rate') or 0.0):.1%}, "
            f"alineación acción {float(summary.get('action_alignment_rate') or 0.0):.1%}, "
            f"aceptados alineados={int(summary.get('accepted_aligned_policy_cycles') or 0)}, "
            f"aceptados desalineados={int(summary.get('accepted_misaligned_policy_cycles') or 0)}, "
            f"Δ medio={float(summary.get('mean_policy_quality_delta') or 0.0):+.2f}."
        )

    def _optimize_mapa_layout(self, target_path: Path) -> str | None:
        """Aplica el optimizador de layout TikZ si el .tex es un mapa conceptual.

        Detecta el mapa por los estilos mc* (mcroot + mcbranch). Ejecuta
        scripts/optimize_mapa_layout.py con --write para: resolver choques,
        colocar las palabras de enlace sin empalmes (place_labels) y llenar el
        alto de la página (estira Y / comprime X, --target-aspect 1.4).
        Devuelve una línea de reporte o None si no aplica.
        """
        import subprocess
        import sys as _sys

        tex = Path(target_path)
        if not tex.is_file() or tex.suffix.lower() != ".tex":
            return None
        try:
            content = tex.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        # Detección: mapa conceptual con estilos mc*
        if "mcroot" not in content or "mcbranch" not in content:
            return None

        script = Path(__file__).resolve().parents[1] / "optimize_mapa_layout.py"
        if not script.is_file():
            return "- Mapa (optimizador TikZ): script no encontrado"
        cmd = [
            _sys.executable, str(script), str(tex),
            "--iters", "1200", "--repulsion", "0.35", "--step", "0.2",
            "--spring", "0.03", "--xlim", "13.5", "--ylim", "11",
            "--target-aspect", "1.4", "--vspread", "1.4", "--hspread", "1.08",
            "--label-clearance", "1.35", "--write",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except (subprocess.SubprocessError, OSError) as exc:
            return f"- Mapa (optimizador TikZ): ERROR ({exc})"
        tail = (proc.stdout or "").strip().splitlines()
        summary = tail[0] if tail else ""
        status = "APLICADO" if proc.returncode == 0 else f"rc={proc.returncode}"
        return f"- Mapa conceptual (optimizador TikZ): {status} {summary}".rstrip()

    def _build_prompts(self, request: AgentRequest, context: str) -> list[str]:
        base = (
            "Eres AulaTeX, agente editorial academico para plantillas LaTeX institucionales. "
            "Trabaja en espanol academico, con criterio editorial, trazabilidad, enfoque institucional "
            "y salida accionable. No inventes fuentes; si falta informacion, marca supuestos.\n\n"
            f"Nivel: {request.level}\n"
            f"Accion: {request.action}\n"
            f"Actividad: {request.activity_number}\n\n"
            f"Contexto local:\n{context}\n"
        )
        research = (
            base
            + "\nTAREA 1 INVESTIGAR: diagnostica el estado editorial del objetivo. "
            "Identifica identidad institucional, estructura, bibliografia, faltantes, riesgos de compilacion "
            "y oportunidades de mejora. Devuelve hallazgos priorizados."
        )
        generate = (
            base
            + "\nTAREA 2 GENERAR: propone la plantilla o actividad solicitada. "
            "Incluye estructura para reporte y presentacion cuando aplique, pauta de realizacion, "
            "bibliografia local y criterios de revision. Entrega bloques listos para convertir a archivos."
        )
        evaluate = (
            base
            + "\nTAREA 3 EVALUAR: revisa la propuesta como editor severo. "
            "Devuelve checklist, pruebas de compilacion recomendadas, riesgos, criterios de aceptacion "
            "y siguiente ciclo incremental investigar-compilar-evaluar."
        )
        return [research, generate, evaluate]

    def _normalize_engines(self, engines: list[str]) -> list[str]:
        allowed = set(self.llm.engines() or LLM_ENGINES)
        out = [engine for engine in restrict_engines_to_available(engines) if engine in allowed]
        return out or [MODEL_ROUTER_ENGINE]

    def _optimize_engines(self, engines: list[str]) -> tuple[str, ...]:
        """Motores para la optimización de calidad.

        Respeta el modo exclusivo de model-router. Fuera de ese modo, prefiere
        GPT-5.6 (Luna/Terra) por su fiabilidad con prompts largos.
        """
        restricted = restrict_engines_to_available(engines)
        if restricted == [MODEL_ROUTER_ENGINE]:
            return (MODEL_ROUTER_ENGINE,)
        allowed = set(self.llm.engines() or LLM_ENGINES)
        requested_gpt56 = [e for e in restricted if e in allowed and e.startswith("GPT-5.6")]
        if requested_gpt56:
            return tuple(requested_gpt56)
        preferred = [e for e in ("GPT-5.6-Luna", "GPT-5.6-Terra") if e in allowed]
        return tuple(preferred) or tuple(self._normalize_engines(engines))

    def _record_stage_transition(self, workflow: AgenticStateMachine, base_stage: str) -> None:
        if base_stage == "planificar":
            if workflow.state == "initialized":
                workflow.transition("planned", "plan editorial producido")
            else:
                workflow.record("cycle-stage", "ok", "plan editorial reforzado en ciclo posterior")
        elif base_stage == "investigar":
            if workflow.state == "planned":
                workflow.transition("researched", "diagnostico documental producido")
            else:
                workflow.record("cycle-stage", "ok", "diagnostico documental reforzado en ciclo posterior")
        elif base_stage == "generar":
            if workflow.state == "researched":
                workflow.transition("generated", "propuesta editorial producida")
            else:
                workflow.record("cycle-stage", "ok", "propuesta editorial reforzada en ciclo posterior")

    def _normalize_cycle_mode(self, mode: str) -> str:
        value = (mode or "stages").strip().lower()
        return value if value in {"stages", "full"} else "stages"

    def _expand_tasks(self, base_tasks: list[AgentTask], iterations: int, cycle_mode: str) -> list[AgentTask]:
        count = max(1, int(iterations))
        if cycle_mode == "full":
            tasks: list[AgentTask] = []
            for cycle_index in range(1, count + 1):
                for task in base_tasks:
                    tasks.append(
                        AgentTask(
                            stage=f"{task.stage}-ciclo-{cycle_index:03d}",
                            role=task.role,
                            mission=f"{task.mission} | ciclo intensivo {cycle_index}/{count}",
                            prompt=(
                                task.prompt
                                + "\n\nCICLO INTENSIVO AULATEX:\n"
                                + f"- Ciclo actual: {cycle_index} de {count}.\n"
                                + "- No repitas sin mejora: usa memoria compartida, hallazgos previos y riesgos acumulados.\n"
                                + "- Devuelve avances incrementales, huecos restantes, decisiones aceptables y siguiente accion verificable.\n"
                            ),
                            weight=task.weight,
                        )
                    )
            return tasks
        return base_tasks[: max(1, min(count, len(base_tasks)))]

    def _base_stage(self, stage: str) -> str:
        return stage.split("-ciclo-", 1)[0]

    def _resolve_target_context(self, request: AgentRequest) -> AgentTargetContext:
        target = self.workspace.resolve_target(request.target)
        if request.generation_mode != "downward":
            scope = self.workspace.find_scope_for_target(target, activity_number=request.activity_number)
            return AgentTargetContext(
                target_path=target,
                context_path=target,
                scope_key=scope.key if scope is not None else "",
                display_target=self.workspace.relative(target),
                generation_mode="direct",
            )

        by_key, _children = self.workspace.editorial_scope_index()
        parent_scope = by_key.get(request.parent_scope_key)
        if parent_scope is None:
            raise ValueError("No se pudo resolver el padre editorial para la generacion descendente.")

        parent_path = self.workspace.resolve_target(parent_scope.relative_path)
        child_name = request.child_name.strip() if request.child_name.strip() else f"Actividad {request.activity_number}"
        child_preview = self._preview_child(parent_scope, request.child_level, child_name, request.activity_number)
        return AgentTargetContext(
            target_path=parent_path,
            context_path=parent_path,
            scope_key=parent_scope.key,
            display_target=f"{parent_scope.key} -> {request.child_level}:{child_name}",
            generation_mode="downward",
            parent_scope_key=parent_scope.key,
            child_level=request.child_level,
            child_name=child_name,
            child_preview=child_preview,
        )

    def _preview_child(self, parent_scope, child_level: str, child_name: str, activity_number: int) -> str:
        parent_rel = parent_scope.relative_path.rstrip("/")
        if child_level == "actividad":
            return f"{parent_rel} :: reporte-{parent_scope.label}-Actividad-{activity_number}.tex"
        slug = child_name.strip().lower().replace(" ", "-")
        return f"{parent_rel}/{slug}"

    def _select_compile_targets(self, target_ctx: AgentTargetContext, activity_number: int) -> list[Path]:
        if target_ctx.generation_mode == "downward":
            return []
        tex_files = self.workspace.find_tex_files(target_ctx.target_path, limit=30)
        activity_marker = f"actividad-{int(activity_number)}".lower()
        reports = [
            path for path in tex_files
            if path.name.startswith("reporte-") and activity_marker in path.name.lower()
        ]
        presentations = [
            path for path in tex_files
            if path.name.startswith("presentacion-") and activity_marker in path.name.lower()
        ]
        selected = reports[:1] + presentations[:1]
        return selected

    def _should_materialize_template(self, request: AgentRequest, target_ctx: AgentTargetContext) -> bool:
        action = request.action.strip().lower()
        if target_ctx.generation_mode != "direct" or request.level not in {"materia", "actividad"}:
            return False
        if action == "realizar-actividad":
            return not self._select_compile_targets(target_ctx, request.activity_number)
        return (
            action == "generar-plantilla"
        )

    @staticmethod
    def _extract_tex_document(text: str) -> str:
        """Devuelve el documento LaTeX completo contenido en la respuesta del LLM.

        El arquitecto responde en markdown y envuelve el TEX en vallas de código.
        Sin este rescate su redacción se queda en el log y el .tex conserva la
        plantilla con \\pendiente{}.
        """
        if not text:
            return ""
        candidates: list[str] = []
        for match in re.finditer(r"```(?:la)?tex\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE):
            candidates.append(match.group(1))
        if not candidates:
            for match in re.finditer(r"```\s*\n(.*?)```", text, re.DOTALL):
                candidates.append(match.group(1))
        if not candidates:
            candidates.append(text)

        for body in sorted(candidates, key=len, reverse=True):
            if r"\begin{document}" in body and r"\end{document}" in body:
                start = body.index("\\documentclass") if "\\documentclass" in body else 0
                end = body.index(r"\end{document}") + len(r"\end{document}")
                document = body[start:end].strip()
                if "\\documentclass" in document:
                    return document
        return ""

    def _apply_generated_tex(
        self,
        request: AgentRequest,
        target_ctx: AgentTargetContext,
        tasks: list[AgentTask],
        stage_results: list[LLMCallResult],
        workflow: AgenticStateMachine,
    ) -> dict[str, object]:
        """Vuelca al .tex la redacción del arquitecto cuando el archivo sigue vacío.

        Solo actúa si el destino conserva placeholders activos, de modo que nunca
        pisa una actividad ya redactada.
        """
        summary: dict[str, object] = {"applied": False, "reason": "", "target": "", "chars": 0}
        if request.action.strip().lower() != "realizar-actividad":
            summary["reason"] = "accion-no-aplicable"
            return summary

        targets = self._select_compile_targets(target_ctx, request.activity_number)
        destination: Path | None = None
        if target_ctx.target_path.is_file() and target_ctx.target_path.suffix.lower() == ".tex":
            destination = target_ctx.target_path
        elif len(targets) == 1:
            destination = targets[0]
        else:
            destination = next((p for p in targets if p.name.startswith("reporte-")), None)
        if destination is None:
            summary["reason"] = "sin-destino-tex"
            return summary

        current = destination.read_text(encoding="utf-8", errors="replace")
        active_text = re.sub(r"(?<!\\)%[^\n]*", "", current)
        is_placeholder = bool(re.search(r"\\pendiente\{", active_text))
        is_scaffold = not active_text.strip() or "en construcción" in active_text.lower()
        if not is_placeholder and not is_scaffold:
            summary["reason"] = "destino-ya-redactado"
            return summary

        document = ""
        for task, result in zip(tasks, stage_results):
            if self._base_stage(task.stage) != "generar" or not result.ok or not result.text.strip():
                continue
            candidate = self._extract_tex_document(result.text)
            if len(candidate) > len(document):
                document = candidate
        if not document:
            summary["reason"] = "arquitecto-sin-tex-completo"
            workflow.record("apply-generated-tex", "error", "la etapa generar no devolvio un documento LaTeX completo")
            return summary
        if re.search(r"\\pendiente\{", document):
            summary["reason"] = "propuesta-con-placeholders"
            workflow.record("apply-generated-tex", "error", "la propuesta del arquitecto aun trae placeholders")
            return summary
        if destination.name.startswith("presentacion-") and "beamer" not in document[:500].lower():
            summary["reason"] = "propuesta-no-es-presentacion"
            workflow.record("apply-generated-tex", "error", "el destino es una presentación pero el documento generado no usa Beamer")
            return summary

        destination.write_text(document, encoding="utf-8")
        summary.update(
            {
                "applied": True,
                "reason": "propuesta-del-arquitecto-aplicada",
                "target": self.workspace.relative(destination),
                "chars": len(document),
            }
        )
        workflow.record("apply-generated-tex", "ok", f"{summary['target']}: {len(document)} chars aplicados")
        return summary

    def _should_run_extractor(self, request: AgentRequest, target_ctx: AgentTargetContext) -> bool:
        if request.skip_extractor or target_ctx.generation_mode == "downward":
            return False
        action = request.action.strip().lower()
        if request.run_extractor:
            return True
        return action in {"realizar-actividad", "generar-actividad"} and request.level in {"materia", "actividad"}

    def _should_run_detail_planner(self, request: AgentRequest, target_ctx: AgentTargetContext) -> bool:
        if not request.run_detail_planner or target_ctx.generation_mode == "downward":
            return False
        return request.action.strip().lower() == "realizar-actividad" and request.level in {"materia", "actividad"}

    def _detail_planner_context(self, result: DetailPlannerResult) -> str:
        report = result.report_path.read_text(encoding="utf-8")
        return "## Detail planner previo\n\n" + report[:6000]

    def _detail_planner_manifest(self, result: DetailPlannerResult | None) -> dict:
        if result is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "ok": result.ok,
            "run_dir": self.workspace.relative(result.run_dir),
            "manifest": self.workspace.relative(result.manifest_path),
            "report": self.workspace.relative(result.report_path),
            "processed_scopes": list(result.processed_scopes),
            "updated_scopes": list(result.updated_scopes),
        }

    def _run_extractor_tool(
        self,
        request: AgentRequest,
        target_ctx: AgentTargetContext,
        workflow: AgenticStateMachine,
        memory: SharedMemory,
    ) -> ExtractorRunResult | None:
        workflow.record("tool-select", "ok", "ExtractorAdapter seleccionado para run-extractor")
        invocation = safe_invoke(self.extractor_adapter.run, self._build_extractor_request(request, target_ctx))
        if invocation.ok:
            result = invocation.result
            workflow.record(
                "tool-result",
                "ok" if result.ok else "error",
                f"extractor ok={result.ok} salida={self.workspace.relative(result.output_dir)}",
            )
            memory.remember("note", f"Extractor ejecutado: {self.workspace.relative(result.manifest_path)}")
            return result
        workflow.record("tool-result", "error", f"extractor fallo: {invocation.error}")
        memory.remember("risk", f"Extractor no ejecutado: {invocation.error}")
        return None

    def _build_extractor_request(self, request: AgentRequest, target_ctx: AgentTargetContext) -> ExtractorRequest:
        return ExtractorRequest(
            target=str(target_ctx.target_path),
            activity_number=request.activity_number,
            fuentes=request.extractor_fuentes,
            planeacion=request.extractor_planeacion,
            conceptos=request.extractor_conceptos,
            salida=request.extractor_salida,
            motor=request.extractor_motor,
            probe_only=request.extractor_probe_only,
        )

    def _extractor_manifest(self, result: ExtractorRunResult | None) -> dict:
        if result is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "ok": result.ok,
            "run_dir": self.workspace.relative(result.run_dir),
            "manifest": self.workspace.relative(result.manifest_path),
            "output_dir": self.workspace.relative(result.output_dir),
            "stdout": self.workspace.relative(result.stdout_path),
            "stderr": self.workspace.relative(result.stderr_path),
        }

    def _materialization_manifest(self, result: MaterializationResult | None) -> dict:
        if result is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "ok": result.ok,
            "target_dir": self.workspace.relative(result.target_dir),
            "artifacts": [self.workspace.relative(path) for path in result.artifacts],
            "notes": list(result.notes),
        }

    def _render_materialization_report(self, result: MaterializationResult) -> str:
        lines = [
            "## Materializacion de plantilla",
            "",
            f"- Estado: {'OK' if result.ok else 'CON OBSERVACIONES'}",
            f"- Carpeta: `{self.workspace.relative(result.target_dir)}`",
            "",
            "### Artefactos",
        ]
        lines.extend(f"- `{self.workspace.relative(path)}`" for path in result.artifacts)
        lines.append("")
        return "\n".join(lines)

    def _format_stage(self, result: LLMCallResult, task: AgentTask) -> str:
        status = "ok" if result.ok else "error"
        body = result.text if result.ok else result.error
        return (
            "# AulaTeX stage\n\n"
            f"- Etapa: {task.stage}\n"
            f"- Rol: {task.role}\n"
            f"- Mision: {task.mission}\n"
            f"- Motor: {result.engine}\n"
            f"- Estado: {status}\n\n"
            f"{body}\n"
        )

    def _build_report(
        self,
        request: AgentRequest,
        target_ctx: AgentTargetContext,
        tasks: list[AgentTask],
        stage_results: list[LLMCallResult],
        compile_results: list[dict],
        consensus,
        extractor_result: ExtractorRunResult | None = None,
        detail_plan_result: DetailPlannerResult | None = None,
    ) -> str:
        lines = [
            "# Reporte AulaTeX",
            "",
            f"- Objetivo: `{target_ctx.display_target}`",
            f"- Nivel: {request.level}",
            f"- Accion: {request.action}",
            f"- Actividad: {request.activity_number}",
            "",
            "## Arquitectura agentica",
            "",
            "- Planificacion con memoria compartida",
            "- Uso de herramientas con invocacion segura",
            "- Flujo con maquina de estados y auditoria",
            "- Verificacion/validacion editorial",
            "- Consenso multiagente con critico adversarial",
            "",
            "## Contexto de ejecucion",
            "",
            f"- Modo de generacion: {request.generation_mode}",
            f"- Padre editorial: {target_ctx.parent_scope_key or 'N/A'}",
            f"- Nivel hijo: {target_ctx.child_level or 'N/A'}",
            f"- Hijo solicitado: {target_ctx.child_name or 'N/A'}",
            f"- Vista previa: {target_ctx.child_preview or 'N/A'}",
            "",
            "## Detail planner",
            "",
        ]
        if detail_plan_result is not None:
            lines.extend(
                [
                    f"- Estado: {'OK' if detail_plan_result.ok else 'ERROR'}",
                    f"- Reporte: `{self.workspace.relative(detail_plan_result.report_path)}`",
                    f"- Scopes procesados: {len(detail_plan_result.processed_scopes)}",
                    f"- Scopes actualizados: {len(detail_plan_result.updated_scopes)}",
                    "",
                ]
            )
        else:
            lines.extend(["- No se ejecuto detail planner en este ciclo.", ""])
        lines.extend(
            [
            "## Ciclo LLM",
            "",
            ]
        )
        for index, (task, result) in enumerate(zip(tasks, stage_results), start=1):
            lines.append(f"### {index}. {task.stage} - {task.role} - {result.engine}")
            lines.append("")
            lines.append(result.text if result.ok else f"ERROR: {result.error}")
            lines.append("")
        lines.append(consensus.to_markdown())
        lines.extend(["## Extractor", ""])
        if extractor_result is not None:
            lines.append(f"- Estado: {'OK' if extractor_result.ok else 'ERROR'}")
            lines.append(f"- Manifest: `{self.workspace.relative(extractor_result.manifest_path)}`")
            lines.append(f"- Salida: `{self.workspace.relative(extractor_result.output_dir)}`")
        else:
            lines.append("- No se ejecuto extractor en este ciclo.")
        lines.append("")
        lines.extend(["## Compilacion", ""])
        if compile_results:
            for item in compile_results:
                lines.append(f"- {item['tex']}: {'OK' if item['ok'] else 'ERROR'} ({item['returncode']})")
        else:
            lines.append("- No se compilaron archivos en este ciclo.")
        lines.append("")
        return "\n".join(lines)

    def _write_target_feedback(self, target: Path, report_path: Path) -> None:
        if target.is_file():
            target = target.parent
        feedback_dir = target / "retroalimentacion-aulatex"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        dest = feedback_dir / report_path.name
        dest.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
