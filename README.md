# 软考学习 Toolkit · ruankao.skill

系统架构设计师学习资料与八个 AI 学习 Skill。可以直接阅读教材、题库和图文复习册，也可以安装 Skill，在自己的工作区讲题、练习、写论文和整理笔记。

[系统架构设计师资料目录](https://github.com/Goodyzhang/ruankao.skill/tree/main/materials/系统架构设计师) · [在线视觉复习册](https://goodyzhang.github.io/ruankao.skill/artifacts/) · [下载选择](#下载选择) · [安装与使用](#安装与使用) · [版本记录](#版本记录)

## 系统架构设计师资料

全部新增资料位于 `materials/系统架构设计师/`；视觉复习册沿用 `artifacts/高级/系统架构设计师/`，已有在线地址继续可用。

| 类别 | 内容与入口 |
| --- | --- |
| [教材](https://github.com/Goodyzhang/ruankao.skill/tree/main/materials/系统架构设计师/教材) | 第 2 版教材 Markdown、配套插图、目录索引与学习卡 |
| [笔记](https://github.com/Goodyzhang/ruankao.skill/tree/main/materials/系统架构设计师/笔记) | 20 章知识点、口诀与专题整理；保留已有内容的完整程度说明 |
| [题库](https://github.com/Goodyzhang/ruankao.skill/tree/main/materials/系统架构设计师/题库) | 综合知识历年题、押题练习及参考解析 |
| [案例分析](https://github.com/Goodyzhang/ruankao.skill/tree/main/materials/系统架构设计师/案例分析) | 历年案例、专题案例、押题练习与可复用题包 |
| [论文](https://github.com/Goodyzhang/ruankao.skill/tree/main/materials/系统架构设计师/论文) | 论文真题、通用写作模板与教学材料；不含个人论文和项目底稿 |
| [视觉复习册](https://goodyzhang.github.io/ruankao.skill/artifacts/) | 第 2–5 章：计算机系统、信息系统、信息安全、软件工程；各章提供图文、速查、自测 |

题干与参考解析保留原有年份、来源、OCR、回忆版及待核标记。个人作答、错次、批改结果和复习状态已从本次资料副本中移除。资料覆盖以各分类索引为准，缺题、缺图处保留说明。

## 下载选择

**工具和资料分别发布，任选其一，也可配合使用。**

| 需要什么 | 下载 |
| --- | --- |
| 安装 AI 学习工具 | [工具 Release · v1.0.0](https://github.com/Goodyzhang/ruankao.skill/releases/tag/v1.0.0)：`ruankao-toolkit-v1.0.0.zip` |
| 一次下载全部文字与题图资料 | [资料 Release · materials-v1.0.0](https://github.com/Goodyzhang/ruankao.skill/releases/tag/materials-v1.0.0)：`ruankao-architect-materials-v1.0.0.zip` |
| 只下载某类资料 | 同一资料 Release 提供 `textbook`、`notes`、`questions-cases`、`essays` 四个分类 ZIP |
| 阅读视觉复习册 | [在线目录](https://goodyzhang.github.io/ruankao.skill/artifacts/)；离线使用可克隆仓库 |

工具包包含八个完整 Skill、Python 脚本、本地实验室运行资源、可选 Harness，以及原有初始化种子和空白学习记录，保持已有安装方式兼容。此次补齐的完整资料由独立资料包提供，不会随初始化自动复制。

资料包解压即可阅读，无需安装 Skill。合集与分类包内容重叠，选择一种即可；需要 Agent 使用时，将解压后的 `系统架构设计师` 目录放入自己的资料区，并明确告诉 Agent 题库位置。不要覆盖个人答卷和论文目录。

视觉复习册图片较多，不放入这两个 Release 的 ZIP，也不放入 GitHub 自动生成的 Source code 压缩包。完整 Git 仓库保留全部阅读页面、必要图片和脚本：

```sh
git clone --branch v1.0.0 --depth 1 https://github.com/Goodyzhang/ruankao.skill.git
```

离线阅读时打开 `artifacts/index.html`，保持各章资源文件相对位置。下载页提供 `SHA256SUMS.txt`，可核对压缩包完整性。

## 安装与使用

需要 Python 3.9+ 和能够读取、编辑本地文件的 Agent。解压工具包后，在包根目录执行：

```sh
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform codex --dry-run
python3 scripts/init_toolkit.py --vault "../RuankaoVault" --platform codex
```

Windows 使用 `py -3` 替换 `python3`。支持的平台参数：

| 参数 | Skill 安装位置 |
| --- | --- |
| `codex` / `antigravity` | `.agents/skills/` |
| `claude` | `.claude/skills/`，供 Claude Code / Claudian 使用 |
| `trae` | `.trae/skills/` |
| `zcode` | `.zcode/skills/` |

在目标工作区新建会话，可先说：

```text
我准备系统架构设计师高级，请读取 soft-exam-architect-prep。
软考资料放在当前工作区，请先核对资料位置，再了解我的基础与学习时间。
不要将示例项目或模板当成我的真实经历。
```

已有文件默认保留。更新 Skill 时加 `--upgrade-skills`；该选项会替换同名 Skill 文件，保留已有学习资料。已有权威源与发现桥接的工作区，应沿用自己的目录约定。

[完整安装步骤、初始化 prompt 与常见问题](docs/installation.md) · [可选 Antigravity Harness](integrations/antigravity-harness/README.md)

## 八个 Skill 的分工

| Skill | 用途 | 如何开始 |
| --- | --- | --- |
| `soft-exam-question-tutor` | 单题讲解、错因诊断、可选 Grill、授权后归档 | 发完整题图或题目文本并要求解析 |
| `soft-exam-architect-prep` | 高级计划、案例、论文写作与批改、周期复习 | 提出高级学习或论文请求 |
| `soft-exam-architect-organizer` | 高级历史学习对话归档 | 明确提交完整历史对话 |
| `soft-exam-prep` | 中级学习计划、练习和复习进度 | 提出中级备考请求 |
| `soft-exam-organizer` | 中级历史学习对话归档 | 明确提交完整历史对话 |
| `soft-exam-review-book` | 章节或专题图文复习册 | 要求制作、续写或修改复习册 |
| `soft-exam-lab` | 本地网页作答、逐点评阅、原文批注 | 显式点名调用 |
| `soft-exam-bank-ingest` | 案例与论文题整理、原图保存、解析和续接 | 显式点名调用 |

普通讲题由 tutor 处理；单篇论文写作与批改由高级 prep 处理。Lab 和题库整理只有在显式调用后启动，提及名字不启动场次。安装时保留完整 Skill 目录及其引用资源。

### 案例与论文实验室

Lab 在本机打开作答页面，支持计时、保存、撤销、Markdown／公式预览和绘图。交卷后由当前 Agent 阅读答卷与评分依据，再给出原文批注和参考答案。网页本身不自动完成语义阅卷；推定训练评分与官方细则分别标明。

```text
$soft-exam-lab 为我准备 2018 年下半年系统架构设计师案例分析真题，按原卷选答规则练习，使用自由计时。
```

[Lab 使用说明](docs/soft-exam-lab.md) · [题库整理说明](docs/soft-exam-bank-ingest.md)

### 论文写作与批改

支持审题、通用提纲、逐段陪写和完整改稿；逐项核对题目要求、技术机制、本人行动、结果与前后一致性。局部材料只评价已见部分；真实经历与授权模拟分别标注。

[写作方法](skills/soft-exam-architect-prep/references/paper-writing.md) · [批改与训练评分](skills/soft-exam-architect-prep/references/paper-scoring.md) · [校准样例](skills/soft-exam-architect-prep/references/paper-calibration.md)

## 版本记录

`v1.0.0` 将工具与学习资料分开发行，补齐系统架构设计师材料分类及视觉复习册，重整文档入口。Skill 交互与安装行为沿用已有版本；本版主要变更为资料整理与发布。

- [v1.0.0 工具发布说明](docs/releases/v1.0.0.md)
- [materials-v1.0.0 资料发布说明](docs/releases/materials-v1.0.0.md)
- [完整更新日志](docs/CHANGELOG.md)
- [资料处理与验证](docs/data-preparation.md)

## 来源与协作

代码、Skill 和本项目原创说明使用 MIT；教材、试题、课程材料、品牌与角色素材保留各自权利归属，MIT 不另行授予这些第三方内容的权利。书目信息、题源与已知缺漏保留在分类说明和正文中，详见 [NOTICE](NOTICE.md)。

欢迎通过 [Issue](https://github.com/Goodyzhang/ruankao.skill/issues) 提交勘误，或通过 Pull Request 补充可公开资料。贡献时注明来源、考试年份与版本，区分原题、改编题和自编题，并排除个人答卷及项目材料。
