#!/usr/bin/env python3
import re, sys
from pathlib import Path

INDEX_FILES = {"MEMORY.md", "MEMORY_EXTENDED.md"}
VALID_TYPES = {"user", "feedback", "project", "reference"}
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
INDEX_LINK_RE = re.compile(r"\([^)]+\.md\)")


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def extract_field(fm, key):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_type(fm):
    m = re.search(r"^\s*type:\s*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else ""


def slug_from_filename(filename):
    stem = filename[:-3]  # remove .md
    return stem.replace("_", "-")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: memory_graph_check.py <memory-directory>")
    directory = Path(sys.argv[1])

    if not directory.is_dir():
        sys.exit(f"not a directory: {directory}")

    all_md = list(directory.glob("*.md"))
    memory_files = [f for f in all_md if f.name not in INDEX_FILES]

    slug_map = {}
    file_data = {}

    # Precompute lowercase filename mapping for case-insensitive lookup
    actual_filenames_lower = {f.name.lower(): f.name for f in all_md}

    for f in memory_files:
        text = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        file_data[f.name] = (fm, body)
        if fm:
            name = extract_field(fm, "name")
            if name:
                slug_map[name.lower()] = f.name

    findings = []

    # BAD_FRONTMATTER
    for fname, (fm, _) in file_data.items():
        if fm is None:
            findings.append(f"BAD_FRONTMATTER | {fname} | missing frontmatter")
            continue
        name = extract_field(fm, "name")
        desc = extract_field(fm, "description")
        mtype = extract_type(fm)
        if not name:
            findings.append(f"BAD_FRONTMATTER | {fname} | missing or empty name")
        if not desc:
            findings.append(f"BAD_FRONTMATTER | {fname} | missing or empty description")
        if mtype not in VALID_TYPES:
            findings.append(f"BAD_FRONTMATTER | {fname} | invalid type: {mtype!r}")

    # SLUG_MISMATCH
    for fname in (f.name for f in memory_files):
        expected = slug_from_filename(fname)
        fm, _ = file_data[fname]
        if fm:
            actual = extract_field(fm, "name")
            if actual and actual != expected:
                findings.append(f"SLUG_MISMATCH | {fname} | name '{actual}' != expected '{expected}'")

    # BROKEN_WIKI_LINK
    for fname, (_, body) in file_data.items():
        for raw_target in WIKI_LINK_RE.findall(body):
            clean_target = raw_target.split('#')[0].split('|')[0].strip()
            if clean_target.lower() not in slug_map:
                findings.append(f"BROKEN_WIKI_LINK | {fname} | unresolved slug [[{clean_target}]]")

    # DEAD_INDEX_LINK
    referenced_files = set()
    for index_name in INDEX_FILES:
        index_path = directory / index_name
        if not index_path.exists():
            continue
        text = index_path.read_text(encoding="utf-8")
        for raw in INDEX_LINK_RE.findall(text):
            target = raw[1:-1]
            referenced_files.add(target)
            if target.lower() not in actual_filenames_lower:
                findings.append(f"DEAD_INDEX_LINK | {index_name} | missing target {target}")

    # ORPHAN_MEMORY (from index files)
    # Check lowercase to allow case-insensitive match
    referenced_files_lower = {f.lower() for f in referenced_files}
    for fname in (f.name for f in memory_files):
        if fname.lower() not in referenced_files_lower:
            findings.append(f"ORPHAN_MEMORY | {fname} | not referenced in any index file")

    # ORPHAN_GRAPH (from shell script - no in-edges or out-edges)
    for fname in (f.name for f in memory_files):
        fm, body = file_data[fname]
        slug = extract_field(fm, "name") if fm else ""
        has_out = bool(WIKI_LINK_RE.findall(body))
        has_in = False
        if slug:
            for _, b in file_data.values():
                if any(s.split('#')[0].split('|')[0].strip().lower() == slug.lower() for s in WIKI_LINK_RE.findall(b)):
                    has_in = True
                    break
        if not has_out and not has_in:
            findings.append(f"ORPHAN_GRAPH | {fname} | no incoming or outgoing wiki-links")

    order = ["BAD_FRONTMATTER", "SLUG_MISMATCH", "BROKEN_WIKI_LINK", "DEAD_INDEX_LINK", "ORPHAN_MEMORY", "ORPHAN_GRAPH"]
    grouped = {k: [] for k in order}
    for line in findings:
        key = line.split(" | ")[0]
        grouped.setdefault(key, []).append(line)

    for key in order:
        for line in grouped.get(key, []):
            print(line)

    print(f"{len(findings)} findings")

    # Task 1: Check for cycles in markdown wiki-links
    graph = {}
    for fname, (_, body) in file_data.items():
        source_stem = slug_from_filename(fname).lower()
        graph[source_stem] = [slug.split('#')[0].split('|')[0].strip().lower() for slug in WIKI_LINK_RE.findall(body)]

    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, path + [neighbor]):
                    return True
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycle_path = path[cycle_start:] + [neighbor]
                print(f"[CYCLE] Cyclic wiki-link reference: {' -> '.join(cycle_path)}")
                sys.exit(1)

        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node, [node])

    sys.exit(0 if not findings else 1)

if __name__ == "__main__":
    main()
