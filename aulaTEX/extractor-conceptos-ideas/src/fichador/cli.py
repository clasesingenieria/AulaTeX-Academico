from __future__ import annotations

import argparse
from pathlib import Path
import sys
from collections import Counter
from typing import Any

from .env_config import load_env, env_str, env_int, env_float, env_bool
from .document_reader import extract_pages_from_sources, parse_extensions, SUPPORTED_EXTENSIONS, read_any_text_file
from .preprocessing import build_fragments, load_concept_lines, unique_preserve_order
from .concept_extractor import extract_candidate_concepts, extract_candidate_concepts_from_planeacion
from .search import TfidfSearchEngine
from .tfhub_search import TfHubSearchEngine, DEFAULT_TFHUB_MODEL
from .api_client import get_api_config
from .api_search import ApiEmbeddingSearchEngine
from .api_concepts import extract_concepts_with_chat, normalize_concepts_with_chat, curate_concepts_for_subject_with_chat
from .fichas import build_fichas
from .exporters import export_all
from .planeacion_parser import parse_planeacion_text, summarize_planeacion_analysis, PlaneacionAnalizada
from .planeacion_anthropic import (
    planeacion_confidence,
    extract_planeacion_with_anthropic,
    merge_planeacion_analysis,
    concepts_from_remote_planeacion,
)
from .refinement import refine_hits_by_concept
from .subject_profiles import infer_subject_slug, filter_concepts_by_subject


