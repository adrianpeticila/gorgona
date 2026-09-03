import re

def insert_test_before_main(filepath, test_code, imports=""):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if imports:
        # insert after first import
        content = re.sub(r'^(import [^\n]+)', r'\1\n' + imports, content, count=1)
    
    # insert before if __name__
    parts = content.split("if __name__ == '__main__':")
    if len(parts) == 2:
        content = parts[0] + test_code + "\n\nif __name__ == '__main__':" + parts[1]
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

exposure_test = """
    def test_scan_path_includes_github_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_dir = Path(tmpdir) / ".github"
            gh_dir.mkdir()
            wf = gh_dir / "workflow.yml"
            wf.write_text("key: sk-proj-1234567890abcdefghij1234567890abcdefghij", encoding="utf-8")
            findings = ExposureGuard().scan_path(Path(tmpdir))
            self.assertEqual(len(findings), 1)
"""

isolation_test = """
    def test_swapped_args_brand_correct(self):
        g = IsolationGuard({"BrandA": {"Foreign": ["BrandB"]}})
        violations = g.check_content("BrandB here", target_brand="BrandA")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].target_brand, "BrandA")
"""

text_clean_test = """
    def test_tilde_fences_and_indented_blocks_preserved(self):
        text = "prose — text\\n~~~bash\\necho — code\\n~~~\\n    shell — option --long"
        cleaned = TextCleanerGuard().clean(text)
        self.assertIn("~~~bash\\necho — code\\n~~~", cleaned)
        self.assertIn("    shell — option --long", cleaned)
        self.assertTrue(cleaned.startswith("prose, text"))
        # Also test scan ignores them
        findings = TextCleanerGuard().scan("~~~bash\\necho — code\\n~~~\\n    shell — option --long")
        self.assertEqual(len(findings), 0)
"""

insert_test_before_main("tests/test_exposure.py", exposure_test, "import tempfile\nfrom pathlib import Path")
insert_test_before_main("tests/test_isolation.py", isolation_test, "")
insert_test_before_main("tests/test_text_clean.py", text_clean_test, "")
