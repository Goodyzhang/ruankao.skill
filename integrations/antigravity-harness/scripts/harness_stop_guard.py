import json
import sys

from harness_common import is_soft_exam_context, last_planner_response, text_content

# Ensure clean UTF-8 I/O on Windows
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

    if data.get("terminationReason") != "model_stop":
        allow()
        return

    if not data.get("fullyIdle", False):
        allow()
        return

    transcript_path = data.get("transcriptPath", "")
    if not is_soft_exam_context(transcript_path):
        allow()
        return

    last_planner = last_planner_response(transcript_path)
    if not last_planner:
        allow()
        return

    content = text_content(last_planner.get("content"))
    tool_calls = last_planner.get("tool_calls") or []
    tool_names = [
        call.get("name")
        for call in tool_calls
        if isinstance(call, dict) and call.get("name")
    ]

    has_complete_explanation = (
        "## 迁移提示" in content
        or "## 考点与判别词" in content
        or ("题目复原" in content and "解题链" in content)
    )

    if has_complete_explanation and "ask_question" not in tool_names:
        response = {
            "decision": "continue",
            "reason": (
                "检测到软考单题讲解已完成，但本轮未调用 ask_question。"
                "请按当前作答状态立即调用 Grill 门控卡或归档确认卡，再等待用户选择。"
            ),
        }
        print(json.dumps(response, ensure_ascii=False))
        return

    allow()

if __name__ == "__main__":
    main()
