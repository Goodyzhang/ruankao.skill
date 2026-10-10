"""Exam selection follows actual answers and paper numbers, never the best scores."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import test_soft_exam_exam as fixture

lab = fixture.lab


class AutoSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pack, self.rubric = fixture.fixture()
        self.exam = self.pack.pop('exam')
        self.exam['selection_policy'] = 'answered-lowest-numbered'
        for n, case in enumerate(self.pack['cases'], 1): case['source']['case_number'] = n

    def submit(self, answered=(1, 2, 4), formal=False):
        if formal: self.pack['exam'] = self.exam
        lab.atomic(self.root/'pack.json', self.pack)
        lab.atomic(self.root/'rubric.json', self.rubric)
        self.path = lab.prepare(self.root/'attempts', self.root/'pack.json', self.root/'rubric.json')
        self.engine = lab.Session(self.path)
        s = self.engine.state()
        self.engine.update('start', dict(attempt_id=s['attempt_id'], revision=s['revision']))
        s = self.engine.state()
        for n in answered: s['answers'][f'q{n}']['markdown'] = '项目方案。'
        self.engine.update('submit', dict(attempt_id=s['attempt_id'], revision=s['revision'], answers=s['answers']))

    def evaluation(self, awarded=8, include_scope=True):
        s = self.engine.state()
        sub = lab.read(self.path/'submission.json')
        qids = {'q1'} | {q for q, a in sub['answers'].items() if a['markdown'].strip()}
        points = [p for p in self.rubric['points'] if p['question_id'] in qids]
        decisions = []
        for i, p in enumerate(points):
            d = {'point_id':p['id'], 'status':'awarded' if i < awarded else 'omitted', 'comment':'固定验收判定'}
            if d['status'] == 'awarded': d['evidence'] = [{'kind':'text','start':0,'end':2,'quote':'项目'}]
            decisions.append(d)
        e = dict(schema_version=1, attempt_id=s['attempt_id'], submission_hash=lab.digest(sub), rubric_hash=s['rubric_hash'],
                 reviewer='current-agent', self_check={'scope':'按作答和题号核对'}, decisions=decisions,
                 reference_checks=fixture.reference_checks(points))
        if include_scope:
            e['exam_reassessment'] = dict(title='按正式试卷重评', exam=self.exam,
                request='用户要求按照真题评分标准重算', reason='历史练习缺少正式试卷规则')
        return e

    def grade(self, e):
        lab.atomic(self.root/'evaluation.json', e)
        return lab.grade(self.path, self.root/'evaluation.json')

    def finalize(self, g):
        note = self.root/'record.md'
        note.write_text(self.engine.state()['attempt_id'])
        receipt = dict(attempt_id=self.engine.state()['attempt_id'], grade_hash=lab.digest(g),
            covered_points=[p['id'] for p in g['results'] if p.get('counted', True) and p['status'] in ('omitted','incorrect')],
            files=[dict(path=str(note), sha256=hashlib.sha256(note.read_bytes()).hexdigest())])
        lab.atomic(self.root/'receipt.json', receipt)
        lab.finalize(self.path, self.root/'receipt.json')

    def test_confirmed_legacy_scope_becomes_75_and_survives_regrade(self):
        self.submit()
        frozen = {f:(self.path/f).read_bytes() for f in ('pack.json','submission.json','rubric-v1.json')}
        g = self.grade(self.evaluation())
        self.assertEqual((g['reference_score'],g['max_score'],g['exam_outcome']['status']), (40,75,'fail'))
        self.assertEqual(g['selected_case_ids'], ['case1','case2','case4'])
        self.assertEqual(set(g['questions']), {'q1','q2','q4'})
        self.finalize(g)
        first_id = self.engine.state()['grade_id']
        g = self.grade(self.evaluation(include_scope=False))
        self.finalize(g)
        self.assertEqual(g['max_score'],75)
        self.assertTrue((self.path/'reviews'/(first_id+'.html')).exists())
        for f, value in frozen.items(): self.assertEqual((self.path/f).read_bytes(), value)
        for name in ('report.html','index.html','offline.html'):
            data = json.loads(re.search(r'<script id="lab-data" type="application/json">(.*?)</script>', (self.path/'public'/name).read_text(), re.S)[1])
            self.assertEqual(data['pack']['exam']['max_score'],75)
            self.assertEqual(data['grade']['selected_case_ids'],['case1','case2','case4'])

    def test_multiple_answers_use_lowest_numbers_not_highest_scores(self):
        self.pack['cases'] = [self.pack['cases'][n] for n in (0,4,3,2,1)]
        self.submit(answered=(1,2,3,4,5),formal=True)
        e = self.evaluation(awarded=0,include_scope=False)
        for d in e['decisions']:
            if d['point_id'].startswith(('q4-','q5-')):
                d.update(status='awarded', evidence=[{'kind':'text','start':0,'end':2,'quote':'项目'}])
        g = self.grade(e)
        self.assertEqual(g['selected_case_ids'],['case1','case2','case3'])
        self.assertEqual(g['supplemental_case_ids'],['case4','case5'])
        self.assertEqual((g['reference_score'],g['training_score'],g['max_score']),(0,0,75))
        self.assertEqual((g['questions']['q4']['reference'],g['questions']['q5']['reference']),(25,25))
        self.assertFalse(g['questions']['q4']['counted'])
        self.assertEqual(set(g['dimensions']),{'考点1','考点2','考点3'})
        self.assertEqual({q['question_id'] for q in g['weaknesses']['questions']},{'q1','q2','q3'})
        self.assertEqual(lab.read(self.path/'submission.json')['selected_case_ids'],g['selected_case_ids'])
        self.finalize(g)

    def test_missing_elective_keeps_75_and_required_blank_is_graded(self):
        self.submit(answered=(4,),formal=True)
        g = self.grade(self.evaluation(awarded=0,include_scope=False))
        self.assertEqual(g['selected_case_ids'],['case1','case4'])
        self.assertEqual(g['unanswered_score'],25)
        self.assertEqual((g['reference_score'],g['max_score']),(0,75))

    def test_supplemental_pending_does_not_change_pass_decision(self):
        self.submit(answered=(1,2,3,4),formal=True)
        e = self.evaluation(awarded=9,include_scope=False)
        e['decisions'][-1].update(status='pending',pending_reason='补充题待核验')
        g = self.grade(e)
        self.assertEqual((g['reference_score'],g['exam_outcome']['status']),(45,'pass'))
        self.assertTrue(g['pending'])
        self.assertFalse(g['weaknesses']['known_only'])

    def test_answer_detection_includes_user_images_but_not_background(self):
        pack = dict(self.pack,exam=self.exam)
        answers = {f'q{i}':{'markdown':'   ','attachments':[]} for i in range(1,6)}
        answers['q2'].update(scene={'elements':[{'id':'bg','customData':{'labSource':'question-background'}}]},drawing_png='background')
        answers['q3']['attachments']=[{'name':'handwriting.png'}]
        answers['q4']['scene']={'elements':[{'id':'deleted','isDeleted':True}]}
        answers['q5']['drawing_png']='handwriting'
        self.assertEqual(lab.grading_cases(pack,{'answers':answers}),(['case1','case3','case5'],[]))
        answers['q2']['scene']['elements'].append({'id':'student-arrow'})
        self.assertEqual(lab.grading_cases(pack,{'answers':answers}),(['case1','case2','case3'],['case5']))

    def test_unverified_numbers_or_rules_are_rejected(self):
        for mode in ('missing-number','duplicate-number','wrong-total'):
            with self.subTest(mode=mode):
                pack=copy.deepcopy(self.pack);pack['exam']=copy.deepcopy(self.exam)
                if mode=='missing-number':pack['cases'][1]['source'].pop('case_number')
                elif mode=='duplicate-number':pack['cases'][1]['source']['case_number']=1
                else:pack['exam']['max_score']=125
                with self.assertRaises(lab.LabError):lab.validate_exam(pack,self.rubric)

    def test_reassessment_requires_user_request_and_keeps_old_report_on_error(self):
        self.submit()
        g=self.grade(self.evaluation())
        before=(self.path/'public/report.html').read_bytes()
        e=self.evaluation();e['exam_reassessment']['request']=''
        with self.assertRaises(lab.LabError):self.grade(e)
        self.assertEqual(before,(self.path/'public/report.html').read_bytes())

    def test_offline_import_derives_scope_from_actual_answers(self):
        self.pack['exam']=self.exam
        lab.atomic(self.root/'pack.json',self.pack);lab.atomic(self.root/'rubric.json',self.rubric)
        path=lab.prepare(self.root/'attempts',self.root/'pack.json',self.root/'rubric.json')
        doc=lab.read(path/'state.json');doc['status']='submitted'
        for q in ('q1','q3','q4','q5'):doc['answers'][q]['markdown']='项目方案。'
        lab.atomic(self.root/'import.json',doc)
        fixture.subprocess.run([fixture.sys.executable,str(fixture.REPO/'skills/soft-exam-lab/scripts/lab.py'),
            'import-answer','--session',str(path),'--file',str(self.root/'import.json')],capture_output=True,check=True)
        self.assertEqual(lab.read(path/'submission.json')['selected_case_ids'],['case1','case3','case4'])


if __name__ == '__main__': unittest.main()
