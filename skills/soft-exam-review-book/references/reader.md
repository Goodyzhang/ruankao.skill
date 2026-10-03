# 离线阅读界面

本包 `skill_root/assets/reader/` 是可复制的静态界面骨架，`skill_root` 指当前权威 SKILL.md 所在目录。路径不相对 Vault 或终端 cwd 推断。正文、图注、速查条目、题目与关联说明由作者逐节创作。代码只提供阅读和自测交互，不从笔记批量抽取或生成知识内容。

## 文件与落地方式

| 文件 | 用途 |
|---|---|
| `index.html` | 章节入口，列出已完成小节及正文、速查、自测链接 |
| `section.html` | 独立小节模板；复制后按小节重命名 |
| `reader.css` | 纸色、蓝色目录、连续正文、移动端与打印样式 |
| `reader.js` | 三种阅读方式、hash 定位、图片放大和自测界面 |
| `quiz-state.js` | 按书册、章节、小节隔离的答题状态 |
| `figure-placeholder.svg` | 明确标识的模板占位；不计入正式图像验收 |

最简单的使用方式是把整个 `assets/reader/` 目录的内容复制到新章节目录，保留一个 `index.html`，将 `section.html` 复制为各小节独立页面。CSS、JS 与页面同目录即可直接打开，不需要服务器、构建、CDN、`fetch` 或 ES module。

若章节已有公共素材目录，可把 CSS／JS 放到例如 `assets/reader/`，手动调整 HTML 中的一个样式引用和两个脚本引用。脚本顺序为 `quiz-state.js`、`reader.js`，均使用普通 `defer`。图片和链接也用相对于当前 HTML 的路径。保持已验收样章原文件不动。

正式页面须替换全部占位内容、删除 `data-template="true"` 与模板提示，并替换占位图。骨架的单张占位图不代表小节的图像配额；素材数量、内容与审核按创作契约另行验收。

## 页面接口

每个含自测的小节在 `body` 上填写三个稳定 ID：

```html
<body data-book-id="architect-v2" data-chapter-id="02"
      data-section-id="02-05-cabling">
```

同一小节修订正文时保持这些 ID。不把文章版本、修改日期或文件哈希拼入 ID。不同小节必须用不同 `data-section-id`；不同教材体系或不兼容版本用不同 `data-book-id`。

保留模板中的三组 `[data-panel]`、tab 的 `aria-controls` 和对应 ID：`article`、`quick`、`quiz`。正文内部可以自由添加语义锚点，例如 `id="horizontal-cabling"`。访问该锚点会先显示其所在面板，再打开祖先折叠区并定位；浏览器前进、后退沿原生 hash 历史工作。

侧栏用原生 `details` 组织“章→节→知识点”层级；在手机上仍保留可折叠目录。跨页导航使用普通链接，如 `02-05-cabling.html#quick`。不要用 JavaScript 拼出猜测的文件名。不存在的后续小节写为普通文字，不伪造可点击链接。

## 图文与放大图

保留连续正文，图放在刚解释的关系或过程后面。每张图配完整 `alt` 和简短结论式图注。Mermaid 应先真实渲染为本地 SVG，并保留 `.mmd` 源码；页面直接引用 SVG。

```html
<figure>
  <a class="figure-link" data-zoom href="assets/cabling-map.png"
     aria-label="放大综合布线结构图">
    <img src="assets/cabling-map.png" width="1536" height="1024"
         alt="按建筑内外的位置标出各布线子系统及连接关系">
  </a>
  <figcaption>这里写读者应从图中辨认出的关系。</figcaption>
</figure>
```

放大图提供关闭、Escape 关闭、适合窗口／原尺寸切换，并把键盘焦点送回原图。没有 JavaScript 或对话框能力时，图像仍是普通可打开的链接。图片尺寸属性应填写真实宽高，避免滚动和锚点位置跳动。

## 自测与进度契约

每个题目使用模板中的 `fieldset` 结构。须具备 `data-question-id`、`data-question-version`、`data-answer`，以及 `data-prompt`、`data-feedback`、`data-result`、`data-explanation`、`data-retry-question` 元素。每题 radio 的 `name` 独立，选项 `value` 使用稳定的字符串 ID；正确答案填写对应 `value`。

```html
<fieldset class="question" data-question-id="subsystem-boundary"
          data-question-version="1" data-answer="horizontal">
  <!-- 按 section.html 中的完整结构填入题干、选项、解释和重做按钮。 -->
</fieldset>
```

题目增删或重排不重新编号已有稳定 ID。题干、选项内容、正确答案或题图有实质变化时，提升该题 `data-question-version`。正文、图注、解析润色或排版调整不修改题目版本；选项 ID 与文字不变、仅调整排列顺序时，也不修改题目版本。

保存键为 `ruankao-review:v1:<book>:<chapter>:<section>`，各部分经过 URL 编码。存储记录按题目 ID 保存版本、内容签名和选择项。不同小节可使用相同题目 ID，进度互不覆盖。

恢复时逐题比较，只有仍匹配的记录生效。文本签名覆盖题干、按稳定 `value` 排序后的选项文字，以及正确答案；忘记提升版本时，这些内容变化也只使对应题失效。解析不参与签名；纯空白排版变化与同 ID 选项的排列变化不影响签名。题图文件内容无法仅凭路径识别，所以改题图仍须手动提升该题版本。此签名不是知识正确性检测。

“重做此题”仅清除当前题，“重做本节”仅清除当前小节。无需服务器或账号。存储读取损坏、被禁用、空间不足或写入失败时，页面保留当前会话内的作答，并明确说明刷新可能丢失；不显示虚假的保存成功。

本地文件的存储行为取决于浏览器。清理数据、切换浏览器或设备、移动文件路径都可能使原进度不可用。界面不承诺跨设备同步，也不依赖跨文件共享存储。原 SMTP／POP3 样章使用的旧保存格式不自动迁移。

## 定向检查

结构检查只读取文件：

使用当前环境已有的 Python 3，传入由 `skill_root` 解析出的 `scripts/check_book.py` 绝对路径，以及实际章节目录。不要假设技能装在 Vault 的 `.claude/` 下。参数形式为 `Python 3 解释器 + 检查器绝对路径 + 章节目录绝对路径`；用参数数组或平台正确的引用方式处理空格。没有 Python 时，用现有文件/网页工具做对应的静态检查并标明未运行检查器，不自动安装环境。

检查模板自身时追加 `--allow-template`；正式材料不加。目录扫描忽略“制作”“证据”和隐藏子目录。检查范围包括本地素材与链接、跨页锚点、重复 HTML ID、模板残留、明显网络加载、题目结构、独立 radio 分组及进度命名空间。外部来源的普通引用链接可以保留；运行所需资源必须本地化。

该脚本不能证明知识准确、图像正确或浏览器交互可用。若浏览器环境允许，实际检查：三种阅读方式；深层 hash 直接进入和前进／后退；目录跨页；图片放大与 Escape；作答后刷新；分别重做单题和本节；手机宽度下阅读。环境拒绝访问或没有可用 UI 时，记录未验证项，不另找路径绕过拒绝。

本次实现验证（2026-10-03）：模板两页结构检查通过；两个 JavaScript 文件语法检查通过；10 个 Node 纯状态测试通过，覆盖正文无耦合、解析润色与选项重排保留进度、题干／选项内容／答案变化逐题失效、小节隔离、存储拒绝、损坏记录和单题重做。检查器定向夹具覆盖失效文件／锚点、远程放大图和模板残留。未进行本轮真实浏览器 UI 验收，不能把以上结果描述为已实测浏览器交互。
