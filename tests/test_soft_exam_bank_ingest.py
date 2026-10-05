"""Synthetic behavioral checks; no personal banks, accounts or model grading."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_soft_exam_lab import fixtures, lab
import test_soft_exam_review_routing as routing
from test_soft_exam_review_routing import harness, user, CONFIRMED, MARKER

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bank', ROOT / 'skills/soft-exam-bank-ingest/scripts/bank.py')
bank = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bank)


class BankTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'course'
        self.root.mkdir()
        self.scope = {'authorization': 'explicit synthetic test', 'section_id': 'section-a', 'start': 10, 'end': 11}
        bank.start(self.root, 'batch-a', self.scope)
        pack, rubric = fixtures()
        case = pack['cases'][0]
        case['source'] = {'kind': 'web-bank', 'locator': 'https://example.test/section-a', 'label': 'synthetic web bank', 'identity_verified': False}
        figure = self.root / 'images/original.svg'
        bank.atomic(figure, '<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>')
        case['figures'] = [{'file': 'images/original.svg', 'caption': 'synthetic original', 'source_locator': 'example.test'}]
        self.record = {'schema_version': 1, 'id': case['id'], 'version': 1, 'kind': 'case',
                       'chapter': 'chapter-a', 'section_id': 'section-a', 'source_items': [10, 11],
                       'markdown_file': 'bank/case.md', 'markdown': '# Case\n\nTwo questions with PRIVATE analysis.',
                       'complete': True, 'verification': {'state': 'verified', 'evidence': ['model reviewed synthetic fixture'], 'unresolved': []},
                       'assets': [{'file': 'images/original.svg', 'role': 'original', 'sha256': bank.digest(figure.read_bytes())}],
                       'pack': pack, 'rubric': rubric}

    def save(self, record=None, **kwargs):
        return bank.save(self.root, record or self.record, 'batch-a', **kwargs)

    def test_save_merge_and_repeat_do_not_duplicate_or_reset(self):
        md = self.root / self.record['markdown_file']
        bank.atomic(md, '# Existing human note\n\nPersonal answer stays.\n')
        self.save()
        before = {p: p.read_bytes() for p in [md, bank.run_path(self.root, 'batch-a')]}
        self.save()
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual(md.read_text().count(self.record['markdown']), 1)
        self.assertIn('Personal answer stays.', md.read_text())
        self.assertEqual(bank.check(self.root, self.record['id'])['source_items'], [10, 11])

    def test_scope_and_expansion_are_bounded(self):
        with self.assertRaises(ValueError): bank.step(self.root, 'batch-a', 12, 'captured', {'file': 'draft'})
        with self.assertRaises(ValueError): bank.step(self.root, 'batch-a', 12, 'captured', {'same_case_id': 'x', 'section_id': 'other'}, True)
        bank.step(self.root, 'batch-a', 12, 'captured', {'same_case_id': self.record['id'], 'section_id': 'section-a'}, True)
        rec = copy.deepcopy(self.record); rec['source_items'].append(12)
        self.save(rec)
        self.assertEqual(bank.check(self.root, rec['id'])['source_items'], [10, 11, 12])

    def test_invalid_scope_and_identity(self):
        for field, value in [('start', True), ('end', None), ('authorization', ''), ('start', -1)]:
            scope = dict(self.scope); scope[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): bank.start(self.root, 'bad', scope)
        for field, value in [('version', True), ('source_items', [True]), ('source_items', [10, 10])]:
            rec = copy.deepcopy(self.record); rec[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.save(rec)

    def test_same_batch_incremental_update_keeps_history(self):
        self.save()
        with self.assertRaises(ValueError): bank.step(self.root, 'batch-a', 11, 'analysis', {'update_id': 'other'})
        bank.step(self.root, 'batch-a', 11, 'analysis', {'update_id': self.record['id'], 'file': 'new analysis'})
        rec = copy.deepcopy(self.record); rec['version'] = 2; rec['markdown'] += '\nNew teaching notes.'
        self.save(rec)
        item = bank.read(bank.run_path(self.root, 'batch-a'))['items']['11']
        self.assertTrue(any(e['stage'] == 'analysis' for e in item['history']))
        self.assertTrue((self.root / bank.BASE / rec['id'] / 'record-v1.json').is_file())

    def test_new_version_cannot_drop_subquestions(self):
        self.save()
        rec = copy.deepcopy(self.record); rec['version'] = 2; rec['source_items'] = [10]
        with self.assertRaises(ValueError): self.save(rec)
        rec = copy.deepcopy(self.record); rec['version'] = 2
        rec['pack']['cases'][0]['questions'][0]['id'] = 'new-q'
        rec['rubric']['points'][0]['question_id'] = 'new-q'
        with self.assertRaises(ValueError): self.save(rec)

    def test_managed_human_edit_requires_read_and_reconcile(self):
        self.save()
        md = self.root / self.record['markdown_file']
        edited = self.record['markdown'] + '\nHuman annotation retained.'
        bank.atomic(md, bank.merge_markdown(md.read_text(), dict(self.record, markdown=edited)))
        rec = copy.deepcopy(self.record); rec['version'] = 2; rec['markdown'] = edited + '\nNew analysis.'
        with self.assertRaises(ValueError): self.save(rec)
        self.assertIn('Human annotation retained.', md.read_text())
        self.save(rec, reconcile_hash=bank.digest(edited.strip().encode()))
        self.assertIn('Human annotation retained.', md.read_text())

    def test_replay_after_markdown_before_receipt_write(self):
        self.save()
        pointer = self.root / bank.BASE / self.record['id'] / 'current.json'
        old = pointer.read_bytes()
        rec = copy.deepcopy(self.record); rec['version'] = 2; rec['markdown'] += '\nUpdated.'
        self.save(rec)
        bank.atomic(pointer, old)
        self.save(rec)
        self.assertEqual(bank.check(self.root, rec['id'])['version'], 2)

    def test_pending_has_no_export_and_assets_still_checked(self):
        rec = copy.deepcopy(self.record); rec['complete'] = False
        rec['verification'] = {'state': 'pending', 'evidence': ['missing question'], 'unresolved': ['missing question']}
        self.save(rec)
        with self.assertRaises(ValueError): bank.export_lab(self.root, rec['id'], self.root / 'export')
        (self.root / 'images/original.svg').write_text('changed')
        with self.assertRaises(ValueError): bank.check(self.root, rec['id'])

    def test_public_export_isolates_answers_and_rejects_true_request(self):
        bank.atomic(self.root / 'images/answer.svg', '<svg>PRIVATE ANSWER</svg>')
        self.record['assets'].append({'file': 'images/answer.svg', 'role': 'answer', 'sha256': bank.digest((self.root / 'images/answer.svg').read_bytes())})
        self.save()
        dest = self.root / 'export'; bank.export_lab(self.root, self.record['id'], dest)
        text = '\n'.join(f.read_text() for f in (dest / 'public').rglob('*') if f.is_file())
        self.assertNotIn('PRIVATE', text)
        self.assertNotIn('points', text)
        self.assertTrue((dest / 'private/rubric.json').is_file())
        lab.validate_pack(bank.read(dest / 'public/pack.json'), bank.read(dest / 'private/rubric.json'), dest / 'public')
        with self.assertRaises(ValueError): bank.export_lab(self.root, self.record['id'], self.root / 'true', require_true=True)

    def test_public_answer_field_or_answer_image_rejected(self):
        rec = copy.deepcopy(self.record); rec['pack']['cases'][0]['questions'][0]['answer'] = 'PRIVATE'
        with self.assertRaises(ValueError): self.save(rec)
        rec = copy.deepcopy(self.record); rec['assets'][0]['role'] = 'answer'
        with self.assertRaises(ValueError): self.save(rec)

    def test_atomic_failure_preserves_prior_data(self):
        file = self.root / 'data.json'; bank.atomic(file, {'before': 1})
        with patch.object(bank.os, 'replace', side_effect=OSError('simulated disk error')):
            with self.assertRaises(OSError): bank.atomic(file, {'after': 2})
        self.assertEqual(bank.read(file), {'before': 1})
        self.assertFalse(list(self.root.glob('.bank-*')))

    def test_verified_local_links_are_checked_but_pending_can_wait(self):
        rec = copy.deepcopy(self.record); rec['markdown'] += '\n![missing](missing.png)'
        with self.assertRaises(ValueError): self.save(rec)
        rec['verification'] = {'state': 'pending', 'evidence': ['source captured'], 'unresolved': ['missing image']}
        rec['complete'] = False
        self.save(rec)

    def test_relative_resource_and_fenced_example_links(self):
        self.record['markdown'] += '\n![original](../images/original.svg)\n~~~markdown\n[example](missing.txt)\n~~~\n'
        self.save()
        bank.check(self.root, self.record['id'])

    def test_receipt_cannot_point_to_other_markdown(self):
        self.save()
        pointer = self.root / bank.BASE / self.record['id'] / 'current.json'
        receipt = bank.read(pointer); receipt['markdown_file'] = 'other.md'
        bank.atomic(self.root / 'other.md', (self.root / self.record['markdown_file']).read_bytes())
        bank.atomic(pointer, receipt)
        with self.assertRaises(ValueError): bank.check(self.root, self.record['id'])

    def test_paths_and_changed_source_hash_rejected(self):
        for path in ('../outside.md', '/outside.md'):
            rec = copy.deepcopy(self.record); rec['markdown_file'] = path
            with self.subTest(path=path), self.assertRaises(ValueError): self.save(rec)
        outside = self.root.parent / 'outside'; outside.mkdir()
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        rec = copy.deepcopy(self.record); rec['markdown_file'] = 'linked/note.md'
        with self.assertRaises(ValueError): self.save(rec)

    def test_essay_requires_coverage_and_cannot_export_to_case_lab(self):
        rec = {k: copy.deepcopy(v) for k, v in self.record.items() if k not in ('pack', 'rubric')}
        rec.update(kind='essay', id='simulation-a', assets=[], essay={'mode': 'exam-simulation', 'profile': {'project': 'synthetic'}, 'requirements': ['role', 'mechanism'], 'abstract': 'Complete abstract', 'body': 'Complete synthetic prose', 'coverage': {'role': 'paragraph1', 'mechanism': 'paragraph2'}})
        self.save(rec)
        with self.assertRaises(ValueError): bank.export_lab(self.root, rec['id'], self.root / 'export')
        rec['version'] = 2; rec['essay']['coverage'].pop('mechanism')
        with self.assertRaises(ValueError): self.save(rec)


class BankRoutingTests(unittest.TestCase):
    setUp = routing.ReviewRoutingTests.setUp
    write_records = routing.ReviewRoutingTests.write_records
    assert_route = routing.ReviewRoutingTests.assert_route

    def test_explicit_switch_and_continuation_release_single_question(self):
        for request in ('$soft-exam-bank-ingest 整理案例', '@soft-exam-bank-ingest 整理论文', '使用 soft-exam-bank-ingest 整理10～11'):
            with self.subTest(request=request):
                self.assertTrue(harness.is_bank_ingest_request(request))
                self.assert_route([user('请解析这道软考题'), CONFIRMED, MARKER, user(request), CONFIRMED, MARKER, user('继续')], False)

    def test_mentions_quotes_and_images_do_not_invoke(self):
        for request in ('文档示例：`$soft-exam-bank-ingest`', '> $soft-exam-bank-ingest 整理', '我看到 @soft-exam-bank-ingest，是什么？', '请讲解软考案例题', '“使用 soft-exam-bank-ingest”是什么意思？'):
            with self.subTest(request=request): self.assertFalse(harness.is_bank_ingest_request(request))

    def test_normal_question_after_batch_uses_tutor(self):
        self.assert_route([user('$soft-exam-bank-ingest 整理'), user('请解析这道软考题'), CONFIRMED], True)


if __name__ == '__main__':
    unittest.main()
