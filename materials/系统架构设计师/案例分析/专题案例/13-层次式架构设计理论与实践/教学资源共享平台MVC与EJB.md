---
tags: [软考, 系统架构设计师-高级, 案例分析, MVC, EJB, JavaEE, web-bank]
chapter: "13-层次式架构设计理论与实践"
case_id: legacy-13-mvc-ejb
verification: pending-identity
identity: "软考达人章节练习题目274（9+6+10=25分）；未核实年份——不冒填"
---

# 教学资源共享平台的 MVC 与 EJB（题目 274，9+6+10＝25 分）

## 题干与材料摘要

平台提供统一身份、资源申报与展示、元模型及综合管理，以 Java EE MVC 组织架构。三问分别为 MVC 构件定位、EJB 历史类型及职责、会话状态分类。

- **MVC 架构截图（原图截图）**：![274-MVC架构-截图](../../assets/a1859e2642468662.png)

## 小问与答案

**问题 1：MVC 与构件定位**
- 网站答案整理：（1）JSP；（2）Servlet；（3）Service；（4）JavaBean；（5）DAO。
- 分析：视图呈现信息并承接交互，控制器接收请求和协调处理，模型承载业务数据与行为。在题设 Java EE 分层中，JSP 对应呈现，Servlet 对应控制，Service 组织业务，JavaBean 承载相关对象数据，DAO 封装数据访问。MVC 三种职责不等于只能存在三个类；模型内部可以继续分层。不要将数据库访问逻辑写进视图职责。编号依据网站答案，架构原图尚未完整归档。

**问题 2：EJB 的三类 Bean**
- 网站历史口径：Session Bean 承担会话业务；Entity Bean 表达持久业务数据；Message-Driven Bean 异步接收处理消息。
- 理解方法：按“业务调用、持久数据、异步消息”区分。这是题设所采用的历史分类，不将 Entity Bean 的旧式描述当成所有现代 Java 企业应用的实现要求。

**问题 3：有状态与无状态构件**
- 网站答案整理：有状态为身份认证 a、资源发布 b、在线编辑 d；无状态为资源检索 c、统计分析 e。
- 分析：前三者需保持某个客户连续交互的上下文；后两者可依据本次输入独立完成。判别点是跨调用是否在该构件中保存客户专属会话状态。并非读取数据库就有状态，也非业务名称含“查询”就必然无状态。实际可将状态移到其他存储，但本题没有给出这种替代设计。

## 知识点链接

- [表现层框架设计（MVC）](https://github.com/Goodyzhang/ruankao.skill/blob/main/materials/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E5%B8%88/%E7%AC%94%E8%AE%B0/%E7%9F%A5%E8%AF%86%E7%82%B9/13-%E5%B1%82%E6%AC%A1%E5%BC%8F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E7%90%86%E8%AE%BA%E4%B8%8E%E5%AE%9E%E8%B7%B5.md)
- [中间层架构设计（业务逻辑层）](https://github.com/Goodyzhang/ruankao.skill/blob/main/materials/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E5%B8%88/%E7%AC%94%E8%AE%B0/%E7%9F%A5%E8%AF%86%E7%82%B9/13-%E5%B1%82%E6%AC%A1%E5%BC%8F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E7%90%86%E8%AE%BA%E4%B8%8E%E5%AE%9E%E8%B7%B5.md)

## 核验状态与来源

- 核验状态：`pending`（web-bank，未核实年份）；MVC 五个空位已与网站答案对照（补图记录）。
- 实验室可用性：**暂不可导出**——web-bank 身份未核实。
