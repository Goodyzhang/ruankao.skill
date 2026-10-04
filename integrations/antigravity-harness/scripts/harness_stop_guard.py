import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

from harness_common import (
    current_flow_records, explanation_only_requested, explicit_archive_request,
    interaction_mode, is_soft_exam_context, read_recent_records,
    text_content, user_request,
)


RECOVERY_MARKER = "[soft-exam-card-recovery]"
BLOCKED_MARKER = "[soft-exam-card-blocked]"
TERMINAL_CHOICES = (
    "确认归档",
    "直接归档",
    "不归档",
    "归档完毕",
    "已归档",
    "归档完成",
    "全流程已归档",
    "结束",
    "换题",
    "已完成",
    "完成",
    "等待下一题",
    "等待上传",
    "结束本次学习",
    "结束本题",
    "退出",
)


def is_terminal_choice(text):
    if not text:
        return False
    cleaned = re.sub(
        r"^(?:A\d+:\s*)?(?:\((?:recommended|推荐)\)|\[(?:recommended|推荐)\]|[0-9]+[.\s、]|[a-zA-Z][.\s、])\s*",
        "",
        text,
        flags=re.I,
    ).strip()
    return any(keyword in cleaned for keyword in TERMINAL_CHOICES)


def is_environment_card(call):
    """Use the real question, not its answers/options, to separate setup from Grill."""
    if call.get("name") != "ask_question":
        return False
    args = call.get("args", call.get("arguments", {}))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return False
    if not isinstance(args, dict):
        return False
    questions = args.get("questions", [])
    if isinstance(questions, dict):
        questions = [questions]
    if not isinstance(questions, list) or not questions:
        return False
    # Mixed question batches retain ordinary card checks; setup must be separate.
    return all(isinstance(question, dict) and re.search(
        r"归档目录|资料根目录|CLI\s*路径|Vault\s*(?:位置|目录|路径)",
        str(question.get("question", "")), re.I,
    ) for question in questions)


