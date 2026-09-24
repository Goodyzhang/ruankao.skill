# Antigravity 超长上下文 Harness

这是 soft-exam-question-tutor 的可选 Antigravity 增强模块。它不会安装到 Codex、Claude Code / Claudian、Trae 或 Kimi。

模块在已确认的软考单题会话中做三件事：

1. 每次模型调用前注入短暂的续接提醒，降低长上下文中遗漏卡片调用的概率。
2. 对全部工具调用执行白名单检查，仅允许 ask_question、view_file、replace_file_content、grep_search。
3. 在完全空闲的 model_stop 阶段，发现完整讲题缺少 ask_question 时让 Agent 继续补发门控卡。

图片附件或泛化的“这题”“讲解”等字样不会单独激活 Harness。它依赖明确软考信号或已经进入的单题流程，避免干扰普通图片、代码和文档任务。

## 安装

先用 Toolkit 的初始化脚本安装 Skill 与资料，再在发布包根目录执行：

~~~powershell
py -3 integrations/antigravity-harness/install_harness.py --workspace "D:\YourVault" --dry-run
py -3 integrations/antigravity-harness/install_harness.py --workspace "D:\YourVault"
~~~

macOS / Linux：

~~~sh
python3 integrations/antigravity-harness/install_harness.py --workspace "../YourVault" --dry-run
python3 integrations/antigravity-harness/install_harness.py --workspace "../YourVault"
~~~

安装器会合并三个名为 soft-exam- 开头的 Hook，不改动其它 Hook。若目标中已存在不同版本的同名 Harness 文件或 Hook，默认保留；确认需要更新时使用 --force。
安装时会按当前系统实际可用的 Python 命令写入 Hook；手动复制 `hooks.json` 时需自行确认其中的 Python 命令能在 Antigravity 中运行。

## 验收

在 Antigravity 中打开目标工作区后：

1. 用已作答的软考单题触发讲解，确认讲题正文后出现 ask_question 门控卡。
2. 在该会话中尝试白名单外工具，确认 Antigravity 显示 deny。
3. 上传一张非软考图片或执行普通文档任务，确认 Harness 不注入提醒，也不阻断工具。

Hook 的字段与事件基于 Google Antigravity Hooks 文档。实际卡片工具是否暴露仍取决于当前客户端与会话能力。

若回复正文出现 `call:default_api:ask_question{...}` 之类文本，说明卡片没有实际调用。检查当前会话是否提供 `ask_question`，以及所选自定义 Agent 是否启用了该工具；工具缺失时按主 Skill 的运行时契约报告停在哪一步。Stop Hook 不会阻止这类明确的能力缺失报告结束。
