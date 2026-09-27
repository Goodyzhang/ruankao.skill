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
            for event_handlers in merged[name].values():
                command_hook = event_handlers[0].get("hooks", [event_handlers[0]])[0]
                self.assertTrue(command_hook["command"].startswith(harness.python_command() + " "))
                script_arg = command_hook["command"][len(harness.python_command()) + 1:].split()[0]
                relative_script = Path(script_arg)
                self.assertEqual(relative_script.parts[0], "scripts")
                self.assertTrue((hooks.parent / relative_script).is_file())
        self.assertIn("PostInvocation", merged["soft-exam-stop-guard"])
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

    def run_hook(self, name, records, post_invocation=False, **event_fields):
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
                args = [str(script)] + (["--post-invocation"] if post_invocation else [])
                with contextlib.redirect_stdout(output), mock.patch.object(sys, "argv", args):
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
                "harness_stop_guard.py", records[:-1] + [
                    {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "ask_question"}]},
                    result, records[-1],
                ], **event
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

    def active_grill(self):
        return [
            {"type": "USER_INPUT", "content": "<USER_REQUEST>\n\n</USER_REQUEST>\n<ADDITIONAL_METADATA>image</ADDITIONAL_METADATA>"},
            {"type": "PLANNER_RESPONSE", "content": "题目归属：软考明确\n## 题目复原\n## 迁移提示"},
            {"type": "USER_INPUT", "content": "<USER_REQUEST>\n？\n</USER_REQUEST>\n<ADDITIONAL_METADATA>time</ADDITIONAL_METADATA>"},
            {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "ask_question"}]},
            {"type": "GENERIC", "content": "Created At: now\nCompleted At: now\nA1: 开始本题 Grill 深度诊断"},
            {"type": "PLANNER_RESPONSE", "content": "第一轮练习", "tool_calls": [{"name": "ask_question"}]},
            {"type": "GENERIC", "content": "Created At: now\nCompleted At: now\nA1: 内容选项 B"},
        ]

    def test_question_mark_and_heading_free_feedback_keep_card_due(self):
        for feedback in ("回答正确，继续第二轮。", "### 第 1 轮反馈与第 2 轮追问\ncall:default_api:ask_question{questions:[...]}\n"):
            records = self.active_grill() + [{"type": "PLANNER_RESPONSE", "content": feedback}]
            reminder = self.run_hook("harness_pre_invocation.py", records)
            self.assertTrue(reminder["injectSteps"])
            stop = self.run_hook("harness_stop_guard.py", records, terminationReason="model_stop", fullyIdle=True)
            self.assertEqual(stop["decision"], "continue")
            post = self.run_hook("harness_stop_guard.py", records, post_invocation=True)
            self.assertEqual(post["terminationBehavior"], "force_continue")
            records[-1]["tool_calls"] = [{"name": "ask_question"}]
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})

    def test_new_task_ends_context_even_after_question_mark_recovery(self):
        for request in ("检查这个 Hook 问题", "帮我写一份周报"):
            records = self.active_grill() + [
                {"type": "USER_INPUT", "content": f"<USER_REQUEST>{request}</USER_REQUEST>"},
                {"type": "PLANNER_RESPONSE", "content": "call:default_api:ask_question{quoted example}"},
            ]
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})

    def test_large_tool_result_does_not_remove_question_context(self):
        records = self.active_grill() + [
            {"type": "GENERIC", "content": "large file result " + "x" * 370000},
            {"type": "PLANNER_RESPONSE", "content": "回答正确，下一轮。"},
        ]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

    def test_new_question_does_not_inherit_previous_archive_choice(self):
        for request, media in (("下一题", None), ("再来一题，我选 B", None), ("我选 B", [{"type": "image"}])):
            records = self.active_grill()
            records[-1]["content"] = "Completed At: now\nA1: 确认归档"
            records.extend([
                {"type": "USER_INPUT", "content": f"<USER_REQUEST>{request}</USER_REQUEST>", "media": media},
                {"type": "PLANNER_RESPONSE", "content": "题目归属：软考明确\n## 题目复原\n新题\n## 迁移提示\n规律"},
            ])
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

    def test_successful_or_pending_cards_and_terminal_choices_are_not_repeated(self):
        for choice in ("确认归档", "直接归档并跳过 Grill", "不归档，直接结束", "结束本次题目"):
            records = self.active_grill()
            records[-1]["content"] = "Completed At: now\nA1: " + choice
            records.append({"type": "PLANNER_RESPONSE", "content": "### Grill 诊断总结\n本题结束。"})
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        records = self.active_grill()[:-1] + [{"type": "PLANNER_RESPONSE", "content": "等待卡片作答。"}]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})

    def test_recovery_retries_are_bounded_and_logged(self):
        records = self.active_grill() + [{"type": "PLANNER_RESPONSE", "content": "回答正确。"}]
        for _ in range(2):
            result = self.run_hook("harness_stop_guard.py", records, post_invocation=True)
            self.assertEqual(result["terminationBehavior"], "force_continue")
            message = result["injectSteps"][0]["ephemeralMessage"]
            self.assertIn("[soft-exam-card-recovery]", message)
            records.append({"type": "EPHEMERAL_MESSAGE", "content": message})
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, terminationReason="model_stop", fullyIdle=True)["decision"], "allow")
            records.append({"type": "PLANNER_RESPONSE", "content": "仍然只有文字。"})
        result = self.run_hook("harness_stop_guard.py", records, post_invocation=True)
        blocked = result["injectSteps"][0]["ephemeralMessage"]
        self.assertIn("[soft-exam-card-blocked]", blocked)
        records.extend([
            {"type": "EPHEMERAL_MESSAGE", "content": blocked},
            {"type": "PLANNER_RESPONSE", "content": "卡片生成失败，当前题未完成。"},
        ])
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        events = [json.loads(line) for line in (Path(self.tmp.name) / "soft-exam-card-events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(events[-1]["check"], "recovery_report_requested")
        self.assertTrue(any(e["action"] == "force_continue" for e in events))
        self.assertNotIn("回答正确", json.dumps(events, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
