# ruankao.skill

面向中文软考学习的 Agent Skill：读取一道题的截图或文本，复原题目、识别中级／高级、讲清解题依据，按作答状态开展可选 Grill，并在用户确认后归档到 Obsidian。

仓库发布可独立安装的 `soft-exam-question-tutor`。学习计划、论文调度和整段历史对话导入由工作区的其它流程负责。

## 本次更新：2026-09-16

本次更新已纳入 `main`，重点处理先弹卡后讲解、预告卡片后结束，以及中断后重复询问等流程问题。

- **前置执行契约**：在主 Skill 前部明确“先输出讲解，再按本题状态调用卡片”，避免关键时序要求藏在长文件末尾。
- **条件式 Grill**：已作答才默认询问是否练习；未作答、作答未知、快速讲或跳过时不主动 Grill；明确结束或换题时停止当前题。
- **本题状态与续接**：记录本题 ID、已输出讲解、最近卡片、实际用户答复、轮数和归档授权；新题不继承旧题完成状态或授权。
- **运行时适配**：新增 [runtime-interaction.md](skills/soft-exam-question-tutor/references/runtime-interaction.md)，说明 Antigravity 的调用示例、工具能力检查和失败后的恢复方式。
- **统一时序规则**：诊断引用只维护出题内容，执行顺序统一指向主 Skill；保留每题确认、原文保真、章级归档与写后回读。
- **使用说明**：补充 Antigravity 安装、初始化、旧安装升级、故障定位和[人工验收场景](docs/validation.md)。

这是工作流规则修订。已进行文件结构、引用和发布差异检查；尚未完成 Antigravity 的真实 UI 行为回归。模型仍可能忽略指令，Skill 也无法修复模型服务或客户端的流中断。

## 环境要求

- Agent 能加载 Skill 并读取本地文件；图片题需要视觉能力或完整 OCR 文本。
- 卡片交互需要当前会话实际提供结构化提问工具。Antigravity 优先使用 `ask_question`，具体字段以运行时 schema 为准。
- 讲题不要求写知识库；归档需要可访问的 Obsidian Vault 和用户授权。

## 安装与更新

### Antigravity：项目级安装

在 Vault 或项目根目录运行：

```bash
npx skills add https://github.com/Goodyzhang/ruankao.skill/tree/main/skills/soft-exam-question-tutor -a antigravity
```

