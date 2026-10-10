"""A conflicting reference must never replace the frozen scoring authority."""
import unittest
import copy
import subprocess
import sys
import test_soft_exam_lab as fixture

lab = fixture.lab


class ReferenceConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.LabTests()
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.case.submit()

    def revise(self, change):
        case = self.case
        rubric = copy.deepcopy(case.rubric)
        change(rubric)
        path = case.root / 'revised.json'
        lab.atomic(path, rubric)
        subprocess.run([sys.executable, str(fixture.SKILL / 'scripts/lab.py'), 'revise-rubric',
                        '--session', str(case.path), '--file', str(path), '--reason', '定向验收修订'],
                       check=True, capture_output=True)
        return case.evaluation()

    def test_evaluation_cannot_replace_reference_or_existing_report(self):
        case = self.case
        evaluation = case.evaluation()
        case.run_grade(evaluation)
        before = (case.path / 'public/report.html').read_bytes()
        evaluation['reference_answers'] = {'q-write': {
            'origin': 'source', 'source': '自编题干版本1',
            'markdown': '先删除缓存，再提交数据库。提交失败也删除缓存。'}}
        with self.assertRaisesRegex(lab.LabError, '评分表'):
            case.run_grade(evaluation)
        self.assertEqual(before, (case.path / 'public/report.html').read_bytes())

    def test_missing_or_conflicting_review_blocks_report(self):
        for mode in ('missing', 'conflict', 'empty-note', 'missing-point', 'duplicate-point', 'other-question'):
            with self.subTest(mode=mode):
                evaluation = self.case.evaluation()
                check = evaluation['reference_checks']['q-write']
                if mode == 'missing': evaluation.pop('reference_checks')
                elif mode == 'conflict': check['status'] = 'conflict'
                elif mode == 'empty-note': check['note'] = ''
                elif mode == 'missing-point': check['checked_point_ids'].pop()
                elif mode == 'duplicate-point': check['checked_point_ids'] = ['p-order', 'p-order']
                else: check['checked_point_ids'] = ['p-order', 'p-ttl']
                with self.assertRaises(lab.LabError): self.case.run_grade(evaluation)
                self.assertFalse((self.case.path / 'grade.json').exists())

    def test_different_source_blocks_report(self):
        evaluation = self.revise(lambda r: r['reference_answers']['q-write'].update(sources=['未核实的另一份答案']))
        with self.assertRaisesRegex(lab.LabError, '同一组'): self.case.run_grade(evaluation)

    def test_independent_conflicting_correct_blocks_report(self):
        evaluation = self.revise(lambda r: r['reference_answers']['q-write'].update(markdown='先删除缓存，再提交数据库。'))
        with self.assertRaisesRegex(lab.LabError, '摘自同版'): self.case.run_grade(evaluation)

    def test_source_display_is_derived_and_revision_preserves_submission(self):
        original = (self.case.path / 'submission.json').read_bytes()
        evaluation = self.revise(lambda r: r['reference_answers']['q-write'].update(source='虚构官方出处'))
        result = self.case.run_grade(evaluation)
        self.assertEqual(result['reference_answers']['q-write']['source'], '自编题干版本1')
        self.assertEqual(original, (self.case.path / 'submission.json').read_bytes())
        self.assertTrue((self.case.path / 'rubric-v1.json').exists())
        self.assertEqual(result['reference_score'], 0)

    def test_unresolved_source_remains_pending_without_final_score(self):
        evaluation = self.revise(lambda r: r['reference_answers']['q-write'].update(origin='pending', markdown='来源相互矛盾，暂不展示确定答案。'))
        evaluation['reference_checks']['q-write'].update(status='pending', note='两份来源的写入顺序相反，尚无取舍依据。')
        with self.assertRaisesRegex(lab.LabError, '待核验状态'): self.case.run_grade(evaluation)
        evaluation['decisions'][0].update(status='pending', pending_reason='顺序来源争议')
        result = self.case.run_grade(evaluation)
        self.assertIsNone(result['reference_score'])
        self.assertTrue(result['pending'])


if __name__ == '__main__':
    unittest.main()
