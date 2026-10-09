#!/usr/bin/env python3
"""Validate packaging, links and empty study-record templates (standard library)."""
from pathlib import Path
import importlib.util
import json
import re
from urllib.parse import unquote

EXPECTED_SKILLS = {
    'soft-exam-question-tutor', 'soft-exam-organizer', 'soft-exam-prep',
    'soft-exam-architect-organizer', 'soft-exam-architect-prep', 'soft-exam-review-book', 'soft-exam-lab', 'soft-exam-bank-ingest',
}


def validate(ROOT):
    VAULT = ROOT / 'vault'
    HARNESS = ROOT / 'integrations' / 'antigravity-harness'
    errors = []
    skills = sorted((ROOT / 'skills').glob('*/SKILL.md'))
    names = {path.parent.name for path in skills}
    if names != EXPECTED_SKILLS:
        errors.append(f'Skill set mismatch: missing={sorted(EXPECTED_SKILLS - names)}, extra={sorted(names - EXPECTED_SKILLS)}')
    for name in EXPECTED_SKILLS:
        required = ['SKILL.md']
        if name in {'soft-exam-question-tutor', 'soft-exam-review-book', 'soft-exam-lab', 'soft-exam-bank-ingest'}:
            required.append('agents/openai.yaml')
        if name == 'soft-exam-review-book':
            required += [f'references/{stem}.md' for stem in (
                'environment', 'sources', 'teaching', 'collaboration', 'visuals', 'reader', 'relay')]
            required += [f'assets/reader/{item}' for item in (
                'index.html', 'section.html', 'reader.css', 'reader.js', 'quiz-state.js', 'figure-placeholder.svg')]
            required += ['assets/characters/whale-reference.png', 'scripts/check_book.py']
        if name == 'soft-exam-bank-ingest':
            required += ['scripts/bank.py'] + ['references/' + n + '.md' for n in ('browser', 'teaching', 'essay', 'records', 'validation')]
            metadata = ROOT / 'skills' / name / 'agents/openai.yaml'
            if metadata.is_file() and 'allow_implicit_invocation: false' not in metadata.read_text(encoding='utf-8'):
                errors.append('Bank ingest must require explicit invocation')
        if name == 'soft-exam-lab':
            required += ['scripts/lab.py', 'assets/frontend/dist/lab.js', 'assets/frontend/dist/lab.css', 'references/grading.md', 'references/runtime.md', 'references/paper-rules.md']
            metadata = ROOT / 'skills' / name / 'agents/openai.yaml'
            if metadata.is_file() and 'allow_implicit_invocation: false' not in metadata.read_text(encoding='utf-8'):
                errors.append('Lab must require explicit invocation')
        if name == 'soft-exam-question-tutor':
            required += ['references/first-use.md', 'references/runtime-interaction.md', 'references/knowledge-base-contract.md']
        for item in required:
            path = ROOT / 'skills' / name / item
            if not path.is_file() or not path.stat().st_size:
                errors.append(f'Missing or empty Skill resource: {name}/{item}')

    harness_paths = [
        HARNESS / 'README.md',
        HARNESS / 'hooks.json',
        HARNESS / 'install_harness.py',
        HARNESS / 'rules' / 'soft-exam-suspension.md',
        HARNESS / 'scripts' / 'harness_common.py',
        HARNESS / 'scripts' / 'harness_pre_invocation.py',
        HARNESS / 'scripts' / 'harness_stop_guard.py',
        HARNESS / 'scripts' / 'harness_tool_guard.py',
    ]
    for path in harness_paths:
        if not path.is_file():
            errors.append(f'Missing Harness file: {path.relative_to(ROOT)}')
    try:
        harness_hooks = json.loads((HARNESS / 'hooks.json').read_text(encoding='utf-8'))
        for name in ('soft-exam-tool-guard', 'soft-exam-stop-guard', 'soft-exam-pre-invocation'):
            if name not in harness_hooks:
                errors.append(f'Missing Harness hook: {name}')
    except (OSError, json.JSONDecodeError):
        errors.append('Invalid Harness hooks.json')
    for path in (HARNESS / 'scripts').glob('*.py'):
        try:
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        except SyntaxError:
            errors.append(f'Invalid Harness Python: {path.relative_to(ROOT)}')

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
        text = p.read_text(encoding='utf-8')
        if not text.startswith('---\n') or not re.search(r'^name: ' + re.escape(p.parent.name) + r'\s*$', text, re.M):
            errors.append(f'{p.relative_to(ROOT)}: invalid Skill name/frontmatter')
        if not re.search(r'^description:\s*\S', text, re.M):
            errors.append(f'{p.relative_to(ROOT)}: missing description')

    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts or 'dist' in p.parts or 'node_modules' in p.parts:
            continue
        if p.name == '.soft-exam.local.json':
            errors.append(f'{p.relative_to(ROOT)}: machine-local binding must not be published')
        if p.suffix not in {'.md', '.yaml', '.yml', '.py', '.json', '.html', '.css', '.js', '.cjs', '.svg', '.ps1', '.sh', '.txt'}:
            continue
        text = p.read_text(encoding='utf-8')
        # Match concrete device paths and credential shapes, not the regex examples here.
        if re.search(r'(?:/Users/|/home/|[A-Za-z]:\\Users\\)[A-Za-z0-9_-]+[/\\]', text):
            errors.append(f'{p.relative_to(ROOT)}: device path')
        if re.search(r'\b(?:ghp_|gho_|sk-)[A-Za-z0-9]{20,}\b', text):
            errors.append(f'{p.relative_to(ROOT)}: possible credential')
        if p.suffix != '.md':
            continue
        for line in visible_lines(text):
            for target in re.findall(r'!?\[[^\]]*\]\((<?[^)]+>?)\)', line):
                target = target.strip('<>').split('#', 1)[0]
                if not target or re.match(r'\w+://', target):
                    continue
                if not (p.parent / unquote(target)).exists():
                    errors.append(f'{p.relative_to(ROOT)}: missing Markdown link {target}')
            if VAULT in p.parents:
                for dest in re.findall(r'\[\[([^\]]+)\]\]', line):
                    target = dest.split('|', 1)[0]
                    name, _, anchor = target.partition('#')
                    q = VAULT / (name.removesuffix('.md') + '.md') if name else p
                    if not q.is_file():
                        errors.append(f'{p.relative_to(ROOT)}: missing Wiki-link {name}')
                    elif anchor and not any(re.sub(r'^#+\s*', '', h).strip() == anchor for h in q.read_text(encoding='utf-8').splitlines() if h.startswith('#')):
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
        if not p.is_file():
            errors.append(f'Missing notebook: {p.relative_to(ROOT)}')
            continue
        text = p.read_text(encoding='utf-8')
        if re.search(r'^###\s|\*\*(?:我的选项|原题抄写|正确选项)', text, re.M):
            errors.append(f'{p.relative_to(ROOT)}: populated mistake record')
        if len(text) > 1500:
            errors.append(f'{p.relative_to(ROOT)}: unexpectedly large notebook')
    # Reuse the shipped checker: templates and public demo must resolve offline assets.
    checker = ROOT / 'skills/soft-exam-review-book/scripts/check_book.py'
    if checker.is_file():
        spec = importlib.util.spec_from_file_location('review_book_checker', checker)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for folder, templates in ((ROOT / 'skills/soft-exam-review-book/assets/reader', True), (ROOT / 'docs/demo', False)):
            pages = sorted(folder.rglob('*.html'))
            if not pages:
                errors.append(f'Missing HTML pages: {folder.relative_to(ROOT)}')
                continue
            if templates:
                html_errors, _ = module.check(pages, allow_template=True)
            else:
                # The accepted SMTP sample predates the reusable quiz schema.
                # Validate its dependencies without rewriting IDs/storage keys.
                html_errors = check_public_pages(module, pages, folder)
            errors.extend(html_errors)
    return errors



