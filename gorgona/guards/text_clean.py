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


def _tokenize_markdown(text: str) -> List[Tuple[bool, str]]:
    CODE_PATTERN = re.compile(
        r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`|(?:\n\n(?:(?: {4}|\t)[^\n]*(?:\n|$))+)|^ {4}[^\n]*(?:\n|$))',
        re.MULTILINE
    )
    tokens = CODE_PATTERN.split(text)
    return [(i % 2 == 1, token) for i, token in enumerate(tokens)]


class TextCleanerGuard:
    """Zero em-dash policy and anti-slop copy enforcement."""

    FORBIDDEN_CHARACTERS = [
        ("\u2014", "em-dash character"),
        ("\u2013", "en-dash character"),
        ("\u2015", "horizontal bar"),
        ("\u2212", "minus sign"),
        ("\u00ad", "soft hyphen"),
        ("\u200b", "zero-width space"),
        ("\u200c", "zero-width non-joiner"),
        ("\u200d", "zero-width joiner"),
        ("\ufeff", "zero-width no-break space"),
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
        tokens = _tokenize_markdown(text)

        current_offset = 0
        for is_code, token in tokens:
            if not is_code:
                if self.ban_em_dash:
                    for char, desc in self.FORBIDDEN_CHARACTERS:
                        start = 0
                        while True:
                            idx = token.find(char, start)
                            if idx == -1:
                                break
                            global_idx = current_offset + idx
                            line_num = text[:global_idx].count('\n') + 1
                            findings.append(StyleFinding(
                                rule="forbidden_dash",
                                description=desc,
                                line_number=line_num,
                                matched_text=char,
                                suggestion="Replace with comma, period, or hyphen",
                            ))
                            start = idx + 1

                for pattern, name, repl in self.SLOP_PATTERNS:
                    for match in re.finditer(pattern, token, re.IGNORECASE):
                        global_idx = current_offset + match.start()
                        line_num = text[:global_idx].count('\n') + 1
                        findings.append(StyleFinding(
                            rule="ai_slop",
                            description=f"AI marker detected: '{name}'",
                            line_number=line_num,
                            matched_text=match.group(0),
                            suggestion=f"Consider: {repl}",
                        ))

            current_offset += len(token)

        return findings

    def clean(self, text: str) -> str:
        """Automated sanitizer for dashes and artifacts, avoiding code blocks."""
        tokens = _tokenize_markdown(text)

        cleaned_tokens = []
        for is_code, token in tokens:
            if is_code:
                cleaned_tokens.append(token)
            else:
                # Prose: apply cleaning
                cleaned = token
                cleaned = cleaned.replace("\u2014", ", ")
                cleaned = cleaned.replace("\u2013", "-")
                cleaned = cleaned.replace("\u2015", "-")
                cleaned = cleaned.replace("\u2212", "-")
                cleaned = cleaned.replace("\u00ad", "")
                cleaned = cleaned.replace("\u200b", "")
                cleaned = cleaned.replace("\u200c", "")
                cleaned = cleaned.replace("\u200d", "")
                cleaned = cleaned.replace("\ufeff", "")

                # Clean space-comma artifacts and double spaces
                cleaned = re.sub(r'\s+,', ',', cleaned)
                cleaned = re.sub(r' ,', ',', cleaned)
                cleaned = re.sub(r',(?:\s*,)+', ',', cleaned)
                cleaned = cleaned.replace("  ", " ")
                cleaned_tokens.append(cleaned)

        return "".join(cleaned_tokens)
