import unittest
import subprocess
import tempfile
import os
import shutil
import sys
from pathlib import Path

class TestCLI(unittest.TestCase):
    def run_cli(self, args):
        result = subprocess.run(
            [sys.executable, "-m", "gorgona"] + args,
            capture_output=True,
            text=True
        )
        return result

    def test_doctor(self):
        res = self.run_cli(["doctor"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("PASS", res.stdout)

    def test_scan(self):
        # non-existent path exits 1 without printing "Scanning target"
        res = self.run_cli(["scan", "/nonexistent_path_for_test"])
        self.assertEqual(res.returncode, 1)
        self.assertNotIn("Scanning target", res.stdout)

        # invalid args exit 2 (argparse standard)
        res = self.run_cli(["scan", "--invalid-arg-xyz"])
        self.assertEqual(res.returncode, 2)

        # clean path exits 0
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "clean.txt"), "w", encoding="utf-8") as f:
                f.write("This is a clean file.\n")
            res = self.run_cli(["scan", td])
            self.assertEqual(res.returncode, 0)

            # forbidden file (.env) flagged, exits 1
            with open(os.path.join(td, ".env"), "w", encoding="utf-8") as f:
                f.write("SECRET=123\n")
            res = self.run_cli(["scan", td])
            self.assertEqual(res.returncode, 1)
            self.assertIn(".env", res.stdout)

        # path with secrets exits 1
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "secret.txt"), "w", encoding="utf-8") as f:
                # assuming the exposure guard detects something like "password = '...'" or AWS keys
                f.write("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n")
            res = self.run_cli(["scan", td])
            self.assertEqual(res.returncode, 1)

    def test_guard_isolation(self):
        # We need a gorgona.json for isolation
        with tempfile.TemporaryDirectory() as td_config, tempfile.TemporaryDirectory() as td:
            config_path = os.path.join(td_config, "gorgona.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write('{"isolation": {"brand": "A", "rules": {"B": ["SecretB"]}}}')

            clean_file = os.path.join(td, "clean.txt")
            with open(clean_file, "w", encoding="utf-8") as f:
                f.write("Just A things.")

            res = self.run_cli(["guard-isolation", td, "--rules", config_path])
            self.assertEqual(res.returncode, 0)

            leak_file = os.path.join(td, "leak.txt")
            with open(leak_file, "w", encoding="utf-8") as f:
                f.write("Leaking SecretB here.")

            res = self.run_cli(["guard-isolation", td, "--rules", config_path])
            self.assertEqual(res.returncode, 1)

    def test_clean(self):
        with tempfile.TemporaryDirectory() as td:
            target = os.path.join(td, "dirty.txt")
            with open(target, "w", encoding="utf-8") as f:
                f.write("Dirty \u2014 text")

            # --dry-run
            res = self.run_cli(["clean", target, "--dry-run"])
            self.assertEqual(res.returncode, 1)
            with open(target, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "Dirty \u2014 text")

            # --fix
            res = self.run_cli(["clean", target, "--fix"])
            self.assertEqual(res.returncode, 0)
            with open(target, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "Dirty, text")

    def test_lint_memory(self):
        with tempfile.TemporaryDirectory() as td:
            # Create a simple valid memory directory
            os.makedirs(os.path.join(td, "memory"))
            mem_dir = os.path.join(td, "memory")
            with open(os.path.join(mem_dir, "MEMORY.md"), "w", encoding="utf-8") as f:
                f.write("Index")
            with open(os.path.join(mem_dir, "test.md"), "w", encoding="utf-8") as f:
                f.write("---\nname: test\ntype: user\ndescription: foo\n---\n")

            # It might fail with ORPHAN_MEMORY if MEMORY.md doesn't link it, but let's check it runs
            res = self.run_cli(["lint-memory", mem_dir])
            # Could be 1 if there are findings (like orphan), but we just ensure it executes
            self.assertTrue(res.returncode in [0, 1])
            self.assertIn("findings", res.stdout)

    def test_init(self):
        with tempfile.TemporaryDirectory() as td:
            target = os.path.join(td, "init_test")
            res = self.run_cli(["init", target])
            self.assertEqual(res.returncode, 0)
            self.assertTrue(os.path.exists(os.path.join(target, "gorgona.json")))

            # Fails without force if exists
            res = self.run_cli(["init", target])
            self.assertEqual(res.returncode, 1)

            # Succeeds with force
            res = self.run_cli(["init", target, "--force"])
            self.assertEqual(res.returncode, 0)

    def test_single_env_scan_one_violation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("SECRET=123", encoding="utf-8")
            res = self.run_cli(["scan", str(env_file)])
            self.assertEqual(res.returncode, 1)
            # Count occurrences of "[SECURITY] .env:"
            self.assertEqual(res.stdout.count("[SECURITY] .env:"), 1)

    def test_clean_dry_run_exit_code(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "dirty.md"
            md_file.write_text("This is bad \u2014 em dash.", encoding="utf-8")
            res = self.run_cli(["clean", str(md_file), "--fix", "--dry-run"])
            self.assertEqual(res.returncode, 1)

    def test_max_files_negative(self):
        res = self.run_cli(["scan", ".", "--max-files", "-1"])
        self.assertEqual(res.returncode, 2)

    def test_invalid_json_rules(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
            tf.write("not valid json")
            tf_path = tf.name
        try:
            res = self.run_cli(["guard-isolation", ".", "--rules", tf_path])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Error: Failed to load rules file", res.stderr)
            self.assertNotIn("Traceback", res.stderr)
        finally:
            os.unlink(tf_path)

    def test_lint_memory_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem_path = Path(tmpdir) / "MEMORY.md"
            f1 = Path(tmpdir) / "valid.md"
            f2 = Path(tmpdir) / "other.md"
            mem_path.write_text("---\nname: index\ntype: index\n---\n[valid](valid.md)\n[other](other.md)", encoding="utf-8")
            f1.write_text("---\nname: valid\ndescription: v\ntype: user\n---\nLink to [[other]]", encoding="utf-8")
            f2.write_text("---\nname: other\ndescription: o\ntype: user\n---\nLink to [[valid]]", encoding="utf-8")
            res = self.run_cli(["lint-memory", str(tmpdir)])
            self.assertEqual(res.returncode, 1)
            self.assertIn("[CYCLE]", res.stdout)

if __name__ == '__main__':
    unittest.main()
