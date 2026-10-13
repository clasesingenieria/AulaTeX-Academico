from __future__ import annotations

from dataclasses import dataclass, field
from .search import SearchHit


@dataclass
class ConceptFicha:
    concept: str
    hits: list[SearchHit] = field(default_factory=list)

    @property
    def locations(self) -> list[str]:
        return sorted({h.source_location for h in self.hits})

    @property
    def sources(self) -> list[str]:
        return sorted({h.source_name for h in self.hits})

    @property
    def locations_text(self) -> str:
        return "; ".join(self.locations) if self.hits else "Sin ubicaciones detectadas"

    @property
    def sources_text(self) -> str:
        return "; ".join(self.sources) if self.hits else "Sin fuentes detectadas"

    @property
    def best_score(self) -> float:
        return max((h.score for h in self.hits), default=0.0)

    @property
    def average_score(self) -> float:
        return sum(h.score for h in self.hits) / len(self.hits) if self.hits else 0.0

    @property
    def quality_label(self) -> str:
        if not self.hits:
            return "sin hallazgos"
        if self.best_score >= 0.28:
            return "alta"
        if self.best_score >= 0.14:
            return "media"
        return "baja"

    @property
    def observation(self) -> str:
        if not self.hits:
            return "No se localizaron fragmentos por encima del umbral configurado. Conviene revisar el concepto o ampliar el corpus."
        notes: list[str] = []
        if self.quality_label == "alta":
            notes.append("La ficha presenta una coincidencia fuerte con el concepto buscado.")
        elif self.quality_label == "media":
            notes.append("La ficha presenta coincidencias útiles, pero conviene revisar la pertinencia de cada cita.")
        else:
            notes.append("La ficha presenta coincidencias débiles; se recomienda validar manualmente las citas.")
        if len(self.sources) > 1:
            notes.append("Se agruparon referencias de múltiples fuentes para enriquecer el concepto.")
        elif len(self.hits) > 1:
            notes.append("Se agruparon varias referencias dentro de la misma fuente.")
        low_hits = sum(1 for h in self.hits if h.score < 0.08)
        if low_hits:
            notes.append(f"Hay {low_hits} referencia(s) de baja similitud que podrían introducir ruido.")
        return " ".join(notes)


def build_fichas(concepts: list[str], hits_by_concept: dict[str, list[SearchHit]]) -> list[ConceptFicha]:
    fichas: list[ConceptFicha] = []
    for concept in concepts:
        hits = sorted(hits_by_concept.get(concept, []), key=lambda h: (-h.score, h.source_name.lower(), h.page, h.fragment_id))
        fichas.append(ConceptFicha(concept=concept, hits=hits))
    return fichas
