# 软考学习 Toolkit · ruankao.skill

[下载 v0.6.0](https://github.com/Goodyzhang/ruankao.skill/releases/tag/v0.6.0) · [在线复习册](#3-在线复习册与资产目录) · [安装与使用](#4-安装与使用) · [更新日志](#5-更新日志)

## 1. 这套工具做什么

发一道题，讲清考点，换条件练习，确认后留下可复习的记录。一章学完，将教材、知识点和错题二次蒸馏为图文复习册；练案例题时，打开本地作答环境，提交后逐点评阅。

**v0.6.0 新功能：在内建浏览器中登录“软考〇人（防谶）”，快速整理案例题和论文题。** 打开小节后，直接点名 `soft-exam-bank-ingest`，指定题号或整理剩余题目。Agent 保存题干和原图，合并同案例的小问，补上考场答案、采分要点与详细解析；论文生成完整应试模拟范文，整理中断后可续接。

```text
@soft-exam-bank-ingest 为我完成当前打开页面79～85题的案例题和论文题整理。
```

需要能实际看图的模型、浏览器工具与本地保存能力。优先使用内建浏览器，不要求特定 browser-use CLI；首次资料位置不明确时，用真实目录候选卡片引导。只读取题目、展开解析和导航，答案保存本地，不代填网站或交卷。

[题库整理说明](docs/soft-exam-bank-ingest.md) · [案例作答实验室](docs/soft-exam-lab.md) · [新版本说明](docs/releases/v0.6.0.md)

## 2. Skill 家族

公开包包含八个完整 Skill，支持 Antigravity、Codex、Claude Code／Claudian、Trae 和 ZCode。它们共用章节与归档契约，各自负责不同任务。

| Skill | 用途 | 入口 |
|---|---|---|
| `soft-exam-question-tutor` | 单题讲解、错因诊断、变式 Grill、授权后章级归档 | 发送完整题图或文本并要求讲题 |
| `soft-exam-bank-ingest` **新** | 浏览器案例／论文入库，原图保存、小问合并、逐问解析与续接 | 显式点名 |
| `soft-exam-lab` | 案例题作答网页、计时绘图、严格逐点评阅与练习档案 | 显式点名 |
| `soft-exam-review-book` | 已学章节二次蒸馏为图文、速查与自测 | 要求制作、续写或修订复习册 |
| `soft-exam-prep` | 软件设计师中级学习计划、练习和复习进度 | 中级备考请求 |
| `soft-exam-organizer` | 导入明确提交的完整中级历史对话 | 点名或提交历史导入任务 |
| `soft-exam-architect-prep` | 系统架构设计师高级计划、案例、论文与周期复习 | 高级备考请求 |
| `soft-exam-architect-organizer` | 导入明确提交的完整高级历史对话 | 点名或提交历史导入任务 |

题库整理与实验室仅接受 `$skill-name`、`@skill-name` 或“使用 skill-name”的实际调用；引用名称和初始化时提及不启动。已启动批次或场次可直接“继续”。普通讲题保持 tutor 路由；章节制作和题库批次不继承单题工具限制、强制 Grill 或逐题归档卡。

安装时保留八个完整目录与各自的 `references/`、`assets/`、`scripts/`，不能只复制入口文件。两级知识资料与空错题本随包提供，个人题库、登录信息与本机配置不进入发布包。

## 3. 在线复习册与资产目录

**[打开全部复习册目录 →](https://goodyzhang.github.io/ruankao.skill/artifacts/)**

当前已整理高级／系统架构设计师的以下章节，每个小节均可切换“图文、速查、自测”。

| 在线阅读 | 范围与内容 | 最近更新 |
|---|---|---|
| [第二章 · 计算机系统基础知识](https://goodyzhang.github.io/ruankao.skill/artifacts/高级/系统架构设计师/02_计算机系统基础知识/index.html) **新** | 2.1–2.9；151 张图、348 道自测 | 2026-10-05 |
| [第三章 · 信息系统基础知识](https://goodyzhang.github.io/ruankao.skill/artifacts/高级/系统架构设计师/03_信息系统基础知识/index.html) **新** | 3.1–3.8；88 张图、243 道自测、276 条术语索引 | 2026-10-05 |
| [第五章 · 软件工程基础知识](https://goodyzhang.github.io/ruankao.skill/artifacts/高级/系统架构设计师/05_软件工程基础知识/index.html) | 5.1–5.7；42 个知识组、159 道自测 | 2026-10-04 |
| [SMTP／POP3 图文样章](https://goodyzhang.github.io/ruankao.skill/demo/smtp-pop3/) | 邮件收发机制、速查与 6 道自测 | 2026-10-03 |

复习册会随整理与勘误持续更新；合并到 `main` 后由 GitHub Pages 发布。**欢迎其他考生协作推送，一起完成各个科目的知识库搭建。** 可提交 [Issue](https://github.com/Goodyzhang/ruankao.skill/issues) 或 Pull Request，补充讲解、图解、变式题及完整章节。

章节按 `artifacts/<级别>/<科目>/NN_章名/` 保存。贡献请注明教材版本和来源，区分原题、改编题与自编题，检查图文关系、导航和自测；仅提交可公开的复习内容。教材全文、个人作答、项目底稿与制作日志保留本地，出处与许可见 [NOTICE](NOTICE.md)。

**复习册不放入 Release 安装包，也不放入 GitHub 自动生成的 Source code 压缩包。** 在线直接阅读；离线使用可 [克隆完整仓库](https://github.com/Goodyzhang/ruankao.skill) 后打开相应 `index.html`，保留其图片、CSS 与 JavaScript。SMTP／POP3 样章仍随安装包提供。

## 4. 安装与使用

### 先看三种使用方式

<p>
<img src="docs/images/tutor-grill-archive.png" width="240" alt="讲题、变式 Grill 与本地归档的操作示意">
<img src="docs/images/visual-review-book.png" width="240" alt="视觉复习册，含实际 SMTP／POP3 样章截图">
<img src="docs/images/case-answer-lab.png" width="240" alt="案例题作答与评阅报告的界面示意">
</p>

以上是宣传示意；复习册图中包含现有 SMTP／POP3 样章截图，作答实验室布局以实际页面为准。

#### 讲题、练习和归档


![做题前后对比：原来截图搜题后讲解宽泛、来不及记录；安装 Skill 后对齐考点、换条件练习，确认后分别归档知识点与错题](docs/images/study-before-after.png)

发一张完整题图，告诉它“我选 B，请解析”。讲解会围绕题目考查的知识、推理过程和选项边界展开。有需要时继续做变式练习，看看条件改变后还能不能判断；未作答或只想快速听解析，也可以跳过练习。

普通讲题后可确认归档；明确要求“只讲解”时直接结束。确认归档后，Agent 将本题的知识点与错题记录整理到对应章节，并回读核验。省下手动复制和排版的时间，下一次能找到当时的错因。本题已有明确归档授权时直接沿用；用户明确授权第 1–3 题及目标时，逐题执行并记录结果，范围之外的新题重新确认。


#### 一章学完：知识点二次蒸馏

![协作工作室：统筹核验、创意写作、核心图与辅助图共同形成复习册](docs/images/knowledge-distillation-studio.png)

复习册按教材小节连续展开，正文解释机制，大图表达关系，速查保存判断线索，自测检验条件迁移。相似名词放在同尺度图中比较，通信采用时序图，计算用小黑板与逐步演算；经核验反复出错或用户点名的考点详细讲解。

创意写作优先交给 Antigravity（`agy`）中的 Gemini，Claude Code 作为后备；Codex 核验并制作核心图，Grok 可制作少文字的辅助图。CLI 找不到时填写位置或跳过，无需全部安装。生图前两轮提示词复核、tutor 方法复核，生成后实际看图，再在内建浏览器检查页面。原始教材和笔记保留，局部修订不重置无关自测。

```text
使用 soft-exam-review-book，将系统架构设计师高级第三章“信息系统基础知识”做成图文、速查与自测复习册。重点比较 TPS、MIS、DSS、ES、OAS、ERP；按小节完成，整章结束后统一审阅。
```

#### 案例题：作答与智能阅卷

`soft-exam-lab` 打开本机作答网页，提供计时、Markdown／公式预览、题图放大、简易绘图和自动保存。用户交卷后，当前 Agent 依据冻结评分表逐点评阅，分别给出参考估分与严格训练分，以及失分对照、图形报告和强化 prompt。

```text
@soft-exam-lab 为我来一道系统架构设计师软件系统设计案例题真题，就做一道。
```

一道指完整案例大题及全部小问；一套默认三道专题案例题，缺方向或数量时弹卡。使用者无需 npm 或额外模型 API；Python 不可用时引导离线导出／导入答卷。未经核实年份题号的网站材料标为 `web-bank`，完整核验后可以普通练习，不冒充历年真题。

### 快速开始：完整初始化

需要 Python 3.9 或更新版本。脚本仅使用标准库，无需安装 Python 依赖。

#### 1. 获取发布包

从 [Release](https://github.com/Goodyzhang/ruankao.skill/releases/tag/v0.6.0) 下载 `ruankao-toolkit-v0.6.0.zip` 并解压。该包保留全部八个 Skill、实验室本地运行资源与 SMTP／POP3 样章，排除 `artifacts/`。也可以获取相同版本的完整 Git 仓库（包含知识库）：

```sh
git clone --branch v0.6.0 --depth 1 https://github.com/Goodyzhang/ruankao.skill.git
cd ruankao.skill
```

以下命令在解压目录或仓库根目录中运行。`../RuankaoVault` 是目标 Vault，可替换为自己的路径；目标应与发布包目录分开。

#### 2. 安装到 Antigravity 工作区

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

脚本将八个完整 Skill 放入 `.agents/skills/`，将资料放入 `个人资料/笔记/软考/`。已有文件默认保留，并列出跳过的文件；重复运行不会清空错题和进度。

在 **Antigravity 中打开目标目录并新建会话**；使用 Obsidian 时，也将这个目录作为 Vault 打开。普通学习资料目录同样可用。发现目录与加载行为见 [Antigravity 官方说明](https://antigravity.google/docs/skills)。

#### 可选：超长上下文 Harness

Antigravity 用户可以安装 [可选 Harness](integrations/antigravity-harness/README.md)。它仅在已确认的软考单题会话中提醒卡片续接、约束工具并拦截讲题后裸退；普通图片、文档和其它 Agent 不受影响。

#### 3. 首次使用

```text
当前工作区就是我的 Obsidian Vault。
软考知识库位于“个人资料/笔记/软考”。
我准备系统架构设计师高级，请读取 soft-exam-architect-prep，
先了解我的考试批次、基础与每周学习时间，再给本周计划。
不要把模板或虚构论文案例当成我的真实经历。
```

中级学习换成 `soft-exam-prep`。计划、进度和项目底稿由使用者提供事实后填写。

#### 安装后初始化 prompt（可复制）

安装后在目标工作区新建会话，复制下面的 prompt。将 `{请在这里填写你的工作区或 Vault 路径}` 替换为你的路径；已经在目标工作区中时，也可改为 `.`。Skill 根目录由 Agent 探测，无需照抄作者的本机路径。

```markdown
请执行软考学习导师（Soft Exam Tutor）初始化流程。
我的工作区或 Vault：{请在这里填写你的工作区或 Vault 路径}

请先确认该目录存在，将以下路径均相对于它解析。读取现有的最新 SOP、契约与规则，作为后续执行依据；本次仅初始化，不启动讲题、案例题场次、复习册制作或归档。

1. 【探测权威目录与分工】
   - 如存在 AGENTS.md，完整读取其软考入口、路由与方法学；不要假定安装包一定提供这个文件。
   - 优先遵循工作区已声明的权威目录。如 .agents/skills/ 或 .trae/skills/ 中只是发现桥接，继续读取其指向的完整源文件。
   - 独立安装时，核对 .claude/skills/、.agents/skills/、.trae/skills/、.zcode/skills/ 中实际存在的 soft-exam-question-tutor，以完整且已声明的源作为 SKILL_ROOT。存在多个冲突版本时先说明差异，不能静默任选或混用。
   - 确认八个 Skill 的分工：单题由 soft-exam-question-tutor 负责；学习计划和周期复习由对应级别的 prep 负责；完整历史导入由 organizer 负责；章节复习册由 soft-exam-review-book 负责；soft-exam-lab 只接受用户显式点名，初始化中提及名称不算启动；题库整理 soft-exam-bank-ingest 同样只接受显式调用。

2. 【运行时与终止保护】
   - 如存在 GEMINI.md、.agents/rules/soft-exam-suspension.md，读取相关规则；缺失时如实报告，不伪造加载结果，也不自行安装 Hook。
   - 卡片必须通过当前会话实际提供的原生提问工具调用，不能在正文输出伪 JSON 或调用文字冒充卡片。
   - 卡片待答时等待真实返回，不重复弹卡；预选、空回复和超时不当作用户作答或授权。
   - 识别带 (Recommended)、[推荐]、选项编号的真实终止选择；用户选择结束本题、已完成等待下一题或不归档时正常结束，不能循环补卡。
   - 核对已有归档授权与实际写入、回读结果；已经完成的步骤不重复执行，不能仅凭模型声称“已归档”判断完成。

3. 【完整读取单题核心契约】
   - SKILL_ROOT/soft-exam-question-tutor/SKILL.md
   - SKILL_ROOT/soft-exam-question-tutor/references/first-use.md
   - SKILL_ROOT/soft-exam-question-tutor/references/runtime-interaction.md
   - SKILL_ROOT/soft-exam-question-tutor/references/knowledge-base-contract.md
   - SKILL_ROOT/soft-exam-question-tutor/references/grill-diagnostic-contract.md
   - 后续只按实际任务加载其它 Skill 的完整 SOP，不让单题规则限制章节制作或实验室。

4. 【资料位置】
   - 检查已有本地绑定及工作区默认资料目录，已有有效绑定直接复用。
   - 必要位置不明确时，用实际可用的追问卡提供 1～2 个真实候选，或请我手动填写绝对路径；没有候选就说明没有探测到。没有卡片工具时说明限制，并按契约处理。
   - 选择位置不等于同意归档本题，不创建虚构做题记录，不把初始化扩展为批量归档授权。

【完成汇报】
1. 列出实际读取的核心契约相对路径；版本、哈希或修改时间只报告实际可核验的信息，缺失文件另列。
2. 简述五项守则：输入 Gate 补齐、五段式讲解、基于真实作答的 Grill 门控、授权范围内章级归档与回读、终止与中断保护。
3. 核心契约齐全且工具检查完成后回复：“软考辅导环境已就绪，请上传软考题目图片、截图或文本开始。”未完成时说明缺口，不声称就绪。
```

需要案例题时，初始化后另发显式调用：

```text
$soft-exam-lab 为我来一道系统架构设计师软件系统设计案例题真题，就做一道。先确认题库和练习档案位置，使用自由计时。
```

#### 首次使用：先检查，再引导

不用事先把每个目录都改成示例中的样子。Skill 会先检查你明确提供的位置、已有绑定，以及工作区中的默认资料布局；已有有效配置直接沿用。

需要选择时，会出现位置卡片：点击探测到的资料目录，或直接输入你自己的**绝对路径**。候选会显示实际路径；没有候选就请你填写。选择保存位置不等于同意归档某一道题，单题仍按本题授权执行。

- **只想讲题**：可以先讲解，归档前再确定目标科目与位置。
- **已有笔记**：沿用现有章级文件和命名，不另造一份平行错题本。
- **制作复习册**：需要协作时才查找对应 CLI；找不到可填写可执行文件位置或跳过，由后备角色继续。
- **没有 Obsidian 或卡片工具**：普通资料目录也能使用；环境配置可用简短文字问答，单题练习与归档仍遵守其实际交互规则。

已选择的位置与跳过项按本地续接约定复用；换机器或路径失效后再核验。工具探测不会自动安装软件、修改 PATH 或替换你的模型配置。

### 其它安装方式

#### 其它 Agent

```sh
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform codex
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform claude
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform trae
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform zcode
```

| 参数 | 目标目录 |
|---|---|
| `antigravity` / `codex` | `.agents/skills/`（共用一份） |
| `claude` | `.claude/skills/`（Claude Code / Claudian） |
| `trae` | `.trae/skills/` |
| `zcode` | `.zcode/skills/` |

`--platform antigravity claude` 可同时安装。结构化提问工具以当前会话实际暴露的能力为准；脚本不会安装或伪造工具。

#### 只安装 Skills

把 `skills/` 下八个目录完整复制到平台目录，或使用 [Skills CLI](https://github.com/vercel-labs/skills)：

```sh
npx skills add Goodyzhang/ruankao.skill -a antigravity
```

在选择界面选齐八个 Skill。此方式只安装 Skill；知识资料仍需通过初始化脚本或手动复制 `vault/` 的内容取得。

#### 已有权威源与发现桥接的工作区

若已有 `.claude/skills/` 权威源与 `.agents/skills/` 发现桥接，应沿用该组织方式，将公开包合并到权威源，再维护桥接。不要用 `--upgrade-skills` 覆盖发现桥接。通用初始化面向独立 Vault，不负责迁移已有多端同步配置。

### 日常使用

- **讲题**：提供完整题图后说“我选 B，请解析”。Agent 先复原题目、说明考点、解题链和选项边界，再询问是否 Grill。未作答或明确快速讲时跳过 Grill；明确要求直接归档时沿用授权写入。
- **Grill**：“开始 Grill”。生成变式含一个正确项和两个干扰项；复用原题时按宿主能力保留完整选项。选择后先反馈，再决定下一题，最多三轮。“结束”或“换题”结束当前题。
- **归档**：“将本题归档到高级”。授权只用于本题；写入章级知识点和错题本后回读核验。下一题重新建立状态与授权。
- **章节复习册**：“第五章已经学完，请制作图文速查复习册”。按小节取材、写作、生图、复核，整章完成后统一审阅；也可指定某个专题或局部修订。
- **复习**：“今天有哪些 D1/D7/D21 到期？”依据实际完成日期计算，空日期不会被当作今天到期。
- **论文**：“按我的论文项目底稿整理架构评估提纲”。先填真实事实与证据；缺失内容保持待补。示例角色、规模和指标不能直接变成个人经历。
- **历史导入**：“请用高级 organizer 整理下面这份完整历史对话”。只导入明确提交的材料；题干、选项或必要图片缺失时先补齐。

### 资料目录

```text
skills/                         八个完整 Skill
scripts/                        初始化与包验证
tests/                          初始化、路由与阅读状态测试
docs/demo/smtp-pop3/             可离线打开的 SMTP／POP3 样章
artifacts/高级/系统架构设计师/   仅完整 Git 仓库／在线知识库提供
  02_计算机系统基础知识/         第二章复习册
  03_信息系统基础知识/           第三章复习册
  05_软件工程基础知识/           第五章完整复习册，index.html 为入口
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

### 更新与保留个人资料

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

### 常见问题

<details>
<summary>展开安装、卡片与归档排查</summary>

| 现象 | 处理 |
|---|---|
| 没发现 Skill | 确认打开的是目标 Vault，检查 `.agents/skills/soft-exam-question-tutor/SKILL.md`，再新建会话 |
| 只讲题、不弹卡 | 升级到 v0.3.7 并用 `--force` 更新可选 Harness。PostInvocation 在每轮回复后检查漏卡并要求自动补发；以真实工具事件判断是否成功，正文中的调用文字不能替代卡片。工具未暴露时检查所选 Agent 的工具配置 |
| 对话变长或回复“？”后再次漏卡 | v0.3.7 按当前题和真实卡片返回续接，不再依赖反馈标题；大段工具结果不会按 256 KiB 截断题目上下文。升级后重开工作区以加载新 Hook；执行结果见会话产物目录下 `soft-exam-card-events.jsonl` |
| Grill 收尾后没有归档确认卡 | 提前达到掌握证据可以结束追问，但仍需本题的归档确认。v0.3.6 的 Stop Hook 会在已确认的单题流程中尝试补发原生归档卡；用户已明确结束、拒绝或确认归档时不重复发卡 |
| Grill 收尾时出现 `call:default_api:ask_question` 文字 | 这是正文文本，没有真实卡片。升级可选 Harness 后新建会话验证；已显示的乱码无法由 Hook 撤回 |
| 卡片已弹出，正文却夹着调用参数 | 直接点选已出现的卡片，不根据正文重复作答或重发；升级 Skill 与可选 Harness 后新建会话复测 |
| Hook 路径出现 `.agents/.agents/scripts` | 升级到 v0.3.2 并用 `--force` 更新可选 Harness；Hook 脚本路径应相对于 `.agents/` 写成 `scripts/...` |
| 等待卡片 | 先完成已有卡片；没有返回结果不能当作同意 |
| 工具缺失或报错 | Agent 应报告阻塞位置；用户明确选择文字交互后才能改用文字问答 |
| 对话中断 | 发送“继续当前题”，核对最近工具结果与写入状态后续接 |
| 缺图或 OCR 损坏 | 补齐原题，不根据解析反推题干 |
| 提示保留已有文件 | 属于默认保护行为；Skill 可显式升级，资料人工合并 |

</details>

### 验证

```sh
python3 scripts/validate_toolkit.py
python3 -m unittest discover -s tests -v
# 开发验证：若已有支持 node:test 的 Node.js
node --test tests/test_review_quiz_state.cjs
```

发布验证范围与实际结果见 [v0.6.0 发布说明](docs/releases/v0.6.0.md)、[题库整理验收](docs/soft-exam-bank-ingest-validation.md) 和 [实验室验收](docs/soft-exam-lab-validation.md)。安装脚本与确定性保存、续接、路由均有行为测试；浏览器检查单列。Windows、其它 Agent 的真实卡片／浏览器与物理触控未实测。Node 仅用于开发验证，安装和离线阅读不需要它。


## 5. 更新日志

### v0.6.0 — 2026-10-05

- 新增第八个 Skill `soft-exam-bank-ingest`：在内建浏览器登录“软考〇人”，按小节或题号整理案例题与论文题，保存原图、合并小问、补充 tutor 解析与完整模拟范文。
- 保存与续接使用版本化台账，保护人工备注；普通网站材料以 `web-bank` 接入实验室，真题身份检查保持严格。
- 同步八 Skill 安装校验和 Harness 路由，新增 ZCode 安装目标；首次位置引导与普通单题流程保留。
- 发布第二、第三章在线复习册，新增资产目录，将 Skill 分工、阅读入口与安装使用前移。
- 复用三张宣传图片说明使用场景；Release 和 Source code 继续排除 `artifacts/`。

[发布说明与验证范围](docs/releases/v0.6.0.md)。

### v0.5.0 — 2026-10-04

- 新增第七个 Skill `soft-exam-lab`：显式启动架构师案例题作答环境，可靠保存、绘图、提交冻结与中断续接。
- 当前 Agent 按冻结采分点严格评阅，分别提供参考估分与训练分；生成图形报告、失分对照、强化 prompt 和本地练习档案。
- 同步安装、发现元数据、Harness 路由与恢复包；普通单题和复习册继续沿用原入口。
- 新增可复制的安装后初始化 prompt，探测实际权威目录，使用相对路径或使用者填写的路径。
- Release 安装包和 Source code 压缩包排除 `artifacts/`；完整知识库保留在 Git 仓库与在线站点。

升级方法与验证范围见 [v0.5.0 发布说明](docs/releases/v0.5.0.md)。

### v0.4.3 — 2026-10-04

- 复习册 Goal 沿用任务内的协作授权，明确 tutor／Grill 通用方法、提示词和公开知识的交接范围，同范围不重复确认。
- 续接区分待授权、重复卡、未发送与已返回结果；保存真实依据，不伪造用户回答或绕过平台审批。
- 加入 Goal 授权范围模板；独立演练三个场景，并通过正常审批完成一次真实 agy 教学方法复核。

升级与验证范围见 [v0.4.3 发布说明](docs/releases/v0.4.3.md)。


### v0.4.2 — 2026-10-04

- 吸收 [DreamLanter 的 PR #1](https://github.com/Goodyzhang/ruankao.skill/pull/1)：移除默认“我已选 C”，区分候选错因与实际证据，保留原题与练习选项映射，按需加载资料。
- 文字模式由用户明确选择后启用；同步 Harness，防止合法文字练习被重复补卡。明确只讲解时正常收尾。
- 明确批量归档授权绑定题号、目标与操作；逐题查重、保存状态并从实际未完成位置恢复，保留人工记录。

升级与验证范围见 [v0.4.2 发布说明](docs/releases/v0.4.2.md)。

### v0.4.1 — 2026-10-04

- 强化复习册生图流程：两轮提示词改稿、Gemini tutor 复核、生成后整图核验；35 字作为知识密度下限，公式保留符号、单位、条件和逐步演算。
- 修正协作探测：Gemini 经 Antigravity（`agy`）调用；核对真实帮助、完整参数和业务状态，分别记录请求模型与返回披露。
- 核验前先读完整案例，区分局部与全局结论；优先内建浏览器检查，局部更新不重置无关作答。
- 下载包加入高级／系统架构设计师第五章完整复习册：7 节、42 个知识组、159 道自测；在线知识库继续随主分支更新。

升级方法与验证范围见 [v0.4.1 发布说明](docs/releases/v0.4.1.md)。

### v0.4.0 — 2026-10-03

- 新增第六个 Skill `soft-exam-review-book`：教材、知识点和错题二次蒸馏为图文、速查、自测，支持按小节顺序接力与局部更新。
- 原有五个 Skill 加入首次使用引导：检查已有环境，按实际候选选择资料与归档位置，支持绝对路径和可选工具跳过。
- 公开 SMTP／POP3 样章，提供在线阅读与离线资源；README 新增协作工作室和做题对比漫画。
- 安装与升级覆盖完整复习册资源，保留已有笔记；可选 Harness 区分章节制作与当前单题，保留 v0.3.9 的卡片收尾修复。

详细变化与验证范围见 [v0.4.0 发布说明](docs/releases/v0.4.0.md)。

<details>
<summary>已发布版本记录（v0.3.9 及更早）</summary>

### v0.3.9 — 2026-10-01

- 修复 Antigravity 归档确认与流程收尾阶段的卡片死循环 Bug：
  - 增强 `harness_stop_guard.py` 对带 `(Recommended)` / `[推荐]` 标识或选项编号前缀的选项文本提取能力（解决 Antigravity 原生推荐项导致前缀匹配失败的问题）。
  - 扩充终止关键词（支持 `已完成`、`等待下一题`、`等待上传`、`全流程已归档` 等常见收尾状态）。
  - 新增正文已宣布全流程归档完成时的防御性旁路，避免循环要求模型补发。
  - 同步更新 Harness 挂起规则与单元测试套件。

### v0.3.8 — 2026-09-27

- 在 v0.3.7 的卡片自动恢复基础上，修复“下一题”“再来一题”或新截图加“我选 B”的新题边界：旧题的归档选择不再使新题漏卡被放行。
- 保留问号续接与故障排查边界，新增三种连续做题输入的回归覆盖；17 项 Harness 测试通过。

### v0.3.7 — 2026-09-27

- 新增 PostInvocation 卡片检查，模型回复结束后立即要求补发缺失卡片；Stop 复用同一检查，避免只依赖最终停止事件。
- 修复真实 Antigravity 消息包装、问号续接和无固定标题的 Grill 反馈导致上下文丢失；依据真实卡片返回确定下一张卡是否待发。
- 读取完整的最近事件，避免大段文件读取结果截断当前题上下文；已有真实调用、等待作答、明确结束或归档授权不重复发卡。
- 连续两次补发失败时明确报告未完成，不静默跳过或误归档。新增不包含题目内容的 Hook 执行记录，以追查实际运行情况。
- 重放真实会话中的两次漏卡及正常收尾，并增加对应回归测试；仍需在目标客户端验证真实卡片显示。

### v0.3.6 — 2026-09-25

- 修正 Grill 提前达到掌握证据时只输出总结、不弹归档确认卡：Stop Hook 在确认的单题流程中补发归档卡，并避免用户已明确结束或已作出归档选择时重复发卡。
- 当前题一经明确判定为软考，后续 G1/G2 等不带五段式或 `### Grill` 标题的反馈仍保持 Harness 激活；PreInvocation 提醒明确包含提前收尾的归档步骤。
- 用实际 Antigravity 会话的收尾片段重放，并新增回归测试。

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

</details>

### 致谢

感谢[软考达人](https://github.com/ruankaodaren/ruankao)等公开学习资源。第三方出处以具体条目标记为准；本项目与这些资源相互独立。
