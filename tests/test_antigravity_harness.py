import contextlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest import mock


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
            event_handlers = next(iter(merged[name].values()))
            command_hook = event_handlers[0].get("hooks", [event_handlers[0]])[0]
            self.assertTrue(
                command_hook["command"].startswith(harness.python_command() + " ")
            )
            relative_script = Path(command_hook["command"].split()[-1])
            self.assertEqual(relative_script.parts[0], "scripts")
            script_path = hooks.parent / relative_script
            self.assertTrue(script_path.is_file(), script_path)
        self.assertTrue(
            (self.workspace / ".agents" / "scripts" / "harness_stop_guard.py").is_file()
        )

    def test_python_launcher_falls_back_when_py_is_unavailable(self):
        with mock.patch.object(
            harness.shutil, "which", side_effect=lambda name: "python.exe" if name == "python" else None
        ):
            self.assertEqual(harness.python_command(), "python")

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

    def run_hook(self, name, records, **event_fields):
        transcript = Path(self.tmp.name) / "transcript.jsonl"
        transcript.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )
        payload = {
            "conversationId": "test-conversation",
            "workspacePaths": [str(self.workspace)],
            "transcriptPath": str(transcript),
            "artifactDirectoryPath": self.tmp.name,
            "modelName": "test-model",
            **event_fields,
        }
        script = harness.ROOT / "scripts" / name
        output = io.StringIO()
        sys.path.insert(0, str(script.parent))
        try:
            with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload, ensure_ascii=False))):
                with contextlib.redirect_stdout(output):
                    runpy.run_path(str(script), run_name="__main__")
        finally:
            sys.path.pop(0)
        return json.loads(output.getvalue())

    def test_pre_invocation_accepts_normal_antigravity_metadata(self):
        result = self.run_hook(
            "harness_pre_invocation.py",
            [{"type": "USER_INPUT", "content": "用 soft-exam-question-tutor skill 讲解这道软考题"}],
            invocationNum=0,
            initialNumSteps=1,
        )
        self.assertTrue(result["injectSteps"])

    def test_old_exam_context_does_not_capture_diagnostics(self):
        records = [
            {"type": "USER_INPUT", "content": "请讲解这道软考题"},
            {"type": "PLANNER_RESPONSE", "content": "## 题目复原\n## 迁移提示"},
            {"type": "USER_INPUT", "content": "检查软考 Skill 的 ask_question 为什么弹不出来"},
        ]
        reminder = self.run_hook(
            "harness_pre_invocation.py", records, invocationNum=1, initialNumSteps=3
        )
        self.assertEqual(reminder["injectSteps"], [])
        tool = self.run_hook(
            "harness_tool_guard.py", records, toolCall={"name": "run_command", "args": {}}
        )
        self.assertEqual(tool["decision"], "allow")

    def test_current_question_continuation_keeps_harness_active(self):
        records = [
            {"type": "USER_INPUT", "content": "请讲解这道软考题"},
            {"type": "PLANNER_RESPONSE", "content": "## 题目复原\n## 迁移提示"},
            {"type": "USER_INPUT", "content": "A1: 开始 Grill"},
        ]
        result = self.run_hook(
            "harness_pre_invocation.py", records, invocationNum=1, initialNumSteps=3
        )
        self.assertTrue(result["injectSteps"])

    def test_stop_allows_missing_tool_report_but_catches_bare_explanation(self):
        user_input = {"type": "USER_INPUT", "content": "请讲解这道软考题"}
        explanation = "## 题目复原\n题干\n## 迁移提示\n解题提示"
        event = {"terminationReason": "model_stop", "fullyIdle": True}
        bare = self.run_hook(
            "harness_stop_guard.py",
            [user_input, {"type": "PLANNER_RESPONSE", "content": explanation}],
            **event,
        )
        self.assertEqual(bare["decision"], "continue")

        unavailable = self.run_hook(
            "harness_stop_guard.py",
            [
                user_input,
                {
                    "type": "PLANNER_RESPONSE",
                    "content": explanation + "\n当前会话未暴露结构化提问工具，停在归档确认阶段。",
                },
            ],
            **event,
        )
        self.assertEqual(unavailable["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
