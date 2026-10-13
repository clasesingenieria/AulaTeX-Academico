from typing import TypedDict
from langgraph.graph import StateGraph, END
import json
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "memory" / "editorial_memory.json"

class EditorialState(TypedDict, total=False):
    prompt: str
    proposals: list[str]
    fused: str

def load_memory():
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    return {"history": []}

def save_memory(data):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def consensus_node(state: EditorialState):
    proposals = state.get("proposals", [])
    unique = []
    for item in proposals:
        if item and item not in unique:
            unique.append(item)
    fused = "\n\n===== CONSENSO =====\n\n".join(unique)
    memory = load_memory()
    memory.setdefault("history", []).append(fused)
    save_memory(memory)
    return {"fused": fused}

def build_graph():
    graph = StateGraph(EditorialState)
    graph.add_node("consensus", consensus_node)
    graph.set_entry_point("consensus")
    graph.add_edge("consensus", END)
    return graph.compile()
