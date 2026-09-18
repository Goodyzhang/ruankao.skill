import json
import sys

from harness_common import HARNESS_MARKER, is_soft_exam_context

if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        print(json.dumps({"injectSteps": []}))
        return

    if not is_soft_exam_context(data.get("transcriptPath", "")):
        print(json.dumps({"injectSteps": []}))
        return

    message = (
        f"{HARNESS_MARKER}\n"
        "当前已确认处于软考单题流程。按执行与续接契约继续：\n"
        "1. 讲题五段式完成后，同轮实际调用 ask_question 挂起；不要以纯文本结束。\n"
        "2. Grill 练习和归档确认同样通过 ask_question 挂起。\n"
        "3. 本流程仅允许 ask_question、view_file、replace_file_content、grep_search。"
    )
    print(
        json.dumps(
            {"injectSteps": [{"ephemeralMessage": message}]},
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()
