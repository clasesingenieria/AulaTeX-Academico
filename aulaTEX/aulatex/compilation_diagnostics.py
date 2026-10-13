from __future__ import annotations


ENVIRONMENT_CATEGORIES = {
    "tex-environment-missing-class",
    "tex-environment-missing-package",
    "tex-environment-missing-binary",
}


def classify_compile_failure(output: str) -> str:
    lowered = output.lower()
    if "article.cls" in output and "not found" in lowered:
        return "tex-environment-missing-class"
    if ".sty' not found" in lowered or ".cls' not found" in lowered:
        return "tex-environment-missing-package"
    if "latexmk" in lowered and "not recognized" in lowered:
        return "tex-environment-missing-binary"
    if "pdflatex" in lowered and "not recognized" in lowered:
        return "tex-environment-missing-binary"
    if "citation" in lowered or "undefined references" in lowered:
        return "latex-references"
    if "bib" in lowered and ("error" in lowered or "not found" in lowered):
        return "bibtex"
    return "latex-unknown"


def is_environment_issue(category: str) -> bool:
    return category in ENVIRONMENT_CATEGORIES