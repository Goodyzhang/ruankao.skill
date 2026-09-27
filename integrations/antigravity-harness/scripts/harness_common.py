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
CONTINUATION_CUES = ("grill", "归档", "继续当前题", "我选")
RUNTIME_CUES = ("skill", "hook", "harness", "ask_question", "工具", "客户端")
DIAGNOSTIC_ACTIONS = ("检查", "排查", "修复", "调试", "弹不", "问题")

def read_recent_records(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    try:
        with open(transcript_path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            chunks = []
            newline_count = 0
            # A single view_file result can exceed one chunk. Retain complete
            # recent events instead of losing the question before that result.
            while position > 0 and newline_count <= MAX_RECORDS:
                count = min(position, MAX_TAIL_BYTES)
                position -= count
                handle.seek(position)
                chunk = handle.read(count)
                chunks.append(chunk)
                newline_count += chunk.count(b"\n")
            raw = b"".join(reversed(chunks))
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


def user_request(record):
    content = text_content(record.get("content"))
    wrapped = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, re.S)
    return (wrapped.group(1) if wrapped else content).strip()


def is_continuation(request):
    lowered = request.lower()
    return (
        any(cue in lowered for cue in CONTINUATION_CUES)
        or lowered in {"继续", "结束", "a", "b", "c", "d", "1", "2", "3", "?", "？"}
        or bool(re.match(r"^a\d+\s*:", lowered))
    )


def current_flow_records(records):
    """Keep the current question across short replies, but stop at a new task."""
    latest_user_index = next(
        (index for index in range(len(records) - 1, -1, -1)
         if records[index].get("type") == "USER_INPUT"),
        None,
    )
    if latest_user_index is None:
        return []
    start = latest_user_index
    for index in range(latest_user_index, -1, -1):
        record = records[index]
        if record.get("type") != "USER_INPUT":
            continue
        start = index
        request = user_request(record).lower()
        if any(cue in request for cue in RUNTIME_CUES) and any(
            action in request for action in DIAGNOSTIC_ACTIONS
        ):
            return []
        if record.get("media") or "下一题" in request or "再来一题" in request:
            break
        if not is_continuation(request):
            break
    return records[start:]


def is_soft_exam_context(transcript_path):
    for record in current_flow_records(read_recent_records(transcript_path)):
        if record.get("type") == "USER_INPUT":
            request = user_request(record).lower()
            if (
                any(signal in request for signal in STRONG_SOFT_EXAM_SIGNALS)
                and any(cue in request for cue in QUESTION_CUES)
                and any(action in request for action in QUESTION_ACTIONS)
            ):
                return True
        if record.get("type") == "PLANNER_RESPONSE":
            content = text_content(record.get("content"))
            if "## 题目复原" in content and re.search(
                r"(?m)^题目归属：(?:软考明确|软考知识域相关但题源未确认)\s*$", content
            ):
                return True
        if record.get("type") == "EPHEMERAL_MESSAGE" and HARNESS_MARKER in text_content(record.get("content")):
            return True
    return False


def last_planner_response(transcript_path):
    for record in reversed(read_recent_records(transcript_path)):
        if record.get("type") == "PLANNER_RESPONSE":
            return record
    return None
