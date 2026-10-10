# 版本化数据契约

所有对象 `schema_version: 1`。脚本使用 UTF-8 JSON、原子写入、稳定身份。文本证据偏移是 **Python Unicode 字符偏移**，不是 JS UTF-16 字节/码元偏移。

## 题包 pack.json（公开）

`id / version / title / scoring_notice / cases[]`。每大题 `id / title / stem / complete: true / max_score / source / figures[] / questions[]`。

- `source`: `kind` 为 original/recollection/adapted/authored/web-bank，`label / locator`；真题还需 `identity_verified: true / year / case_number / identity_evidence`。web-bank 是尚未核实年份、考试题号的网站材料，仅作普通练习，`require_true` 必须拒绝。
- `figures[]`: `file` 为源目录内相对路径、`caption / source_locator`。`prepare` 复制为本场 figures/ 文件，不暴露任意文件目录。
- `questions[]`: `id / title / prompt / complete: true / max_score`。大题分值等于全部小问之和。

## 私有 rubric.json

`pack_id / pack_version / version / basis`（published 或 inferred-training）、`answer_source: {reliable: true, locator, level}`、`training_policy: unit-weight-deduplicated-v1`、`points[]`。

采分点 `id / question_id / weight / criterion / conditions[] / equivalents[] / correct / dimension / source`；原始规则若允许扣分，另记录 `reference_deductions`，由 Agent 判定证据后在评阅中提交。把模糊大点拆成原子点；一个点给分0或全部权重，独立条件拆点，避免临场改权重。每小问点权重总和必须匹配分值。训练扣分在开卷前冻结。

## state.json / submission.json

运行器生成 `attempt_id / status / revision / pack_hash / rubric_hash / rubric_file / started_at / paused_seconds / answers` 等。小问答案包含 `markdown / scene / drawing_png / attachments[]`。scene 保存 Excalidraw elements、必要 appState、files；PNG 来自同一 scene 导出。附件存名称和本地 raster data URI。提交文件只写一次，恢复不覆盖；新场次身份不同。计时为服务端时间，离线时间另标记客户端申报。

## Agent evaluation.json

`attempt_id / submission_hash / rubric_hash / reviewer: current-agent / self_check`（逐项记录自检过程和结论），`decisions[] / extra_errors[] / recommendations[]`。

- decisions：每点一个 `point_id / status`（awarded/omitted/incorrect/pending）、`comment / evidence[]`，错误可用 `cause_id`，待核验加 `pending_reason`。
- 文本 evidence：`kind: text / start / end / quote`，范围严格对应已提交原文；图证据：`kind: diagram / element_id / description`，实际看PNG，核对节点/箭头；附件：`kind: attachment / index / description`。没有依据不写命中。
- 文本 evidence 可加 `focus: [{start, end, quote}]`，用绝对 Python Unicode 字符偏移定位本段证据内真正得分或错误的词句。新评阅须优先给精确片段，证据中的中性上下文不整段涂色；范围必须包含在外层 evidence 内，quote 必须精确相等。多处得分可给多个片段。
- extra_errors：`question_id / cause_id / point_id`（可省略）`/ comment / source / evidence`。同一因使用同一身份，已因该错丢分不再叠罚。
- warnings：可选数组，每项 `question_id / point_id`（可省略）`/ comment / source / evidence`。仅用于有依据的表述风险，evidence 必须是文本并可给 focus。该字段不接受 amount 等扣分字段，不改变参考分、训练分或错题统计。
- recommendations：`priority / topic / reason / prompt`，prompt 包含实际误解与待验证迁移条件。
- reference_checks：以计分小问 ID 为键，每项 `status / checked_point_ids[] / note`。status 为 `consistent` 或 `pending`；只允许全部计分小问、各自全部采分点恰好出现一次。note 记录本次依据、空号/条件/方案等实际核对结论及来源分歧的处理。未解决冲突不能写 consistent；pending 须对应 pending 参考答案和至少一个 pending 判定。已核实答案遇到不可读作答时，答案核对可为 consistent、作答判定仍为 pending。此记录随 evaluation 的 rubric_hash 绑定已核对版本。

`grade.json` 和 `reviews/` 保存每次结果与离线HTML，分数、分布、维度从点结果计算。待核验总分为 null；已核验分数可以局部展示。脚本不检查同义/因果语义。

报告根据判定生成颜色：awarded 的文本证据为绿色，incorrect、reference_errors 与 extra_errors 的文本证据为红色，warnings 为黄色；遗漏和待核验不自动着色。重叠处红色优先于黄色、黄色优先于绿色，悬停保留相关评语；右侧各条反馈仍展示自己的依据。公式按完整公式高亮。没有 focus 的历史证据按原证据范围展示，不臆造精确得分词。