def build_parser() -> argparse.ArgumentParser:
    load_env()
    parser = argparse.ArgumentParser(prog="fichador", description="Genera fichas de conceptos con citas textuales desde una carpeta de fuentes. Incluye Azure/OpenAI.")
    parser.add_argument("--fuentes", default=env_str("FUENTES_DIR", "input/fuentes"), help="Archivo o carpeta con fuentes. Puede venir de FUENTES_DIR en .env.")
    parser.add_argument("--planeacion", default=env_str("PLANEACION_PATH", "input/planeaciones/planeacion_ejemplo.txt"), help="Archivo de planeación para extraer conceptos. Puede venir de PLANEACION_PATH.")
    parser.add_argument("--conceptos", default=env_str("CONCEPTOS_PATH", "input/planeaciones/conceptos_ejemplo.txt"), help="TXT con conceptos, uno por línea. Puede venir de CONCEPTOS_PATH.")
    parser.add_argument("--salida", default=env_str("OUTPUT_DIR", "output"), help="Carpeta de salida. Puede venir de OUTPUT_DIR.")
    parser.add_argument("--recursivo", action=argparse.BooleanOptionalAction, default=env_bool("RECURSIVO", True), help="Busca fuentes en subcarpetas. Default desde RECURSIVO.")
    parser.add_argument("--extensiones", default=env_str("EXTENSIONES", ",".join(sorted(SUPPORTED_EXTENSIONS))), help="Extensiones separadas por coma.")
    parser.add_argument("--motor", choices=["tfidf", "tfhub", "azure", "openai", "anthropicfoundry"], default=env_str("MOTOR", "azure"), help="Motor: tfidf, tfhub, azure, openai o anthropicfoundry.")
    parser.add_argument("--tfhub-model", default=env_str("TFHUB_MODEL", DEFAULT_TFHUB_MODEL), help="Nombre/ruta del modelo de sentence-transformers.")
    parser.add_argument("--top-k", type=int, default=env_int("TOP_K", 12))
    parser.add_argument("--max-citas", type=int, default=env_int("MAX_CITAS", 8))
    parser.add_argument("--umbral", type=float, default=env_float("UMBRAL", None))
    parser.add_argument("--auto-conceptos", type=int, default=env_int("AUTO_CONCEPTOS", 25))
    parser.add_argument("--planeacion-conceptos", type=int, default=env_int("PLANEACION_CONCEPTOS", 20), help="Conceptos a extraer desde la planeación. 0 para desactivar.")
    parser.add_argument("--auto-conceptos-motor", choices=["local", "azure-chat", "openai-chat", "anthropic-chat"], default=env_str("AUTO_CONCEPTOS_MOTOR", "local"), help="Motor opcional para depurar conceptos automáticos.")
    parser.add_argument("--normalizar-conceptos-con-chat", action=argparse.BooleanOptionalAction, default=env_bool("NORMALIZAR_CONCEPTOS_CON_CHAT", False), help="Usa chat para normalizar conceptos, sin generar citas.")
    parser.add_argument("--depurar-conceptos-por-materia", action=argparse.BooleanOptionalAction, default=env_bool("DEPURAR_CONCEPTOS_POR_MATERIA", True), help="Aplica una depuración específica por materia antes de construir fichas.")
    parser.add_argument("--materia-slug", default=env_str("MATERIA_SLUG"), help="Slug de materia para aplicar un perfil editorial específico. Si no se indica, se intenta inferir automáticamente.")
    parser.add_argument("--conceptos-por-materia-top", type=int, default=env_int("CONCEPTOS_POR_MATERIA_TOP", 20), help="Número máximo de conceptos que se conservan tras la depuración por materia.")
    parser.add_argument("--planeacion-asistida-con-chat", action=argparse.BooleanOptionalAction, default=env_bool("PLANEACION_ASISTIDA_CON_CHAT", True), help="Usa un modelo de chat para reconstruir o validar la estructura de la planeación cuando sea necesario.")
    parser.add_argument("--planeacion-chat-auto", action=argparse.BooleanOptionalAction, default=env_bool("PLANEACION_CHAT_AUTO", True), help="Activa la asistencia de chat solo cuando la confianza del parser local sea baja.")
    parser.add_argument("--planeacion-confianza-minima", type=float, default=env_float("PLANEACION_CONFIANZA_MINIMA", 0.75) or 0.75, help="Umbral mínimo de confianza del parser local antes de invocar asistencia de chat.")
    parser.add_argument("--refinar-fichas-iterativamente", action=argparse.BooleanOptionalAction, default=env_bool("REFINAR_FICHAS_ITERATIVAMENTE", True), help="Refina cada concepto con ciclos de evaluación y expansión guiados por el modelo de chat.")
    parser.add_argument("--rondas-refinamiento", type=int, default=env_int("RONDAS_REFINAMIENTO", 2), help="Número máximo de rondas de refinamiento por concepto.")
    parser.add_argument("--consultas-expansion", type=int, default=env_int("CONSULTAS_EXPANSION", 3), help="Consultas adicionales máximas sugeridas por el modelo en cada ronda.")
    parser.add_argument("--hits-por-expansion", type=int, default=env_int("HITS_POR_EXPANSION", 4), help="Número máximo de hits que se recuperan por cada consulta de expansión.")
    parser.add_argument("--max-caracteres-cita", type=int, default=env_int("MAX_CARACTERES_CITA", 700))
    parser.add_argument("--max-caracteres-fragmento", type=int, default=env_int("MAX_CARACTERES_FRAGMENTO", 1200))
    parser.add_argument("--min-caracteres-fragmento", type=int, default=env_int("MIN_CARACTERES_FRAGMENTO", 160))
    parser.add_argument("--api-batch-size", type=int, default=env_int("API_BATCH_SIZE", 64))
    parser.add_argument("--cache-embeddings", action=argparse.BooleanOptionalAction, default=env_bool("CACHE_EMBEDDINGS", True))
    parser.add_argument("--azure-base-url", default=env_str("AZURE_OPENAI_BASE_URL") or env_str("AZURE_OPENAI_ENDPOINT"))
    parser.add_argument("--azure-api-key", default=env_str("AZURE_OPENAI_API_KEY"))
    parser.add_argument("--azure-embedding-deployment", default=env_str("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"))
    parser.add_argument("--azure-chat-deployment", default=env_str("AZURE_OPENAI_CHAT_DEPLOYMENT"))
    parser.add_argument("--anthropic-base-url", default=env_str("ANTHROPIC_FOUNDRY_BASE_URL") or env_str("ANTHROPIC_FOUNDRY_ENDPOINT"))
    parser.add_argument("--anthropic-api-key", default=env_str("ANTHROPIC_FOUNDRY_API_KEY"))
    parser.add_argument("--anthropic-chat-deployment", default=env_str("ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT"))
    parser.add_argument("--openai-api-key", default=env_str("OPENAI_API_KEY"))
    parser.add_argument("--openai-embedding-model", default=env_str("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    parser.add_argument("--openai-chat-model", default=env_str("OPENAI_CHAT_MODEL"))
    parser.add_argument("--probar-config", action="store_true", help="Solo revisa configuración y fuentes; no genera fichas.")
    parser.add_argument("--probar-tfhub", action="store_true", help="Carga el modelo de embeddings local de prueba y sale.")
    parser.add_argument("--probar-azure", action="store_true", help="Prueba embeddings con Azure y sale.")
    parser.add_argument("--probar-anthropic", action="store_true", help="Prueba mensajes con Anthropic Foundry y sale.")
    parser.add_argument("--probar-openai", action="store_true", help="Prueba embeddings con OpenAI público y sale.")
    return parser


def _build_api_config(args, provider: str):
    return get_api_config(
        provider,
        azure_base_url=args.azure_base_url,
        azure_api_key=args.azure_api_key,
        azure_embedding_deployment=args.azure_embedding_deployment,
        azure_chat_deployment=args.azure_chat_deployment,
        anthropic_base_url=args.anthropic_base_url,
        anthropic_api_key=args.anthropic_api_key,
        anthropic_chat_deployment=args.anthropic_chat_deployment,
        openai_api_key=args.openai_api_key,
        openai_embedding_model=args.openai_embedding_model,
        openai_chat_model=args.openai_chat_model,
    )


def _load_concepts(args, fragments) -> tuple[list[str], PlaneacionAnalizada | None, dict | None, dict | None, str | None, dict | None]:
    concepts: list[str] = []
    analysis: PlaneacionAnalizada | None = None
    remote_planeacion: dict | None = None
    final_planeacion: dict | None = None
    concept_curation: dict | None = None
    subject_slug = args.materia_slug or infer_subject_slug(args.fuentes, args.planeacion)
    from_file = load_concept_lines(args.conceptos)
    if from_file:
        print(f"[3/5] Conceptos cargados desde archivo: {len(from_file)}")
        concepts.extend(from_file)

    if args.planeacion and args.planeacion_conceptos > 0:
        ptext = read_any_text_file(args.planeacion)
        if ptext.strip():
            analysis = parse_planeacion_text(ptext)
            summary = summarize_planeacion_analysis(analysis)
            if summary:
                print(f"      Interpretación de planeación: {summary}")
            confidence = planeacion_confidence(analysis)
            print(f"      Confianza parser local de planeación: {confidence:.2f}")

            use_remote_planeacion = False
            if args.planeacion_asistida_con_chat and args.motor == "anthropicfoundry":
                if args.planeacion_chat_auto:
                    use_remote_planeacion = confidence < args.planeacion_confianza_minima
                else:
                    use_remote_planeacion = True

            if use_remote_planeacion:
                print("      Refinando estructura de planeación con Anthropic Foundry")
                remote_planeacion = extract_planeacion_with_anthropic(args.planeacion, _build_api_config(args, "anthropicfoundry"))
                final_planeacion = merge_planeacion_analysis(analysis, remote_planeacion)
                remote_concepts = concepts_from_remote_planeacion(remote_planeacion)
                if remote_concepts:
                    print(f"      Conceptos recuperados por Anthropic desde la planeación: {len(remote_concepts)}")
                    concepts.extend(remote_concepts)
            else:
                final_planeacion = merge_planeacion_analysis(analysis, None)

            from_plan = extract_candidate_concepts_from_planeacion(analysis, top_n=args.planeacion_conceptos)
            if from_plan:
                print(f"      Conceptos extraídos desde planeación: {len(from_plan)}")
                concepts.extend(from_plan)

    concepts = unique_preserve_order(concepts)

    if args.depurar_conceptos_por_materia and concepts:
        filtered = filter_concepts_by_subject(concepts, subject_slug, top_n=max(args.conceptos_por_materia_top, len(concepts)))
        if subject_slug:
            print(f"      Perfil editorial detectado para materia: {subject_slug}")
        print(f"      Conceptos tras filtro heurístico por materia: {len(filtered)}")
        concepts = filtered

        if args.motor == "anthropicfoundry":
            concept_curation = curate_concepts_for_subject_with_chat(
                concepts,
                subject_slug=subject_slug,
                config=_build_api_config(args, "anthropicfoundry"),
                top_n=args.conceptos_por_materia_top,
            )
            curated = unique_preserve_order(concept_curation.get("kept", []))
            if curated:
                print(f"      Conceptos tras depuración Anthropic por materia: {len(curated)}")
                concepts = curated

    if concepts and args.normalizar_conceptos_con_chat:
        provider = "azure" if args.motor == "azure" else "openai" if args.motor == "openai" else "anthropicfoundry" if args.motor == "anthropicfoundry" else "azure"
        print(f"      Normalizando conceptos con chat vía {provider}")
        concepts = normalize_concepts_with_chat(concepts, _build_api_config(args, provider), max_items=len(concepts))

    if concepts:
        return concepts, analysis, remote_planeacion, final_planeacion, subject_slug, concept_curation

    if args.auto_conceptos_motor == "azure-chat":
        print(f"[3/5] Detectando {args.auto_conceptos} conceptos: TF-IDF local + depuración con Azure chat")
        concepts = extract_concepts_with_chat(fragments, _build_api_config(args, "azure"), top_n=args.auto_conceptos)
    elif args.auto_conceptos_motor == "anthropic-chat":
        print(f"[3/5] Detectando {args.auto_conceptos} conceptos: TF-IDF local + depuración con Anthropic Foundry")
        concepts = extract_concepts_with_chat(fragments, _build_api_config(args, "anthropicfoundry"), top_n=args.auto_conceptos)
    elif args.auto_conceptos_motor == "openai-chat":
        print(f"[3/5] Detectando {args.auto_conceptos} conceptos: TF-IDF local + depuración con OpenAI chat")
        concepts = extract_concepts_with_chat(fragments, _build_api_config(args, "openai"), top_n=args.auto_conceptos)
    else:
        print(f"[3/5] No hubo archivo de conceptos/planeación útil. Detectando {args.auto_conceptos} conceptos desde el corpus.")
        concepts = extract_candidate_concepts(fragments, top_n=args.auto_conceptos)

    if not concepts:
        print("ERROR: No se detectaron conceptos. Proporciona CONCEPTOS_PATH o PLANEACION_PATH en .env.", file=sys.stderr)
        raise SystemExit(2)
    return concepts, analysis, remote_planeacion, final_planeacion, subject_slug, concept_curation


def _build_engine(args, fragments):
    if args.motor == "anthropicfoundry":
        threshold = 0.03 if args.umbral is None else args.umbral
        return TfidfSearchEngine(fragments=fragments), threshold
    if args.motor == "tfhub":
        threshold = 0.20 if args.umbral is None else args.umbral
        return TfHubSearchEngine(fragments=fragments, model_url_or_path=args.tfhub_model), threshold
    if args.motor == "azure":
        threshold = 0.20 if args.umbral is None else args.umbral
        cache_dir = Path(".cache") if args.cache_embeddings else None
        return ApiEmbeddingSearchEngine(fragments=fragments, config=_build_api_config(args, "azure"), batch_size=args.api_batch_size, cache_dir=cache_dir), threshold
    if args.motor == "openai":
        threshold = 0.20 if args.umbral is None else args.umbral
        cache_dir = Path(".cache") if args.cache_embeddings else None
        return ApiEmbeddingSearchEngine(fragments=fragments, config=_build_api_config(args, "openai"), batch_size=args.api_batch_size, cache_dir=cache_dir), threshold
    threshold = 0.03 if args.umbral is None else args.umbral
    return TfidfSearchEngine(fragments=fragments), threshold


def _build_engine_with_fallback(args, fragments) -> tuple[Any, float, str]:
    """Construye el motor solicitado y, si falla un proveedor remoto, cae a TF-IDF."""
    try:
        engine, threshold = _build_engine(args, fragments)
        return engine, threshold, args.motor
    except Exception as exc:
        if args.motor in {"azure", "openai", "tfhub"}:
            print(f"      AVISO: fallo en motor '{args.motor}': {exc}", file=sys.stderr)
            print("      Se aplicará fallback automático a motor local 'tfidf'.", file=sys.stderr)
            threshold = 0.03 if args.umbral is None else args.umbral
            return TfidfSearchEngine(fragments=fragments), threshold, "tfidf"
        raise


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.probar_tfhub:
        from .probar_tfhub import main as probar_tfhub_main
        probar_tfhub_main()
        return
    if args.probar_azure:
        from .azure_ping import main as azure_ping_main
        azure_ping_main()
        return
    if args.probar_anthropic:
        from .anthropic_ping import main as anthropic_ping_main
        anthropic_ping_main()
        return
    if args.probar_openai:
        from .openai_ping import main as openai_ping_main
        openai_ping_main()
        return

    source_path = Path(args.fuentes)
    out_dir = Path(args.salida)
    extensions = parse_extensions(args.extensiones)

    print(f"[1/5] Leyendo fuente(s): {source_path}")
    pages, report = extract_pages_from_sources(source_path, recursive=args.recursivo, extensions=extensions)
    if args.probar_config:
        print("Configuración cargada correctamente.")
        print(f"Fuentes dir/archivo: {source_path}")
        print(f"Recursivo: {args.recursivo}")
        print(f"Conceptos path: {args.conceptos}")
        print(f"Planeación path: {args.planeacion}")
        print(f"Salida: {out_dir}")
        print(f"Motor: {args.motor}")
        print(f"Fuentes cargables encontradas: {len(report.loaded_files)}")
        for p in report.loaded_files[:20]:
            print(f"- {p}")
        if len(report.loaded_files) > 20:
            print(f"... y {len(report.loaded_files)-20} más")
        return

    if not report.loaded_files:
        print("ERROR: No se cargó ninguna fuente útil. Revisa FUENTES_DIR, RECURSIVO y EXTENSIONES en .env.", file=sys.stderr)
        raise SystemExit(2)
    if not any(p.text.strip() for p in pages):
        print("ERROR: No se extrajo texto. Los PDFs pueden ser escaneados y requerir OCR.", file=sys.stderr)
        raise SystemExit(2)

    type_counts = Counter(p.suffix.lower().lstrip(".") for p in report.loaded_files)
    print(f"      Fuentes cargadas: {len(report.loaded_files)} | Páginas/bloques: {len(pages)}")
    print("      Tipos: " + ", ".join(f"{k or 'sin_ext'}={v}" for k, v in sorted(type_counts.items())))
    if report.skipped_files:
        print(f"      Omitidos/no legibles: {len(report.skipped_files)}")

    print("[2/5] Dividiendo corpus en fragmentos citables")
    fragments = build_fragments(pages, max_chars=args.max_caracteres_fragmento, min_chars=args.min_caracteres_fragmento)
    if not fragments:
        print("ERROR: No se generaron fragmentos útiles.", file=sys.stderr)
        raise SystemExit(2)
    print(f"      Fragmentos: {len(fragments)}")

    concepts, planeacion_analysis, planeacion_remote, planeacion_final, subject_slug, concept_curation = _load_concepts(args, fragments)
    print(f"      Total de conceptos a buscar: {len(concepts)}")

    print(f"[4/5] Buscando citas con motor: {args.motor}")
    if args.motor in {"azure", "openai"}:
        print("      Nota: este motor envía fragmentos del corpus al proveedor para calcular embeddings.")
    if args.motor == "anthropicfoundry":
        print("      Nota: Anthropic Foundry se usará para tareas de chat/normalización; la recuperación de citas se mantiene en motor local TF-IDF.")
    engine, threshold, effective_motor = _build_engine_with_fallback(args, fragments)
    if effective_motor != args.motor:
        print(f"      Motor efectivo: {effective_motor}")
    hits_by_concept = {}
    for concept in concepts:
        hits = engine.search(concept, top_k=max(args.top_k, args.max_citas), threshold=threshold, max_quote_chars=args.max_caracteres_cita)[:args.max_citas]
        hits_by_concept[concept] = hits
        source_count = len({h.source_name for h in hits})
        print(f"      {concept}: {len(hits)} cita(s) en {source_count} fuente(s)")

    refinement_diagnostics = None
    if args.refinar_fichas_iterativamente and args.motor == "anthropicfoundry":
        print("      Refinando fichas iterativamente con Anthropic Foundry + recuperación local")
        hits_by_concept, refinement_diagnostics = refine_hits_by_concept(
            concepts,
            hits_by_concept,
            engine,
            config=_build_api_config(args, "anthropicfoundry"),
            threshold=threshold,
            max_rounds=args.rondas_refinamiento,
            max_queries=args.consultas_expansion,
            hits_per_query=args.hits_por_expansion,
            max_quote_chars=args.max_caracteres_cita,
        )

    print("[5/5] Exportando fichas")
    fichas = build_fichas(concepts, hits_by_concept)
    paths = export_all(
        fichas,
        out_dir,
        planeacion_analysis=planeacion_analysis,
        planeacion_remote=planeacion_remote,
        planeacion_final=planeacion_final,
        subject_slug=subject_slug,
        concept_curation=concept_curation,
        refinement_diagnostics=refinement_diagnostics,
        conceptos=concepts,
    )
    print("\nListo. Archivos generados:")
    for kind, path in paths.items():
        print(f"- {kind}: {path}")


if __name__ == "__main__":
    main()
