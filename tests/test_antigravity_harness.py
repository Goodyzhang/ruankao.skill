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

    def test_image_question_confirmed_by_current_reply_triggers_stop(self):
        records = [
            {"type": "USER_INPUT", "content": "为我讲一下这道题（附图）"},
            {
                "type": "PLANNER_RESPONSE",
                "content": (
                    "题目归属：软考明确\n级别：系统架构设计师-高级\n"
                    "## 题目复原\n题干与选项\n## 迁移提示\n规律"
                ),
            },
        ]
        stopped = self.run_hook(
            "harness_stop_guard.py", records,
            terminationReason="model_stop", fullyIdle=True,
        )
        self.assertEqual(stopped["decision"], "continue")

        records.append({"type": "USER_INPUT", "content": "检查一张普通图片"})
        unrelated = self.run_hook(
            "harness_tool_guard.py", records,
            toolCall={"name": "run_command", "args": {}},
        )
        self.assertEqual(unrelated["decision"], "allow")

    def test_grill_closing_leaked_call_is_recovered(self):
        records = [
            {"type": "USER_INPUT", "content": "为我讲一下这道题（附图）"},
            {
                "type": "PLANNER_RESPONSE",
                "content": "题目归属：软考明确\n## 题目复原\n题干\n## 迁移提示\n规律",
                "tool_calls": [{"name": "ask_question"}],
            },
            {"type": "GENERIC", "content": "A1: 开始 Grill"},
            {
                "type": "PLANNER_RESPONSE",
                "content": "**G1 反馈：回答正确！**\n请完成下一轮。",
                "tool_calls": [{"name": "ask_question"}],
            },
            {"type": "GENERIC", "content": "A1: 正确答案"},
        ]
        reminder = self.run_hook(
            "harness_pre_invocation.py", records, invocationNum=2, initialNumSteps=3
        )
        self.assertTrue(reminder["injectSteps"])

        closing = {
            "type": "PLANNER_RESPONSE",
            "content": (
                "### Grill 第 3 轮反馈与诊断收官\n本轮小结。"
                "call:default_api:ask_question{questions:[...]}"
            ),
        }
        event = {"terminationReason": "model_stop", "fullyIdle": True}
        leaked = self.run_hook("harness_stop_guard.py", records + [closing], **event)
        self.assertEqual(leaked["decision"], "continue")

        closing["tool_calls"] = [{"name": "ask_question"}]
        with_card = self.run_hook("harness_stop_guard.py", records + [closing], **event)
        self.assertEqual(with_card["decision"], "allow")

        closing.pop("tool_calls")
        unrelated = self.run_hook(
            "harness_stop_guard.py",
            records + [{"type": "USER_INPUT", "content": "检查这个 Hook 问题"}, closing],
            **event,
        )
        self.assertEqual(unrelated["decision"], "allow")

    def test_early_grill_mastery_still_needs_archive_card(self):
        records = [
            {"type": "USER_INPUT", "content": "为我讲一下这道题（附图）"},
            {
                "type": "PLANNER_RESPONSE",
                "content": "题目归属：软考明确\n## 题目复原\n题干\n## 迁移提示\n规律",
                "tool_calls": [{"name": "ask_question"}],
            },
            {"type": "GENERIC", "content": "A1: 开始 Grill"},
            {
                "type": "PLANNER_RESPONSE",
                "content": "**G1 反馈：回答正确！**",
                "tool_calls": [{"name": "ask_question"}],
            },
            {"type": "GENERIC", "content": "A1: 正确答案"},
            {
                "type": "PLANNER_RESPONSE",
                "content": "**G2 反馈：回答正确！**\n### Grill 诊断总结\n已达到掌握证据，提前结束 Grill 追问。",
            },
        ]
        event = {"terminationReason": "model_stop", "fullyIdle": True}
        missing = self.run_hook("harness_stop_guard.py", records, **event)
        self.assertEqual(missing["decision"], "continue")
        self.assertIn("归档确认卡", missing["reason"])

        records[-1]["tool_calls"] = [{"name": "ask_question"}]
        with_card = self.run_hook("harness_stop_guard.py", records, **event)
        self.assertEqual(with_card["decision"], "allow")

        records[-1].pop("tool_calls")
        for choice in ("不归档，直接结束", "确认归档（高级）"):
            result = {
                "type": "GENERIC",
                "content": (
                    "Created At: now\nCompleted At: now\n"
                    f"A1: {choice}"
                ),
            }
            finished = self.run_hook(
                "harness_stop_guard.py", records[:-1] + [result, records[-1]], **event
            )
            self.assertEqual(finished["decision"], "allow")

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
