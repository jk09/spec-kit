"""Deterministic evals for the spec skills: each mutation plants a defect in the salon example
that spec-write is told to avoid, and the checker must catch it. Run: python -m unittest discover -s tests_kit"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SALON = ROOT / "examples" / "salon" / "specs"
FEAT = "features/FEAT-appointments.md"
DOM = "domain/DOM-schedule.md"

# name -> (file, old, new): the defect planted in the example
MUTATIONS = {
    "two shall in one requirement": (
        FEAT, "shall run ACT-OpenSlot.", "shall run ACT-OpenSlot and shall log it."),
    "vague word": (
        FEAT, "shall reject the request.", "shall normally reject the request.", ),
    "action loses Errors entry": (
        FEAT, "; SlotTaken: an Appointment already holds the Slot (REQ-003)", ""),
    "action drops a Preserves": (
        FEAT, "- Preserves: INV-001, INV-002\n- Realizes: REQ-001", "- Preserves: INV-001\n- Realizes: REQ-001"),
    "invariant forgets an affecting action": (
        DOM, "- Affected-by: ACT-BookAppointment, ACT-CancelAppointment\n", "- Affected-by: ACT-BookAppointment\n"),
    "unresolved TBD": (
        FEAT, "shall run ACT-CloseSlot.", "shall run ACT-CloseSlot within TBD seconds."),
    "unknown glossary term in Writes": (
        FEAT, "- Writes: schedule\n- Preserves: INV-001\n- Realizes: REQ-004", "- Writes: calendar\n- Preserves: INV-001\n- Realizes: REQ-004"),
}


def check(root):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "spec_check.py"), "--strict", "--root", str(root)],
                          capture_output=True, text=True)


class Mutations(unittest.TestCase):
    def test_each_planted_defect_is_caught(self):
        for name, (rel, old, new) in MUTATIONS.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "specs"
                shutil.copytree(SALON, root)
                f = root / rel
                text = f.read_text()
                self.assertIn(old, text, f"mutation '{name}' no longer matches the example")
                f.write_text(text.replace(old, new, 1))
                r = check(root)
                self.assertNotEqual(r.returncode, 0, f"checker missed: {name}\n{r.stdout}")


if __name__ == "__main__":
    unittest.main()
