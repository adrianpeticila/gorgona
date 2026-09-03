"""Command-line interface for Gorgona."""

import argparse
import sys
import os
import json
import tempfile
import runpy
from pathlib import Path

from gorgona import __version__
from gorgona.guards.exposure import ExposureGuard
from gorgona.guards.isolation import IsolationGuard
from gorgona.guards.text_clean import TextCleanerGuard
from gorgona.guards.memory_graph import MemoryGraphGuard


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

    checks = []

    checks.append(("Python Version (>= 3.10)", sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}"))

    try:
        exposure = ExposureGuard()
        findings = exposure.scan_text("ghp_123456789012345678901234567890123456 and sk-proj-1234567890abcdefghij1234567890abcdefghij")
        passed = len(findings) == 2
        checks.append(("Exposure Canary", passed, "Detects synthetic secrets"))
    except Exception as e:
        checks.append(("Exposure Canary", False, str(e)))

    try:
        cleaner = TextCleanerGuard()
        findings = cleaner.scan("delve into this \u2014 test")
        passed = len(findings) > 0
        checks.append(("Clean Canary", passed, "Detects slop and unicode"))
    except Exception as e:
        checks.append(("Clean Canary", False, str(e)))

    try:
        isolation = IsolationGuard()
        isolation.add_rule("DoctorBrand", "OtherBrand", "test")
        findings = isolation.check_content("DoctorBrand", "test")
        passed = len(findings) == 1
        checks.append(("Isolation Canary", passed, "Detects forbidden terms"))
    except Exception as e:
        checks.append(("Isolation Canary", False, str(e)))

    try:
        graph = MemoryGraphGuard()
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")
        cycle, _ = graph.detect_graph_cycle()
        checks.append(("MemoryGraph Canary", cycle, "Detects graph cycles"))
    except Exception as e:
        checks.append(("MemoryGraph Canary", False, str(e)))

    all_passed = True
    for name, passed, note in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}: {note}")
        if not passed:
            all_passed = False

    print("\n" + ("System healthy and ready." if all_passed else "Diagnostics identified issues."))
    return 0 if all_passed else 1

def cmd_scan(args):
    if args.max_files <= 0:
        print("Error: --max-files must be greater than 0", file=sys.stderr)
        return 2

    target_path = Path(args.path).resolve()

    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    print(f"Scanning target: {target_path}")

    exposure = ExposureGuard()
    cleaner = TextCleanerGuard(ban_em_dash=True)

    total_issues = 0

    if target_path.is_file():
        files = [target_path]
    else:
        # filter .git properly
        def is_git(p):
            return any(part == ".git" for part in p.parts)

        all_files = []
        for p in target_path.rglob("*"):
            if p.is_file():
                if not is_git(p.relative_to(target_path)):
                    all_files.append(p)
        files = all_files[:args.max_files]

    for f in files:
        if f.name in exposure.FORBIDDEN_FILES:
            total_issues += 1
            print(f"  [SECURITY] {f.name}:0 -> forbidden_file ({f.name})")

        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"  [WARNING] {f.name}: Skipped binary / non-UTF-8 file")
            continue
        except Exception as e:
            print(f"  [ERROR] {f.name}:0 -> read_error ({e})")
            total_issues += 1
            continue

        for sf in cleaner.scan(content):
            total_issues += 1
            print(f"  [STYLE] {f.name}:{sf.line_number} -> {sf.description} ({sf.matched_text})")

        for ef in exposure.scan_text(content, source_label=str(f)):
            total_issues += 1
            print(f"  [SECURITY] {f.name}:{ef.line_number} -> {ef.description} ({ef.snippet})")

    if total_issues == 0:
        print("\nClean scan. No guardrail violations detected.")
        return 0
    else:
        print(f"\nScan complete: {total_issues} violation(s) found.")
        return 1

def cmd_guard_isolation(args):
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    loaded_rules = {}
    rules_path = None
    if args.rules:
        rules_path = Path(args.rules).resolve()
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "isolation" in data:
                    b = data["isolation"].get("brand", "default")
                    loaded_rules[b] = data["isolation"].get("rules", {})
                else:
                    loaded_rules = data
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error: Failed to load rules file '{args.rules}': {e}", file=sys.stderr)
            return 1

    if args.terms:
        b = args.brand if args.brand else "_default"
        if b not in loaded_rules:
            loaded_rules[b] = {}
        if "_CLI_TERMS" not in loaded_rules[b]:
            loaded_rules[b]["_CLI_TERMS"] = []
        loaded_rules[b]["_CLI_TERMS"].extend(args.terms)

    isolation = IsolationGuard(brand_rules=loaded_rules)

    if args.brand:
        target_brand = args.brand
    elif len(loaded_rules) == 1:
        target_brand = next(iter(loaded_rules.keys()))
    else:
        target_brand = next(iter(loaded_rules.keys()), "default")

    if target_path.is_file():
        text = target_path.read_text(encoding="utf-8", errors="ignore")
        violations = isolation.check_content(target_brand, text, source_label=str(target_path))
    else:
        violations = []
        for p in target_path.rglob("*"):
            if any(part.startswith(".git") for part in p.parts):
                continue
            if p.is_file():
                if rules_path and p.resolve() == rules_path:
                    continue
                try:
                    if p.stat().st_size > 1_000_000:
                        continue
                    content = p.read_text(encoding="utf-8")
                    violations.extend(isolation.check_content(target_brand, content, source_label=str(p)))
                except (OSError, UnicodeDecodeError):
                    continue

    if violations:
        for v in violations:
            print(f"[ISOLATION] {v.file_path or target_path}:{v.line_number} -> Forbidden term '{v.forbidden_keyword}' found for brand '{target_brand}' (source: {v.foreign_brand})")
        return 1
    else:
        print("Clean isolation scan. No cross-brand leakages detected.")
        return 0

