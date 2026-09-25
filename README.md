# 软考学习 Toolkit

面向 **Antigravity + Obsidian** 的软考学习套组，也支持 Codex、Claude Code / Claudian 和 Trae。包含 5 个 Skill、两级知识资料、空错题本及保留已有笔记的初始化脚本。

[下载 v0.3.6](https://github.com/Goodyzhang/ruankao.skill/releases/tag/v0.3.6) · [资料处理说明](docs/data-preparation.md) · [交互验收](docs/validation.md)

## 五个 Skill

| Skill | 用途 |
|---|---|
| `soft-exam-question-tutor` | 单题截图或文本、解析、可选 Grill 与确认后归档 |
| `soft-exam-prep` | 中级计划、知识学习、练习和进度 |
| `soft-exam-organizer` | 用户明确提交的完整中级历史对话整理 |
| `soft-exam-architect-prep` | 高级计划、案例、论文和 D1/D7/D21 复习 |
| `soft-exam-architect-organizer` | 用户明确提交的完整高级历史对话整理 |

单题统一交给 tutor；其余 Skill 引用 tutor 的章节与归档契约。安装时保留五个同级目录及各自的 `references/`，不能只复制入口文件。

## 快速开始：完整初始化

需要 Python 3.9 或更新版本。脚本仅使用标准库，无需安装 Python 依赖。

### 1. 获取发布包

从 [Release](https://github.com/Goodyzhang/ruankao.skill/releases/tag/v0.3.6) 下载 `ruankao-toolkit-v0.3.6.zip` 并解压，也可以获取相同版本源码：

```sh
git clone --branch v0.3.6 --depth 1 https://github.com/Goodyzhang/ruankao.skill.git
cd ruankao.skill
```

以下命令在解压目录或仓库根目录中运行。`../RuankaoVault` 是目标 Vault，可替换为自己的路径；目标应与发布包目录分开。

### 2. 安装到 Antigravity 工作区

macOS / Linux：

```sh
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform antigravity --dry-run
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform antigravity
```

Windows PowerShell：

```powershell
py -3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform antigravity --dry-run
py -3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform antigravity
```

脚本将五个完整 Skill 放入 `.agents/skills/`，将资料放入 `个人资料/笔记/软考/`。已有文件默认保留，并列出跳过的文件；重复运行不会清空错题和进度。

在 **Obsidian 中打开目标 Vault**，再在 **Antigravity 中打开同一个目录并新建会话**。发现目录与加载行为见 [Antigravity 官方说明](https://antigravity.google/docs/skills)。

### 可选：超长上下文 Harness

Antigravity 用户可以安装 [可选 Harness](integrations/antigravity-harness/README.md)。它仅在已确认的软考单题会话中提醒卡片续接、约束工具并拦截讲题后裸退；普通图片、文档和其它 Agent 不受影响。

### 3. 首次使用

```text
当前工作区就是我的 Obsidian Vault。
软考知识库位于“个人资料/笔记/软考”。
我准备系统架构设计师高级，请读取 soft-exam-architect-prep，
先了解我的考试批次、基础与每周学习时间，再给本周计划。
不要把模板或虚构论文案例当成我的真实经历。
```

中级学习换成 `soft-exam-prep`。计划、进度和项目底稿由使用者提供事实后填写。

## 其它安装方式

### 其它 Agent

```sh
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform codex
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform claude
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform trae
```

| 参数 | 目标目录 |
|---|---|
| `antigravity` / `codex` | `.agents/skills/`（共用一份） |
| `claude` | `.claude/skills/`（Claude Code / Claudian） |
| `trae` | `.trae/skills/` |

`--platform antigravity claude` 可同时安装。结构化提问工具以当前会话实际暴露的能力为准；脚本不会安装或伪造工具。

### 只安装 Skills

把 `skills/` 下五个目录完整复制到平台目录，或使用 [Skills CLI](https://github.com/vercel-labs/skills)：

```sh
npx skills add Goodyzhang/ruankao.skill -a antigravity
```

在选择界面选齐五个 Skill。此方式只安装 Skill；知识资料仍需通过初始化脚本或手动复制 `vault/` 的内容取得。

### 已有权威源与发现桥接的工作区

若已有 `.claude/skills/` 权威源与 `.agents/skills/` 发现桥接，应沿用该组织方式，将公开包合并到权威源，再维护桥接。不要用 `--upgrade-skills` 覆盖发现桥接。通用初始化面向独立 Vault，不负责迁移已有多端同步配置。

## 日常使用

- **讲题**：提供完整题图后说“我选 B，请解析”。Agent 先复原题目、说明考点、解题链和选项边界，再询问是否 Grill。未作答或明确快速讲时跳过 Grill。
- **Grill**：“开始 Grill”。每张练习卡含一个正确项和两个干扰项；选择后先反馈，再决定下一题，最多三轮。“结束”或“换题”结束当前题。
- **归档**：“将本题归档到高级”。授权只用于本题；写入章级知识点和错题本后回读核验。下一题重新建立状态与授权。
- **复习**：“今天有哪些 D1/D7/D21 到期？”依据实际完成日期计算，空日期不会被当作今天到期。
- **论文**：“按我的论文项目底稿整理架构评估提纲”。先填真实事实与证据；缺失内容保持待补。示例角色、规模和指标不能直接变成个人经历。
- **历史导入**：“请用高级 organizer 整理下面这份完整历史对话”。只导入明确提交的材料；题干、选项或必要图片缺失时先补齐。

## 资料目录

```text
skills/                         五个完整 Skill
scripts/                        初始化与包验证
tests/                          初始化行为测试
integrations/antigravity-harness/ 可选长上下文 Harness 与安装器
vault/
  软考工具包使用说明.md
  个人资料/笔记/软考/
    系统架构设计师-高级/
      知识点/                   20 章
      错题本/                   20 个空错题框架
      真题库/                   上午、下午、论文、案例
      00_学习总计划.md
      01_学习进度看板.md
      02_论文项目底稿.md        空白项目事实表
      03_错题与复盘模板.md
      …                         学习卡、速查、论文示例与模板
    软件设计师-中级/
      知识点/                   12 章 + 4 份速查
      真题库/                   上午、下午
      软考-软设-错题本.md       12 章空框架
      00_学习总计划.md
      00_备考仪表盘.md
```

两级目录合计 126 份初始化资料，另有一份 Vault 使用说明。部分知识章尚为骨架；真题库覆盖不完整，并保留 OCR、回忆版、缺图及答案分歧标记。关键图示缺失时需补图，不能依据答案猜题。来源与许可范围见 [NOTICE](NOTICE.md)。

## 更新与保留个人资料

下载新版到独立目录，运行初始化，默认只补充缺少的文件。需要更新 Skill 时使用：

```sh
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform antigravity --upgrade-skills --dry-run
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform antigravity --upgrade-skills
```

`--upgrade-skills` 会覆盖所选平台的同名 Skill 文件，包括手工定制的内容。它始终保留已有知识点、错题本、计划与论文底稿。知识资料升级需人工比较、合并；不要用公开模板覆盖个人记录。

已安装旧版可选 Harness 的 Antigravity 工作区，还需从新版发布包根目录单独更新 Hook 与脚本。先预览，再执行：

```powershell
py -3 integrations/antigravity-harness/install_harness.py --workspace "D:\YourVault" --force --dry-run
py -3 integrations/antigravity-harness/install_harness.py --workspace "D:\YourVault" --force
```

macOS / Linux 把 `py -3` 换成 `python3`。`--force` 只替换同名 Harness Hook、脚本和规则，保留其它 Hook；更新后在 Antigravity 中重新打开工作区并新建会话验收。

## 常见问题

| 现象 | 处理 |
|---|---|
| 没发现 Skill | 确认打开的是目标 Vault，检查 `.agents/skills/soft-exam-question-tutor/SKILL.md`，再新建会话 |
| 只讲题、不弹卡 | 先看会话是否有真实 `ask_question` 工具事件；正文中的调用文字不能替代卡片。若工具可用但只出现调用文字，升级到 v0.3.6 的可选 Harness 并新建会话复测；若工具未暴露，再检查所选 Agent 的工具配置 |
| Grill 收尾后没有归档确认卡 | 提前达到掌握证据可以结束追问，但仍需本题的归档确认。v0.3.6 的 Stop Hook 会在已确认的单题流程中尝试补发原生归档卡；用户已明确结束、拒绝或确认归档时不重复发卡 |
| Grill 收尾时出现 `call:default_api:ask_question` 文字 | 这是正文文本，没有真实卡片。升级可选 Harness 后新建会话验证；已显示的乱码无法由 Hook 撤回 |
| 卡片已弹出，正文却夹着调用参数 | 直接点选已出现的卡片，不根据正文重复作答或重发；升级 Skill 与可选 Harness 后新建会话复测 |
| Hook 路径出现 `.agents/.agents/scripts` | 升级到 v0.3.2 并用 `--force` 更新可选 Harness；Hook 脚本路径应相对于 `.agents/` 写成 `scripts/...` |
| 等待卡片 | 先完成已有卡片；没有返回结果不能当作同意 |
| 工具缺失或报错 | Agent 应报告阻塞位置；用户明确选择文字交互后才能改用文字问答 |
| 对话中断 | 发送“继续当前题”，核对最近工具结果与写入状态后续接 |
| 缺图或 OCR 损坏 | 补齐原题，不根据解析反推题干 |
| 提示保留已有文件 | 属于默认保护行为；Skill 可显式升级，资料人工合并 |

## 验证

```sh
python3 scripts/validate_toolkit.py
python3 -m unittest discover -s tests -v
```

包结构、链接、空错题本和初始化行为已有本地验证。**尚未完成 Antigravity / 其它 Agent 的真实 UI 回归**；手动流程见 [交互验收](docs/validation.md)。

## 更新日志

### v0.3.6 — 2026-09-25

- 修正 Grill 提前达到掌握证据时只输出总结、不弹归档确认卡：Stop Hook 在确认的单题流程中补发归档卡，并避免用户已明确结束或已作出归档选择时重复发卡。
- 当前题一经明确判定为软考，后续 G1/G2 等不带五段式或 `### Grill` 标题的反馈仍保持 Harness 激活；PreInvocation 提醒明确包含提前收尾的归档步骤。
- 用 Antigravity 会话 `6001515b-7323-486d-b216-6b54f9acf0f3` 的收尾片段重放，并新增回归测试。

### v0.3.5 — 2026-09-25

- 修正 Grill 轮次后 Harness 上下文丢失：当前题已由模型明确判为软考时，后续 Grill 回复继续保持提醒与工具守卫生效。
- Stop Hook 识别 Grill 收尾正文里的伪 `ask_question` 调用且没有真实工具事件的情况，请求 Agent 继续补发原生归档确认卡。
- 用真实会话片段重放确认此前返回 `allow`、修复后返回 `continue`；增加 Grill 收尾回归测试。

### v0.3.4 — 2026-09-25

- 修正“题图＋为我讲一下这道题”的首轮 Harness 漏激活：模型本轮已明确判定为软考题并完成讲解时，Stop Hook 会拦截只有调用文字、没有真实卡片的裸退。
- 激活依据限定在当前用户消息之后的讲题回复，避免旧题回复影响下一项普通任务。
- 用实际 Antigravity 会话片段复现并验证修复；增加对应回归测试。

### v0.3.3 — 2026-09-25

- 调整单题运行时指引：正文只放讲解或上一题反馈，下一张卡的题干、选项与参数交给原生工具调用，减少重复与原始调用文本混入正文。
- 按真实工具事件判断卡片状态：卡片已显示时等待点选，不因正文混入调用文字而重发。
- 精简容易被照搬的调用示例，并更新可选 Harness 的瞬时提醒和排查说明。

### v0.3.2 — 2026-09-25

- 修正三个 Antigravity Hook 命令的相对路径：运行目录已是 `.agents/`，无需再写 `.agents/scripts/...`。
- 修正安装测试的路径基准，确保发布包中的 Hook 命令能从 `.agents/` 找到脚本。
- 已安装 v0.3.1 Harness 的工作区需用 `--force` 更新同名 Hook；无需为此重新安装知识资料。

### v0.3.1 — 2026-09-25

- 修正可选 Antigravity Harness 的 Hook 命令路径和 Python 启动器选择，避免安装后脚本无法运行。
- 收紧 Harness 的软考单题激活条件，避免历史对话中的泛化词触发工具白名单与强制续写。
- 允许在 `ask_question` 未暴露时明确报告能力缺口；补充对伪工具调用文本的排查说明。
- 增加相关安装和守卫测试。真实 Antigravity 卡片 UI 仍需在目标客户端验收。

### v0.3.0 — 2026-09-18

- 新增可选 Antigravity 超长上下文 Harness：PreInvocation 续接提醒、PreToolUse 白名单和 fullyIdle Stop 拦截协同工作。
- Harness 只对已确认的软考单题流程生效；图片附件和泛化讲题用语不再单独触发。
- 增加独立安装器，可合并三个命名 Hook 并保留工作区其它 Hook；同名 Harness 升级需要显式 --force。
- 新增 Harness 安装行为测试和包结构校验。真实 Antigravity UI 回归仍需在目标客户端完成。

### v0.2.0 — 2026-09-16

- 从单题 Skill 扩展为五个 Skill 的完整 toolkit。
- 加入两级脱敏知识资料、真题转录、空白错题本、计划及项目底稿。
- 修正中级资料路径，补齐高级目录和专项参考，统一 Skill 依赖。
- 增加多平台初始化、只升级 Skill 的选项和保留个人资料的行为测试。
- 修正可定位的资料链接，标记缺失内容；补齐来源、升级和排查说明。

### 2026-09-16 — 单题流程更新

- 前置讲解、卡片、Grill、归档与中断续接契约。
- 依据实际工具能力交互，沿用同题已有工具结果与归档授权。
- 增加运行时参考和人工验收步骤。

### v0.1.0

- 首次发布独立 `soft-exam-question-tutor`，提供单题讲解和确认后归档。

## 致谢

感谢[软考达人](https://github.com/ruankaodaren/ruankao)等公开学习资源。第三方出处以具体条目标记为准；本项目与这些资源相互独立。
