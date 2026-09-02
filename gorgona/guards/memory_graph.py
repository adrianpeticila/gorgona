"""Memory graph guard: Prevent circular loops, runaway depth, and context bloat."""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class LoopReport:
    loop_detected: bool
    cycle_path: List[str] = field(default_factory=list)
    depth: int = 0
    warning: str = ""


class MemoryGraphGuard:
    """Detects infinite reasoning chains, repetitive subagent delegations, and cyclic dependencies."""

    def __init__(self, max_depth: int = 8, repetition_threshold: int = 3):
        self.max_depth = max_depth
        self.repetition_threshold = repetition_threshold
        self.history: List[str] = []
        self.adjacency: Dict[str, List[str]] = {}

    def record_step(self, step_identifier: str) -> LoopReport:
        self.history.append(step_identifier)
        count = self.history.count(step_identifier)

        if count >= self.repetition_threshold:
            return LoopReport(
                loop_detected=True,
                cycle_path=[step_identifier] * count,
                depth=len(self.history),
                warning=f"Repetitive execution detected: '{step_identifier}' occurred {count} times.",
            )

        if len(self.history) > self.max_depth * 4:
            return LoopReport(
                loop_detected=True,
                cycle_path=self.history[-5:],
                depth=len(self.history),
                warning=f"Execution stack depth {len(self.history)} exceeded safety ceiling.",
            )

        return LoopReport(loop_detected=False, depth=len(self.history))

    def add_edge(self, from_node: str, to_node: str):
        if from_node not in self.adjacency:
            self.adjacency[from_node] = []
        self.adjacency[from_node].append(to_node)

    def detect_graph_cycle(self) -> Tuple[bool, List[str]]:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycle: List[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        cycle.append(node)
                        return True
                elif neighbor in rec_stack:
                    cycle.append(neighbor)
                    cycle.append(node)
                    return True
            rec_stack.remove(node)
            return False

        for node in list(self.adjacency.keys()):
            if node not in visited:
                if dfs(node):
                    cycle.reverse()
                    return True, cycle
        return False, []
