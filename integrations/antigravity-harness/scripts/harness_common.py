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


def mode_choice(text):
    """Recognize an explicit mode choice, not a mention in a question/document."""
    text = re.sub(r"^A\d+:\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\((?:Recommended|推荐)\)|\[(?:Recommended|推荐)\]", "", text, flags=re.I).strip()
    match = re.fullmatch(
        r"(?:请|本题)?(?:改用|使用|切换到|切回|恢复|继续用|选择|同意|用)?"
        r"(文字|文本|卡片|原生卡片)模式(?:继续本题|继续|讲题|练习|Grill)?[。！!]?",
        text, re.I,
    )
    if match:
        return "text" if match[1] in {"文字", "文本"} else "card"
    return None


def interaction_mode(records):
    """Only USER_INPUT or a real mode-selection card response changes mode."""
    mode = "card"
    pending_mode_card = False
    for record in records:
        if record.get("type") == "USER_INPUT":
            choice = mode_choice(user_request(record))
            if choice:
                mode = choice
            pending_mode_card = False
        elif record.get("type") == "PLANNER_RESPONSE":
            pending_mode_card = False
            for call in record.get("tool_calls") or []:
                if call.get("name") != "ask_question":
                    continue
                args = call.get("args", call.get("arguments", {}))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        continue
                questions = args.get("questions", []) if isinstance(args, dict) else []
                if isinstance(questions, list) and len(questions) == 1:
                    question = questions[0]
                    if isinstance(question, dict) and re.search(
                        r"本题.*交互方式|选择.*(?:文字|文本|卡片)模式", str(question.get("question", "")),
                    ):
                        pending_mode_card = True
        elif record.get("type") == "GENERIC" and pending_mode_card:
            if record.get("status", "DONE") == "DONE":
                answer = re.search(r"(?m)^A\d+:\s*([^\n]+)", text_content(record.get("content")))
                choice = mode_choice(answer[1]) if answer else None
                if choice:
                    mode = choice
            pending_mode_card = False
    return mode


def explanation_only_requested(records):
    for record in reversed(records):
        if record.get("type") != "USER_INPUT":
            continue
        request = user_request(record)
        if re.search(r"(?:开始|进入).*Grill|(?:把|将)本题归档", request, re.I):
            return False
        if re.match(r"^(?:请|本题)?(?:只|仅)(?:讲解|解析|给解析)", request):
            return not re.search(r"(?:然后|随后|并|再).*(?:Grill|归档|练习)", request, re.I)
    return False


def explicit_archive_request(records):
    """Suppress redundant archive cards; this never grants filesystem access."""
    return any(re.match(
        r"^(?:请|请你|帮我|为我)?(?:把|将)(?:本题|第\s*[0-9一二三四五六七八九十]+"
        r"(?:\s*[-–—～~至到、,，]\s*[0-9一二三四五六七八九十]+)*\s*题)\s*归档(?:到|[，,。\s]|$)",
        user_request(record),
    ) for record in records if record.get("type") == "USER_INPUT")


def is_continuation(request):
    lowered = request.lower()
    return (
        any(cue in lowered for cue in CONTINUATION_CUES)
        or lowered in {"继续", "结束", "a", "b", "c", "d", "1", "2", "3", "?", "？"}
        or bool(re.match(r"^a\d+\s*:", lowered))
        or mode_choice(request) is not None
    )


def is_review_book_request(request):
    """Recognize authoring intent without excluding questions inside a review book."""
    if "复习册" not in request and "soft-exam-review-book" not in request:
        return False
    single_question = r"(?:这道题|这题|本题|这道软考题|一道题|一道软考题|第\s*\d+\s*题)"
    explanation = r"(?:讲解|讲|解析|分析|解答|诊断|怎么做|为什么选)"
    book_question = r"(?:复习册|soft-exam-review-book)[^。！？\n，,]{0,20}" + single_question
    # "Explain this question in the book" is tutoring; "update the book using
    # this question's explanation" still asks for an authored artifact.
    if re.search(explanation + r"[^。！？\n，,]{0,30}" + book_question, request) or re.search(
        book_question + r"[，,\s]*(?:请|继续|再|帮我|给我|为我|详细|仔细)*" + explanation,
        request,
    ):
        return False
    authoring = r"(?:制作|生成|创建|编写|编排|整理|重写|更新|修改|完善|扩写|续写|继续|完成|做|写)"
    nearby = r"[^。！？\n]{0,80}"
    return "soft-exam-review-book" in request or bool(re.search(authoring + nearby + "复习册", request) or re.search(
        "复习册" + nearby + authoring, request
    ))


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
        # Chapter authoring ends inherited single-question restrictions.
        if is_review_book_request(request):
            return []
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
