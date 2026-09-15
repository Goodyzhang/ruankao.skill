# Bridge 桥接模式 Grill 专项指引

本文件是 Grill 通用出题流程的一个领域示例。进入任何 Grill 时先执行 [grill-question-design.md](grill-question-design.md)；本文件只提供 Bridge 的术语、真题锚点和易混模式素材。

## 适用信号

题目出现 Bridge、Abstraction、Implementor、Shape、Drawing、两棵继承树、菱形聚合、抽象与实现独立变化等信号时使用本指引。

## 先定位，再出题

先把当前题归为以下一个主考点：

| 主考点 | 识别信号 | 当前截图中的结论 |
|---|---|---|
| 定义与特点 | 抽象与实现分离、独立变化、两维度扩展 | Bridge 的核心定义 |
| UML 角色映射 | Abstraction、Implementor、类图、菱形聚合 | Shape = Abstraction；Drawing = Implementor |
| 模式辨析 | Bridge 与 Adapter、Decorator、Strategy 等比较 | 用户将实现侧 Drawing 误作抽象侧 Shape |

当前截图的错因应记录为：**角色树混淆**。Shape 位于菱形端，代表 Abstraction；Drawing 位于菱形箭头指向端，代表 Implementor；Rectangle/Circle 是 RefinedAbstraction；V1Drawing/V2Drawing 是 ConcreteImplementor。

## 真题检索是 Grill 前置条件

进入第一张练习卡前，必须在本地真题库读取至少一条相近真题。可先从以下已核验锚点开始：

| 用途 | 真题锚点 | 可用于哪一轮 |
|---|---|---|
| 定义与模式辨析 | [[个人资料/笔记/软考/软件设计师-中级/真题库/上午题/2015-下半年-上午#Q45|2015 下半年软件设计师上午 Q45]] | Bridge、Adapter、Composite、Decorator 的选项辨析 |
| UML 角色映射 | [[个人资料/笔记/软考/系统架构设计师-高级/真题库/上午题/2015-下半年-上午#Q32|2015 下半年系统架构设计师上午 Q32]] | Shape / Drawing / Rectangle / V2Drawing 的角色定位 |
| 代码与聚合关系 | [[个人资料/笔记/软考/软件设计师-中级/真题库/下午题/2024-下半年-下午#试题三|2024 下半年软件设计师下午试题三]] | Implementor 接口、调用方向和 Image 与 Implementor 的聚合关系 |

向用户讲解或开始 Grill 前，用一行说明已命中的真题，例如“相近真题：2015 下半年系统架构设计师上午 Q32（Bridge 角色映射）”。不要把未核验的回忆题称为真题。

若上述锚点不可读，使用关键词 Bridge、桥接模式、Abstraction、Implementor、Shape、Drawing 在真题库检索。仍找不到时明确说明本地真题缺口，生成题只能标为变式题。

## 选择题式 Grill 配方

### G1：先纠正当前错因

优先复用原题角色选项。当前运行时支持 4 项时保留原始 A/B/C/D；只支持 3 项时使用 Shape、Drawing、Rectangle。

> UML 图中，哪个类对应 Bridge 的 Abstraction？

- A. Shape
- B. Drawing
- C. Rectangle
- D. V2Drawing

正确项：A。B 是 Implementor，C 是 RefinedAbstraction，D 是 ConcreteImplementor。

### G2：用真题巩固定义

以 2015 下半年软件设计师上午 Q45 的考法出题：

> 下列哪种模式用于将抽象部分与实现部分分离，使两者独立变化？

- A. Bridge
- B. Adapter
- C. Composite
- D. Decorator

正确项：A。此题应在用户点完 G1 后作为定义巩固或变式使用。

### G3：用易混模式做干扰项

> 某系统希望“图形种类”和“绘图实现”分别扩展、任意组合，最合适的模式是？

- A. Bridge：两棵独立继承树，通过聚合连接
- B. Adapter：把已有不兼容接口转换为目标接口
- C. Decorator：在同一 Component 继承树上动态附加职责

正确项：A。

## 干扰项生成规则

| 易混模式 | 干扰项应表达的特征 | 与 Bridge 的边界 |
|---|---|---|
| Adapter | 接口不兼容后的转换 | Adapter 解决兼容；Bridge 在设计时分离两个变化维度 |
| Decorator | 动态增加职责、包装同一 Component | Decorator 是同一组件树的递归包装；Bridge 是两棵独立树的组合 |
| Strategy | Context 持有可替换算法 | Strategy 替换算法族；Bridge 分离抽象层与实现层 |
| Abstract Factory | 创建一族相关对象 | Abstract Factory 解决创建；Bridge 解决结构与扩展维度 |

干扰项必须只错在一个真实的模式边界，不能使用与设计模式无关的选项。

## 收尾判定

用户先选对 G1 的角色映射，再选对 G2 或 G3 的定义/模式辨析，即可收尾。若 G1 选错，先反馈“菱形端 = Abstraction，箭头指向端 = Implementor”，再出同一角色边界的下一张选择题；不要改成填写式追问。
