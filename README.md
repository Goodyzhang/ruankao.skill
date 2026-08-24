# ruankao.skill

面向中文软考学习场景的 Agent Skill：接收一道题的截图、图片或文本，完成题目复原、软考识别、中级/高级分级、推理讲解、可选的错因诊断式 Grill，并在用户明确同意后归档到 Obsidian 知识库。

Skill 内部标识为 `soft-exam-question-tutor`，仓库内容和使用说明以简体中文为主。

## 主要能力

- 对图片或文本执行输入 Gate：题干、选项、图表或限定词缺失时请求补充，不猜题。
- 区分“软考题源明确”“软考知识域相关但题源未确认”和“非软考或证据不足”。
- 根据题型、来源与考查深度判断软件设计师（中级）、系统架构设计师（高级）或两者共有。
- 按“题干判别词 → 解题链 → 答案与选项分析 → 迁移提示”讲解。
- 用户已作答时，依据实际理由进行诊断式 Grill；新题未作答时不强行追问。
- 只有用户确认后才写入 Obsidian；归档时保留原题、正确选项、简析、用户选项、其它选项分析和知识点链接。

## 环境要求

- 支持 [Agent Skills](https://agentskills.io/) 的 Claude Code、Codex、Kimi CLI 或其它 Agent。
- 处理截图时建议使用支持视觉输入的模型；纯文本模型可以处理用户粘贴的题目或 OCR 文本。
- 只有归档时才需要对 Obsidian Vault 的写权限。

## 安装

### Skills CLI

在 Obsidian Vault 或项目根目录执行：

```powershell
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor
```

指定 Agent：

```powershell
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -a claude-code
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -g -a codex
npx skills add Goodyzhang/ruankao.skill --skill soft-exam-question-tutor -g -a kimi-code-cli
```

### GitHub CLI（最新已发布 tag）

```powershell
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent claude-code --scope project
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent codex --scope user
gh skill install Goodyzhang/ruankao.skill soft-exam-question-tutor --agent kimi-cli --scope user
```

`gh skill install` 会优先解析仓库的最新 tag，再解析默认分支。当前已有 `v0.1.0` tag，因此上述未固定命令会安装该已发布版本。要在下一个 Release 前使用当前默认分支的工作流，请按下方“手动安装”克隆仓库，或使用已验证的提交 SHA 配合 `--pin`。

### 手动安装

克隆或下载仓库后，将 `skills/soft-exam-question-tutor/` 整个目录复制到对应位置：

| Agent | 项目级目录 | 用户级目录 |
|---|---|---|
| Claude Code / Claudian | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.codex/skills/` |
| Kimi CLI | `.agents/skills/` | `~/.agents/skills/` |

安装完成后重新加载 Agent 或重新打开会话。

## 使用方法

直接发送图片或题目文本，例如：

- “为我讲一下这道题。”
- “我选了 C，为什么错？请 Grill 一下。”
- “这是系统架构设计师的题吗？我哪里做错了？”

处理链为：

```text
输入 Gate → 题源与分级 → 讲题 → 按作答状态决定可选 Grill → 用户确认后归档
```

多题材料会先编号并逐题处理。用户没有说明是否作答、明确未作答，或要求快速讲时，Skill 不会强行启动 Grill；每题归档前都需要自己的明确确认。

## Obsidian 知识库

以下是常见的 Vault 相对目录示例：

```text
个人资料/笔记/软考/
├── 软件设计师-中级/
└── 系统架构设计师-高级/
    ├── 知识点/
    └── 错题本/
```

首次归档前，请在 `AGENTS.md`、`CLAUDE.md` 或其它工作区指令中声明 Vault 相对根目录，或在 Agent 询问时确认根目录和目标文件。Skill 不会静默创建发布者的默认目录，也不写入设备绝对路径。

## 内容与版权边界

本仓库只发布讲题与归档工作流，不包含教材 PDF、考试题库、答案语料、用户截图或个人笔记。请使用合法取得的学习资料，并在转载题目时遵守相应版权与考试规定。

## 致谢

向开源项目 [软考达人](https://github.com/ruankaodaren/ruankao) 致敬。该项目长期维护软考题库、知识库和学习工具，为中文软考学习社区提供了持续价值。

`ruankao.skill` 是独立实现的 Agent Skill，不包含、复制或分发软考达人的代码、题库、解析或素材；上述链接仅用于致谢与推荐。

## License

[MIT](LICENSE) © 2026 Goodyzhang
