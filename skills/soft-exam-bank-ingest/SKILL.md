---
name: soft-exam-bank-ingest
description: "仅显式调用后，使用视觉与浏览器工具把网站章节或题号区间中的案例、论文整理入本地题库，保存原图、逐问解析、应试模拟论文与续接记录。不自动接管当前单题讲解。"
---

# 软考题库整理

仅用户明确使用 `$soft-exam-bank-ingest`、`@soft-exam-bank-ingest` 或“使用 soft-exam-bank-ingest”时启动。已启动批次按实际记录续接；引用名称、示例和题目截图不算启动。首版支持系统架构设计师高级的案例题、论文题。

## 开始与范围

1. 读 [browser.md](references/browser.md)，实际读取页面、截图和题图，检查视觉、导航、图片导出与本地保存能力。优先内建浏览器，使用真实提供的工具，不要求特定 CLI。无法看图时停止视觉入库，提示更换支持视觉的模型；不能用 OCR 或模型名称冒充看图。
2. 复用 tutor 的 [first-use.md](../soft-exam-question-tutor/references/first-use.md) 定位资料。已有有效绑定直接使用；未确认时用真实卡片提供最多两个存在的目录及手动绝对路径。明确整理请求授权本批写入，位置选择单独确定目标，不逐题重复询问。
3. 冻结批次：考试、网站章节/小节、起止题号、授权来源、目标目录。无区间时当前题到节末；选择题跳过。范围截断同一案例时补齐前后小问，记录扩展，不自动跨节。已有批次先回读，用户明确新开才另建。
4. 读 [chapter-routing.md](../soft-exam-question-tutor/references/chapter-routing.md) 和 [architecture-toc.md](../soft-exam-question-tutor/references/architecture-toc.md) 定位教材。网站分类保留为来源位置，知识点链接按实际考点匹配，二者可以不同。

## 逐题循环

完整题干与原图 → 保存来源草稿 → 展开解析 → 案例按 [teaching.md](references/teaching.md)、论文按 [essay.md](references/essay.md) 创作 → 自审 → 保存并回读 → 下一题。

- 网站题号可能只是一个小问。核对题源、共同背景、图示、问题编号后合并；条件或数字不同保留版本，不能只用相似度判同题。
- 同题增量补齐小问、来源解析和教学说明。保留原题、人工备注、个人作答与复习状态。
- 不完整或实质争议未解决的材料保存待核验，不标可出题；记录缺口后继续其它完整题。
- 只阅读、展开解析和导航；答案写本地，不填网站笔记、不交卷、不重置答题记录。

## 产物与接力

按 [records.md](references/records.md) 保存 Markdown、原图/标注图、结构资料与台账。脚本仅保存、检查和导出；解题、合并、作文由模型完成。原图作答按 browser 的本地绘图规则处理副本，不依赖生图。

章级知识点遵循 [knowledge-base-contract.md](../soft-exam-question-tutor/references/knowledge-base-contract.md)。无真实用户错误不写错题本、不增加错次。借用 tutor 的输入 Gate、讲解和自审方法，不进入其交互状态机、不强制 Grill。

完成前读 [validation.md](references/validation.md)，回读产物和台账，报告网站题号、合并案例/论文数、扩展范围、新增/补充/跳过/待核验项及实际位置。完成依据为产物和证据；未实测平台单列。