## archive-receipt.json

`attempt_id / grade_hash / covered_points[] / files[]`。files 含实际绝对路径、SHA256；必须回读含本场身份的章级归档文件。covered_points 列出 omitted/incorrect 点以及实际额外扣分的 `extra:原因身份`。归档完成前状态不能清空。

## 正式试卷 exam（pack.json 的可选字段）

没有 `exam` 的包为单题、专题或全题练习，保持其原有分母；指定年度完整真题必须提供 `exam` 并使用 `prepare --paper-kind`。

```json
{
  "kind": "case-analysis",
  "instructions": "试题一必答，试题二至五任选两题。每题25分，满分75分。",
  "required_case_ids": ["case-1"],
  "choose_count": 2,
  "max_score": 75,
  "pass_score": 45,
  "rules_source": "实际核验的原卷或官方试题分析书及页码",
  "pass_source": "实际核验的该批次合格标准通知链接"
}
```

`kind` 为 `case-analysis` 或 `essay`。`choose_count` 是必答以外的选答数量，各合法选题组合的分数必须等于 `max_score`。可提供来源明确的 `duration_minutes` 作展示；是否限时仍由本场计时模式决定。网页说明中应写出原卷超选处理规则，实际界面只允许选择规定数量。

论文 `required_case_ids: []`、`choose_count: 1`，每候选论题只含一个75分小问，候选数量按原卷。另提供 `essay_limits`，如2018原卷核验后为 `{"abstract_min":0,"abstract_max":400,"body_min":2000,"body_max":3000}`。

`state.json / submission.json` 新增 `selected_case_ids`。开始前可以保存未选齐的草稿，开始、作答中及交卷时必须符合选题数量，提交后冻结。`answers` 保留所有候选题草稿；`evaluation.decisions`、错误扣分和报告只包含选中题目的采分点。

论文小问的 answer 新增 `essay: {abstract, body}`；其 `markdown` 必须精确等于 `"## 摘要\n\n" + abstract + "\n\n## 正文\n\n" + body`。文本证据仍使用合成后原文的 Python Unicode 字符偏移。离线导入必须同时携带选题和完整作答结构。

## 论文审题映射（私有 rubric.json）

论文评分表必须提供 `essay_requirements`，以每篇的小问 ID 为键、原卷论述要求数组为值。每项包含 `id / text / source / point_ids[]`；采分点必须属于该小问。报告按真实逐点结果展示已覆盖、部分覆盖、未覆盖或待核验，不能由关键词匹配代替语义判断。

## 完整参考答案（仅私有 rubric.json）

`reference_answers` 以小问 ID 为键，内容包含：

- `markdown`：完整应试参考答案。
- `origin`：`source`（据完整可靠来源整理）、`skill-generated`（依题意和可靠依据生成）或 `pending`（存在未核实事项）。
- `sources[]`：实际依据、书名页码或链接，集合必须等于本小问全部采分点 `source` 的集合。模拟项目假设写入正文。报告用此列表生成展示用 `source`，不采信另写的来源标签。
- `images[]`：可选，每图 `data` 为 PNG/JPEG/WebP data URI，另有 `caption`。
- 论文另有 `essay: {abstract, body}`，与上述 Markdown 格式一致，参考范文须符合该卷字数要求。

grade 要求每个计分小问有完整参考答案，拒绝 evaluation 携带 `reference_answers`。非 pending 答案中须包含每个采分点 `correct` 的原文片段；从已核实完整答案提取这些片段，不独立生成两份结论。必要条件和同义边界由 Agent 一起审查。来源只有笼统建议时由当前 Agent 补成完整答案，不能把采分点摘要冒充完整范文。`pending` 参考答案要求对应小问确有待核验采分点，核对记录也必须 pending，报告不输出确定总分。

旧场次和提交后生成的论文范文均通过现有 `revise-rubric` 加入新评分表，再更新 evaluation.rubric_hash、移除独立答案并完成本次 reference_checks。修订保留原表、原因和历史报告，不修改 submission.json。无完整答案、来源不一致、答案片段未绑定、漏核对或仍有冲突时，grade 在写报告前失败。语义审阅不能由这些字段检查替代。

这些内容只进入提交后的报告，不放进公开题包。新报告新增 `selected_case_ids / reference_answers / exam_outcome / weaknesses`；论文报告另有 `essay_review`。合格判定使用参考估分，主要失分统计忽略未选题及待核验权重。历史报告没有完整参考答案时提示补充评阅，不伪造内容。
