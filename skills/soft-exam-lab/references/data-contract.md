# 版本化数据契约

所有对象 `schema_version: 1`。脚本使用 UTF-8 JSON、原子写入、稳定身份。文本证据偏移是 **Python Unicode 字符偏移**，不是 JS UTF-16 字节/码元偏移。

## 题包 pack.json（公开）

`id / version / title / scoring_notice / cases[]`。每大题 `id / title / stem / complete: true / max_score / source / figures[] / questions[]`。

- `source`: `kind` 为 original/recollection/adapted/authored，`label / locator`；真题还需 `identity_verified: true / year / case_number / identity_evidence`。
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
- extra_errors：`question_id / cause_id / point_id`（可省略）`/ comment / source / evidence`。同一因使用同一身份，已因该错丢分不再叠罚。
- recommendations：`priority / topic / reason / prompt`，prompt 包含实际误解与待验证迁移条件。

`grade.json` 和 `reviews/` 保存每次结果与离线HTML，分数、分布、维度从点结果计算。待核验总分为 null；已核验分数可以局部展示。脚本不检查同义/因果语义。

## archive-receipt.json

`attempt_id / grade_hash / covered_points[] / files[]`。files 含实际绝对路径、SHA256；必须回读含本场身份的章级归档文件。covered_points 列出 omitted/incorrect 点以及实际额外扣分的 `extra:原因身份`。归档完成前状态不能清空。
