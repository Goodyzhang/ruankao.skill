# 保存与续接契约

## 位置与身份

以下位置均相对已确认的科目根目录，不写死 Vault 路径。完整案例优先 `真题库/案例分析/NN-章名/`，论文题源进入题库，全文进入 `论文/`；已有匹配题目原位增补。原图、答案图和可编辑稿分开保存于题库附件目录。

案例身份采用稳定 ASCII ID，例如 `site-section-case`，不使用未经核实的年份。网站题号与本地小问分别记录；相似度只能给模型提供线索，不能直接合并。题源、背景、数字、图示及小问编号的比对结果写入证据。个人作答、人工备注和真实错次不由本 Skill生成。

`真题库/_structured/soft-exam-bank-ingest/ID/` 保存不可变的 `record-vN.json` 和当前回执 `current.json`。`真题库/_ingest/soft-exam-bank-ingest/批次.json` 是台账；来源草稿、页面解析及各阶段文件放在同名批次目录。台账不能替代原文。

## 结构资料

`scripts/bank.py` 使用 Python 3.9+ 标准库。案例校验与导出依赖同家族 `soft-exam-lab/scripts/lab.py`；安装应保留两个目录的同级关系。

每条记录使用 `schema_version: 1`，包含 `id`、正整数 `version`、`kind: case|essay`、教材章名 `chapter`、网站小节身份 `section_id`、`source_items`、相对路径 `markdown_file`、模型写好的 `markdown`、`complete`、`verification` 和 `assets`。

- `verification.state` 为 `pending|verified`，证据存于 `evidence`，缺口存于 `unresolved`。只有完整、存在核验证据且无实质缺口的记录才可 verified。训练评分口径已明确、等价答案边界已解决的材料可核验为练习资料；不能因此宣称官方答案或真题身份已确认。
- `assets` 每项含 `file`、`role: original|answer|editable`、实际文件的 `sha256`。公开题图只能引用 original。答案图和解析不进入公开包。
- 案例包含 `pack` 和 `rubric`，字段按实验室 [data-contract.md](../../soft-exam-lab/references/data-contract.md)。一个记录对应一整道案例，全部小问使用稳定身份。`source.kind: web-bank` 表示未经核实年份题号的网站材料；可作普通练习，不能响应真题要求。
- 论文包含 `essay.mode: exam-simulation`、`requirements`、`profile`、`abstract`、`body`、`coverage`。coverage 逐项覆盖 requirements。未规定字数时检查约 300 字摘要、约 2,300 字正文训练目标；脚本不裁切作文。论文首版不导出到实验室。
- 题面、源解析、核验答案、逐点要点及教材链接都由模型写作并检查；脚本只校验结构和文件，不从关键词生成答案。

## 使用与恢复

```bash
python3 "{SKILL_ROOT}/soft-exam-bank-ingest/scripts/bank.py" --root "{科目绝对路径}" start --batch batch-id --scope scope.json
python3 "{SKILL_ROOT}/soft-exam-bank-ingest/scripts/bank.py" --root "{科目绝对路径}" step --batch batch-id --number 133 --stage captured --evidence evidence.json
python3 "{SKILL_ROOT}/soft-exam-bank-ingest/scripts/bank.py" --root "{科目绝对路径}" save --batch batch-id --record record.json
python3 "{SKILL_ROOT}/soft-exam-bank-ingest/scripts/bank.py" --root "{科目绝对路径}" status --batch batch-id
python3 "{SKILL_ROOT}/soft-exam-bank-ingest/scripts/bank.py" --root "{科目绝对路径}" export-lab --id case-id --destination "{导出绝对路径}"
```

scope 包含 `authorization`、`section_id`、正整数 `start/end`，另外记录考试、网站章节、小节、目标和当前页面。已存在批次的 scope 必须一致。范围补齐需要 `step --expanded`，证据含 `same_case_id` 与同一个 `section_id`；模型先确认属于同一案例，跨章扩展禁止。

每一步先落来源/创作文件，再将路径和实际观察写入 evidence；阶段依次为 captured、analysis、drafted、reviewed。缺口写 pending，选择题写 skipped。只有 save 完成文件回读才能写 saved。已完成案例需要增补时，同批 step 的 evidence 提供 `update_id` 等于既有案例 ID，先检查原回执，再记录更新阶段；无须强制新建批次。页面导航失败时保留当前号与下一步，不连点下一题。恢复时 status 回读所有带回执的记录（包括 pending）及图像哈希；回到未完成阶段，不重做已完成题目。

文件逐个采用原子写入，整个多文件事务不是数据库事务。中断后按版本文件、正文管理区、回执逐项恢复；未写回执不宣称完成。重复写同版本须内容相同，不产生新档。内容变更增加版本并保留旧版。新增版本不能丢原网站小问和稳定小问身份。

脚本只更新正文中的 `soft-exam-bank-ingest:ID` 管理区，保留区外人工内容。同版本重复保存不改台账。verified 记录检查普通 Markdown 的本地文件链接；Wiki 链接和标题定位由模型实际回读确认。区内被人工改过会拒绝静默覆盖：模型先读差异，把原题、批注和作答保留下来，写入新版本，再用 `save --reconcile-hash` 提供刚读到的管理区正文 SHA256。哈希仅是防止并发覆盖的凭据，不替代语义合并。旧笔记没有管理区时先人工增量规划，只追加新增内容；不要把已有题干重复抄进整个新管理区。

## 实验室交接

export-lab 输出 `public/pack.json` 及其 original 图，以及独立 `private/rubric.json`。公开服务根只能是 public，不能直接暴露导出根、题库根或结构资料根。`--require-true` 会拒绝 web-bank。pending、缺图、缺解析、原图哈希变化和实质争议未解决记录都不能导出。交接后实验室仍按其显式调用及提交契约运行，题库整理不会替用户作答。
