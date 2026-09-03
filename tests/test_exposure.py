import unittest
import tempfile
from pathlib import Path
from gorgona.guards.exposure import ExposureGuard

class TestExposureGuard(unittest.TestCase):
    def setUp(self):
        self.guard = ExposureGuard()

    def test_github_pat_lengths(self):
        # 34 chars
        text1 = "ghp_1234567890123456789012345678901234"
        self.assertGreater(len(self.guard.scan_text(text1)), 0)

        # 47 chars
        text2 = "github_pat_11AAAAAAA0123456789abcdefghijklmnopqrstuvwxyz"
        self.assertGreater(len(self.guard.scan_text(text2)), 0)

        # 82 chars
        text3 = "github_pat_11AAAAAAA0123456789abcdefghijklmnopqrstuvwxyz11AAAAAAA0123456789abcdefghijklmnopqrstuvwxyz"
        self.assertGreater(len(self.guard.scan_text(text3)), 0)

    def test_generic_secret_special_chars(self):
        text = "api_key=Pass!@#123_test"
        self.assertGreater(len(self.guard.scan_text(text)), 0)

    def test_multiline_line_number_accuracy(self):
        text = "line1\nline2\nghp_1234567890123456789012345678901234\nline4\napi_key=Pass!@#123_test"
        findings = self.guard.scan_text(text)
        pat_f = [f for f in findings if f.category == "github_pat"][0]
        api_f = [f for f in findings if f.category == "api_key_generic"][0]
        self.assertEqual(pat_f.line_number, 3)
        self.assertEqual(api_f.line_number, 5)

    def test_anthropic_key_exclusive_classification(self):
        findings = self.guard.scan_text("sk-ant-api03-1234567890abcdefghij1234567890")
        categories = [f.category for f in findings]
        self.assertIn("anthropic_key", categories)
        self.assertNotIn("openai_key", categories)

    def test_template_variables_ignored(self):
        findings = self.guard.scan_text("API_KEY=${SUPER_SECRET_ENV_VAR}\nTOKEN={{process.env.APP_TOKEN}}")
        categories = [f.category for f in findings]
        self.assertNotIn("api_key_generic", categories)

    def test_env_example_not_forbidden(self):
        from pathlib import Path
        self.assertFalse(self.guard._is_forbidden_file(".env.example"))


    def test_scan_path_includes_github_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_dir = Path(tmpdir) / ".github"
            gh_dir.mkdir()
            wf = gh_dir / "workflow.yml"
            wf.write_text("key: sk-proj-1234567890abcdefghij1234567890abcdefghij", encoding="utf-8")
            findings = ExposureGuard().scan_path(Path(tmpdir))
            self.assertEqual(len(findings), 1)


if __name__ == '__main__':
    unittest.main()
