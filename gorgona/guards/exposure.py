"""Exposure guard: Scan text and source trees for secret leaks and private metadata."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Finding:
    category: str
    description: str
    snippet: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class ExposureGuard:
    """Detects leaked credentials, private tokens, personal identifiers, and dirty files."""

    PATTERNS = [
        ("api_key_generic", r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\.]{16,})['\"]", "Exposed API key or secret token"),
        ("openai_key", r"sk-[a-zA-Z0-9]{20,}", "OpenAI API secret key format"),
        ("anthropic_key", r"sk-ant-[a-zA-Z0-9_\-]{20,}", "Anthropic API key format"),
        ("github_pat", r"gh[pousr]-[a-zA-Z0-9]{20,}", "GitHub Personal Access Token"),
        ("bearer_token", r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{25,}", "Bearer authorization header token"),
        ("private_key_header", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private cryptographic key"),
        ("aws_access_key", r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    ]

    FORBIDDEN_FILES = [
        ".env",
        ".env.local",
        ".env.production",
        ".DS_Store",
        "id_rsa",
        "id_ed25519",
        "credentials.json",
    ]

    def __init__(self, custom_patterns: Optional[List[tuple]] = None):
        self.patterns = [(cat, re.compile(pat), desc) for cat, pat, desc in self.PATTERNS]
        if custom_patterns:
            for cat, pat, desc in custom_patterns:
                self.patterns.append((cat, re.compile(pat), desc))

    def scan_text(self, text: str, source_label: Optional[str] = None) -> List[Finding]:
        """Scan a raw string for potential secret exposures."""
        findings = []
        lines = text.splitlines()
        for idx, line in enumerate(lines, 1):
            for cat, regex, desc in self.patterns:
                match = regex.search(line)
                if match:
                    raw_val = match.group(0)
                    masked = raw_val[:6] + "..." + raw_val[-4:] if len(raw_val) > 12 else "***"
                    findings.append(Finding(
                        category=cat,
                        description=desc,
                        snippet=f"Line {idx}: {masked}",
                        file_path=source_label,
                        line_number=idx,
                    ))
        return findings

    def scan_path(self, target_path: Path) -> List[Finding]:
        """Scan a directory or file recursively for forbidden files and secret patterns."""
        findings = []
        path_obj = Path(target_path)

        if not path_obj.exists():
            return findings

        if path_obj.is_file():
            return self._scan_single_file(path_obj)

        for p in path_obj.rglob("*"):
            if any(part.startswith(".git") for part in p.parts):
                continue

            if p.name in self.FORBIDDEN_FILES:
                findings.append(Finding(
                    category="forbidden_file",
                    description=f"Forbidden sensitive file present: {p.name}",
                    snippet=str(p),
                    file_path=str(p),
                ))

            if p.is_file():
                # Avoid binary files
                try:
                    if p.stat().st_size > 1_000_000:
                        continue
                    findings.extend(self._scan_single_file(p))
                except (OSError, UnicodeDecodeError):
                    continue

        return findings

    def _scan_single_file(self, file_path: Path) -> List[Finding]:
        findings = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            findings.extend(self.scan_text(content, source_label=str(file_path)))
        except Exception as e:
            findings.append(Finding(
                category="read_error",
                description=f"Could not read file: {e}",
                snippet=str(file_path),
                file_path=str(file_path),
            ))
        return findings
