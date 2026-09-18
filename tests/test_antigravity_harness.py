import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "harness_installer",
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "antigravity-harness"
    / "install_harness.py",
)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class HarnessInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "Vault"

    def install(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return harness.install(self.workspace, **kwargs)

    def test_dry_run_leaves_workspace_unchanged(self):
        self.install(dry_run=True)
        self.assertFalse(self.workspace.exists())

    def test_install_merges_named_hooks_and_payload(self):
        hooks = self.workspace / ".agents" / "hooks.json"
        hooks.parent.mkdir(parents=True)
        hooks.write_text(json.dumps({"other-hook": {"Stop": []}}), encoding="utf-8")
        self.install()
        merged = json.loads(hooks.read_text(encoding="utf-8"))
        self.assertIn("other-hook", merged)
        for name in harness.HOOK_NAMES:
            self.assertIn(name, merged)
        self.assertTrue(
            (self.workspace / ".agents" / "scripts" / "harness_stop_guard.py").is_file()
        )

    def test_force_controls_named_hook_upgrade(self):
        hooks = self.workspace / ".agents" / "hooks.json"
        hooks.parent.mkdir(parents=True)
        hooks.write_text(
            json.dumps({"soft-exam-stop-guard": {"Stop": []}}),
            encoding="utf-8",
        )
        self.install()
        preserved = json.loads(hooks.read_text(encoding="utf-8"))
        self.assertEqual(preserved["soft-exam-stop-guard"], {"Stop": []})
        self.install(force=True)
        upgraded = json.loads(hooks.read_text(encoding="utf-8"))
        self.assertNotEqual(upgraded["soft-exam-stop-guard"], {"Stop": []})


if __name__ == "__main__":
    unittest.main()
