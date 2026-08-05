# ruankao.skill

面向中文软考学习场景的 Agent Skill：接收题目截图、图片或文本，完成题目复原、软考识别、软件设计师（中级）/系统架构设计师（高级）分流、推理讲解、选项分析，并在用户明确同意后归档到 Obsidian 知识库。

仓库内容和使用说明以简体中文为主。Skill 内部标识为 `soft-exam-question-tutor`。

## 主要能力

- 多模态模型直接识图；非多模态模型尝试读取已有 OCR，失败时明确请求题目文本或建议切换模型。
- 区分“软考题源明确”“软考知识域相关但题源未确认”和“非软考或证据不足”。
- 根据题型、来源与考查深度判断软件设计师（中级）、系统架构设计师（高级）或两者共有。
- 按“考点定位 → 逻辑链 → 答案 → 逐项分析/错误诊断 → 易错点 → 变式题”讲解。
- 只有用户确认后才写入 Obsidian；归档时保留原题、正确选项、简析、用户选项、其它选项分析和知识点链接。

## 环境要求

- 支持 [Agent Skills](https://agentskills.io/) 的 Claude Code、Codex、Kimi CLI 或其它 Agent。
- 处理截图时建议使用支持视觉输入的模型；纯文本模型可以处理用户粘贴的题目或 OCR 文本。
- 只有归档时才需要对 Obsidian Vault 的写权限。

## 安装

### Skills CLI（推荐）

在 Obsidian Vault 或项目根目录执行：

```powershell
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor
```

指定 Agent：

```powershell
# Claudian / Claude Code：项目级安装到当前 Vault
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -a claude-code

# Codex：用户级安装
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -g -a codex

# Kimi Code CLI：用户级安装
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -g -a kimi-code-cli
```

### GitHub CLI

```powershell
# Claude Code 项目级
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent claude-code --scope project

# Codex 用户级
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent codex --scope user

# Kimi CLI 用户级
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent kimi-cli --scope user

# 固定安装 v0.1.0
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent codex --scope user --pin v0.1.0
```

### 手动安装

下载 Release 中的 `soft-exam-question-tutor-v0.1.0.zip`，解压后将整个 `soft-exam-question-tutor` 目录复制到对应位置：

| Agent | 项目级目录 | 用户级目录 |
|---|---|---|
| Claude Code / Claudian | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.codex/skills/` |
| Kimi CLI | `.agents/skills/` | `~/.agents/skills/` |

安装完成后重新加载 Agent 或重新打开会话。

## 自动触发

Skill 的描述已覆盖“发题目截图并要求讲解”“为什么选”“怎么做”“我哪里错了”等表达。支持语义发现的 Agent 可以自动触发，无需点名 Skill。

如果所用 Agent 的自动发现不稳定，可在 Vault 根目录的 `AGENTS.md` 或 `CLAUDE.md` 中加入：

> 收到题目图片、截图或题目文本且用户要求讲题时，必须读取并执行 `soft-exam-question-tutor`；用户确认前不得写入知识库。

## 使用方法

直接发送图片或题目文本，例如：

- “为我讲一下这道题。”
- “为什么选 B？其它选项错在哪里？”
- “这是系统架构设计师的题吗？我哪里做错了？”

讲解完成后，Agent 会询问是否归档。需要归档时可回复：

> 是，我选了 C，请整理进知识库。

未作答时回复“是，未作答”即可。拒绝或不回复时不会创建、修改知识库文件。

## Obsidian 知识库

默认根目录为：

```text
个人资料/笔记/软考/
├── 软件设计师-中级/
└── 系统架构设计师-高级/
    ├── 知识点/
    └── 错题本/
```

可以在 `AGENTS.md`、`CLAUDE.md` 或其它工作区指令中声明自己的知识库根目录；显式配置优先于默认值。Skill 使用 Vault 相对 Wiki-link，不写入设备绝对路径。

## 内容与版权边界

本仓库只发布讲题与归档工作流，不包含教材 PDF、考试题库、答案语料、用户截图或个人笔记。请使用合法取得的学习资料，并在转载题目时遵守相应版权与考试规定。

## 致谢

向开源项目[软考达人](https://github.com/ruankaodaren/ruankao)致敬。该项目长期维护软考题库、知识库和学习工具，为中文软考学习社区提供了持续价值。

`ruankao.skill` 是独立实现的 Agent Skill，不包含、复制或分发软考达人的代码、题库、解析或素材；上述链接仅用于致谢与推荐。

## License

[MIT](LICENSE) © 2026 Goodyzhang
