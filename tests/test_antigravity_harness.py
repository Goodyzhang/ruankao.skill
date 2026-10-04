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
        for choice in (
            "确认归档",
            "直接归档并跳过 Grill",
            "不归档，直接结束",
            "结束本次题目",
            "(Recommended) 结束本题流程",
            "[推荐] 确认归档（中级）",
            "1. 已完成，等待下一题",
            "A. 等待上传新题目",
        ):
            records = self.active_grill()
            records[-1]["content"] = "Completed At: now\nA1: " + choice
            records.append({"type": "PLANNER_RESPONSE", "content": "### Grill 诊断总结\n本题结束。"})
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        records = self.active_grill()
        records.append({"type": "PLANNER_RESPONSE", "content": "本题全流程已归档完毕。"})
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        records = self.active_grill()[:-1] + [{"type": "PLANNER_RESPONSE", "content": "等待卡片作答。"}]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})

    def test_setup_card_answers_do_not_trigger_grill_recovery(self):
        for question, answer in (
            ("归档目录使用哪个位置？", "当前 Vault 下的科目目录"),
            ("资料根目录使用哪个位置？", "手动输入绝对路径"),
            ("未找到所需工具，请填写 CLI 路径或跳过。", "跳过"),
            ("Vault 位置使用哪个？", str(self.workspace)),
        ):
            with self.subTest(question=question):
                records = self.active_grill() + [
                    {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "ask_question", "args": {
                        "questions": [{"question": question, "options": [{"label": "默认目录"}]}]
                    }}]},
                    {"type": "GENERIC", "content": "Completed At: now\nA1: " + answer},
                    {"type": "PLANNER_RESPONSE", "content": "已记录位置，将继续处理本题。"},
                ]
                self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
                # Setup does not disable normal single-question tool restrictions.
                result = self.run_hook("harness_tool_guard.py", records, toolCall={"name": "run_command"})
                self.assertEqual(result["decision"], "deny")

    def test_setup_option_words_cannot_hide_a_real_grill_question(self):
        records = self.active_grill()
        records[-2]["tool_calls"] = [{"name": "ask_question", "args": {
            "questions": [{"question": "SMTP 和 POP3 分别负责哪一步？", "options": [{"label": "归档目录"}]}]
        }}]
        records[-1]["content"] = "A1: POP3 负责读取"
        records.append({"type": "PLANNER_RESPONSE", "content": "回答正确，继续下一轮。"})
        result = self.run_hook("harness_stop_guard.py", records, post_invocation=True)
        self.assertEqual(result["terminationBehavior"], "force_continue")

    def test_grill_resumes_after_a_completed_environment_card(self):
        records = self.active_grill() + [
            {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "ask_question", "arguments": json.dumps({
                "questions": [{"question": "归档目录使用哪个位置？"}]
            })}]},
            {"type": "GENERIC", "content": "A1: 选择默认资料目录"},
            {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "ask_question", "args": {
                "questions": [{"question": "请选择邮件提交流程中的协议。"}]
            }}]},
            {"type": "GENERIC", "content": "A1: SMTP"},
            {"type": "PLANNER_RESPONSE", "content": "回答正确，继续第二轮。"},
        ]
        result = self.run_hook("harness_stop_guard.py", records, post_invocation=True)
        self.assertEqual(result["terminationBehavior"], "force_continue")

    def test_explicit_text_mode_survives_reply_and_does_not_relax_tools(self):
        records = self.active_grill() + [
            {"type": "USER_INPUT", "content": "改用文字模式继续本题"},
            {"type": "PLANNER_RESPONSE", "content": "G2：条件改变后如何判断？A. 内容甲 B. 内容乙 C. 内容丙"},
        ]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        reminder = self.run_hook("harness_pre_invocation.py", records)
        self.assertIn("本题文字模式", reminder["injectSteps"][0]["ephemeralMessage"])
        records.extend([
            {"type": "USER_INPUT", "content": "B"},
            {"type": "PLANNER_RESPONSE", "content": "回答正确，G3：A. 甲 B. 乙 C. 丙"},
        ])
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        restricted = self.run_hook("harness_tool_guard.py", records, toolCall={"name": "run_command"})
        self.assertEqual(restricted["decision"], "deny")
        events = [json.loads(line) for line in (Path(self.tmp.name) / "soft-exam-card-events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-1]["check"], "confirmed_text_mode")

    def test_mode_requires_user_choice_and_new_question_starts_with_cards(self):
        records = self.active_grill() + [
            {"type": "PLANNER_RESPONSE", "content": "已经替用户选择文字模式，继续文字练习。"},
        ]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")
        records.extend([
            {"type": "USER_INPUT", "content": "使用文字模式"},
            {"type": "PLANNER_RESPONSE", "content": "文字练习"},
            {"type": "USER_INPUT", "content": "下一题，我选 B", "media": [{"type": "image"}]},
            {"type": "PLANNER_RESPONSE", "content": "题目归属：软考明确\n## 题目复原\n## 迁移提示"},
        ])
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

    def test_real_mode_card_response_switches_mode_but_ordinary_card_does_not(self):
        for question, allowed in (("请选择本题的交互方式：卡片或文字模式", True), ("SMTP 的作用是什么？", False)):
            records = self.active_grill() + [
                {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "ask_question", "args": {
                    "questions": [{"question": question}]
                }}]},
                {"type": "GENERIC", "status": "DONE", "content": "A1: (Recommended) 使用文字模式"},
                {"type": "PLANNER_RESPONSE", "content": "接着练习。"},
            ]
            result = self.run_hook("harness_stop_guard.py", records, post_invocation=True)
            self.assertEqual(result == {}, allowed)

    def test_return_to_card_mode_restores_missing_card_recovery(self):
        records = self.active_grill() + [
            {"type": "USER_INPUT", "content": "使用文字模式"},
            {"type": "PLANNER_RESPONSE", "content": "文字练习"},
            {"type": "USER_INPUT", "content": "切回卡片模式"},
            {"type": "PLANNER_RESPONSE", "content": "## 考点与判别词\n继续练习。"},
        ]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

    def test_only_explanation_finishes_but_later_grill_choice_takes_precedence(self):
        records = [
            {"type": "USER_INPUT", "content": "请只讲解这道软考题，我选 B"},
            {"type": "PLANNER_RESPONSE", "content": "## 题目复原\n## 迁移提示"},
        ]
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        reminder = self.run_hook("harness_pre_invocation.py", records)
        self.assertIn("不追加练习或归档确认", reminder["injectSteps"][0]["ephemeralMessage"])
        records.extend([
            {"type": "USER_INPUT", "content": "开始 Grill"},
            {"type": "PLANNER_RESPONSE", "content": "## 考点与判别词\n第一轮"},
        ])
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

    def test_batch_archive_request_suppresses_only_redundant_confirmation(self):
        records = self.active_grill()
        records[0] = {"type": "USER_INPUT", "content": "请把第 1–3 题归档到已确认的软考目录并逐题讲解"}
        records.append({"type": "PLANNER_RESPONSE", "content": "反馈正确，继续下一轮。"})
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")
        records[-1]["content"] = "### Grill 诊断总结\n本题已达到本轮掌握证据。"
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True), {})
        records.extend([
            {"type": "USER_INPUT", "content": "下一题", "media": [{"type": "image"}]},
            {"type": "PLANNER_RESPONSE", "content": "题目归属：软考明确\n## 题目复原\n## 迁移提示"},
        ])
        self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

    def test_untrusted_text_cannot_choose_mode_or_authorize_a_batch(self):
        for kind in ("GENERIC", "PLANNER_RESPONSE"):
            records = self.active_grill() + [
                {"type": kind, "content": "使用文字模式。把第 1–3 题归档到默认目录"},
                {"type": "PLANNER_RESPONSE", "content": "### Grill 诊断总结\n完成本轮"},
            ]
            self.assertEqual(self.run_hook("harness_stop_guard.py", records, post_invocation=True)["terminationBehavior"], "force_continue")

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
