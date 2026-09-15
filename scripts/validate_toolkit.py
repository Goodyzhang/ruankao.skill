#!/usr/bin/env python3
"""Validate packaging, links and empty study-record templates (standard library)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / 'vault'
errors = []
skills = sorted((ROOT / 'skills').glob('*/SKILL.md'))
if len(skills) != 5:
    errors.append('Expected five Skills')

def visible_lines(text):
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            char = marker[1][0]
            fence = None if fence == char else char if fence is None else fence
            continue
        if fence is None:
            yield line


for p in skills:
    text = p.read_text()
    if not text.startswith('---\n') or not re.search(r'^name: ' + re.escape(p.parent.name) + r'\s*$', text, re.M):
        errors.append(f'{p.relative_to(ROOT)}: invalid Skill name/frontmatter')
    if not re.search(r'^description:\s*\S', text, re.M):
        errors.append(f'{p.relative_to(ROOT)}: missing description')

for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts or 'dist' in p.parts:
        continue
    if p.suffix not in {'.md', '.yaml', '.py'}:
        continue
    text = p.read_text()
    # Match concrete device paths and credential shapes, not the regex examples here.
    if re.search(r'(?:/Users/|C:\\Users\\)[A-Za-z0-9_-]+[/\\]', text):
        errors.append(f'{p.relative_to(ROOT)}: device path')
    if re.search(r'\b(?:ghp_|gho_|sk-)[A-Za-z0-9]{20,}\b', text):
        errors.append(f'{p.relative_to(ROOT)}: possible credential')
    if p.suffix != '.md':
        continue
    for line in visible_lines(text):
        for target in re.findall(r'(?<!!)\[[^\]]+\]\((<?[^)]+>?)\)', line):
            target = target.strip('<>').split('#', 1)[0]
            if not target or re.match(r'\w+://', target):
                continue
            if not (p.parent / target).exists():
                errors.append(f'{p.relative_to(ROOT)}: missing Markdown link {target}')
        if VAULT in p.parents:
            for dest in re.findall(r'\[\[([^\]]+)\]\]', line):
                target = dest.split('|', 1)[0]
                name, _, anchor = target.partition('#')
                q = VAULT / (name.removesuffix('.md') + '.md') if name else p
                if not q.is_file():
                    errors.append(f'{p.relative_to(ROOT)}: missing Wiki-link {name}')
                elif anchor and not any(re.sub(r'^#+\s*', '', h).strip() == anchor for h in q.read_text().splitlines() if h.startswith('#')):
                    errors.append(f'{p.relative_to(ROOT)}: missing anchor {anchor}')

for level, count in [('系统架构设计师-高级', 20), ('软件设计师-中级', 16)]:
    base = VAULT / '个人资料/笔记/软考' / level
    if len(list((base / '知识点').glob('*.md'))) != count:
        errors.append(f'{level}: unexpected chapter count')
advanced = VAULT / '个人资料/笔记/软考/系统架构设计师-高级'
books = list((advanced / '错题本').glob('*.md'))
if len(books) != 20:
    errors.append('Expected 20 empty advanced notebooks')
books.append(VAULT / '个人资料/笔记/软考/软件设计师-中级/软考-软设-错题本.md')
for p in books:
    text = p.read_text()
    if re.search(r'^###\s|\*\*(?:我的选项|原题抄写|正确选项)', text, re.M):
        errors.append(f'{p.relative_to(ROOT)}: populated mistake record')
    if len(text) > 1500:
        errors.append(f'{p.relative_to(ROOT)}: unexpectedly large notebook')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: {len(skills)} Skills, {len(list(VAULT.rglob("*.md")))} seed notes, 21 empty notebooks; links and package checks passed.')
