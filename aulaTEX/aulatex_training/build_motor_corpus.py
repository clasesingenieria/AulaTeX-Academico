"""CLI para crear y particionar el corpus SFT privado del motor inteligente."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .motor_training import (
    build_sft_rows,
    dataset_stats,
    grouped_split,
    repo_root,
    validate_sft_row,
    write_jsonl,
    write_splits,
)


def main(argv: list[str] | None = None) -> int:
    root_default = repo_root(Path.cwd())
    parser = argparse.ArgumentParser(description="Construye el corpus SFT privado de AulaTeX.")
    parser.add_argument("--root", default=str(root_default))
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Score editorial mínimo; usa 95 para entrenar solo con actividades validadas.")
    parser.add_argument("--allow-redacted", action="store_true",
                        help="Incluye documentos con PII sustituyéndola; requiere revisión humana posterior.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "data/private/processed"
    rows, findings = build_sft_rows(
        root, strict_privacy=not args.allow_redacted, min_score=args.min_score
    )
    errors = [(row.get("target"), validate_sft_row(row)) for row in rows if validate_sft_row(row)]
    if errors:
        print(json.dumps(errors[:10], ensure_ascii=False, indent=2))
        return 2
    if not rows:
        print("[motor-corpus] No hay ejemplos exportables. Revise privacidad y fuentes autorizadas.")
        return 2

    write_jsonl(out_dir / "sft.jsonl", rows)
    splits = grouped_split(rows, seed=args.seed)
    manifest = write_splits(
        root / "data/private/splits", splits, seed=args.seed,
        source_root=root, privacy_count=sum(finding.count for finding in findings),
    )
    report = {
        "stats": dataset_stats(rows),
        "privacy_documents_excluded_or_redacted": len({finding.source for finding in findings}),
        "privacy_findings": sum(finding.count for finding in findings),
        "manifest": manifest.__dict__,
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