def check_public_pages(reader, paths, folder):
    """Check portable HTML dependencies; legacy quiz UI is tested separately."""
    pages = {path.resolve(): reader.Page(path.resolve()) for path in paths}
    errors = []
    root = folder.resolve()
    def fail(path, text):
        errors.append(str(path) + ': ' + text)
    for path, page in pages.items():
        for issue in page.errors:
            fail(path, issue)
        for value in page.resources + page.links:
            target, url = reader.local_target(page, value)
            resource = value in page.resources
            if target is None:
                if resource and url.scheme != 'data':
                    fail(path, 'external runtime resource: ' + value)
                elif url.scheme in ('javascript', 'file'):
                    fail(path, 'nonportable link: ' + value)
                continue
            if url.path.startswith('/') or (target != root and root not in target.parents):
                fail(path, 'resource/link escapes the offline demo: ' + value)
            elif not target.is_file():
                fail(path, 'missing local resource/link: ' + value)
            elif url.fragment and target.suffix.lower() == '.html':
                destination = pages.get(target) or reader.Page(target)
                if unquote(url.fragment) not in destination.ids:
                    fail(path, 'missing HTML anchor: ' + value)
        text = path.read_text(encoding='utf-8')
        if re.search(r'\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\s*\(|\bimport\s*\(', text):
            fail(path, 'dynamic/network load needs review')
    for path in root.rglob('*'):
        if path.suffix not in ('.css', '.svg', '.js', '.html') or not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        if path.suffix == '.svg' and re.search(r'(?:href|src)=["\'](?:https?:)?//', text):
            fail(path, 'SVG has an external dependency')
        if path.suffix in ('.css', '.html'):
            if re.search(r'@import\b', text):
                fail(path, 'CSS import needs explicit local dependencies')
            for value in re.findall(r'url\(\s*["\']?([^)"\']+)', text):
                if value.startswith('data:'):
                    continue
                target = (path.parent / unquote(value)).resolve()
                if re.match(r'\w+:|//|/', value) or root not in target.parents or not target.is_file():
                    fail(path, 'CSS resource is not available offline: ' + value)
        if path.suffix == '.js' and re.search(r'\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\s*\(|\bimport\s*\(', text):
            fail(path, 'dynamic/network load needs review')
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(EXPECTED_SKILLS)} named Skills and resources, {len(list((root / "vault").rglob("*.md")))} seed notes, '
          '21 empty notebooks; Markdown links, privacy scan, reader templates and demo offline assets passed.')


if __name__ == '__main__':
    main()