def card_check(data):
    transcript = data.get("transcriptPath", "")
    if not is_soft_exam_context(transcript):
        return "outside_exam_context", "", None
    records = current_flow_records(read_recent_records(transcript))
    planner_index = next(
        (i for i in range(len(records) - 1, -1, -1)
         if records[i].get("type") == "PLANNER_RESPONSE"), None,
    )
    if planner_index is None:
        return "no_planner_record", "", None
    planner = records[planner_index]
    step = planner.get("step_index")
    content = text_content(planner.get("content"))
    if planner.get("status", "DONE") != "DONE":
        return "planner_not_done", "", step
    calls = planner.get("tool_calls") or []
    if calls:
        # A real call owns the next step, including a card awaiting its answer.
        return "real_tool_call", "", step
    if "当前会话未暴露结构化提问工具" in content:
        return "tool_unavailable", "", step
    if interaction_mode(records) == "text":
        return "confirmed_text_mode", "", step
    if explanation_only_requested(records):
        return "explanation_only", "", step

    latest_user = next((r for r in reversed(records) if r.get("type") == "USER_INPUT"), {})
    request = user_request(latest_user)
    if is_terminal_choice(request) or re.search(r"(?:把|将)本题归档", request):
        return "user_finished", "", step

    # Actual card answers survive wording/heading changes in the next feedback.
    latest_answer = None
    card_index = next((i for i in range(planner_index - 1, -1, -1) if any(
        call.get("name") == "ask_question" for call in records[i].get("tool_calls") or []
    )), None)
    if card_index is not None:
        result = next((r for r in records[card_index + 1:planner_index] if r.get("type") == "GENERIC"), {})
        if result.get("status", "DONE") == "DONE":
            answer = re.search(r"(?m)^A\d+:\s*([^\n]+)", text_content(result.get("content")))
            if answer:
                latest_answer = answer.group(1).strip()
        if latest_answer is None:
            return "card_pending_or_failed", "", step
    if card_index is not None and any(
        is_environment_card(call) for call in records[card_index].get("tool_calls") or []
    ):
        # Choosing a directory neither answers a Grill round nor authorizes filing.
        # Explicit explanation/wrap-up checks below still apply if the agent emits them.
        latest_answer = None
    if latest_answer and is_terminal_choice(latest_answer):
        return "archive_or_end_answered", "", step
    if re.search(r"(?:流程已(?:圆满)?结束|已(?:圆满)?归档完成|全流程已归档完毕|已为您重置题目上下文)", content):
        return "archive_or_end_announced", "", step

    # Count only consecutive repairs since a user message or actual card call.
    retry_messages = []
    for record in reversed(records):
        if record.get("type") == "USER_INPUT" or any(
            call.get("name") == "ask_question" for call in record.get("tool_calls") or []
        ):
            break
        if record.get("type") in {"EPHEMERAL_MESSAGE", "SYSTEM_MESSAGE"}:
            retry_messages.append(text_content(record.get("content")))
    if any(BLOCKED_MARKER in message for message in retry_messages):
        return "recovery_report_requested", "", step
    if any(
        RECOVERY_MARKER in text_content(record.get("content"))
        for record in records[planner_index + 1:]
    ):
        return "recovery_already_requested", "", step

    leaked = "call:default_api:ask_question" in content
    explanation = (
        "## 迁移提示" in content or "## 考点与判别词" in content
        or ("题目复原" in content and "解题链" in content)
    )
    wrap_up = "Grill" in content and ("诊断总结" in content or "诊断收官" in content)
    if explicit_archive_request(records) and (wrap_up or (explanation and latest_answer is None)):
        return "archive_already_requested", "", step
    attempts = sum(RECOVERY_MARKER in message for message in retry_messages)
    if not (leaked or explanation or wrap_up or latest_answer or attempts):
        return "no_card_due", "", step
    if attempts >= 2:
        return "recovery_exhausted", (
            BLOCKED_MARKER + "\n原生卡片补发连续两次未形成工具事件。"
            "停止重试，明确告诉用户本题停在卡片生成失败，保留未完成状态；"
            "不要宣称已完成，不归档，不开始下一题。"
        ), step
    purpose = "归档确认卡" if wrap_up else "本轮原定的门控、练习或归档确认卡"
    return "missing_card", (
        RECOVERY_MARKER + "\n本轮需要卡片，但没有真实 ask_question 工具事件。"
        f"正文已发送，不重复讲解、题干、选项或调用格式；现在只实际调用原生 {purpose}，"
        "然后等待真实返回。正文中的调用文字不算调用；不要开始下一题或擅自归档。"
    ), step


def emit(data, event, check, response, step=None):
    # Per-conversation diagnostics contain event metadata, never question text
    # or tool arguments. They distinguish skipped checks from missing execution.
    directory = data.get("artifactDirectoryPath")
    if directory:
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "conversationId": data.get("conversationId"),
            "terminationReason": data.get("terminationReason"),
            "fullyIdle": data.get("fullyIdle"),
            "plannerStep": step,
            "check": check,
            "action": response.get("terminationBehavior", response.get("decision", "allow")),
        }
        try:
            with (Path(directory) / "soft-exam-card-events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as error:
            print(f"soft-exam card event log unavailable: {error}", file=sys.stderr)
    print(json.dumps(response, ensure_ascii=False))


def main():
    if sys.platform == "win32":
        for stream in (sys.stdin, sys.stdout):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
    post_invocation = "--post-invocation" in sys.argv
    event = "PostInvocation" if post_invocation else "Stop"
    default = {} if post_invocation else {"decision": "allow"}
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        emit({}, event, "invalid_input", default)
        return
    if not post_invocation:
        if data.get("terminationReason") != "model_stop":
            emit(data, event, "not_model_stop", default)
            return
        if not data.get("fullyIdle", False):
            emit(data, event, "not_idle", default)
            return
    check, reason, step = card_check(data)
    if not reason:
        response = default
    elif post_invocation:
        response = {
            "injectSteps": [{"ephemeralMessage": reason}],
            "terminationBehavior": "force_continue",
        }
    else:
        response = {"decision": "continue", "reason": reason}
    emit(data, event, check, response, step)


if __name__ == "__main__":
    main()
