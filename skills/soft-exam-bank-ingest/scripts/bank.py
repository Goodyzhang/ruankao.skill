#!/usr/bin/env python3
"""Deterministic storage and handoff. Agents author content and semantic decisions."""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit

ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,95}$')
BASE = Path('真题库/_structured/soft-exam-bank-ingest')
RUNS = Path('真题库/_ingest/soft-exam-bank-ingest')
STAGES = ('captured', 'analysis', 'drafted', 'reviewed', 'saved', 'pending', 'skipped')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(data):
    if not isinstance(data, bytes):
        data = json.dumps(data, ensure_ascii=False, sort_keys=True,
                          allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def safe(root, relative):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts and str(path) != '.', 'invalid relative path')
    target = Path(root) / path
    require(all(not (Path(root) / Path(*path.parts[:i])).is_symlink()
                for i in range(1, len(path.parts) + 1)), 'symlink resource')
    return target


def atomic(path, value):
    path = Path(path)
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8') if not isinstance(value, (str, bytes)) else value.encode('utf-8') if isinstance(value, str) else value
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.bank-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def lab_module():
    path = Path(__file__).resolve().parents[2] / 'soft-exam-lab/scripts/lab.py'
    require(path.is_file(), 'soft-exam-lab is required for case validation/export')
    spec = importlib.util.spec_from_file_location('bank_lab', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_links(record, root):
    """Check deterministic local Markdown resources, not factual/heading semantics."""
    body = re.sub(r'(?ms)^\s*(```|~~~).*?^\s*\1\s*$', '', record['markdown'])
    base = safe(root, record['markdown_file']).parent
    for value in re.findall(r'!?\[[^\]]*\]\((<?[^)]+>?)\)', body):
        value = value.strip('<>')
        parsed = urlsplit(value)
        if parsed.scheme or not parsed.path:
            continue
        target = (base / unquote(parsed.path)).resolve()
        require(target.is_relative_to(Path(root).resolve()) and target.is_file(), 'missing or outside local Markdown link: ' + value)


def validate(record, root, ready=False):
    require(record.get('schema_version') == 1, 'schema version must be 1')
    require(ID.fullmatch(record.get('id', '')) and type(record.get('version')) is int
            and record['version'] > 0, 'invalid item identity/version')
    require(record.get('kind') in ('case', 'essay'), 'invalid item kind')
    require(record.get('chapter') and record.get('source_items') and record.get('section_id'), 'missing routing/source')
    require(all(type(n) is int and n > 0 for n in record['source_items']) and
            len(set(record['source_items'])) == len(record['source_items']), 'invalid source item numbers')
    require(record.get('markdown'), 'agent-authored markdown missing')
    safe(root, record['markdown_file'])
    verification = record.get('verification', {})
    require(verification.get('state') in ('pending', 'verified'), 'missing verification state')
    if verification['state'] == 'verified':
        require(record.get('complete') is True and verification.get('evidence') and
                verification.get('unresolved') == [], 'verified item lacks completeness/evidence')
        check_links(record, root)
    roles = {}
    for asset in record.get('assets', []):
        require(asset.get('role') in ('original', 'answer', 'editable'), 'invalid asset role')
        file = safe(root, asset['file'])
        require(file.is_file(), 'missing asset: ' + asset['file'])
        require(asset.get('sha256') == digest(file.read_bytes()), 'asset hash mismatch')
        require(asset['file'] not in roles, 'duplicate asset')
        roles[asset['file']] = asset['role']
    if record['kind'] == 'case':
        pack = record.get('pack', {})
        require(pack.get('schema_version') == 1 and len(pack.get('cases', [])) == 1, 'one canonical case required')
        case = pack['cases'][0]
        require(case.get('id') == record['id'] and case.get('questions'), 'case identity/questions missing')
        qids = [q.get('id') for q in case['questions']]
        require(len(qids) == len(set(qids)), 'duplicate subquestion identity')
        for fig in case.get('figures', []):
            require(roles.get(fig.get('file')) == 'original', 'public figure must be a declared original')
        if verification['state'] == 'verified' or ready:
            require(verification['state'] == 'verified', 'item is pending')
            lab_module().validate_pack(pack, record.get('rubric', {}), root)
    else:
        essay = record.get('essay', {})
        require(essay.get('mode') == 'exam-simulation' and essay.get('requirements') and
                essay.get('profile'), 'simulation profile/requirements missing')
        if verification['state'] == 'verified':
            require(essay.get('abstract') and essay.get('body') and essay.get('coverage'), 'essay incomplete')
            require(set(essay['coverage']) == set(essay['requirements']), 'essay coverage does not match requirements')
        if ready:
            raise ValueError('essay runtime is not supported by soft-exam-lab v1')
    return roles


def merge_markdown(existing, record):
    start = '<!-- soft-exam-bank-ingest:' + record['id'] + ':start -->'
    end = '<!-- soft-exam-bank-ingest:' + record['id'] + ':end -->'
    body = start + '\n' + record['markdown'].strip() + '\n' + end
    require(start not in record['markdown'] and end not in record['markdown'], 'nested managed markers')
    if start in existing or end in existing:
        require(existing.count(start) == existing.count(end) == 1 and existing.index(start) < existing.index(end), 'broken managed region')
        return existing[:existing.index(start)] + body + existing[existing.index(end) + len(end):]
    if existing:
        return existing.rstrip('\n') + '\n\n' + body + '\n'
    header = ('---\nsoft_exam_bank_id: ' + record['id'] + '\nchapter: ' +
              json.dumps(record['chapter'], ensure_ascii=False) + '\nkind: ' + record['kind'] +
              '\nupdated: ' + datetime.date.today().isoformat() + '\n---\n\n')
    return header + body + '\n'


def run_path(root, batch):
    require(ID.fullmatch(batch), 'invalid batch identity')
    return safe(root, str(RUNS / (batch + '.json')))


def start(root, batch, scope):
    path = run_path(root, batch)
    require(scope.get('authorization') and scope.get('section_id') and
            type(scope.get('start')) is int and type(scope.get('end')) is int and
            0 < scope['start'] <= scope['end'], 'explicit batch scope required')
    if path.exists():
        state = read(path)
        require(state['scope'] == scope, 'existing batch scope differs; choose new identity')
        return state
    state = {'schema_version': 1, 'id': batch, 'scope': scope, 'items': {}, 'expanded_items': [], 'next_step': 'capture current item'}
    atomic(path, state)
    return state


def step(root, batch, number, stage, evidence, expanded=False):
    require(stage in STAGES and evidence, 'stage evidence missing')
    path = run_path(root, batch)
    state = read(path)
    require(state['scope']['start'] <= number <= state['scope']['end'] or expanded, 'item outside scope')
    if expanded:
        require(evidence.get('same_case_id') and evidence.get('section_id') == state['scope']['section_id'], 'expansion requires same case and section evidence')
        state['expanded_items'] = sorted(set(state['expanded_items'] + [number]))
    previous = state['items'].get(str(number), {})
    require(stage != 'saved', 'saved is recorded only after save and readback')
    if previous.get('stage') == 'saved':
        require(evidence.get('update_id') == previous.get('case_id'), 'completed item: explicit update identity required')
        check(root, previous['case_id'])
    item = dict(previous)
    history = item.get('history', [])
    if previous:
        history = history + [{'stage': previous['stage'], 'evidence': previous.get('evidence'), 'receipt': previous.get('receipt')}]
    item.update(stage=stage, evidence=evidence, history=history)
    state['items'][str(number)] = item
    state['next_step'] = evidence.get('next_step', stage)
    atomic(path, state)
    return state


def save(root, record, batch, reconcile_hash=None):
    validate(record, root)
    state_file = run_path(root, batch)
    state = read(state_file)
    require(str(record['section_id']) == str(state['scope']['section_id']), 'cross-section item')
    permitted = set(range(state['scope']['start'], state['scope']['end'] + 1)) | set(state['expanded_items'])
    require(set(record['source_items']) <= permitted, 'item outside authorized/expanded scope')
    folder = safe(root, str(BASE / record['id']))
    version_file = folder / ('record-v' + str(record['version']) + '.json')
    if version_file.exists():
        require(read(version_file) == record, 'version is immutable; increment version for content changes')
    current = folder / 'current.json'
    if current.exists():
        old = read(current)
        require(record['version'] >= old['version'], 'version rollback')
        previous = read(folder / ('record-v' + str(old['version']) + '.json'))
        require(digest((folder / ('record-v' + str(old['version']) + '.json')).read_bytes()) == old['record_sha256'], 'prior record changed')
        require(record['kind'] == previous['kind'] and record['markdown_file'] == previous['markdown_file'], 'stable kind/path changed')
        if record['version'] > old['version']:
            require(set(previous['source_items']) <= set(record['source_items']), 'update drops source subquestions')
            if record['kind'] == 'case':
                prior_ids = {q['id'] for q in previous['pack']['cases'][0]['questions']}
                require(prior_ids <= {q['id'] for q in record['pack']['cases'][0]['questions']}, 'update drops stable subquestion identities')
    md = safe(root, record['markdown_file'])
    if current.exists() and md.exists():
        prior_text = md.read_text(encoding='utf-8')
        begin = '<!-- soft-exam-bank-ingest:' + record['id'] + ':start -->'
        finish = '<!-- soft-exam-bank-ingest:' + record['id'] + ':end -->'
        require(prior_text.count(begin) == prior_text.count(finish) == 1, 'broken managed region')
        actual_hash = digest(prior_text.split(begin, 1)[1].split(finish, 1)[0].strip().encode('utf-8'))
        # The new body is also valid after interruption between Markdown and receipt writes.
        expected_hashes = {old['managed_sha256'], digest(record['markdown'].strip().encode('utf-8'))}
        if actual_hash not in expected_hashes:
            require(record['version'] > old['version'] and reconcile_hash == actual_hash,
                    'managed content changed; read and merge human edits, then pass its hash with a new version')
        if (record['version'] == old['version'] and actual_hash == old['managed_sha256'] and
                all(state['items'].get(str(n), {}).get('stage') == 'saved' and
                    state['items'][str(n)].get('case_id') == record['id'] for n in record['source_items'])):
            check(root, record['id'])
            return old
    content = merge_markdown(md.read_text(encoding='utf-8') if md.exists() else '', record)
    atomic(version_file, record)
    atomic(md, content)
    require(md.read_text(encoding='utf-8') == content and read(version_file) == record, 'readback failed')
    receipt = {'schema_version': 1, 'id': record['id'], 'version': record['version'],
               'record_sha256': digest(version_file.read_bytes()), 'markdown_file': record['markdown_file'],
               'managed_sha256': digest(record['markdown'].strip().encode('utf-8')),
               'verification': record['verification']['state']}
    atomic(current, receipt)
    for number in record['source_items']:
        previous_item = state['items'].get(str(number), {})
        history = previous_item.get('history', [])
        if previous_item:
            history = history + [{'stage': previous_item['stage'], 'evidence': previous_item.get('evidence'), 'receipt': previous_item.get('receipt')}]
        state['items'][str(number)] = {'stage': 'saved' if record['verification']['state'] == 'verified' else 'pending',
                                      'case_id': record['id'], 'receipt': str(current.relative_to(root)), 'history': history}
    state['next_step'] = 'continue after last saved source item; inspect pending gaps'
    atomic(state_file, state)
    return receipt


def check(root, identity):
    require(ID.fullmatch(identity), 'invalid identity')
    folder = safe(root, str(BASE / identity))
    receipt = read(folder / 'current.json')
    file = folder / ('record-v' + str(receipt['version']) + '.json')
    require(digest(file.read_bytes()) == receipt['record_sha256'], 'record receipt mismatch')
    record = read(file)
    require(record['id'] == identity and record['version'] == receipt['version'] and
            record['markdown_file'] == receipt['markdown_file'] and
            record['verification']['state'] == receipt['verification'], 'receipt metadata differs from record')
    validate(record, root)
    md = safe(root, receipt['markdown_file']).read_text(encoding='utf-8')
    start, end = '<!-- soft-exam-bank-ingest:' + identity + ':start -->', '<!-- soft-exam-bank-ingest:' + identity + ':end -->'
    require(md.count(start) == md.count(end) == 1 and md.index(start) < md.index(end), 'missing or broken managed region')
    actual = md.split(start, 1)[1].split(end, 1)[0].strip()
    require(digest(actual.encode('utf-8')) == receipt['managed_sha256'], 'managed content changed; reconcile before updating')
    return {'id': identity, 'version': receipt['version'], 'verification': receipt['verification'],
            'ready_for_lab': record['kind'] == 'case' and receipt['verification'] == 'verified',
            'source_items': record['source_items'], 'record': record}


def export_lab(root, identity, destination, require_true=False):
    result = check(root, identity)
    record = result['record']
    validate(record, root, ready=True)
    lab_module().validate_pack(record['pack'], record['rubric'], root, require_true=require_true)
    pack = copy.deepcopy(record['pack'])
    dest = Path(destination).resolve()
    require(dest != Path(root).resolve() and not dest.is_relative_to(Path(root).resolve() / BASE), 'invalid export destination')
    for case in pack['cases']:
        for fig in case.get('figures', []):
            src = safe(root, fig['file'])
            relative = 'figures/' + digest(src.read_bytes())[:16] + src.suffix.lower()
            atomic(safe(dest / 'public', relative), src.read_bytes())
            fig['file'] = relative
    atomic(safe(dest, 'public/pack.json'), pack)
    atomic(safe(dest, 'private/rubric.json'), record['rubric'])
    lab_module().validate_pack(read(dest / 'public/pack.json'), read(dest / 'private/rubric.json'), dest / 'public', require_true=require_true)
    return {'pack': str(dest / 'public/pack.json'), 'rubric': str(dest / 'private/rubric.json'), 'source_root': str(dest / 'public')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('start')
    init.add_argument('--batch', required=True)
    init.add_argument('--scope', required=True)
    stage = commands.add_parser('step')
    stage.add_argument('--batch', required=True)
    stage.add_argument('--number', type=int, required=True)
    stage.add_argument('--stage', choices=STAGES, required=True)
    stage.add_argument('--evidence', required=True)
    stage.add_argument('--expanded', action='store_true')
    store_parser = commands.add_parser('save')
    store_parser.add_argument('--batch', required=True)
    store_parser.add_argument('--record', required=True)
    store_parser.add_argument('--reconcile-hash', help='observed managed-body SHA256 after preserving human edits in a new version')
    inspector = commands.add_parser('check')
    inspector.add_argument('--id', required=True)
    status = commands.add_parser('status')
    status.add_argument('--batch', required=True)
    export = commands.add_parser('export-lab')
    export.add_argument('--id', required=True)
    export.add_argument('--destination', required=True)
    export.add_argument('--require-true', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(root.is_dir(), 'confirmed course root must exist')
    if args.command == 'start':
        result = start(root, args.batch, read(args.scope))
    elif args.command == 'step':
        result = step(root, args.batch, args.number, args.stage, read(args.evidence), args.expanded)
    elif args.command == 'save':
        result = save(root, read(args.record), args.batch, args.reconcile_hash)
    elif args.command == 'check':
        result = check(root, args.id)
        result.pop('record')
    elif args.command == 'status':
        result = read(run_path(root, args.batch))
        for item in result['items'].values():
            if item.get('receipt'):
                check(root, item['case_id'])
    else:
        result = export_lab(root, args.id, args.destination, args.require_true)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
