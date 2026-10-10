import json
import sys

from harness_common import (
    HARNESS_MARKER, current_flow_records, explanation_only_requested,
    interaction_mode, is_soft_exam_context, previous_suspended_question, read_recent_records,
)

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

    records = current_flow_records(read_recent_records(data.get("transcriptPath", "")))
    if explanation_only_requested(records):
        interaction = "用户明确只讲解：完成讲解后结束，不追加练习或归档确认。"
    elif interaction_mode(records) == "text":
        interaction = (
            "用户已明确选择本题文字模式：在正文给一道完整内容选择题并等待实际答复；"
            "不要为同一道文字题补卡。模式选择不授权写入，归档仍核对本题或明确批次授权。"
        )
    else:
        interaction = (
            "需要门控、练习或归档确认时，同轮实际调用 ask_question；"
            "先发送讲解或反馈，正文不复写卡片内容或调用格式。"
            "已有适用授权时直接按契约写入回读，不重复询问；缺工具时报告阶段并等用户选择模式。"
        )
    message = (
        f"{HARNESS_MARKER}\n"
        "当前已确认处于软考单题流程。按执行与续接契约继续：\n"
        + interaction + "\n"
        "本流程仅允许 ask_question、view_file、replace_file_content、grep_search。"
    )
    suspended = previous_suspended_question(data.get("transcriptPath", ""))
    if suspended:
        message += (
            f"\n前一题 [{suspended}] 的后续状态需要核对。先核对 question_id 与 per_question；"
            "只有本次确为新题且上一题仍未完成时，在新题正文第一行提醒一次："
            "⚠️ 上一题 [题目标识] 仍待 [实际未完成步骤]，已保留进度。"
            "已有授权不能说成待确认；不因提醒自动归档、不继承旧题授权，不另发旧题卡片。"
        )
    print(
        json.dumps(
            {"injectSteps": [{"ephemeralMessage": message}]},
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()