def cmd_clean(args):
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    cleaner = TextCleanerGuard()

    if target_path.is_file():
        files = [target_path]
    else:
        files = [p for p in target_path.rglob("*") if p.is_file() and not any(part == ".git" for part in p.relative_to(target_path).parts)]

    total_issues = 0
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue

        findings = cleaner.scan(content)
        if findings:
            cleaned = cleaner.clean(content)
            if args.dry_run:
                print(f"Would clean {f.name}:")
                for finding in findings:
                    print(f"  Line {finding.line_number}: {finding.description} ({finding.matched_text})")
                total_issues += 1
            elif args.fix:
                with tempfile.NamedTemporaryFile("w", delete=False, dir=f.parent, encoding="utf-8") as tmp:
                    tmp.write(cleaned)
                    tmp_name = tmp.name
                os.replace(tmp_name, f)
                print(f"Cleaned {f.name}")
            else:
                for finding in findings:
                    print(f"  [STYLE] {f.name}:{finding.line_number} -> {finding.description} ({finding.matched_text})")
                total_issues += 1

    if args.dry_run:
        return 1 if total_issues > 0 else 0
    if args.fix and not args.dry_run:
        return 0
    return 1 if total_issues > 0 else 0

def cmd_lint_memory(args):
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    script = Path(__file__).parent.parent / "tools" / "memory_graph_check.py"
    if not script.exists():
        print("Lint-memory script not found.", file=sys.stderr)
        return 1

    old_argv = sys.argv[:]
    sys.argv = ["memory_graph_check.py", str(target_path)]
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:
        return e.code
    finally:
        sys.argv = old_argv
    return 0

def cmd_init(args):
    target_path = Path(args.path).resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    spec_dir = target_path / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    agents_md = spec_dir / "AGENTS.md"
    design_md = spec_dir / "DESIGN.md"
    gorgona_json = target_path / "gorgona.json"

    if (agents_md.exists() or design_md.exists() or gorgona_json.exists()) and not args.force:
        print("Refusing to overwrite existing file. Use --force.", file=sys.stderr)
        return 1

    agents_md.write_text("# Agents\n", encoding="utf-8")
    design_md.write_text("# Design\n", encoding="utf-8")
    gorgona_json.write_text("{}", encoding="utf-8")
    print(f"Initialized Gorgona project in {target_path}")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gorgona",
        description="Gorgona: Deterministic guardrails and execution discipline for autonomous AI agents.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    subparsers.add_parser("doctor", help="Run self-diagnostics and guard verification")

    scan_parser = subparsers.add_parser("scan", help="Scan text or directory for secret leaks and slop")
    scan_parser.add_argument("path", nargs="?", default=".", help="File or directory path to scan (default: current dir)")
    scan_parser.add_argument("--max-files", type=int, default=1000, help="Max files to scan")

    guard_iso_parser = subparsers.add_parser("guard-isolation", help="Run isolation guard checks")
    guard_iso_parser.add_argument("path", nargs="?", default=".", help="File or directory path")
    guard_iso_parser.add_argument("--brand", type=str, help="Brand name")
    guard_iso_parser.add_argument("--rules", type=str, help="Rules JSON file path")
    guard_iso_parser.add_argument("--terms", nargs="+", help="Direct forbidden terms")

    clean_parser = subparsers.add_parser("clean", help="Clean slop and format issues")
    clean_parser.add_argument("path", help="File or directory path")
    clean_parser.add_argument("--fix", action="store_true", help="Fix issues")
    clean_parser.add_argument("--dry-run", action="store_true", help="Dry run format")

    lint_mem_parser = subparsers.add_parser("lint-memory", help="Lint memory graph")
    lint_mem_parser.add_argument("path", nargs="?", default=".", help="File or directory path")

    init_parser = subparsers.add_parser("init", help="Init project")
    init_parser.add_argument("path", nargs="?", default=".", help="File or directory path")
    init_parser.add_argument("--force", action="store_true", help="Force overwrite")

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
    elif args.command == "guard-isolation":
        return cmd_guard_isolation(args)
    elif args.command == "clean":
        return cmd_clean(args)
    elif args.command == "lint-memory":
        return cmd_lint_memory(args)
    elif args.command == "init":
        return cmd_init(args)

    return 0

if __name__ == "__main__":
    sys.exit(main())
