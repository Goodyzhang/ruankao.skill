---
tags: [软考, 系统架构设计师-高级, 案例分析, 敏捷, Scrum, MVC, SSH, 学员回忆版]
chapter: "13-层次式架构设计理论与实践"
case_id: legacy-13-scrum-ssh
verification: pending-identity
identity: "高级下午案例分析 试题五（25分，10+6+9）；**学员回忆版，具体年份未提供**——不冒填"
---

# Scrum 项目管理系统：状态图 / MVC 归类 / SSH 分层（高级下午试题五，学员回忆版，25 分）

## 题干（原题抄写）

> 【说明】Scrum 是增量的、迭代的敏捷软件开发过程。某软件公司计划开发基于 Web 的 Scrum 项目管理系统，支持项目团队管理、敏捷开发过程管理和工件管理。Scrum 团队由 Scrum 主管、产品负责人和开发团队三种角色组成，开发过程由若干 Sprint（2~4 周迭代周期）组成。Product Backlog 是按商业价值排序的需求列表（条目形式为用户故事）；每个 Sprint 从 Product Backlog 挑选最高优先级用户故事，在 Sprint 计划会议上细化分解为任务、初步估算每个任务的预计完成时间，编写 Sprint Backlog。Sprint 期间每天早晨举行每日站立会议，重新估算剩余任务预计完成时间，更新 Sprint Backlog、Sprint 燃尽图和 Release 燃尽图。Sprint 结束时召开评审会议和回顾会议，交付产品增量；若 Product Backlog 还有未完成用户故事，则筹备下一个 Sprint。系统采用 MVC 架构模式、轻量级 J2EE 架构和 SSH 框架开发，MySQL 作为底层存储。
>
> 问题 1（10 分）：完成 Scrum 敏捷开发状态图 (1)~(5)。
> 问题 2（6 分）：从备选 a~n 选出属于 MVC 中 Model/View/Controller 的内容——a Sprint燃尽图、b Project、c Product Backlog、d 用户故事、e 估算任务预计完成时间、f Release燃尽图、g Sprint回顾会议、h 用户、i 交付产品增量、j 新建项目、k Task、l Sprint、m 产品负责人、n Sprint Backlog。
> 问题 3（9 分）：将备选 a~l 填入系统架构图 (1)~(9)——a Struts2、b Hibernate持久层、c 数据库服务(MySQL)、d SiteMesh、e 业务逻辑层、f jQuery、g 模型层、h 控制层、i EJB、j Web层、k 视图层、l PostgreSQL。

## 图

**缺图**：状态图与系统架构图原图未附——问题 1、3 的填空以文字转写结构保存。列入待补清单。

## 考场答案与采分要点

**问题 1**：(1) Product Backlog　(2) Sprint 计划会议　(3) 每日站立会议　(4) 还有未完成的用户故事　(5) 交付产品增量。

**问题 2**：Model = b、c、d、h、k、l、m、n；View = a、f；Controller = e、j（g 回顾会议、i 交付产品增量为干扰项）。

**问题 3**：(1) d　(2) f（1、2 可互换）　(3) h　(4) e　(5) a　(6) k　(7) j　(8) b　(9) c。

## 解析与易错点

- **问题 1**：状态图方框填状态/产物、箭头填事件：需求→Product Backlog→Sprint 计划会议（选故事、分解 Task、写 Sprint Backlog）→Sprint 中每日站立会议（迭代未结束自循环）→评审会议后按“是否还有未完成用户故事”分流，无剩则交付产品增量。
- **问题 2 MVC 归类判别**：名词（数据/工件/角色）→Model；纯展示（燃尽图）→View；动词操作（新建、估算）→Controller；活动/事件（回顾会议、交付增量）三类不归。
- **问题 3**：SSH = Struts2（Web 控制层）+ Spring（业务逻辑层）+ Hibernate（持久层 ORM）；视图层界面框架 = SiteMesh + jQuery；“轻量级”排除 EJB；数据库照题干选 MySQL。
- 干扰项辨析：g 模型层在分层链路中无对应框；i EJB 是重量级框架，与题干“轻量级 J2EE”冲突；l PostgreSQL 与题干"MySQL"冲突。

## 知识点链接

- [MVC 三组件职责与归类判别](https://github.com/Goodyzhang/ruankao.skill/blob/main/materials/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E5%B8%88/%E7%AC%94%E8%AE%B0/%E7%9F%A5%E8%AF%86%E7%82%B9/13-%E5%B1%82%E6%AC%A1%E5%BC%8F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E7%90%86%E8%AE%BA%E4%B8%8E%E5%AE%9E%E8%B7%B5.md)
- [Scrum 流程与工件](https://github.com/Goodyzhang/ruankao.skill/blob/main/materials/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E5%B8%88/%E7%AC%94%E8%AE%B0/%E7%9F%A5%E8%AF%86%E7%82%B9/05-%E8%BD%AF%E4%BB%B6%E5%B7%A5%E7%A8%8B%E5%9F%BA%E7%A1%80%E7%9F%A5%E8%AF%86.md)

## 核验状态与来源

- 核验状态：`pending`（**学员回忆版**——年份未提供；缺状态图与架构图原图）。
- 实验室可用性：**不可导出**——学员回忆版身份 + 缺图。
