---
name: soft-exam-architect-organizer
description: "把用户明确提交的完整系统架构设计师高级历史对话导入当前 20 章知识点、错题本和可用论文素材。用于历史对话整理；不处理当前单题，也不根据残缺截图补写题目。"
---

# 系统架构设计师高级历史对话导入

本 Skill 只处理用户明确提交、要求整理或归档的完整高级备考对话。当前会话中的单题交给 `soft-exam-question-tutor`；学习计划、复习和论文训练交给 `soft-exam-architect-prep`。

## 知识库位置

默认根目录为 Vault 内的 `个人资料/笔记/软考/`；用户指定其它根目录时使用其配置。

## 前置条件

1. 用户明确要求整理或归档，并提供可追溯的完整对话。
2. 涉及题目的内容必须有完整题干、选项或子问题、可靠答案依据；图片未转录时标为待补，不得根据上下文补全。
3. 逐条依据 [chapter-routing.md](../soft-exam-question-tutor/references/chapter-routing.md) 判定题源、级别和章节；非软考、证据不足或明确属于中级的内容跳过并报告，不写入高级知识库。
4. 阅读 [architecture-toc.md](../soft-exam-question-tutor/references/architecture-toc.md) 和 [knowledge-base-contract.md](../soft-exam-question-tutor/references/knowledge-base-contract.md)，按教程 20 章定位。

## 导入规则

- 通用知识点写入 `知识点/NN-章名.md` 的精确小节；已有内容优先合并。
- 完整错题写入 `错题本/NN-章名-错题.md`，公共字段顺序遵循知识库契约；可在其后追加合法错因标签和 D1/D7/D21。
- 论文可复用素材可追加到 `02_论文项目底稿.md` 的对应提纲，但必须来自用户提供的事实或已验证材料。
- `笔记.md` 与 `03_错题与复盘模板.md` 只作为历史查重和格式参考，不向其中双写新内容。

## 写入与报告

写入前先查重，写入后回读目标段落，报告：来源、导入的知识点/错题/论文素材数量、涉及章节、跳过原因和实际更新文件。未经明确整理请求时只输出草案，不修改文件。
