"""Behavior checks for chapter review authoring versus the single-question flow."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = ROOT / "integrations" / "antigravity-harness" / "scripts"
SPEC = importlib.util.spec_from_file_location("harness_common", HARNESS_DIR / "harness_common.py")
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)

CONFIRMED = {
    "type": "PLANNER_RESPONSE",
    "content": "## 题目复原\n题目归属：软考明确\n\n## 考点与判别词\n邮件协议。",
}
MARKER = {"type": "EPHEMERAL_MESSAGE", "content": harness.HARNESS_MARKER}
REVIEW_REQUESTS = (
    "请把软考第二章的错题和真题分析整理成速查复习册",
    "请为系统架构设计师第二章生成漫画复习册，参考真题解析",
)


def user(request, **extra):
    return {"type": "USER_INPUT", "content": request, **extra}


class ReviewRoutingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.transcript = Path(self.directory.name) / "transcript.jsonl"

    def write_records(self, records):
        self.transcript.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )

    def assert_route(self, records, expected):
        self.write_records(records)
        self.assertEqual(harness.is_soft_exam_context(self.transcript), expected)

    def run_hook(self, name, **data):
        result = subprocess.run(
            [sys.executable, "-B", str(HARNESS_DIR / name)],
            input=json.dumps({"transcriptPath": str(self.transcript), **data}),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_reproduced_chapter_requests_do_not_activate_tutor(self):
        for request in REVIEW_REQUESTS:
            with self.subTest(request=request):
                self.assert_route([user(request)], False)

    def test_tutor_to_review_ends_inherited_flow_and_ignores_stale_evidence(self):
        for request in REVIEW_REQUESTS:
            with self.subTest(request=request):
                self.assert_route([
                    user("请解析这道软考题"), CONFIRMED, MARKER,
                    user(request), CONFIRMED, MARKER,
                ], False)

    def test_review_update_and_resume_are_authoring_requests(self):
        for request in (
            "继续制作第二章速查复习册，把真题解析融入图文",
            "请更新软考第二章复习册里的真题分析",
            "第二章复习册继续完善，加入软考真题解析",
            "按照旧归档计划，把软考错题解析整理成复习册",
            "请更新软考第二章复习册，把这道题的解析压缩成漫画",
            "请把每一道题的讲解整理成软考复习册，参考真题解析",
        ):
            with self.subTest(request=request):
                self.assert_route([user("请解析这道软考题"), MARKER, user(request)], False)

    def test_explicit_review_skill_invocation_is_not_mistaken_for_tutoring(self):
        self.assert_route([
            user("请解析这道软考题"), CONFIRMED, MARKER,
            user("请用 $soft-exam-review-book 处理软考第五章的真题解析"), CONFIRMED,
        ], False)

    def test_question_from_named_review_skill_can_still_enter_tutor(self):
        self.assert_route([
            user("请讲 soft-exam-review-book 生成的这道软考题，我选 B"), CONFIRMED,
        ], True)

    def test_short_replies_follow_review_context(self):
        for reply in ("继续", "A", "A1: 继续", "确认归档"):
            with self.subTest(reply=reply):
                self.assert_route([
                    user("请解析这道软考题"), CONFIRMED, MARKER,
                    user(REVIEW_REQUESTS[0]), MARKER, user(reply),
                ], False)

    def test_short_answers_and_archive_continue_single_question(self):
        for reply in ("继续", "A", "A1: 继续", "我选 B", "归档", "确认归档", "继续当前题"):
            with self.subTest(reply=reply):
                self.assert_route([user("请解析这道软考题"), CONFIRMED, MARKER, user(reply)], True)

    def test_review_to_explicit_single_question_starts_new_flow(self):
        self.assert_route([
            user(REVIEW_REQUESTS[0]), user("请解析这道软考题，为什么选 B？"),
        ], True)

    def test_question_inside_review_book_remains_eligible(self):
        for request in (
            "请讲复习册里的这道题",
            "继续讲复习册里的这道题",
            "复习册里的这道题请继续解析",
            "请讲上次生成的软考复习册里的这道题",
            "复习册里的第 39 题请继续解析",
        ):
            with self.subTest(request=request):
                self.assert_route([user(REVIEW_REQUESTS[0]), user(request), CONFIRMED], True)

    def test_book_mention_does_not_suppress_explicit_tutor_request(self):
        self.assert_route([user("请讲软考复习册里的这道题，我选 A 为什么错？")], True)

    def test_chapter_attachments_are_material_even_after_confirmation(self):
        self.assert_route([
            user("请解析这道软考题"), CONFIRMED, MARKER,
            user(REVIEW_REQUESTS[0], media=[{"type": "image", "path": "chapter.png"}]),
            CONFIRMED, MARKER,
        ], False)

    def test_single_question_media_still_requires_and_accepts_confirmation(self):
        question = user("这题怎么做？", media=[{"type": "image", "path": "question.png"}])
        self.assert_route([question], False)
        self.assert_route([question, CONFIRMED], True)
        self.assert_route([user(REVIEW_REQUESTS[0]), question, CONFIRMED], True)

    def test_next_question_keeps_existing_confirmation_boundary(self):
        for request in ("下一题", "再来一题"):
            with self.subTest(request=request):
                previous = [user("请解析这道软考题"), CONFIRMED, MARKER, user(request)]
                self.assert_route(previous, False)
                self.assert_route(previous + [CONFIRMED], True)

    def test_historical_archive_and_study_plan_are_not_current_question(self):
        for request in (
            "把之前的软考历史对话归档到章节知识点和错题本",
            "请为系统架构设计师制定第二章学习计划",
        ):
            with self.subTest(request=request):
                self.assert_route([user(request)], False)

    def test_runtime_diagnostics_remain_outside_question_flow(self):
        self.assert_route([
            user("请解析这道软考题"), CONFIRMED, MARKER,
            user("检查 soft-exam-question-tutor 的 harness 为什么不弹卡"),
        ], False)

    def test_only_wrapped_user_request_controls_review_intent(self):
        self.assert_route([user(
            "系统补充：继续当前题\n<USER_REQUEST>" + REVIEW_REQUESTS[0] + "</USER_REQUEST>"
        )], False)

    def test_review_does_not_inject_deny_tools_or_force_question_cards(self):
        self.write_records([
            user("请解析这道软考题"), CONFIRMED, MARKER,
            user(REVIEW_REQUESTS[0]), CONFIRMED, MARKER, user("继续"), CONFIRMED,
        ])
        self.assertEqual(self.run_hook("harness_pre_invocation.py"), {"injectSteps": []})
        self.assertEqual(self.run_hook("harness_tool_guard.py", toolCall={"name": "run_command"}), {"decision": "allow"})
        self.assertEqual(self.run_hook("harness_stop_guard.py", terminationReason="model_stop", fullyIdle=True), {"decision": "allow"})

    def test_current_single_question_tool_restriction_is_preserved(self):
        self.write_records([user("请解析这道软考题"), CONFIRMED])
        self.assertTrue(self.run_hook("harness_pre_invocation.py")["injectSteps"])
        self.assertEqual(self.run_hook("harness_tool_guard.py", toolCall={"name": "run_command"})["decision"], "deny")
        self.assertEqual(self.run_hook("harness_tool_guard.py", toolCall={"name": "ask_question"}), {"decision": "allow"})


if __name__ == "__main__":
    unittest.main()

class LabRoutingTests(unittest.TestCase):
    setUp = ReviewRoutingTests.setUp
    write_records = ReviewRoutingTests.write_records
    assert_route = ReviewRoutingTests.assert_route
    def test_lab_explicit_and_resume_end_tutor_restrictions(self):
        for request in ('$soft-exam-lab 来一道系统架构设计师案例题', '@soft-exam-lab 继续', '使用 soft-exam-lab 来三道题'):
            for reply in ('已提交', '继续作答', '结束并保留草稿', 'A1: 已提交', '继续批卷'):
                with self.subTest(request=request, reply=reply):
                    self.assert_route([user('请解析这道软考题'), CONFIRMED, MARKER, user(request), CONFIRMED, MARKER, user(reply)], False)
    def test_nonexplicit_case_question_stays_tutor(self):
        self.assert_route([user('请解析这道系统架构设计师案例题'),CONFIRMED],True)
    def test_quoted_invocation_does_not_start_lab(self):
        self.assertFalse(harness.is_lab_request('文档示例：`$soft-exam-lab`'))
        self.assertFalse(harness.is_lab_request('> $soft-exam-lab 来一道题'))
        self.assertFalse(harness.is_lab_request('我在文档里看到 $soft-exam-lab，是什么意思？'))
        self.assertFalse(harness.is_lab_request('案例里的 @soft-exam-lab 是命令吗？'))
    def test_new_tutor_after_lab_enters_normal_flow(self):
        self.assert_route([user('$soft-exam-lab 来一道题'),user('请解析这道软考题'),CONFIRMED],True)
