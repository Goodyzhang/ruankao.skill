# 运行与交接

从当前完整 Skill 定位脚本，不硬编码用户名。以下占位参数由 Agent 用当前路径替换并正确引用；公开安装包会携带 dist，使用者不运行 npm。

```sh
python3 scripts/lab.py prepare --root '<已确认档案根>' --pack '<题包JSON>' --rubric '<私有评分表JSON>' --source-root '<原图目录>' --count 1 --true-question
python3 scripts/lab.py serve --session '<prepare返回场次>'
python3 scripts/lab.py status --session '<场次>'
python3 scripts/lab.py grade --session '<场次>' --file '<Agent评阅JSON>'
python3 scripts/lab.py finalize --session '<场次>' --file '<回读归档凭据JSON>'
```

`prepare` 默认复用 active；显式新开才 `--new`。专题组卷 `--count 3`。限时添加 `--mode timed --minutes 已确认数值`，自由计时默认。第一次点“开始作答”开始计时；自由模式可暂停；限时后台到点冻结最近成功落盘的答案，前端同步尝试保存最新输入。断网/未落盘的输入只能在客户端恢复，不承诺后台读到它们。

serve 打印随机本机端口，Agent 应保存实际进程会话标识。优先当前 Agent 内建浏览器打开该 URL；失败给同一超链接。不要绑定公网、用未知服务PID结束别人的服务，或把题库作为静态根目录。服务公开白名单 index/offline/report/static/figures，不公开私有 JSON。POST 校验本场凭据、Origin、Host、身份、revision，避免旧页面串答。请求超限或磁盘失败只显示失败，保留输入。

页面提供全小问导航，正文纯文本输入及本地 Markdown/KaTeX/DOMPurify 预览。作答区常驻正文撤销按钮，每个小问最多记录20次编辑；暂停或没有记录时禁用，刷新后从新的编辑开始记录。浏览器未保存稿只在打开页面时读取为恢复候选，正常输入不重复显示恢复提示。Excalidraw 提供基本图形、箭头、文字、分组、撤销、缩放；题图可设底图，PNG/JPEG/WebP 可上传或粘贴。自动保存、手动保存与交卷串行。交卷确认提示空白，但允许提交。图稿与同一份导出 PNG 一并冻结；保存失败不冻结。

发真正的追问卡：“已提交 / 继续作答 / 结束并保留草稿”。点已提交后 **先运行 status、回读 submission.json**；draft 不能批。卡片不在工具集或工具调用失败就使用文字确认，并记录限制。停止练习保留草稿，关闭自己启动的服务；下次用相同场次重启，不换身份。

## 离线兜底

无可用Python时，Agent依照数据契约手工准备本场private题包/评分表、初始state及public目录；复制预构建dist为static，生成与脚本html相同的JSON嵌入页面并设置offline:true。不把答案嵌进去。可由另一可用本地环境先 prepare 再拷贝完整公开目录。file:打开 offline.html 不依赖 fetch；草稿仅localStorage。题图设底图若file:禁止读取时使用上传相同原图，不谎称直接读盘。

交卷会导出提交JSON，用户将导出的实际文件路径提供给Agent；若Python恢复可用执行 `import-answer --session ... --file ...`，没有Python时按同样身份/版本/小问集合/附件/提交状态核验并原子保存，交接记录明确未经运行器验证。离线答卷计时不冒充服务端计时。没有拿到实际文件，仍停在交接。

提交后 page 只读。服务重启会从文件恢复，无需旧进程；不绕过浏览器访问审批。评分后同服务可看 /report.html，离线 public/report.html 持续可读。finalize 成功会清除 active，并由服务监测到 archived 后关闭。

## 修改评分表

事实错误经核验后：`revise-rubric --session ... --file ... --reason ...`。保存旧表和理由；原答卷不动，新评阅绑定新hash，旧HTML/JSON保留。不要向用户暗中修改标准。
