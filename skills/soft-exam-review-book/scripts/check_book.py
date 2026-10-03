#!/usr/bin/env python3
"""Check local reader files and quiz contracts; never create or rewrite content."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids, self.links, self.resources, self.questions = set(), [], [], []
        self.errors, self.body, self.question = [], {}, None
        self.names = set()
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body":
            self.body = a
        if a.get("id"):
            if a["id"] in self.ids:
                self.errors.append("重复 HTML id: " + a["id"])
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if "data-zoom" in a:
                self.resources.append(a["href"])
        if tag in ("img", "script", "audio", "video", "source", "iframe") and a.get("src"):
            self.resources.append(a["src"])
        if tag == "link" and a.get("href"):
            self.resources.append(a["href"])
        if tag == "img" and "alt" not in a:
            self.errors.append("图片缺少 alt: " + a.get("src", ""))
        if tag == "script" and a.get("type") == "module":
            self.errors.append("离线骨架不使用 module 脚本")
        if tag == "fieldset" and "data-question-id" in a:
            self.question = {"attrs": a, "options": [], "names": set(), "hooks": set()}
            self.questions.append(self.question)
        if self.question:
            self.question["hooks"].update(a)
            if tag == "input" and a.get("type") == "radio":
                self.question["options"].append(a.get("value"))
                self.question["names"].add(a.get("name"))
        if a.get("srcset"):
            if re.search(r"(?:https?:)?//", a["srcset"]):
                self.errors.append("srcset 含外部资源")
            elif not a["srcset"].startswith("data:"):
                self.resources.extend(part.strip().split()[0] for part in a["srcset"].split(",") if part.strip())

    def handle_endtag(self, tag):
        if tag == "fieldset":
            self.question = None


def local_target(page, value):
    url = urlsplit(value)
    if url.scheme or url.netloc:
        return None, url
    path = page.path.parent / unquote(url.path) if url.path else page.path
    return path.resolve(), url


def check(paths, allow_template=False):
    pages = {path.resolve(): Page(path.resolve()) for path in paths}
    errors = []
    namespaces = {}
    checked_code = set()
    for path, page in pages.items():
        def fail(message):
            errors.append(str(path) + ": " + message)
        for message in page.errors:
            fail(message)
        if page.body.get("data-template") == "true" and not allow_template:
            fail("仍标记为模板；正式内容完成后移除 data-template 和模板提示")
        for value in page.resources:
            target, url = local_target(page, value)
            if url.path.startswith("/") and target is not None:
                fail("资源使用绝对路径，无法随书册搬移: " + value)
            if target is None:
                if url.scheme != "data":
                    fail("外部或非相对资源: " + value)
            elif not target.is_file():
                fail("缺失资源: " + value)
            elif target.suffix in (".js", ".css"):
                checked_code.add(target)
            elif target.suffix == ".svg":
                svg = target.read_text(encoding="utf-8")
                if re.search(r'(?:href|src)=["\'](?:https?:)?//', svg):
                    fail("SVG 含外部资源: " + value)
        for value in page.links:
            target, url = local_target(page, value)
            if target is None:
                if url.scheme == "javascript":
                    fail("不使用 javascript: 链接")
                continue  # External source citations are allowed.
            if not target.is_file():
                fail("失效本地链接: " + value)
            elif url.fragment and target.suffix.lower() == ".html":
                destination = pages.get(target) or Page(target)
                if unquote(url.fragment) not in destination.ids:
                    fail("不存在的锚点: " + value)
        if page.questions:
            ns = tuple(page.body.get("data-" + key, "") for key in ("book-id", "chapter-id", "section-id"))
            if not all(ns):
                fail("自测缺少 book/chapter/section ID")
            elif ns in namespaces:
                fail("进度命名空间与另一页重复: " + str(namespaces[ns]))
            else:
                namespaces[ns] = path
            ids, names = set(), set()
            for q in page.questions:
                a, options = q["attrs"], q["options"]
                qid = a.get("data-question-id", "")
                if not qid or qid in ids:
                    fail("空或重复的题目 ID: " + qid)
                ids.add(qid)
                if not a.get("data-question-version"):
                    fail("题目缺少版本: " + qid)
                if len(options) < 2 or None in options or "" in options or len(set(options)) != len(options) or a.get("data-answer") not in options:
                    fail("题目选项/答案无效: " + qid)
                if len(q["names"]) != 1 or not all(q["names"]) or names.intersection(q["names"]):
                    fail("radio name 必须每题独立: " + qid)
                names.update(q["names"])
                required = {"data-prompt", "data-explanation", "data-feedback", "data-result", "data-retry-question"}
                if not required.issubset(q["hooks"]):
                    fail("题目缺少界面标记: " + qid)
        text = path.read_text(encoding="utf-8")
        if not allow_template and re.search(r"〔[^〕]*(?:占位|待填写|待配置|示范题)[^〕]*〕|figure-placeholder\.svg", text):
            fail("仍含模板占位内容或占位图片")
        if re.search(r"\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\s*\(|\bimport\s*\(", text):
            fail("发现网络/动态加载调用；请人工检查")
    for path in checked_code:
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\s*\(|\bimport\s*\(", text):
            errors.append(str(path) + ": 发现网络/动态加载调用")
        if path.suffix == ".css":
            for value in re.findall(r"url\(\s*['\"]?([^)'\"]+)", text):
                if value.startswith("data:"):
                    continue
                if urlsplit(value).scheme or value.startswith("/") or not (path.parent / unquote(value)).is_file():
                    errors.append(str(path) + ": CSS 资源不可离线读取: " + value)
            if re.search(r"@import\b", text):
                errors.append(str(path) + ": CSS @import 需移除并改用明确的本地样式引用")
    return errors, len(pages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--allow-template", action="store_true", help="仅检查模板骨架时允许占位标记")
    args = parser.parse_args()
    files = set()
    for path in args.paths:
        if path.is_dir():
            files.update(p for p in path.rglob("*.html") if not any(part.startswith(".") or part in ("制作", "证据") for part in p.relative_to(path).parts))
        elif path.is_file():
            files.add(path)
        else:
            parser.error("路径不存在: " + str(path))
    if not files:
        parser.error("没有 HTML 文件")
    errors, count = check(sorted(files), args.allow_template)
    for error in errors:
        print("FAIL", error)
    print(f"{'FAIL' if errors else 'PASS'}: {count} 页，{len(errors)} 个结构问题。此检查不验证知识事实、图像含义或浏览器交互。")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
