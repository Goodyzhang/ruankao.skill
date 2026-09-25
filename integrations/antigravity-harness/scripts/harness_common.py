import json
import os
import re


MAX_TAIL_BYTES = 262144
MAX_RECORDS = 240
HARNESS_MARKER = "[soft-exam-harness:active]"

STRONG_SOFT_EXAM_SIGNALS = (
    "软考",
    "软设",
    "软件设计师",
    "系统架构设计师",
    "soft-exam-question-tutor",
)

QUESTION_CUES = ("这道题", "这题", "本题", "题目", "软考题", "真题")
QUESTION_ACTIONS = ("讲", "解析", "分析", "怎么做", "我选", "选项")
CONTINUATION_CUES = ("grill", "归档", "继续当前题", "我选", "下一题", "再来一题")
RUNTIME_CUES = ("skill", "hook", "harness", "ask_question", "工具", "客户端")
DIAGNOSTIC_ACTIONS = ("检查", "排查", "修复", "调试", "弹不", "问题")

ACTIVE_FLOW_SIGNALS = (
    HARNESS_MARKER,
    "## 题目复原",
    "## 考点与判别词",
    "## 解题链",
    "## 迁移提示",
)


def read_recent_records(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    try:
        with open(transcript_path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - MAX_TAIL_BYTES))
            raw = handle.read()
    except OSError:
        return []

    records = []
    for line in raw.decode("utf-8", errors="ignore").splitlines()[-MAX_RECORDS:]:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def text_content(value):
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def is_soft_exam_context(transcript_path):
    records = read_recent_records(transcript_path)
    latest_user_index = next(
        (index for index in range(len(records) - 1, -1, -1)
         if records[index].get("type") == "USER_INPUT"),
        None,
    )
    if latest_user_index is None:
        return False
    latest_user = text_content(records[latest_user_index].get("content"))
    if not latest_user:
        return False

    lowered = latest_user.lower()
    if (
        any(cue in lowered for cue in RUNTIME_CUES)
        and any(action in lowered for action in DIAGNOSTIC_ACTIONS)
    ):
        return False
    if (
        any(signal in lowered for signal in STRONG_SOFT_EXAM_SIGNALS)
        and any(cue in latest_user for cue in QUESTION_CUES)
        and any(action in latest_user for action in QUESTION_ACTIONS)
    ):
        return True

    last_planner_index = next(
        (index for index in range(len(records) - 1, -1, -1)
         if records[index].get("type") == "PLANNER_RESPONSE"),
        None,
    )
    if last_planner_index is None:
        return False
    planner_text = text_content(records[last_planner_index].get("content"))
    if not any(signal in planner_text for signal in ACTIVE_FLOW_SIGNALS):
        return False
    if (
        last_planner_index > latest_user_index
        and "## 题目复原" in planner_text
        and re.search(
            r"(?m)^题目归属：(?:软考明确|软考知识域相关但题源未确认)\s*$",
            planner_text,
        )
    ):
        return True
    return (
        any(cue in lowered for cue in CONTINUATION_CUES)
        or lowered.strip() in {"继续", "结束", "a", "b", "c", "d", "1", "2", "3"}
        or bool(re.match(r"^a\d+\s*:", lowered.strip()))
    )


def last_planner_response(transcript_path):
    for record in reversed(read_recent_records(transcript_path)):
        if record.get("type") == "PLANNER_RESPONSE":
            return record
    return None