这条命令明确使用 `main` 的单题 Skill。Skills CLI 的参数与源地址格式见[官方说明](https://github.com/vercel-labs/skills)。已有同名安装时先检查安装器提示，保留个人改动。

也可以手动安装：

```bash
git clone --branch main --single-branch https://github.com/Goodyzhang/ruankao.skill.git
mkdir -p .agents/skills
cp -R ruankao.skill/skills/soft-exam-question-tutor .agents/skills/
```

上面是首次安装示例。更新已有安装时，先备份同名目录，再复制整个 Skill 文件夹；只替换 `SKILL.md` 会漏掉新增引用文件。

Antigravity 项目级目录为 `.agents/skills/<skill-folder>/`，旧 `.agent/skills/` 仍向后兼容；全局目录与版本差异请以 [Antigravity 官方文档](https://antigravity.google/docs/skills) 为准。此处优先使用项目级安装。

### 其它 Agent

通过 Skills CLI 安装指定 Agent：

```bash
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -a claude-code
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -a codex
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -a kimi-code-cli
```

Agent 名称及安装位置以[安装器支持列表](https://github.com/vercel-labs/skills#supported-agents)为准。若需要本次 `main` 更新，使用上面的完整 `tree/main` 地址。使用其它安装器时应检查它选用的分支或 tag，不能把旧 tag 当作最新主分支内容。

安装后重新打开会话，让 Agent 重新发现 Skill。旧会话可要求其重读当前主文件与运行时引用，并按最近真实卡片结果续接。

### 已采用“权威目录＋发现桥接”的工作区

本仓库中的文件夹是完整独立 Skill。若你的 `.agents/skills/soft-exam-question-tutor/SKILL.md` 只是指向 `.claude/skills/` 的桥接，应继续在既定权威目录维护完整 SOP，桥接只负责指向它。不要同时维护两份可执行规则，也不要把公共独立包直接覆盖到桥接上。

已有 `AGENTS.md`、`CLAUDE.md` 或方法学说明重复定义 Grill 时序时，将操作规则收敛到主 Skill；工作区入口保留路由。恢复包应与当前权威版本一并同步。

## 开始使用

### 初始化示例

安装后可发送：

```text
请完整读取已安装的 soft-exam-question-tutor/SKILL.md。
我准备系统架构设计师高级考试。先输出题目讲解，再按本题作答状态处理 Grill。
卡片使用当前会话实际可用的结构化提问工具。
我明确结束或换题时停止当前流程；归档沿用本题已给出的明确授权。
暂时只确认就绪，等待我发送题目。
```

### 发题示例

- “为我讲一下这道题。我选了 C。”
- “我选了 C，请讲解后直接 Grill。”
- “这题还没做，先讲原理，不 Grill。”
- “快速讲一下，只给答案和必要理由。”
- “结束本题，不归档。”

提供完整题干、选项、图表与必要限定词。截图显示你的选项时可以据此判断作答状态；没有证据时不会猜测。材料含多题时先选择或按题号逐题处理。

## 交互流程

```text
完整性检查 → 题源与分级 → 可见讲解
  ├─ 已作答 → Grill 门控 → 内容选择题 → 反馈 → 下一题或收尾
  ├─ 未作答／快速讲／跳过 → 可归档题进入归档确认
  └─ 明确结束／换题 → 结束当前题

本题归档授权 → 写入指定目标 → 回读验证 → 完成
```

### 讲解

默认呈现题目复原、考点与判别词、解题链、答案与选项分析、迁移提示。先让用户看到这些内容，再发需要用户作答的卡片。工具的 `toolSummary` 或归档报告不能代替讲解。

### Grill

- 门控卡决定开始、跳过或结束；练习卡只给内容选项，不要求填写理由。
- 练习题提供一个正确项和可信干扰项；点选前不标答案，不在干扰项上写“错误”“遗漏”等提示。
- 每次答复后给出对应反馈；最多 3 轮，已有原题辨析与关键条件迁移的掌握证据即可收尾。
- 相近真题来自用户提供或经授权可访问的资料；没有可靠题源时明确称为变式题。

### 停止与恢复

用户点选后的实际工具返回就是答复，无需再发“继续”。恢复时先核对最近卡片和结果，避免重复门控。文件写入结果不确定时先回读查重，再补齐本题尚未完成的内容。

工具未暴露或调用失败时，Agent 应说明停在哪个阶段、缺少什么能力；用户明确选择文本模式后才切换。不要把默认选中当成已提交，也不要在尚无卡片时声称“等待你点击”。

## Obsidian 归档

首次归档前，在工作区指令中声明 Vault 相对根目录，或按现有目录确认。例如：

```text
本 Vault 的软考根目录为“个人资料/笔记/软考”。
当前级别为系统架构设计师高级。
知识点写入该级别的“知识点”目录，题目写入“错题本”目录。
请只在本题得到明确归档授权后写入；沿用已有文件名和标题。
```

默认章级结构：

```text
<软考根目录>/
├── 软件设计师-中级/
└── 系统架构设计师-高级/
    ├── 知识点/NN-章名.md
    └── 错题本/NN-章名-错题.md
```

根目录未明确且无法唯一识别时，先确认再写入。每题有独立授权；本题已明确同意归档时不重复询问。知识点、错题目标之外的看板或论文资料需要对应授权。

写入契约保留完整题目、正确答案、简析、用户选择、其它选项分析与精确 Wiki-link。已有题先查重；写后回读，不迁移旧目录，不批量预建空文件。

## 排查与验证

| 现象 | 检查重点 |
|---|---|
| 先弹卡、没有讲解 | 是否完整加载当前主文件；可见正文是否实际发出 |
| 说“下面开始”却没有卡片 | 是否有实际工具调用，还是普通文本响应已经结束 |
| 卡片提交后不继续 | 是否已有工具返回，恢复阶段是否停留在旧卡片 |
| 工具不存在或字段错误 | 当前会话工具清单及 schema，不靠平台名称推断 |
| stream interrupted | 运行时中断；保留最近成功结果，区分服务问题与流程遗漏 |
| 更新后仍沿用旧规则 | 重新加载会话，检查同名安装、桥接目标和恢复包版本 |

[人工验收场景](docs/validation.md)使用自编题，覆盖讲解、门控、反馈、结束、恢复和归档。判断依据是实际输出与工具事件，不能用“Skill 包含某个关键词”代替行为验证。

## 仓库结构

```text
skills/soft-exam-question-tutor/
├── SKILL.md
├── agents/openai.yaml
└── references/
    ├── runtime-interaction.md
    ├── chapter-routing.md
    ├── grill-diagnostic-contract.md
    ├── grill-question-design.md
    └── knowledge-base-contract.md
docs/validation.md
```

## 内容与版权边界

本仓库发布讲题与归档工作流，不包含教材 PDF、考试题库、答案语料、用户截图或个人笔记。相近真题应来自用户提供或经授权可访问的资料。

## 致谢

感谢开源项目[软考达人](https://github.com/ruankaodaren/ruankao)对中文软考学习社区的贡献。本仓库独立实现 Agent Skill，不分发该项目的代码、题库、解析或素材。

## License

[MIT](LICENSE) © 2026 Goodyzhang
