"""Tests for the kit's own scripts. Run: python -m unittest discover -s tests_kit"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import spec_guard  # noqa: E402
import spec_trace  # noqa: E402

SALON = ROOT / "examples" / "salon" / "specs"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


class Checker(unittest.TestCase):
    def test_salon_example_is_clean(self):
        r = run("scripts/spec_check.py", "--strict", "--root", SALON)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_banned_synonym_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "specs"
            subprocess.run(["cp", "-r", str(SALON), str(root)], check=True)
            gl = (root / "glossary.md").read_text()
            avoid = [ln.split("|")[4].strip() for ln in gl.splitlines()
                     if ln.startswith("|") and len(ln.split("|")) > 5 and ln.split("|")[4].strip() not in ("", "Avoid", "---")]
            self.assertTrue(avoid, "salon glossary has no Avoid entries to test with")
            word = avoid[0].split(",")[0].strip()
            f = root / "features" / "FEAT-appointments.md"
            f.write_text(f.read_text().replace("# Appointments", f"# Appointments\n\nThe {word} is here.", 1))
            r = run("scripts/spec_check.py", "--root", root)
            self.assertNotEqual(r.returncode, 0, r.stdout)


class Trace(unittest.TestCase):
    def test_comment_only_mention_fails_strict(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "t.py").write_text("# REQ-001 covered\n")
            (d / "u.py").write_text("def test_REQ_001():\n    pass\nNAME = 'REQ-002'\n")
            loose = spec_trace.scan([d], [])
            strict = spec_trace.scan([d], [], code_only=True)
            self.assertIn("REQ-001", loose)
            self.assertNotIn("REQ-001", strict)
            self.assertIn("REQ-002", strict)

    def test_declared_requires_annotation_or_declaration_line(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "a.py").write_text("X = 'REQ-001'\n@pytest.mark.spec('REQ-002')\ndef f(): pass\n")
            (d / "b.js").write_text("it('REQ-003 rejects', () => {})\nconst y = 'REQ-004'\n")
            hits = spec_trace.scan([d], [], code_only=True, declared_only=True)
            self.assertEqual(sorted(hits), ["REQ-002", "REQ-003"])

    def test_export_contains_actions(self):
        r = run("scripts/spec_trace.py", "--root", SALON, "export")
        data = json.loads(r.stdout)
        self.assertTrue(any(c["id"] == "ACT-BookAppointment" for c in data["contracts"]))

    def test_coverage_reports_missing(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("scripts/spec_trace.py", "--root", SALON, "coverage", "--src", d, "--tests", d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("MISSING", r.stdout)


class Guard(unittest.TestCase):
    def test_mixed_pr_is_flagged(self):
        spec, impl = spec_guard.classify(["specs/features/FEAT-a.md", "src/app.py"])
        self.assertTrue(spec and impl)

    def test_spec_only_and_impl_only_pass(self):
        s, i = spec_guard.classify(["specs/features/FEAT-a.md", "specs/index.md", "README.md"])
        self.assertTrue(s and not i)
        s, i = spec_guard.classify(["src/app.py", "tests/test_app.py"])
        self.assertTrue(i and not s)

    def test_tooling_is_neutral(self):
        s, i = spec_guard.classify(["specs/features/FEAT-a.md", "scripts/spec_check.py", ".github/workflows/x.yml"])
        self.assertTrue(s and not i)


if __name__ == "__main__":
    unittest.main()
