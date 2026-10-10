#!/usr/bin/env python3
"""Local case laboratory. Python 3.9+, standard library only; no semantic grading."""
import argparse
import base64
import hashlib
from itertools import combinations
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

SKILL = Path(__file__).resolve().parents[1]
ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$')
MAX_BODY = 24 * 1024 * 1024


class LabError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise LabError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic(path, value, serialize=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=str(path.parent), prefix='.save-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            if serialize:
                json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            else:
                f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def safe_file(root, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and '..' not in relative.parts, '资源路径越界')
    path = root / relative
    require(all(not (root / Path(*relative.parts[:i])).is_symlink()
                for i in range(1, len(relative.parts) + 1)), '资源不能是符号链接')
    require(path.is_file(), '资源不存在: ' + str(relative))
    return path


def questions(pack, selected=None):
    return {q['id']: q for c in pack['cases'] if selected is None or c['id'] in selected for q in c['questions']}


def essay_markdown(parts):
    return '## 摘要\n\n' + parts['abstract'] + '\n\n## 正文\n\n' + parts['body']


def selection(pack, selected=None, complete=True):
    ids = [c['id'] for c in pack['cases']]
    exam = pack.get('exam')
    if not exam:
        require(selected is None or set(selected) == set(ids), '专题练习包含全部题目')
        return ids
    required = exam['required_case_ids']
    selected = required if selected is None else selected
    require(isinstance(selected, list) and len(selected) == len(set(selected))
            and set(selected) <= set(ids) and set(required) <= set(selected), '选答题重复、无效或缺少必答题')
    chosen = len(selected) - len(required)
    require(exam.get('selection_policy') == 'answered-lowest-numbered'
            or chosen <= exam['choose_count'] and (not complete or chosen == exam['choose_count']), '请按试卷要求选齐计分题目')
    return list(selected)


def grading_cases(pack, submission):
    """Separate counted answers from additional answers under the paper's rule."""
    exam = pack.get('exam', {})
    if exam.get('selection_policy') != 'answered-lowest-numbered':
        return selection(pack, submission.get('selected_case_ids')), []
    required = exam['required_case_ids']
    answered = []
    for case in sorted(pack['cases'], key=lambda c: c['source']['case_number']):
        if case['id'] in required:
            continue
        for question in case['questions']:
            answer = submission['answers'][question['id']]
            scene = answer.get('scene')
            drawing = (any(not e.get('isDeleted') and e.get('customData', {}).get('labSource') != 'question-background'
                           for e in scene.get('elements', [])) if scene else bool(answer.get('drawing_png')))
            if answer['markdown'].strip() or answer.get('attachments') or drawing:
                answered.append(case['id'])
                break
    return required + answered[:exam['choose_count']], answered[exam['choose_count']:]


def report_payload(pack, submission, result):
    reassessment = result.get('exam_reassessment')
    if reassessment:
        pack = dict(pack, title=reassessment['title'], exam=reassessment['exam'])
    return {'mode': 'report', 'pack': pack, 'state': submission, 'grade': result}


def validate_exam(pack, rubric):
    exam = pack.get('exam')
    if not exam:
        return
    require(set(exam) <= {'kind', 'instructions', 'required_case_ids', 'choose_count', 'max_score',
                         'pass_score', 'rules_source', 'pass_source', 'duration_minutes', 'essay_limits', 'selection_policy'}, '未知试卷规则字段')
    require(exam.get('kind') in ('case-analysis', 'essay') and exam.get('instructions')
            and exam.get('rules_source') and exam.get('pass_source'), '缺少试卷类型、作答要求或标准出处')
    ids = {c['id'] for c in pack['cases']}
    required = exam.get('required_case_ids')
    count = exam.get('choose_count')
    require(isinstance(required, list) and len(required) == len(set(required)) and set(required) <= ids,
            '必答题配置无效')
    require(isinstance(count, int) and 0 <= count <= len(ids) - len(required) and len(required) + count > 0,
            '选答数量无效')
    require(isinstance(exam.get('max_score'), (int, float)) and exam['max_score'] > 0
            and isinstance(exam.get('pass_score'), (int, float)) and 0 < exam['pass_score'] <= exam['max_score'], '满分或合格线无效')
    require(exam['max_score'] == 75, '系统架构设计师正式试卷满分为75分；全题训练应使用练习模式')
    require(exam.get('selection_policy') in (None, 'answered-lowest-numbered'), '未知超选计分规则')
    if exam.get('selection_policy'):
        numbers = [c['source'].get('case_number') for c in pack['cases']]
        require(exam['kind'] == 'case-analysis' and all(type(n) is int and n > 0 for n in numbers)
                and len(set(numbers)) == len(numbers), '自动计分须有已核实且不重复的案例题号')
    scores = {c['id']: c['max_score'] for c in pack['cases']}
    for chosen in combinations(ids - set(required), count):
        require(abs(sum(scores[i] for i in required + list(chosen)) - exam['max_score']) < 1e-6,
                '选答组合的分值与试卷满分不一致')
    if exam['kind'] == 'essay':
        require(not required and count == 1 and all(len(c['questions']) == 1 for c in pack['cases']), '论文卷每个论题为一篇，选答一篇')
        limits = exam.get('essay_limits', {})
        require(set(limits) == {'abstract_min', 'abstract_max', 'body_min', 'body_max'}
                and all(isinstance(v, int) and v >= 0 for v in limits.values())
                and limits['abstract_min'] <= limits['abstract_max'] and limits['body_min'] <= limits['body_max'], '须按原卷填写摘要和正文字数要求')
        requirements = rubric.get('essay_requirements', {})
        require(set(requirements) == set(questions(pack)), '每个论题须提供原卷审题要求与采分点映射')
        pointmap = {p['id']: p for p in rubric['points']}
        for qid, tasks in requirements.items():
            require(tasks and len({t['id'] for t in tasks}) == len(tasks), '论文审题要求缺失或重复')
            for task in tasks:
                require(task.get('text') and task.get('source') and task.get('point_ids')
                        and all(pid in pointmap and pointmap[pid]['question_id'] == qid for pid in task['point_ids']),
                        '论文审题要求未对应本题的冻结采分点')


def validate_pack(pack, rubric, source_root, require_true=False, count=None):
    require(set(pack) <= {'schema_version','id','version','title','scoring_notice','cases','exam'}, '公开题包含未知字段，可能泄露解析')
    require(pack.get('schema_version') == 1 and rubric.get('schema_version') == 1, '数据版本必须为 1')
    require(ID.fullmatch(pack.get('id', '')) and pack.get('version'), '题目包身份缺失')
    cases = pack.get('cases', [])
    require(cases and (count is None or len(cases) == count), '题数不足或数量不匹配')
    seen, qids = set(), set()
    for case in cases:
        require(set(case) <= {'id','title','stem','complete','max_score','source','figures','questions'}, '大题含非公开字段')
        require(ID.fullmatch(case.get('id', '')) and case['id'] not in seen, '大题身份重复或无效')
        seen.add(case['id'])
        source = case.get('source', {})
        require(set(source) <= {'kind','locator','label','identity_verified','year','case_number','identity_evidence'}, '公开来源含未知字段')
        require(source.get('kind') in ('original', 'recollection', 'adapted', 'authored', 'web-bank'), '题源类型缺失')
        require(source.get('locator') and source.get('label'), '题源定位缺失')
        if require_true or source['kind'] in ('original', 'recollection'):
            require(source['kind'] in ('original', 'recollection') and source.get('identity_verified') is True,
                    '真题年份、题号与身份尚未核验')
            require(source.get('year') and source.get('case_number') and source.get('identity_evidence'), '真题身份依据缺失')
        require(case.get('stem') and case.get('complete') is True and not re.search('待补充|待补图|TODO', case['stem']), '题干未完整核验')
        require(case.get('questions'), '缺少全部小问')
        for q in case['questions']:
            require(set(q) <= {'id','title','prompt','complete','max_score'}, '小问含非公开字段')
            require(ID.fullmatch(q.get('id', '')) and q['id'] not in qids, '小问身份重复或无效')
            qids.add(q['id'])
            require(q.get('prompt') and q.get('complete') is True and not re.search('待补充|TODO', q['prompt']), '小问不完整')
            require(isinstance(q.get('max_score'), (int, float)) and q['max_score'] > 0, '小问分值无效')
        require(abs(sum(q['max_score'] for q in case['questions']) - case.get('max_score', -1)) < 1e-6, '大题分值不一致')
        for fig in case.get('figures', []):
            require(set(fig) <= {'file','caption','source_locator'}, '题图含非公开字段')
            require(fig.get('caption') and fig.get('source_locator'), '题图缺少说明或原件页码')
            safe_file(source_root, fig['file'])
    require(rubric.get('pack_id') == pack['id'] and rubric.get('pack_version') == pack['version'], '评分表与题目包版本不匹配')
    require(rubric.get('version') and rubric.get('basis') in ('published', 'inferred-training'), '评分表身份或口径缺失')
    require(rubric.get('answer_source', {}).get('reliable') is True and rubric['answer_source'].get('locator') and rubric['answer_source'].get('level'), '缺少可靠参考解析或出处级别')
    require(rubric.get('training_policy') == 'unit-weight-deduplicated-v1', '必须冻结训练扣分口径')
    points = rubric.get('points', [])
    require(points, '评分表无采分点')
    pids = set()
    for p in points:
        require(ID.fullmatch(p.get('id', '')) and p['id'] not in pids, '采分点身份重复')
        pids.add(p['id'])
        require(p.get('question_id') in qids and p.get('weight', 0) > 0, '采分点小问或分值无效')
        require(p.get('criterion') and p.get('conditions') and p.get('equivalents') is not None
                and p.get('correct') and p.get('dimension') and p.get('source'), '采分点边界或来源不完整')
    for qid, q in questions(pack).items():
        require(abs(sum(p['weight'] for p in points if p['question_id'] == qid) - q['max_score']) < 1e-6,
                '采分点总分与小问不一致: ' + qid)
    validate_exam(pack, rubric)


def html(path, payload):
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028')
    atomic(path, '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>软考作答实验室</title><link rel="stylesheet" href="static/lab.css"></head><body><div id="root"></div><script>window.EXCALIDRAW_ASSET_PATH="./static/";</script><script id="lab-data" type="application/json">''' + data + '''</script><script src="static/lab.js"></script></body></html>''', serialize=False)


def prepare(root, pack_path, rubric_path, source_root=None, new=False, mode='free', minutes=None, require_true=False, count=None, paper_kind=None):
    root = Path(root).resolve()
    require(not root.is_symlink(), '档案根不能为符号链接')
    root.mkdir(parents=True, exist_ok=True)
    pointer = root / 'active.json'
    requested = read(pack_path) if paper_kind else None
    if paper_kind:
        require(requested.get('exam', {}).get('kind') == paper_kind, '年度真题须提供正式试卷选答、总分和合格线规则')
    if pointer.exists() and not new:
        current = root / read(pointer)['attempt_id']
        if read(current / 'state.json')['status'] != 'archived':
            if paper_kind:
                existing = read(current / 'pack.json')
                require(existing.get('exam', {}).get('kind') == paper_kind and existing['id'] == requested['id']
                        and existing['version'] == requested['version'], '已有场次与所请求的正式试卷不一致；请保留原稿后选择续接或新开')
            return current
    pack, rubric = read(pack_path), read(rubric_path)
    source_root = Path(source_root or Path(pack_path).parent).resolve()
    validate_pack(pack, rubric, source_root, require_true, count)
    require(mode in ('free', 'timed') and (mode != 'timed' or isinstance(minutes, (int, float)) and minutes > 0), '限时模式须确认正数时长')
    aid = 'lab-' + time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(4)
    session = root / aid
    session.mkdir()
    try:
        public = session / 'public'
        public.mkdir()
        shutil.copytree(SKILL / 'assets/frontend/dist', public / 'static')
        for case in pack['cases']:
            for fig in case.get('figures', []):
                src = safe_file(source_root, fig['file'])
                require(src.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.svg'), '题图格式不支持')
                name = digest({'case': case['id'], 'file': fig['file']})[:16] + src.suffix.lower()
                (public / 'figures').mkdir(exist_ok=True)
                shutil.copyfile(src, public / 'figures' / name)
                fig['file'] = 'figures/' + name
        atomic(session / 'pack.json', pack)
        atomic(session / 'rubric-v1.json', rubric)
        state = {'schema_version': 1, 'attempt_id': aid, 'status': 'draft', 'revision': 0,
                 'pack_hash': digest(pack), 'rubric_hash': digest(rubric), 'rubric_file': 'rubric-v1.json',
                 'mode': mode, 'duration_seconds': minutes * 60 if mode == 'timed' else None,
                 'created_at': time.time(), 'started_at': None, 'pause_started': None,
                 'paused_seconds': 0, 'answers': {q: {'markdown': '', 'scene': None, 'drawing_png': None, 'attachments': []}
                                               for q in questions(pack)}}
        state['selected_case_ids'] = selection(pack, complete=False)
        if pack.get('exam', {}).get('kind') == 'essay':
            for answer in state['answers'].values():
                answer['essay'] = {'abstract': '', 'body': ''}
                answer['markdown'] = essay_markdown(answer['essay'])
        atomic(session / 'state.json', state)
        html(public / 'index.html', {'mode': 'exam', 'offline': False, 'pack': pack, 'state': state})
        html(public / 'offline.html', {'mode': 'exam', 'offline': True, 'pack': pack, 'state': state})
        atomic(pointer, {'attempt_id': aid})
        return session
    except Exception:
        shutil.rmtree(session)
        raise


def image_data(value):
    require(isinstance(value, str) and re.match(r'^data:image/(?:png|jpeg|webp);base64,', value), '图片只接受 PNG/JPEG/WebP')
    try:
        raw = base64.b64decode(value.split(',', 1)[1], validate=True)
    except (ValueError, TypeError):
        raise LabError('图片编码无效')
    require(len(raw) <= 8 * 1024 * 1024 and (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8') or raw.startswith(b'RIFF')), '图片内容无效或过大')


def validate_answers(answers, qids, essay=False):
    require(isinstance(answers, dict) and set(answers) == set(qids), '跨场次或小问集合不匹配')
    for a in answers.values():
        require(set(a) <= {'markdown', 'scene', 'drawing_png', 'attachments', 'essay'}, '未知作答字段')
        require(isinstance(a.get('markdown'), str) and len(a['markdown']) <= 40000, '正文过长或无效')
        if essay:
            parts = a.get('essay')
            require(isinstance(parts, dict) and set(parts) == {'abstract', 'body'}
                    and all(isinstance(v, str) for v in parts.values()) and a['markdown'] == essay_markdown(parts),
                    '论文摘要、正文与证据原文不一致')
        else:
            require('essay' not in a, '案例题不能提交论文结构')
        scene = a.get('scene')
        if scene:
            require(isinstance(scene, dict) and isinstance(scene.get('elements'), list), '图稿结构无效')
            for f in scene.get('files', {}).values():
                image_data(f['dataURL'])
            require(not any(not e.get('isDeleted') for e in scene['elements']) or a.get('drawing_png'), '有图稿必须保存同一份 PNG')
        if a.get('drawing_png'):
            image_data(a['drawing_png'])
        require(isinstance(a.get('attachments', []), list), '附件格式错误')
        for item in a.get('attachments', []):
            image_data(item['data'])
            require(isinstance(item.get('name'), str), '附件文件名无效')


class Session:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.lock = threading.RLock()
        self.pack = read(self.path / 'pack.json')
        self.token = secrets.token_urlsafe(24)

    def state(self):
        return read(self.path / 'state.json')

    def check_frozen(self, s):
        require(digest(self.pack) == s['pack_hash'], '题目包被修改')
        require(digest(read(self.path / s['rubric_file'])) == s['rubric_hash'], '评分表被修改')

    def update(self, action, body):
        with self.lock:
            s = self.state()
            require(body.get('attempt_id') == s['attempt_id'], '场次不匹配')
            if s['status'] != 'draft':
                if action == 'submit' and s['status'] in ('submitted', 'graded', 'archived'):
                    return s
                raise LabError('已提交答卷不可修改')
            require(body.get('revision') == s['revision'], '页面版本过期，请重新加载；本地输入仍可导出')
            self.check_frozen(s)
            now = time.time()
            selected = body.get('selected_case_ids', s.get('selected_case_ids'))
            s['selected_case_ids'] = selection(self.pack, selected, complete=action in ('start', 'submit') or s['started_at'] is not None)
            if 'answers' in body:
                validate_answers(body['answers'], questions(self.pack), self.pack.get('exam', {}).get('kind') == 'essay')
                s['answers'] = body['answers']
            if action == 'start' and s['started_at'] is None:
                s['started_at'] = now
            elif action == 'pause':
                require(s['mode'] == 'free' and s['started_at'] is not None, '限时模式不能暂停')
                if s['pause_started'] is None:
                    s['pause_started'] = now
                else:
                    s['paused_seconds'] += now - s['pause_started']
                    s['pause_started'] = None
            elif action not in ('save', 'submit', 'start'):
                raise LabError('未知动作')
            expired = s['mode'] == 'timed' and s['started_at'] and now >= s['started_at'] + s['duration_seconds']
            if action == 'submit' or expired:
                require(s['started_at'] is not None, '尚未开始作答')
                if s['pause_started'] is not None:
                    s['paused_seconds'] += now - s['pause_started']
                    s['pause_started'] = None
                s['selected_case_ids'], _ = grading_cases(self.pack, s)
                s['status'], s['submitted_at'] = 'submitted', now
                s['elapsed_seconds'] = max(0, now - s['started_at'] - s['paused_seconds'])
                s['submission_reason'] = 'deadline' if expired else body.get('reason', 'user')
                submission = dict(s)
                submission['revision'] += 1
                target = self.path / 'submission.json'
                # Recover an atomic submit whose state commit was interrupted.
                if target.exists():
                    frozen = read(target)
                    require(frozen['attempt_id'] == s['attempt_id'] and frozen['pack_hash'] == s['pack_hash'], '已有答卷身份异常')
                    state = dict(frozen, submission_hash=digest(frozen))
                    atomic(self.path / 'state.json', state)
                    return state
                atomic(target, submission)
                state = dict(submission, submission_hash=digest(submission))
                atomic(self.path / 'state.json', state)
                return state
            s['revision'] += 1
            s['saved_at'] = now
            atomic(self.path / 'state.json', s)
            return s

    def recover(self):
        with self.lock:
            s = self.state()
            if s['status'] == 'draft' and (self.path / 'submission.json').exists():
                frozen = read(self.path / 'submission.json')
                atomic(self.path / 'state.json', dict(frozen, submission_hash=digest(frozen)))
            if (self.path / 'submission.json').exists():
                require(digest(read(self.path / 'submission.json')) == self.state().get('submission_hash'), '冻结答卷被修改')
            self.check_frozen(self.state())

    def expire(self):
        with self.lock:
            s = self.state()
            if s['status'] == 'draft' and s['mode'] == 'timed' and s['started_at'] and time.time() >= s['started_at'] + s['duration_seconds']:
                self.update('submit', {'attempt_id': s['attempt_id'], 'revision': s['revision']})


def validate_text_evidence(evidence, answer):
    """Validate a source passage and optional precise highlight spans."""
    text = answer['markdown']
    start, end = evidence.get('start'), evidence.get('end')
    require(evidence.get('kind') == 'text' and isinstance(start, int) and isinstance(end, int)
            and 0 <= start < end <= len(text) and text[start:end] == evidence.get('quote'), '原文证据定位错误')
    if 'focus' in evidence:
        focus = evidence['focus']
        require(isinstance(focus, list) and focus, '批注高亮片段不能为空')
        for span in focus:
            a, b = span.get('start'), span.get('end')
            require(isinstance(a, int) and isinstance(b, int) and start <= a < b <= end
                    and text[a:b] == span.get('quote'), '批注高亮必须精确对应证据内的原文')


def grade(session, evaluation_path):
    """Validate Agent point decisions and calculate scores; never infer correctness."""
    engine = Session(session)
    engine.recover()
    s = engine.state()
    evaluation = read(evaluation_path)
    reassessment = evaluation.get('exam_reassessment', s.get('exam_reassessment'))
    require(s['status'] in ('submitted', 'graded') or s['status'] == 'archived' and reassessment, '未提交或需明确重评口径，禁止评分')
    sub = read(engine.path / 'submission.json')
    rubric = read(engine.path / s['rubric_file'])
    require(evaluation.get('schema_version') == 1 and evaluation.get('attempt_id') == s['attempt_id']
            and evaluation.get('submission_hash') == digest(sub) and evaluation.get('rubric_hash') == s['rubric_hash'], '评阅输入身份或版本不匹配')
    require(evaluation.get('reviewer') == 'current-agent' and evaluation.get('self_check'), '需记录当前代理自检结果')
    pack = engine.pack
    if reassessment:
        require(not pack.get('exam') and isinstance(reassessment, dict)
                and set(reassessment) == {'title', 'exam', 'request', 'reason'}
                and all(isinstance(reassessment[k], str) and reassessment[k].strip() for k in ('title','request','reason')),
                '旧练习转正式计分须记录用户请求、原因、报告标题及原卷规则')
        require(isinstance(reassessment['exam'], dict) and reassessment['exam'].get('selection_policy') == 'answered-lowest-numbered', '旧案例重评须按已作答题号自动计分')
        pack = dict(pack, title=reassessment['title'], exam=reassessment['exam'])
        validate_exam(pack, rubric)
    selected, supplemental = grading_cases(pack, sub)
    counted_questions = questions(pack, selected)
    reviewed_questions = questions(pack, selected + supplemental)
    decisions = evaluation.get('decisions', [])
    byid = {d['point_id']: d for d in decisions}
    points = {p['id']: p for p in rubric['points'] if p['question_id'] in reviewed_questions}
    require(len(byid) == len(decisions) and set(byid) == set(points), '采分点重复或未全部评阅')
    require('reference_answers' not in evaluation, '完整参考答案只能来自冻结评分表；请用 revise-rubric 修订后重新核对')
    references = rubric.get('reference_answers', {})
    require(set(reviewed_questions) <= set(references) <= set(questions(pack)), '请为每个评阅小问补齐完整参考答案')
    checks = evaluation.get('reference_checks', {})
    require(isinstance(checks, dict) and set(checks) == set(reviewed_questions), '须逐小问完成参考答案与评分表的一致性核对')
    for qid in reviewed_questions:
        ref = references[qid]
        require(ref.get('origin') in ('source', 'skill-generated', 'pending')
                and isinstance(ref.get('markdown'), str) and ref['markdown'].strip(), '参考答案须有完整正文、来源与生成方式')
        qpoints = {pid: p for pid, p in points.items() if p['question_id'] == qid}
        sources = ref.get('sources')
        require(isinstance(sources, list) and all(isinstance(v, str) and v.strip() for v in sources)
                and set(sources) == {p['source'] for p in qpoints.values()}, '参考答案须与本题采分点使用同一组已核实来源: ' + qid)
        check = checks[qid]
        checked = check.get('checked_point_ids', [])
        require(isinstance(checked, list) and len(checked) == len(qpoints) and set(checked) == set(qpoints)
                and isinstance(check.get('note'), str) and check['note'].strip(), '一致性核对须覆盖本题全部采分点并记录实际结论: ' + qid)
        require(check.get('status') == ('pending' if ref['origin'] == 'pending' else 'consistent'),
                '参考答案有未解决矛盾或核对结论不一致，禁止出报告: ' + qid)
        if ref['origin'] != 'pending':
            for pid, point in qpoints.items():
                require(point['correct'] in ref['markdown'], '采分点 correct 必须摘自同版完整参考答案，不能独立编写: ' + pid)
        for figure in ref.get('images', []):
            image_data(figure.get('data'))
            require(figure.get('caption'), '参考答案图示缺少说明')
        if ref['origin'] == 'pending':
            require(any(byid[pid].get('status') == 'pending' for pid, point in points.items() if point['question_id'] == qid), '参考答案待核验时该小问必须保留待核验状态')
        elif engine.pack.get('exam', {}).get('kind') == 'essay':
            parts = ref.get('essay')
            limits = engine.pack['exam']['essay_limits']
            require(isinstance(parts, dict) and set(parts) == {'abstract', 'body'}
                    and all(isinstance(v, str) and v.strip() for v in parts.values())
                    and ref['markdown'] == essay_markdown(parts), '论文须补齐摘要和正文，不能用写作建议替代参考范文')
            require(all(limits[name + '_min'] <= len(re.sub(r'\s', '', text)) <= limits[name + '_max'] for name, text in parts.items()), '参考范文字数应符合该试卷要求')
    references = {qid: dict(references[qid], source='；'.join(dict.fromkeys(references[qid]['sources']))) for qid in reviewed_questions}
    results, qresults, dimensions = [], {}, {}
    for pid, p in points.items():
        d, answer = byid[pid], sub['answers'][p['question_id']]
        require(set(d) <= {'point_id', 'status', 'comment', 'evidence', 'cause_id', 'pending_reason'}, '评阅不能覆盖冻结采分点字段')
        status = d.get('status')
        require(status in ('awarded', 'omitted', 'incorrect', 'pending') and d.get('comment'), '缺少判定或评语')
        evidence = d.get('evidence', [])
        require(status not in ('awarded', 'incorrect') or evidence, '给分/判错必须定位实际证据')
        for e in evidence:
            if e.get('kind') == 'text':
                validate_text_evidence(e, answer)
            elif e.get('kind') == 'diagram':
                elems = {v['id'] for v in (answer.get('scene') or {}).get('elements', []) if not v.get('isDeleted')}
                require(answer.get('drawing_png') and e.get('element_id') in elems and e.get('description') and not any(v.get('id') == e.get('element_id') and v.get('customData', {}).get('labSource') == 'question-background' for v in (answer.get('scene') or {}).get('elements', [])), '图示证据未对应已提交用户图稿')
            elif e.get('kind') == 'attachment':
                require(isinstance(e.get('index'), int) and 0 <= e['index'] < len(answer.get('attachments', [])) and e.get('description'), '附件证据无效')
            else:
                raise LabError('未知证据类型')
        require(status != 'pending' or d.get('pending_reason'), '待核验需说明缺口')
        item = dict(p, **d, earned=p['weight'] if status == 'awarded' else 0, counted=p['question_id'] in counted_questions)
        results.append(item)
        qr = qresults.setdefault(p['question_id'], {'reference_known': 0, 'penalty': 0, 'pending': False, 'pending_weight': 0, 'counts': {k: 0 for k in ('awarded', 'omitted', 'incorrect', 'pending')}})
        qr['reference_known'] += item['earned']
        qr['pending'] |= status == 'pending'
        qr['counts'][status] += 1
        qr['pending_weight'] += p['weight'] if status == 'pending' else 0
        if item['counted']:
            dim = dimensions.setdefault(p['dimension'], {'earned': 0, 'max': 0, 'pending': False, 'lost': 0, 'incorrect': 0, 'omitted': 0})
            dim['earned'] += item['earned']; dim['max'] += p['weight']; dim['pending'] |= status == 'pending'
            if status in ('omitted', 'incorrect'):
                dim['lost'] += p['weight']; dim[status] += 1
    reference_penalties, official_causes = [], set()
    rules = {r['id']: r for r in rubric.get('reference_deductions', [])}
    require(len(rules) == len(rubric.get('reference_deductions', [])), '原始扣分规则身份重复')
    for error in evaluation.get('reference_errors', []):
        rule = rules.get(error.get('rule_id'))
        require(rule and rule.get('source') and rule.get('question_id') in qresults and rule.get('amount', 0) > 0, '扣分未对应冻结来源细则')
        qid, cause, e = rule['question_id'], error.get('cause_id'), error.get('evidence', {})
        require(cause and error.get('comment'), '原始扣分原因缺失')
        a = sub['answers'][qid]
        validate_text_evidence(e, a)
        duplicate = (qid, cause) in official_causes
        already_lost = any(d.get('cause_id') == cause and points[d['point_id']]['question_id'] == qid and d['status'] == 'incorrect' for d in decisions)
        amount = 0 if duplicate or (already_lost and not rule.get('allow_overlap')) else rule['amount']
        official_causes.add((qid, cause))
        qresults[qid]['reference_known'] = max(0, qresults[qid]['reference_known'] - amount)
        reference_penalties.append(dict(error, question_id=qid, amount=amount, source=rule['source']))
    seen, penalties = set(), []
    for error in evaluation.get('extra_errors', []):
        qid, cause = error.get('question_id'), error.get('cause_id')
        require(qid in qresults and cause and error.get('comment') and error.get('evidence') and error.get('source'), '训练扣分缺少错误、证据或依据')
        # Reuse the same evidence validator via explicit text/image checks.
        a = sub['answers'][qid]
        e = error['evidence']
        if e.get('kind') == 'text':
            validate_text_evidence(e, a)
        else:
            require(e.get('kind') == 'diagram' and a.get('drawing_png') and e.get('element_id') in {x['id'] for x in (a.get('scene') or {}).get('elements', [])}, '训练扣分图示证据错误')
        related = error.get('point_id')
        require(related is None or related in points and points[related]['question_id'] == qid, '错误关联采分点不匹配')
        already_lost = any(d.get('cause_id') == cause and points[d['point_id']]['question_id'] == qid and d['status'] == 'incorrect' for d in decisions)
        duplicate = (qid, cause) in seen or (qid, cause) in official_causes or already_lost or (related and byid[related]['status'] == 'incorrect')
        seen.add((qid, cause))
        amount = 0 if duplicate else points[related]['weight'] if related else min(p['weight'] for p in points.values() if p['question_id'] == qid)
        qresults[qid]['penalty'] += amount
        penalties.append(dict(error, amount=amount, deduplicated=bool(duplicate)))
    for warning in evaluation.get('warnings', []):
        qid, related = warning.get('question_id'), warning.get('point_id')
        require(set(warning) <= {'question_id', 'point_id', 'comment', 'source', 'evidence'}
                and qid in qresults and warning.get('comment') and warning.get('source'), '风险提示须有计分小问、说明与依据，不得携带扣分')
        require(related is None or related in points and points[related]['question_id'] == qid, '风险提示关联采分点不匹配')
        validate_text_evidence(warning.get('evidence', {}), sub['answers'][qid])
    for qid, qr in qresults.items():
        qr['max'] = reviewed_questions[qid]['max_score']
        qr['counted'] = qid in counted_questions
        qr['reference'] = None if qr['pending'] else qr['reference_known']
        qr['training'] = None if qr['pending'] else max(0, qr['reference_known'] - qr['penalty'])
    pending = any(q['pending'] for q in qresults.values())
    counted_pending = any(q['pending'] for q in qresults.values() if q['counted'])
    exam = pack.get('exam')
    result = dict(evaluation, results=results, questions=qresults, dimensions=dimensions, penalties=penalties,
                  basis=rubric['basis'], answer_source=rubric['answer_source'], reference_penalties=reference_penalties, pending=pending,
                  reference_score=None if counted_pending else sum(q['reference'] for q in qresults.values() if q['counted']),
                  training_score=None if counted_pending else sum(q['training'] for q in qresults.values() if q['counted']),
                  max_score=exam['max_score'] if exam else sum(q['max'] for q in qresults.values()), elapsed_seconds=sub['elapsed_seconds'],
                  offline_elapsed_seconds=read(engine.path / 'offline-export.json').get('elapsed_seconds') if (engine.path / 'offline-export.json').exists() else None)
    result['selected_case_ids'] = selected
    result['supplemental_case_ids'] = supplemental
    result['reviewed_case_ids'] = selected + supplemental
    result['unanswered_score'] = result['max_score'] - sum(q['max'] for q in qresults.values() if q['counted'])
    if reassessment:
        result['exam_reassessment'] = reassessment
    result['reference_answers'] = references
    result['exam_outcome'] = None if not exam else {
        'status': 'pending' if counted_pending else 'pass' if result['reference_score'] >= exam['pass_score'] else 'fail',
        'pass_score': exam['pass_score'], 'max_score': exam['max_score'],
        'source': exam['pass_source'], 'basis': 'reference-estimate'}
    result['weaknesses'] = {
        'known_only': counted_pending,
        'questions': sorted(({'question_id': qid, 'lost': max(0, q['max'] - q['pending_weight'] - q['reference_known']),
                              'max_score': q['max'], 'incorrect': q['counts']['incorrect'], 'omitted': q['counts']['omitted']}
                             for qid, q in qresults.items() if q['counted']), key=lambda q: -q['lost']),
        'dimensions': sorted((dict(name=name, **value) for name, value in dimensions.items()), key=lambda d: -d['lost'])}
    if exam and exam['kind'] == 'essay':
        essay_review = {}
        for qid in counted_questions:
            parts = sub['answers'][qid]['essay']
            counts = {name: len(re.sub(r'\s', '', text)) for name, text in parts.items()}
            limits = exam['essay_limits']
            tasks = []
            for task in rubric['essay_requirements'][qid]:
                statuses = [byid[pid]['status'] for pid in task['point_ids']]
                status = 'pending' if 'pending' in statuses else 'met' if all(v == 'awarded' for v in statuses) else 'partial' if 'awarded' in statuses else 'not-met'
                tasks.append(dict(task, status=status))
            essay_review[qid] = {'counts': counts, 'limits': limits, 'requirements': tasks,
                                 'within_limits': {name: bool(parts[name].strip()) and limits[name + '_min'] <= counts[name] <= limits[name + '_max'] for name in parts}}
        result['essay_review'] = essay_review
    history = engine.path / 'reviews'; history.mkdir(exist_ok=True)
    rid = 'review-' + digest(result)[:16]
    shutil.copytree(SKILL / 'assets/frontend/dist', engine.path / 'public/static', dirs_exist_ok=True)
    atomic(history / (rid + '.json'), result)
    atomic(engine.path / 'grade.json', result)
    payload = report_payload(pack, sub, result)
    html(engine.path / 'public/report.html', payload)
    html(history / (rid + '.html'), payload)  # use sibling symlink-free local resources below
    shutil.copytree(engine.path / 'public/static', history / 'static', dirs_exist_ok=True)
    if (engine.path / 'public/figures').exists() and not (history / 'figures').exists():
        shutil.copytree(engine.path / 'public/figures', history / 'figures')
    s['status'] = 'submitted' if pending else 'graded'
    s['grade_id'] = rid
    if reassessment:
        s['exam_reassessment'] = reassessment
    atomic(engine.path / 'state.json', s)
    return result


def finalize(session, receipt_path):
    engine = Session(session)
    engine.recover()
    s = engine.state()
    require(s['status'] in ('graded', 'archived'), '仍有未完成评阅')
    result = read(engine.path / 'grade.json')
    require(result['submission_hash'] == s['submission_hash'] and result['rubric_hash'] == s['rubric_hash'] and s['grade_id'] == 'review-' + digest(result)[:16], '评阅与冻结答卷版本不一致')
    receipt = read(receipt_path)
    require(receipt.get('attempt_id') == s['attempt_id'] and receipt.get('grade_hash') == digest(result), '归档凭据版本不匹配')
    required = {p['id'] for p in result['results'] if p.get('counted', True) and p['status'] in ('omitted', 'incorrect')}
    required |= {'extra:' + p['cause_id'] for p in result['penalties'] if p['amount'] and result['questions'][p['question_id']].get('counted', True)}
    require(len(receipt.get('covered_points', [])) == len(set(receipt.get('covered_points', []))) and set(receipt.get('covered_points', [])) == required, '可靠失分点未全部归档或凭据重复')
    for f in receipt.get('files', []):
        path = Path(f['path'])
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == f['sha256'] and s['attempt_id'] in path.read_text(encoding='utf-8'), '归档未回读或哈希不一致')
    require(not required or receipt.get('files'), '失分点缺少归档文件')
    atomic(engine.path / 'archive-receipt.json', receipt)
    payload = report_payload(engine.pack, read(engine.path / 'submission.json'), result)
    html(engine.path / 'public/index.html', payload)
    html(engine.path / 'public/offline.html', payload)
    s['status'], s['archived_at'] = 'archived', time.time()
    atomic(engine.path / 'state.json', s)
    pointer = engine.path.parent / 'active.json'
    if pointer.exists() and read(pointer)['attempt_id'] == s['attempt_id']:
        pointer.unlink()
    return s


def serve(session, port=0):
    engine = Session(session); engine.recover()
    root = engine.path / 'public'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send(self, status, value):
            raw = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw))); self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(raw)
        def origin_ok(self):
            host = '127.0.0.1:' + str(self.server.server_port)
            return self.headers.get('Host') == host and self.headers.get('Origin', 'http://' + host) == 'http://' + host
        def do_GET(self):
            if not self.origin_ok():
                self.send(403, {'error': '不允许其它来源'}); return
            path = unquote(urlsplit(self.path).path)
            if path == '/api/state':
                self.send(200, engine.state()); return
            if path == '/':
                path = '/index.html'
            if path not in ('/index.html', '/offline.html', '/report.html') and not path.startswith(('/static/', '/figures/')):
                self.send(404, {'error': '没有此资源'}); return
            try:
                file = safe_file(root, path.lstrip('/'))
                raw = file.read_bytes()
                if file.name == 'index.html':
                    html(file, {'mode': 'exam', 'offline': False, 'token': engine.token, 'pack': engine.pack, 'state': engine.state()})
                    raw = file.read_bytes()
                self.send_response(200); self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(len(raw))); self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                if file.suffix.lower() == '.svg':
                    self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'")
                self.end_headers(); self.wfile.write(raw)
            except (OSError, LabError):
                self.send(404, {'error': '没有此资源'})
        def do_POST(self):
            try:
                require(self.origin_ok() and secrets.compare_digest(self.headers.get('X-Lab-Token', ''), engine.token), '请求凭据或来源错误')
                action = urlsplit(self.path).path.removeprefix('/api/')
                require(action in ('start', 'save', 'pause', 'submit'), '未知接口')
                size = int(self.headers.get('Content-Length', 0))
                require(0 < size <= MAX_BODY, '请求过大或为空')
                body = json.loads(self.rfile.read(size))
                self.send(200, engine.update(action, body))
            except (LabError, ValueError, KeyError) as e:
                self.send(409, {'error': str(e)})
            except OSError:
                self.send(500, {'error': '磁盘保存失败，答卷未提交；请保留并导出输入'})
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    atomic(engine.path / 'service.json', {'pid': os.getpid(), 'port': server.server_port, 'attempt_id': engine.state()['attempt_id']})
    print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port), 'attempt_id': engine.state()['attempt_id']}, ensure_ascii=False), flush=True)
    def deadlines():
        while not stop.wait(1):
            try:
                engine.expire()
                if engine.state()['status'] == 'archived':
                    server.shutdown(); return
            except (OSError, LabError):
                pass  # disk error retains last good draft; API surfaces actual save failure
    stop = threading.Event()
    threading.Thread(target=deadlines, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        stop.set(); server.server_close()
        (engine.path / 'service.json').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('prepare'); p.add_argument('--root', required=True); p.add_argument('--pack', required=True); p.add_argument('--rubric', required=True)
    p.add_argument('--source-root'); p.add_argument('--new', action='store_true'); p.add_argument('--true-question', action='store_true'); p.add_argument('--count', type=int)
    p.add_argument('--mode', choices=('free', 'timed'), default='free'); p.add_argument('--minutes', type=float)
    p.add_argument('--paper-kind', choices=('case-analysis', 'essay'))
    for name in ('serve', 'status', 'grade', 'finalize', 'import-answer', 'revise-rubric'):
        p = subs.add_parser(name); p.add_argument('--session', required=True)
        if name == 'serve': p.add_argument('--port', type=int, default=0)
        if name in ('grade', 'finalize', 'import-answer'): p.add_argument('--file', required=True)
        if name == 'revise-rubric': p.add_argument('--file', required=True); p.add_argument('--reason', required=True)
    a = parser.parse_args()
    try:
        if a.command == 'prepare':
            result = {'session': str(prepare(a.root, a.pack, a.rubric, a.source_root, a.new, a.mode, a.minutes, a.true_question, a.count, a.paper_kind))}
        elif a.command == 'serve': serve(a.session, a.port); return
        elif a.command == 'status':
            e = Session(a.session); e.recover(); result = e.state()
        elif a.command == 'grade': result = grade(a.session, a.file)
        elif a.command == 'finalize': result = finalize(a.session, a.file)
        elif a.command == 'import-answer':
            e = Session(a.session); e.recover(); doc = read(a.file)
            s = e.state()
            require(doc.get('pack_hash') == s['pack_hash'] and doc.get('rubric_hash') == s['rubric_hash']
                    and doc.get('attempt_id') == s['attempt_id'] and doc.get('status') == 'submitted', '导入答卷身份或提交状态无效')
            require(s['status'] == 'draft', '已有提交不能覆盖')
            selected = selection(e.pack, doc.get('selected_case_ids'))
            validate_answers(doc['answers'], questions(e.pack), e.pack.get('exam', {}).get('kind') == 'essay')
            if s['started_at'] is None:
                e.update('start', {'attempt_id': s['attempt_id'], 'revision': s['revision'], 'selected_case_ids': selected})
            s = e.state()
            result = e.update('submit', {'attempt_id': s['attempt_id'], 'revision': s['revision'], 'answers': doc['answers'], 'selected_case_ids': selected, 'reason': 'offline-import'})
            result['offline_elapsed_seconds'] = doc.get('elapsed_seconds')
            atomic(e.path / 'offline-export.json', doc)  # preserve untrusted client timer separately
        else:
            e = Session(a.session); s = e.state()
            require(s['status'] in ('submitted', 'graded', 'archived'), '仅已提交场次可修订评分表')
            r = read(a.file); validate_pack(e.pack, r, e.path / 'public')
            version = 'rubric-' + digest(r)[:16] + '.json'
            atomic(e.path / version, r)
            atomic(e.path / ('revision-' + digest(r)[:16] + '.json'), {'previous': s['rubric_file'], 'reason': a.reason, 'time': time.time()})
            s.update(rubric_file=version, rubric_hash=digest(r), status='submitted')
            atomic(e.path / 'state.json', s); result = s
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (LabError, OSError, KeyError, json.JSONDecodeError) as e:
        parser.exit(1, str(e) + '\n')


if __name__ == '__main__':
    main()
