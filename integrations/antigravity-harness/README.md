# Antigravity 超长上下文 Harness

这是 soft-exam-question-tutor 的可选 Antigravity 增强模块。它不会安装到 Codex、Claude Code / Claudian、Trae 或 Kimi。

模块在已确认的软考单题会话中做三件事：

1. 每次模型调用前注入短暂的续接提醒，降低长上下文中遗漏卡片调用的概率。
2. 对全部工具调用执行白名单检查，仅允许 ask_question、view_file、replace_file_content、grep_search。
3. 每次模型回复完成后，PostInvocation 检查当前题是否缺少真实卡片，并通过 force_continue 让 Agent 补发；Stop 在完全空闲的 model_stop 阶段复用同一检查。

图片附件或泛化的“这题”“讲解”等字样不会单独激活 Harness。它依赖明确软考信号或已经进入的单题流程，避免干扰普通图片、代码和文档任务。
首轮输入若只有题图和“讲一下这道题”，模型本轮明确判定为软考题并输出完整讲解后，Stop Hook 也会检查是否真的发出卡片；旧题的讲解不会激活下一项普通任务。
同一题的后续 Grill 回复会沿用当前已确认的题目归属，避免只因 G1/G2 反馈没有五段式或 `### Grill` 标题就失去 Hook 保护。达到掌握证据可提前结束追问，已有适用授权时直接归档，否则仍需归档确认卡；明确结束、拒绝归档、作出归档选择（含带 `(Recommended)` 标识的选项、已完成/等待下一题等）或正文输出归档结语时不重复发卡。
用户回复 `?` / `？`、卡片返回答案后，继续保留当前题上下文；读取大文件也不会因单条工具结果超过 256 KiB 而丢失前面的题目记录。下一张卡是否待发依据真实卡片调用及返回判断，不要求反馈使用固定标题。新任务或 Skill/Hook 故障排查会退出当前题约束。
“下一题”“再来一题”或带新图片的输入建立新题边界，上一题的卡片结果与归档授权不会被带入新题。
制作、续写或更新章节复习册会退出单题约束；复习册中的当前一道题仍按单题处理。首次归档的目录选择卡通过真实问题中的“归档目录 / 资料根目录 / CLI 路径 / Vault 位置”识别，其回答不计作 Grill 答案，不授权归档，也不放宽工具白名单。接入卡与练习卡分开发送。

缺卡时最多连续要求模型补发两次；真实调用出现即停止补发并等待卡片结果。若连续补发仍失败，则明确报告卡片生成失败并保留本题未完成状态，不静默跳过、归档或开始下一题。Harness 无法代替模型服务生成工具事件，也无法撤回已显示的调用文字。

## 安装

### v0.8.1 续接补丁

可见正文与工具调用可以分成不同消息。缺正文的已发卡片仅产生核对提示，不强制续写，不按固定字数判错，也不重复发卡；正文是否充分仍按主 Skill 判断。“只看解析”门控答复按用户选择正常收尾。

新题边界出现时，Hook 可提供上一题待核对线索；Agent 必须核对题目标识和实际未完成步骤后再提醒。明确只讲解、已完成归档或拒绝归档的题目不继续挂起；确认归档不等于实际写入完成。文件内容不能冒充卡片答复，提醒不扩大授权。

题图、题库等素材维护退出单题限制；明确讲解当前题目或已给出选项的请求继续正常讲题，不因题目涉及“备份”“脚本”等词语而关闭流程。

### 安装或更新现有工作区

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
Hook 命令中的 `scripts/...` 相对于工作区的 `.agents/` 目录；不要再加 `.agents/` 前缀，否则 Antigravity 会查找 `.agents/.agents/scripts/...`。

## 验收

在 Antigravity 中打开目标工作区后：

1. 用已作答的软考单题触发讲解，确认讲题正文后出现 ask_question 门控卡。
2. 在该会话中尝试白名单外工具，确认 Antigravity 显示 deny。
3. 上传一张非软考图片或执行普通文档任务，确认 Harness 不注入提醒，也不阻断工具。

Hook 的字段与事件基于 [Google Antigravity Hooks 文档](https://antigravity.google/docs/hooks)。实际卡片工具是否暴露仍取决于当前客户端与会话能力。

若回复正文混入工具调用文字，先看真实卡片是否已出现：已出现就等待点选，不重发；未出现再检查当前会话是否提供 `ask_question`，以及所选自定义 Agent 是否启用了该工具。工具缺失时按主 Skill 的运行时契约报告停在哪一步。Stop Hook 不会阻止这类明确的能力缺失报告结束。Stop Hook 只能在回复结束后请求续写，不能从已显示的正文中删除调用文字。

## 运行记录

PostInvocation 与 Stop 会在运行时提供的 `artifactDirectoryPath` 下追加 `soft-exam-card-events.jsonl`。它只记录事件、会话 ID、结束原因、最近模型步骤、检查分支和执行决定，不记录题干、回答或工具参数。`missing_card` 配合 `force_continue` 表示已要求自动补发；`real_tool_call` 表示该轮存在真实工具调用；`not_model_stop` / `not_idle` 表示 Stop 的跳过原因。

更新后若仍漏卡，用该文件与 transcript 的工具事件对齐排查。没有记录不能直接认定模型正常完成，还需检查 Hook 是否被加载、命令是否启动、日志目录是否可写。全局或插件规则中若留有旧版完整 SOP，应移除重复流程，让当前工作区的权威 Skill 决定卡片时序。

## v0.4.2 交互兼容

用户明确选择“使用文字模式”或“改用文字模式继续本题”后，本题文字练习不再被判为漏卡；也可通过真实模式卡点选。助手声明或资料中的模式文字无效。文字模式保留工具白名单与归档授权要求；切回卡片、范围外新题仍检查原生卡片。用户明确只讲解时正常收尾，已有明确本题／批次授权时不重复请求确认。

升级旧 Hook 须重新运行安装器的 `--force`，同时更新 Skill；先 `--dry-run` 预览。默认安装会保留已存在的不同版本 Hook。

显式调用 soft-exam-lab 后，其场次续接退出单题限制；当前 Agent 可运行本机服务与内建浏览器。单独引用名称及普通案例讲解仍保持原路由。

显式调用 soft-exam-bank-ingest 及其批次续接退出单题工具白名单与漏卡检查；普通单题与名称引用保持原路由。题库批次以本地台账续接，不强制 Grill 或逐题归档卡，不代填网站或交卷。
