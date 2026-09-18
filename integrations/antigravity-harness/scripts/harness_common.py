import json
import os


MAX_TAIL_BYTES = 262144
MAX_RECORDS = 240
HARNESS_MARKER = "[soft-exam-harness:active]"

TEXT_RECORD_TYPES = {
    "USER_INPUT",
    "PLANNER_RESPONSE",
    "EPHEMERAL_MESSAGE",
}

STRONG_SOFT_EXAM_SIGNALS = (
    "软考",
    "软设",
    "软件设计师",
    "系统架构设计师",
    "soft-exam-question-tutor",
)

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


def recent_context(transcript_path):
    chunks = []
    for record in read_recent_records(transcript_path):
        if record.get("type") in TEXT_RECORD_TYPES:
            text = text_content(record.get("content"))
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def is_soft_exam_context(transcript_path):
    context = recent_context(transcript_path)
    if not context:
        return False
    return any(
        signal in context
        for signal in STRONG_SOFT_EXAM_SIGNALS + ACTIVE_FLOW_SIGNALS
    )


def last_planner_response(transcript_path):
    for record in reversed(read_recent_records(transcript_path)):
        if record.get("type") == "PLANNER_RESPONSE":
            return record
    return None
