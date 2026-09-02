"""Text cleaner guard: Detect and sanitize AI slop, em-dashes, and LLM filler words."""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class StyleFinding:
    rule: str
    description: str
    line_number: int
    matched_text: str
    suggestion: str


class TextCleanerGuard:
    """Zero em-dash policy and anti-slop copy enforcement."""

    FORBIDDEN_CHARACTERS = [
        ("\u2014", "em-dash character (use comma or period instead)"),
        ("\u2013", "en-dash character in place of hyphen"),
    ]

    SLOP_PATTERNS = [
        (r"\bdelve into\b", "delve into", "explore, examine, inspect"),
        (r"\btapestry of\b", "tapestry of", "collection of, system of"),
        (r"\btestament to\b", "testament to", "proof of, evidence of"),
        (r"\bbeacon of\b", "beacon of", "leader in, center for"),
        (r"\bunleash(?:ing)? the power\b", "unleash the power", "enable, accelerate"),
        (r"\bin the realm of\b", "in the realm of", "in, regarding"),
        (r"\bvibrant ecosystem\b", "vibrant ecosystem", "community, platform"),
        (r"\bit is crucial to remember\b", "it is crucial to remember", "note that"),
        (r"\bfoster(?:ing)? innovation\b", "fostering innovation", "building, creating"),
    ]

    def __init__(self, ban_em_dash: bool = True):
        self.ban_em_dash = ban_em_dash

    def scan(self, text: str) -> List[StyleFinding]:
        findings = []
        lines = text.splitlines()

        for idx, line in enumerate(lines, 1):
            if self.ban_em_dash:
                for char, desc in self.FORBIDDEN_CHARACTERS:
                    if char in line:
                        findings.append(StyleFinding(
                            rule="forbidden_dash",
                            description=desc,
                            line_number=idx,
                            matched_text=char,
                            suggestion="Replace with comma, period, or hyphen",
                        ))

            for pattern, name, repl in self.SLOP_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for m in matches:
                    findings.append(StyleFinding(
                        rule="ai_slop",
                        description=f"AI marker detected: '{name}'",
                        line_number=idx,
                        matched_text=m.group(0),
                        suggestion=f"Consider: {repl}",
                    ))

        return findings

    def clean(self, text: str) -> str:
        """Automated sanitizer for dashes."""
        cleaned = text.replace("\u2014", ", ")
        cleaned = cleaned.replace(" ,", ",")
        return cleaned
