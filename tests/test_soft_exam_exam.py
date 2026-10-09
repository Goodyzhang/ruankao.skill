"""Authored exam fixtures: selection, pass line, essays and reference answers."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('exam_lab', REPO/'skills/soft-exam-lab/scripts/lab.py')
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


def fixture(essay=False):
    cases, points, references, tasks = [], [], {}, {}
    for n in range(1, 5 if essay else 6):
        qid, cid = f'q{n}', f'case{n}'
        cases.append({'id':cid,'title':f'试题{n}','stem':'自编隔离验收题，验证试卷计分规则。','complete':True,'max_score':75 if essay else 25,
                      'source':{'kind':'authored','label':'自编验收','locator':'本文件'},'figures':[],
                      'questions':[{'id':qid,'title':'论文作答' if essay else '问题1','prompt':'围绕项目、技术原理、实施结果作答。','complete':True,'max_score':75 if essay else 25}]})
        for i in range(5):
            points.append({'id':f'{qid}-p{i}','question_id':qid,'weight':15 if essay else 5,'criterion':f'验收采分点{i}',
                           'conditions':['按自编要求判定'],'equivalents':[],'correct':'自编题约定的完整机制。','dimension':f'考点{n}','source':'自编验收'})
        references[qid]={'origin':'skill-generated','source':'自编验收要求','markdown':'说明项目背景、采用的技术机制及实施结果。'}
        if essay:
            parts={'abstract':'介绍项目方案。','body':'结合项目说明技术原理、实施过程和实践结果。'}
            references[qid].update(essay=parts,markdown=lab.essay_markdown(parts))
            tasks[qid]=[{'id':'project','text':'介绍项目与角色','source':'自编论文题','point_ids':[f'{qid}-p0']},
                        {'id':'method','text':'分析技术原理','source':'自编论文题','point_ids':[f'{qid}-p1',f'{qid}-p2']},
                        {'id':'practice','text':'说明实施过程与结果','source':'自编论文题','point_ids':[f'{qid}-p3',f'{qid}-p4']}]
    exam={'kind':'essay' if essay else 'case-analysis','instructions':'自编模拟选题规则，按所选题目计分。','required_case_ids':[] if essay else ['case1'],
          'choose_count':1 if essay else 2,'max_score':75,'pass_score':45,'rules_source':'自编验收规则','pass_source':'验收用45分边界'}
    if essay:exam['essay_limits']={'abstract_min':1,'abstract_max':40,'body_min':4,'body_max':120}
    pack={'schema_version':1,'id':'essay-fixture' if essay else 'case-fixture','version':'1','title':'隔离试卷验收','scoring_notice':'自编测试，不是历年真题。','cases':cases,'exam':exam}
    rubric={'schema_version':1,'pack_id':pack['id'],'pack_version':'1','version':'1','basis':'inferred-training',
            'answer_source':{'reliable':True,'locator':'自编题目约定','level':'authored-fixture'},'training_policy':'unit-weight-deduplicated-v1',
            'points':points,'reference_answers':references}
    if essay:rubric['essay_requirements']=tasks
    return pack,rubric


class ExamRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def prepare(self,essay=False,mutate=None):
        self.pack,self.rubric=fixture(essay)
        if mutate:mutate(self.pack,self.rubric)
        lab.atomic(self.root/'pack.json',self.pack);lab.atomic(self.root/'rubric.json',self.rubric)
        self.path=lab.prepare(self.root/'attempts',self.root/'pack.json',self.root/'rubric.json')
        self.engine=lab.Session(self.path)
    def action(self,name,**fields):
        state=self.engine.state()
        return self.engine.update(name,dict(attempt_id=state['attempt_id'],revision=state['revision'],**fields))
    def submit(self,selected):
        self.action('start',selected_case_ids=selected)
        answers=self.engine.state()['answers']
        for answer in answers.values():
            if 'essay' in answer:
                answer['essay']={'abstract':'项目摘要。','body':'项目方案与实施结果。'}
                answer['markdown']=lab.essay_markdown(answer['essay'])
            else:answer['markdown']='项目方案与实施结果。'
        return self.action('submit',answers=answers)
    def evaluation(self,awarded=0,pending=False):
        state=self.engine.state();sub=lab.read(self.path/'submission.json')
        qids=lab.questions(self.pack,sub['selected_case_ids'])
        points=[p for p in self.rubric['points'] if p['question_id'] in qids]
        decisions=[]
        for i,p in enumerate(points):
            status='awarded' if i<awarded else 'pending' if pending and i==awarded else 'omitted'
            d={'point_id':p['id'],'status':status,'comment':'固定验收判定'}
            if status=='awarded':
                text=sub['answers'][p['question_id']]['markdown'];start=text.index('项目')
                d['evidence']=[{'kind':'text','start':start,'end':start+2,'quote':'项目'}]
            if status=='pending':d['pending_reason']='验收缺口'
            decisions.append(d)
        return {'schema_version':1,'attempt_id':state['attempt_id'],'submission_hash':lab.digest(sub),'rubric_hash':state['rubric_hash'],
                'reviewer':'current-agent','self_check':{'fixture':'固定判定，仅验证规则与算分'},'decisions':decisions,'extra_errors':[]}
    def grade(self,evaluation):
        lab.atomic(self.root/'evaluation.json',evaluation)
        return lab.grade(self.path,self.root/'evaluation.json')
    def test_start_requires_two_electives(self):
        self.prepare()
        with self.assertRaisesRegex(lab.LabError,'选齐'):self.action('start')
        self.assertIsNone(self.engine.state()['started_at'])
    def test_invalid_selection_does_not_save(self):
        self.prepare();before=self.engine.state()
        for ids in (['case2','case3','case4'],['case1','case2','case2'],['case1','case2','missing'],['case1','case2','case3','case4']):
            with self.assertRaises(lab.LabError):self.action('save',selected_case_ids=ids)
        self.assertEqual(before,self.engine.state())
    def test_selection_change_retains_answers_and_refresh(self):
        self.prepare();self.action('start',selected_case_ids=['case1','case2','case3'])
        answers=self.engine.state()['answers'];answers['q2']['markdown']='保留的旧选题草稿'
        self.action('save',answers=answers,selected_case_ids=['case1','case3','case4'])
        restored=lab.Session(self.path).state()
        self.assertEqual(restored['selected_case_ids'],['case1','case3','case4'])
        self.assertEqual(restored['answers']['q2']['markdown'],'保留的旧选题草稿')
    def test_case_score_is_75_and_45_passes(self):
        self.prepare();self.submit(['case1','case2','case4']);result=self.grade(self.evaluation(9))
        self.assertEqual((result['reference_score'],result['max_score']),(45,75))
        self.assertEqual(result['exam_outcome']['status'],'pass')
        self.assertEqual(set(result['questions']),{'q1','q2','q4'})
        self.assertEqual(set(result['reference_answers']),{'q1','q2','q4'})
        self.assertEqual(result['weaknesses']['questions'][0]['question_id'],'q4')
        self.assertEqual(result['weaknesses']['dimensions'][0]['name'],'考点4')
    def test_below_45_fails(self):
        self.prepare();self.submit(['case1','case2','case4'])
        self.assertEqual(self.grade(self.evaluation(8))['exam_outcome']['status'],'fail')
    def test_pending_never_becomes_failure_or_known_loss(self):
        self.prepare();self.submit(['case1','case2','case4']);result=self.grade(self.evaluation(9,True))
        self.assertIsNone(result['reference_score']);self.assertEqual(result['exam_outcome']['status'],'pending')
        losses={q['question_id']:q['lost'] for q in result['weaknesses']['questions']}
        self.assertEqual(losses['q2'],0)
    def test_unselected_points_cannot_be_graded(self):
        self.prepare();self.submit(['case1','case2','case4']);evaluation=self.evaluation()
        evaluation['decisions'].append({'point_id':'q3-p0','status':'omitted','comment':'未选题'})
        with self.assertRaises(lab.LabError):self.grade(evaluation)
    def test_selection_is_frozen_after_submission(self):
        self.prepare();state=self.submit(['case1','case2','case4'])
        with self.assertRaises(lab.LabError):self.action('save',selected_case_ids=['case1','case3','case5'])
        self.assertEqual(lab.read(self.path/'submission.json')['selected_case_ids'],state['selected_case_ids'])
    def test_unequal_elective_totals_are_rejected(self):
        def mutate(p,r):p['cases'][4]['max_score']=30;p['cases'][4]['questions'][0]['max_score']=30;r['points'][-1]['weight']=10
        with self.assertRaisesRegex(lab.LabError,'分值'):self.prepare(mutate=mutate)
    def test_formal_paper_flag_rejects_practice_pack(self):
        self.prepare(mutate=lambda p,r:p.pop('exam'))
        with self.assertRaisesRegex(lab.LabError,'年度真题'):
            lab.prepare(self.root/'other',self.root/'pack.json',self.root/'rubric.json',paper_kind='case-analysis')
    def test_formal_paper_cannot_use_125_point_total(self):
        def mutate(p,r):p['exam'].update(choose_count=4,max_score=125)
        with self.assertRaisesRegex(lab.LabError,'满分为75'):self.prepare(mutate=mutate)
    def test_practice_pack_keeps_all_questions(self):
        self.prepare(mutate=lambda p,r:p.pop('exam'));self.submit([f'case{i}' for i in range(1,6)])
        result=self.grade(self.evaluation(15));self.assertEqual(result['max_score'],125);self.assertIsNone(result['exam_outcome'])
    def test_missing_complete_reference_answer_blocks_report(self):
        self.prepare(mutate=lambda p,r:r.pop('reference_answers'));self.submit(['case1','case2','case4'])
        with self.assertRaisesRegex(lab.LabError,'完整参考答案'):self.grade(self.evaluation())
        self.assertFalse((self.path/'grade.json').exists())
    def test_essay_choose_one_and_requirement_coverage(self):
        self.prepare(essay=True);self.submit(['case2']);result=self.grade(self.evaluation(3))
        self.assertEqual((result['reference_score'],result['max_score']),(45,75))
        self.assertEqual(set(result['questions']),{'q2'})
        self.assertEqual([t['status'] for t in result['essay_review']['q2']['requirements']],['met','met','not-met'])
        self.assertTrue(all(result['essay_review']['q2']['within_limits'].values()))
        self.assertIn('## 正文',result['reference_answers']['q2']['markdown'])
    def test_essay_rejects_multiple_selections(self):
        self.prepare(essay=True)
        with self.assertRaises(lab.LabError):self.action('start',selected_case_ids=['case1','case2'])
    def test_essay_requires_task_point_mapping(self):
        with self.assertRaisesRegex(lab.LabError,'审题要求'):self.prepare(essay=True,mutate=lambda p,r:r.pop('essay_requirements'))
    def test_essay_parts_must_match_evidence_text(self):
        self.prepare(essay=True);self.action('start',selected_case_ids=['case2']);answers=self.engine.state()['answers']
        answers['q2']['essay']['body']='未对应的正文'
        with self.assertRaisesRegex(lab.LabError,'证据原文'):self.action('save',answers=answers)
    def test_essay_outline_is_not_a_full_reference_essay(self):
        self.prepare(essay=True,mutate=lambda p,r:r['reference_answers']['q2'].pop('essay'));self.submit(['case2'])
        with self.assertRaisesRegex(lab.LabError,'参考范文'):self.grade(self.evaluation())
    def test_offline_import_keeps_selected_paper(self):
        self.prepare();submitted=self.submit(['case1','case3','case5'])
        exported=lab.read(self.path/'submission.json');lab.atomic(self.root/'export.json',exported)
        draft=copy.deepcopy(submitted);draft.update(status='draft',started_at=None,revision=0,selected_case_ids=['case1'])
        draft.pop('submission_hash',None);(self.path/'submission.json').unlink();lab.atomic(self.path/'state.json',draft)
        call=subprocess.run([sys.executable,str(REPO/'skills/soft-exam-lab/scripts/lab.py'),'import-answer','--session',str(self.path),'--file',str(self.root/'export.json')],capture_output=True,text=True)
        self.assertEqual(call.returncode,0,call.stderr)
        self.assertEqual(lab.read(self.path/'submission.json')['selected_case_ids'],['case1','case3','case5'])

if __name__=='__main__':unittest.main()
