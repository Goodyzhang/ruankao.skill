# 软考题解流程强制挂起规则（Antigravity 运行时）

本规则只约束已确认进入 soft-exam-question-tutor 的单题流程。图片附件、泛化的“这题”或“讲解”字样本身不足以启动 Harness。

## 卡片时序

1. 用户已作答时，五段式讲解完成后同轮调用 ask_question，展示 Grill 门控卡。
2. Grill 反馈后需要继续练习时，同轮调用下一张选择题卡。每张练习卡包含一个正确项和至少两个可信干扰项。
3. 新题未作答、跳过 Grill 或 Grill 收尾后，需要归档确认时调用 ask_question。用户确认前不得写入。

## 工具边界

已确认的单题流程只允许 ask_question、view_file、replace_file_content 和 grep_search。没有本地真题依据时，明确标为变式题；不得把生成题称为真题。

## Harness 联动

1. PreInvocation Hook 在已确认流程的每次模型调用前注入瞬时提醒，并写入活动标记以抵抗长上下文注意力衰减。
2. PreToolUse Hook 监听全部工具调用，对白名单外工具返回 deny；未确认的会话不受影响。
3. Stop Hook 只在 model_stop 且 fullyIdle 为 true 时检查本轮完整讲题。发现讲题结束但缺少 ask_question 时，返回 continue 让 Agent 补发门控卡。

Stop Hook 负责拦截讲题后裸退；Grill 与归档阶段的具体续接仍以主 Skill 的执行与续接契约为准。

当前会话未暴露结构化提问工具时，报告阻塞阶段并等待用户恢复工具或明确选择文本模式；不得把工具调用格式写进正文冒充卡片，也不反复强制续写。
