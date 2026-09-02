"""Isolation guard: Enforce multi-brand wall boundaries and prevent cross-contamination."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class IsolationViolation:
    brand: str
    foreign_brand: str
    forbidden_keyword: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    snippet: Optional[str] = None


class IsolationGuard:
    """Guarantees that distinct brands or projects never leak keywords into foreign repositories."""

    def __init__(self, brand_rules: Optional[Dict[str, List[str]]] = None):
        # brand -> list of forbidden terms when working on that brand
        self.brand_rules: Dict[str, List[str]] = brand_rules or {}

    def add_rule(self, target_brand: str, forbidden_term: str):
        if target_brand not in self.brand_rules:
            self.brand_rules[target_brand] = []
        self.brand_rules[target_brand].append(forbidden_term)

    def check_content(self, target_brand: str, text: str, source_label: Optional[str] = None) -> List[IsolationViolation]:
        violations = []
        forbidden_list = self.brand_rules.get(target_brand, [])
        if not forbidden_list:
            return violations

        lower_text = text.lower()
        lines = text.splitlines()

        for term in forbidden_list:
            term_lower = term.lower()
            if term_lower in lower_text:
                for idx, line in enumerate(lines, 1):
                    if term_lower in line.lower():
                        violations.append(IsolationViolation(
                            brand=target_brand,
                            foreign_brand="cross_leak",
                            forbidden_keyword=term,
                            file_path=source_label,
                            line_number=idx,
                            snippet=line.strip()[:100],
                        ))
        return violations

    def check_directory(self, target_brand: str, directory_path: Path) -> List[IsolationViolation]:
        violations = []
        dir_obj = Path(directory_path)
        if not dir_obj.exists():
            return violations

        for p in dir_obj.rglob("*"):
            if any(part.startswith(".git") for part in p.parts):
                continue
            if p.is_file():
                try:
                    if p.stat().st_size > 1_000_000:
                        continue
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    violations.extend(self.check_content(target_brand, content, source_label=str(p)))
                except (OSError, UnicodeDecodeError):
                    continue
        return violations
