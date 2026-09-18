import json
import sys

from harness_common import is_soft_exam_context


ALLOWED_TOOLS = {
    "ask_question",
    "view_file",
    "replace_file_content",
    "grep_search",
}

if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def allow():
    print(json.dumps({"decision": "allow"}))


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        allow()
        return

    transcript_path = data.get("transcriptPath", "")
    if not is_soft_exam_context(transcript_path):
        allow()
        return

    tool_call = data.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    if tool_name in ALLOWED_TOOLS:
        allow()
        return

    response = {
        "decision": "deny",
        "reason": (
            "当前已确认处于软考单题流程。仅允许 ask_question、view_file、"
            "replace_file_content、grep_search；请按 Skill 的输入、讲解、"
            "卡片与归档契约继续。"
        ),
    }
    print(json.dumps(response, ensure_ascii=False))

if __name__ == "__main__":
    main()
