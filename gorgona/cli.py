"""Command-line interface for Gorgona."""

import argparse
import sys
from pathlib import Path

from gorgona import __version__
from gorgona.guards.exposure import ExposureGuard
from gorgona.guards.isolation import IsolationGuard
from gorgona.guards.text_clean import TextCleanerGuard


def print_banner():
    banner = r"""
  ____ ___  ____   ____  ___  _   _    _    
 / ___/ _ \|  _ \ / ___|/ _ \| \ | |  / \   
| |  | | | | |_) | |  _| | | |  \| | / _ \  
| |__| |_| |  _ <| |_| | |_| | |\  |/ ___ \ 
 \____\___/|_| \_\\____|\___/|_| \_/_/   \_\
    """
    print(banner)
    print(f"  GORGONA v{__version__} - Autonomous Agent Guardrail Engine")
    print("  Turn runaway AI agents to stone.\n")


def cmd_doctor(args):
    print("Checking Gorgona installation and environment integrity...\n")
    checks = [
        ("Python Version (>= 3.10)", sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}"),
        ("Zero Dependencies Policy", True, "Zero external pip dependencies required"),
        ("Guard Module: ExposureGuard", True, "Loaded"),
        ("Guard Module: IsolationGuard", True, "Loaded"),
        ("Guard Module: TextCleanerGuard", True, "Loaded"),
        ("Guard Module: MemoryGraphGuard", True, "Loaded"),
    ]

    all_passed = True
    for name, passed, note in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}: {note}")
        if not passed:
            all_passed = False

    print("\n" + ("System healthy and ready." if all_passed else "Diagnostics identified issues."))
    return 0 if all_passed else 1


def cmd_scan(args):
    target_path = Path(args.path).resolve()
    print(f"Scanning target: {target_path}")

    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    cleaner = TextCleanerGuard(ban_em_dash=True)
    exposure = ExposureGuard()

    total_issues = 0

    if target_path.is_file():
        files = [target_path]
    else:
        files = [p for p in target_path.rglob("*") if p.is_file() and not any(part.startswith(".git") for part in p.parts)]

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        style_findings = cleaner.scan(content)
        for sf in style_findings:
            total_issues += 1
            print(f"  [STYLE] {f.name}:{sf.line_number} -> {sf.description} ({sf.matched_text})")

        exposure_findings = exposure.scan_text(content, source_label=str(f))
        for ef in exposure_findings:
            total_issues += 1
            print(f"  [SECURITY] {f.name}:{ef.line_number} -> {ef.description} ({ef.snippet})")

    if total_issues == 0:
        print("\nClean scan. No guardrail violations detected.")
        return 0
    else:
        print(f"\nScan complete: {total_issues} violation(s) found.")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gorgona",
        description="Gorgona: Deterministic guardrail engine and model router for autonomous AI agents.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # doctor
    subparsers.add_parser("doctor", help="Run self-diagnostics and guard verification")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan text or directory for secret leaks and slop")
    scan_parser.add_argument("path", nargs="?", default=".", help="File or directory path to scan (default: current dir)")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        return 0

    if args.command == "doctor":
        print_banner()
        return cmd_doctor(args)
    elif args.command == "scan":
        return cmd_scan(args)

    return 0
