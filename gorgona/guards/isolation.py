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

    @property
    def target_brand(self) -> str:
        return self.brand


class IsolationGuard:
    """Guarantees that distinct brands or projects never leak keywords into foreign repositories."""

    def __init__(self, brand_rules: Optional[Dict] = None):
        # brand -> foreign_brand -> list of forbidden terms
        self.brand_rules: Dict[str, Dict[str, List[str]]] = {}
        if brand_rules:
            for brand, rules in brand_rules.items():
                if isinstance(rules, list):
                    self.brand_rules[brand] = {"foreign": rules}
                else:
                    self.brand_rules[brand] = rules

    def add_rule(self, target_brand: str, foreign_brand: str, forbidden_term: str):
        if target_brand not in self.brand_rules:
            self.brand_rules[target_brand] = {}
        if foreign_brand not in self.brand_rules[target_brand]:
            self.brand_rules[target_brand][foreign_brand] = []
        self.brand_rules[target_brand][foreign_brand].append(forbidden_term)

    def check_content(self, *args, **kwargs) -> List[IsolationViolation]:
        target_brand = args[0] if len(args) > 0 else kwargs.get("target_brand")
        text = args[1] if len(args) > 1 else kwargs.get("text")
        source_label = args[2] if len(args) > 2 else kwargs.get("source_label")
        import re
        violations = []

        # If called as check_content("text to check", target_brand="BrandA")
        if kwargs.get("target_brand"):
            real_target_brand = kwargs["target_brand"]
            real_text = target_brand  # first positional was text
        elif text is None and isinstance(target_brand, str):
            # If called with single arg check_content("text")
            real_target_brand = next(iter(self.brand_rules.keys())) if self.brand_rules else "default"
            real_text = target_brand
        else:
            real_target_brand = target_brand
            real_text = text or ""

        if not real_text:
            return violations

        foreign_rules = self.brand_rules.get(real_target_brand, {})
        if not foreign_rules:
            return violations

        lines = real_text.splitlines()

        for foreign_brand, forbidden_list in foreign_rules.items():
            for term in forbidden_list:
                left_bound = r"\b" if term[0].isalnum() or term[0] == '_' else r"(?:^|\s|[.,;:!?\"'\(])"
                right_bound = r"\b" if term[-1].isalnum() or term[-1] == '_' else r"(?:$|\s|[.,;:!?\"'\)])"
                pattern = re.compile(rf"{left_bound}{re.escape(term)}{right_bound}", re.IGNORECASE)
                for idx, line in enumerate(lines, 1):
                    if pattern.search(line):
                        violations.append(IsolationViolation(
                            brand=real_target_brand,
                            foreign_brand=foreign_brand,
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
                    content = p.read_text(encoding="utf-8")
                    violations.extend(self.check_content(target_brand, content, source_label=str(p)))
                except (OSError, UnicodeDecodeError):
                    continue
        return violations
