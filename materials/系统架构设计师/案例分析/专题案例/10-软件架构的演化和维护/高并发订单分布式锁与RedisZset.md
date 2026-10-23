---
tags: [软考, 系统架构设计师-高级, 案例分析, 分布式锁, Redis, 高并发, web-bank]
chapter: "10-软件架构的演化和维护"
case_id: legacy-10-distributed-lock
verification: pending-identity
identity: "软考达人题库章节练习第十章第六节题目 20–22；原始考试年份／题源未提供——不冒填"
---

# 高并发订单、分布式锁与 Redis Zset（题库第六节题目 20–22，9+10+6＝25 分）

## 题干（原题抄写）

> **说明**：某公司计划打造一个集商品展示、在线下单、支付结算及物流配送为一体的综合性电商平台。平台面向广大消费者，提供丰富商品选择和便捷购物体验。电商业务中，高并发访问和数据处理是关键挑战；在订单处理环节，多个用户同时下单或支付时，系统需确保订单状态准确一致。架构师提出采用分布式架构和高效数据库系统应对高并发，并引入分布式锁保障订单状态正确更新，防止数据冲突。此外，项目还将优化页面加载速度和交互设计，通过精准营销和个性化推荐推动业务发展。
>
> **问题 1（9 分）**：多个服务实例可能同时更新同一订单状态。请分别写出基于数据库和基于 Redis 的分布式锁方案的优点和缺陷。
>
> **问题 2（10 分）**：基于 Redis 的分布式锁也会存在死锁场景，举例说明。还有哪些其它的分布式锁类型？
>
> **问题 3（6 分）**：Redis Zset 常见的命令有哪些？

## 考场答案与采分要点

**问题 1**：
- **数据库锁**：优点是实现简单、无需额外依赖、适用范围较广，锁记录可以持久保存。缺点（按题库答案）是数据库可能成为单点；没有失效时间时异常会遗留锁记录；抢锁插入失败直接报错，未获得锁的线程需要重新尝试；通常不支持重入。
- **Redis 锁**：题库答案给出的优点是性能好、容错性好；缺点是锁持有者崩溃且锁无过期机制时可能遗留锁，造成死锁。

**问题 2**：
- **死锁示例**：进程 A 先持有资源 R1 的锁，再等待 B 持有的 R2；进程 B 先持有 R2，再等待 A 持有的 R1。双方形成循环等待。根因是多个资源的加锁顺序不一致。
- **其它分布式锁类型**：基于 ZooKeeper 的分布式锁、基于 etcd 的分布式锁。

**问题 3（Zset 常见命令）**：`ZADD` 添加 member 与 score；`ZRANGE` 按分数升序返回范围；`ZREVRANGE` 按分数降序返回范围；`ZCARD` 获取元素数；`ZCOUNT` 统计分数区间内元素数；`ZRANK`／`ZREVRANK` 查询升序／降序名次；`ZSCORE` 查询 member 的分数。

## 解析与工程边界

- 数据库锁可用带唯一约束的锁记录或事务行锁实现；数据库高可用部署、等待/退避重试、租约过期与持有者校验可分别缓解单点、非阻塞和锁遗留问题。题库列出的缺陷是常见简化实现的风险。
- Redis 常见安全获取方式是 `SET lock_key unique_token NX PX lease_ms`；释放时必须先比对 token 再删除，避免旧持有者误删新锁。长任务需续租或用 fencing token。
- “Redis 容错性好”不应无条件理解为所有故障切换下都保证互斥。
- 题库解析中的 `ZRANG` 是命令拼写错误，应为 `ZRANGE`；新版本还可用 `ZRANGE ... REV` 表示逆序范围。

## 参考资料（原条目）

- [Redis 官方分布式锁模式](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)；[Redis `SET` 命令](https://redis.io/docs/latest/commands/set/)；[Apache ZooKeeper 锁配方](https://zookeeper.apache.org/doc/r3.8.4/recipes.html)；[etcd 创建分布式锁](https://etcd.io/docs/v3.6/tasks/developer/how-to-create-locks/)；[Redis `ZRANGE` 官方文档](https://redis.io/docs/latest/commands/zrange/)。

## 知识点链接

- [服务集群中的分布式锁与并发一致性](https://github.com/Goodyzhang/ruankao.skill/blob/main/materials/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E5%B8%88/%E7%AC%94%E8%AE%B0/%E7%9F%A5%E8%AF%86%E7%82%B9/10-%E8%BD%AF%E4%BB%B6%E6%9E%B6%E6%9E%84%E7%9A%84%E6%BC%94%E5%8C%96%E5%92%8C%E7%BB%B4%E6%8A%A4.md)

## 核验状态与来源

- 核验状态：`pending`（web-bank，年份未提供）。
- 实验室可用性：**暂不可导出**——web-bank 身份未核实。
