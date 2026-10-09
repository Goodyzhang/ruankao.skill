# 框架与方法来源

核查日期：2026-10-04。吸收交互和评价方法，不复制第三方题库、文章和未经许可代码。

- [TAO 考试导航](https://userguide.taotesting.com/user-documentation/latest/public/test-navigation-for-test-takers)：题号、计时、未答标记、交卷确认。
- [Excalidraw 集成](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/integration) 与 [导出](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export)：保存editable scene，exportToBlob生成对应PNG，基本图形替代过早设计UML语义编辑器。
- [react-markdown](https://github.com/remarkjs/react-markdown)、[remark-math / rehype-katex](https://github.com/remarkjs/remark-math)、[KaTeX](https://katex.org/docs/api.html)：保留原文位置的 Markdown 语法树、词句批注和本地公式渲染，不开放答案 HTML 执行。
- [SteLLA](https://arxiv.org/abs/2501.09092)：按rubric拆成可验证采分点，用学生实际证据判定后加权。本功能不复现论文实验或宣称达到论文准确度；当前Agent初评和自检，不伪称双代理复核。
- [清华出版社指定试题解析书](https://www.tup.com.cn/booksCenter/book_10321101.html)：考试研究部编写的2018–2022试题分析书是优先取材线索，网页元数据不等于已经核验某题答案。无统一公开附加扣分规则时本功能定义训练规则，并与参考估分分开。

维护者在 assets/frontend 执行 npm ci、npm run build，依赖固定在 package-lock.json；发布只需dist、源码/构建记录和许可证，不带node_modules。使用者的页面不下载远程运行时。图表直接由逐点结构化结果生成；本版不引入抽象工厂或模型API服务层。
