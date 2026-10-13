"""AulaTeX local suite for editorial LaTeX workflows."""

from .activity_contract import ACTIVITY_1_CONTRACT
from .activity_monitor import ActivityMonitor, ActivityMonitorRequest
from .activity_observer import ActivityObservationRequest, ActivityObserver
from .activity_revision import ActivityRevisionRequest, ActivityReviser
from .agent import AgentRequest, AulaTeXAgent
from .agentic_patterns import AgenticStateMachine, EditorialConsensusEngine
from .bibliography_repair import BibliographyRepairer, BibliographyRepairRequest
from .compilation_diagnostics import ENVIRONMENT_CATEGORIES, classify_compile_failure, is_environment_issue
from .compilation_repair import CompilationRepairRequest, CompilationRepairer
from .editorial_context import EditorialContextProvider
from .extractor_adapter import ExtractorAdapter, ExtractorRequest
from .incremental_detail_planner import DetailPlannerRequest, DetailPlannerResult, IncrementalDetailPlanner
from .intelligent_engine import IntelligentEngine, IntelligentEngineRequest, IntelligentEngineResult
from .langchain_adapter import AulaTeXLLMInterface, AulaTeXLangChainAdapter
from .llm_bridge import LLM_ENGINES, AulaTeXLLMClient
from .workspace import AulaTeXWorkspace

__all__ = [
    "ActivityObservationRequest",
    "ActivityObserver",
    "ActivityReviser",
    "ActivityRevisionRequest",
    "ActivityMonitor",
    "ActivityMonitorRequest",
    "CompilationRepairer",
    "CompilationRepairRequest",
    "ENVIRONMENT_CATEGORIES",
    "classify_compile_failure",
    "is_environment_issue",
    "BibliographyRepairer",
    "BibliographyRepairRequest",
    "ACTIVITY_1_CONTRACT",
    "AgentRequest",
    "AulaTeXAgent",
    "AulaTeXWorkspace",
    "EditorialContextProvider",
    "ExtractorAdapter",
    "ExtractorRequest",
    "DetailPlannerRequest",
    "DetailPlannerResult",
    "IncrementalDetailPlanner",
    "AgenticStateMachine",
    "EditorialConsensusEngine",
    "IntelligentEngine",
    "IntelligentEngineRequest",
    "IntelligentEngineResult",
    "LLM_ENGINES",
    "AulaTeXLLMClient",
    "AulaTeXLLMInterface",
    "AulaTeXLangChainAdapter",
]
