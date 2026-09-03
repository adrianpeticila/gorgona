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
    """Detects infinite reasoning chains, repetitive subagent delegations, and cyclic dependencies.

    Tracks both linear step repetition (history) and topological graph depth.
    - max_depth: The maximum allowed length of a path in the memory graph or execution stack.
    - repetition_threshold: The maximum number of times a single step can be repeated in history.
    """

    def __init__(self, max_depth: int = 8, repetition_threshold: int = 3):
        self.max_depth = max_depth
        self.repetition_threshold = repetition_threshold
        self.history: List[str] = []
        self.adjacency: Dict[str, List[str]] = {}

    def record_step(self, step_identifier: str) -> LoopReport:
        """Records a linear step and checks for repetition and stack depth limits."""
        self.history.append(step_identifier)
        count = self.history.count(step_identifier)

        if count >= self.repetition_threshold:
            return LoopReport(
                loop_detected=True,
                cycle_path=[step_identifier] * count,
                depth=len(self.history),
                warning=f"Repetitive execution detected: '{step_identifier}' occurred {count} times.",
            )

        if len(self.history) > self.max_depth:
            return LoopReport(
                loop_detected=True,
                cycle_path=self.history[-5:],
                depth=len(self.history),
                warning=f"Execution stack depth {len(self.history)} exceeded max_depth ({self.max_depth}).",
            )

        return LoopReport(loop_detected=False, depth=len(self.history))

    def add_edge(self, from_node: str, to_node: str):
        if from_node not in self.adjacency:
            self.adjacency[from_node] = []
        self.adjacency[from_node].append(to_node)

    def detect_graph_cycle(self) -> Tuple[bool, List[str]]:
        """Detects cyclic dependencies in the graph (including self-loops) and returns the exact cycle."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        cycle: List[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    cycle_start_index = path.index(neighbor)
                    cycle.extend(path[cycle_start_index:])
                    cycle.append(neighbor)
                    return True

            rec_stack.remove(node)
            path.pop()
            return False

        for node in list(self.adjacency.keys()):
            if node not in visited:
                if dfs(node):
                    return True, cycle
        return False, []

    def get_max_graph_depth(self) -> int:
        """Calculates the maximum depth of the graph (longest path). Returns -1 if cycle exists."""
        has_cycle, _ = self.detect_graph_cycle()
        if has_cycle:
            return -1

        memo: Dict[str, int] = {}

        def dfs_depth(node: str) -> int:
            if node in memo:
                return memo[node]

            max_d = 0
            for neighbor in self.adjacency.get(node, []):
                max_d = max(max_d, 1 + dfs_depth(neighbor))

            memo[node] = max_d
            return max_d

        max_overall_depth = 0
        for node in self.adjacency.keys():
            max_overall_depth = max(max_overall_depth, dfs_depth(node))

        return max_overall_depth
