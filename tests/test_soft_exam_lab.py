"""Observable persistence, isolation, score arithmetic and evidence invariants."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import time

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'skills/soft-exam-lab'
spec = importlib.util.spec_from_file_location('lab', SKILL / 'scripts/lab.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def fixtures():
    pack = {'schema_version': 1, 'id': 'acceptance-pack', 'version': '1', 'title': '案例实验室 · 自编验收场景',
            'scoring_notice': '自编验收题；可靠题干定义的训练评分表。不是历年真题。', 'cases': [{
                'id': 'case-cache', 'title': '库存查询服务（自编验收）', 'complete': True, 'max_score': 6,
                'source': {'kind': 'authored', 'label': '自编验收样例', 'locator': '本包题干定义，版本1'},
                'stem': '某库存查询服务采用写后删除缓存。题干规定：数据库是事实来源；写入流程必须先成功提交数据库，再删除旧缓存。令缓存TTL为60秒，TTL只限制旧值最长生存期，不能保证实时一致。客户端向服务端发起请求，服务端返回响应。请按本题约定回答全部小问。',
                'figures': [], 'questions': [
                    {'id': 'q-write', 'title': '问题1：写入顺序', 'complete': True, 'max_score': 2, 'prompt': '说明写入和删除缓存的先后关系，以及数据库提交失败时是否删除缓存。'},
                    {'id': 'q-ttl', 'title': '问题2：缓存一致性', 'complete': True, 'max_score': 2, 'prompt': '说明TTL为60秒的含义，以及是否保证实时一致。'},
                    {'id': 'q-arrow', 'title': '问题3：通信方向', 'complete': True, 'max_score': 2, 'prompt': '用文字或图示分别表示请求和响应的方向。'}]}]}
    points = [
        ('p-order','q-write','写后删除顺序','数据库先提交成功，再删除旧缓存。','必须明确成功提交在前','写入顺序'),
        ('p-fail','q-write','失败分支','数据库提交失败，不执行本次删除缓存。','提交失败条件','写入顺序'),
        ('p-ttl','q-ttl','TTL边界','旧缓存最多生存60秒（按本题定义）。','时长与旧缓存对象','缓存边界'),
        ('p-consistency','q-ttl','实时一致','TTL不保证实时一致。','不保证的边界','缓存边界'),
        ('p-request','q-arrow','请求方向','客户端 → 服务端。','请求对象和方向','通信方向'),
        ('p-response','q-arrow','响应方向','服务端 → 客户端。','响应对象和方向','通信方向')]
    rubric = {'schema_version':1,'pack_id':pack['id'],'pack_version':'1','version':'1','basis':'inferred-training',
              'answer_source':{'reliable':True,'locator':'本自编题的显式系统约定','level':'authored-fixture'},
              'training_policy':'unit-weight-deduplicated-v1','points':[{'id':pid,'question_id':qid,'weight':1,'criterion':name,'correct':correct,'conditions':[cond],'equivalents':['保持条件与机制一致的专业同义表述'],'dimension':dim,'source':'自编题干版本1'} for pid,qid,name,correct,cond,dim in points]}
    rubric['reference_answers'] = {qid: {'origin':'source', 'source':'本自编题的显式系统约定', 'markdown':'\n\n'.join(p['correct'] for p in rubric['points'] if p['question_id']==qid)} for qid in lab.questions(pack)}
    return pack,rubric


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.pack,self.rubric=fixtures()
        lab.atomic(self.root/'pack.json',self.pack);lab.atomic(self.root/'rubric.json',self.rubric)
        self.path=lab.prepare(self.root/'archive',self.root/'pack.json',self.root/'rubric.json')
        self.e=lab.Session(self.path)
    def tearDown(self): self.temp.cleanup()
    def action(self, action, **kw):
        s=self.e.state();return self.e.update(action,dict(attempt_id=s['attempt_id'],revision=s['revision'],**kw))
    def submit(self,text=None):
        self.action('start');a=self.e.state()['answers'];
        for qid in a:a[qid]['markdown']=(text or {}).get(qid,'')
        return self.action('submit',answers=a)
    def evaluation(self,status='omitted'):
        s=self.e.state();sub=lab.read(self.path/'submission.json')
        return {'schema_version':1,'attempt_id':s['attempt_id'],'submission_hash':lab.digest(sub),'rubric_hash':s['rubric_hash'],'reviewer':'current-agent','self_check':{'evidence':'全部逐点反查'},'decisions':[{'point_id':p['id'],'status':status,'comment':'验收判定'} for p in self.rubric['points']], 'extra_errors':[]}
    def run_grade(self,d):
        lab.atomic(self.root/'eval.json',d);return lab.grade(self.path,self.root/'eval.json')
    def test_default_resume_does_not_reset_draft(self):
        self.action('start');a=self.e.state()['answers'];a['q-write']['markdown']='已有草稿';self.action('save',answers=a)
        p=lab.prepare(self.root/'archive',self.root/'pack.json',self.root/'rubric.json');self.assertEqual(p,self.path);self.assertEqual(lab.Session(p).state()['answers']['q-write']['markdown'],'已有草稿')
    def test_new_attempt_preserves_old_and_is_empty(self):
        self.submit({'q-write':'旧答案'});p=lab.prepare(self.root/'archive',self.root/'pack.json',self.root/'rubric.json',new=True)
        self.assertNotEqual(p,self.path);self.assertTrue((self.path/'submission.json').exists());self.assertTrue(all(not a['markdown'] for a in lab.Session(p).state()['answers'].values()))
    def test_resume_submitted_continues_grading(self):
        self.submit();self.assertEqual(lab.prepare(self.root/'archive',self.root/'pack.json',self.root/'rubric.json'),self.path)
    def test_true_question_unconfirmed_rejected(self):
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root,True)
    def test_missing_figure_rejected(self):
        self.pack['cases'][0]['figures']=[{'file':'missing.png','caption':'题图','source_locator':'原件页1'}]
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root)
    def test_missing_answer_rejected(self):
        self.rubric['answer_source']['reliable']=False
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root)
    def test_incomplete_question_rejected(self):
        self.pack['cases'][0]['questions'][0]['prompt']='待补充'
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root)
    def test_three_cases_and_shortage(self):
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root,count=3)
        for i in (2,3):
            c=copy.deepcopy(self.pack['cases'][0]);c['id']+=str(i)
            for q in c['questions']:
                old=q['id'];q['id']+=str(i)
                for p in list(self.rubric['points']):
                    if p['question_id']==old:
                        p=copy.deepcopy(p);p['id']+=str(i);p['question_id']=q['id'];self.rubric['points'].append(p)
            self.pack['cases'].append(c)
        lab.validate_pack(self.pack,self.rubric,self.root,count=3)
    def test_false_submitted_card_cannot_grade(self):
        with self.assertRaises(lab.LabError):self.run_grade({'status':'submitted'})
    def test_disk_failure_does_not_submit(self):
        self.action('start')
        with patch.object(lab,'atomic',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.action('submit')
        self.assertEqual(self.e.state()['status'],'draft');self.assertFalse((self.path/'submission.json').exists())
    def test_idempotent_submit_and_postsubmit_edit_rejected(self):
        s=self.submit({'q-write':'正文'});before=(self.path/'submission.json').read_bytes();self.action('submit');self.assertEqual(before,(self.path/'submission.json').read_bytes())
        with self.assertRaises(lab.LabError):self.action('save',answers=s['answers'])
    def test_cross_session_and_stale_revision_rejected(self):
        with self.assertRaises(lab.LabError):self.e.update('save',{'attempt_id':'other','revision':0})
        self.action('start')
        with self.assertRaises(lab.LabError):self.e.update('save',{'attempt_id':self.e.state()['attempt_id'],'revision':0})
    def test_frozen_rubric_modification_rejected(self):
        self.rubric['points'][0]['weight']=20;lab.atomic(self.path/'rubric-v1.json',self.rubric)
        with self.assertRaises(lab.LabError):self.action('start')
    def test_submit_commit_interruption_recovered(self):
        self.action('start');original=lab.atomic
        def fail(path,value):
            if Path(path).name=='state.json':raise OSError('interrupted')
            original(path,value)
        with patch.object(lab,'atomic',side_effect=fail):
            with self.assertRaises(OSError):self.action('submit')
        self.e.recover();self.assertEqual(self.e.state()['status'],'submitted')
    def test_timer_pause_and_refresh(self):
        with patch.object(lab.time,'time',return_value=100):self.action('start')
        with patch.object(lab.time,'time',return_value=110):self.action('pause')
        other=lab.Session(self.path)
        with patch.object(lab.time,'time',return_value=130):other.update('pause',{'attempt_id':other.state()['attempt_id'],'revision':other.state()['revision']})
        with patch.object(lab.time,'time',return_value=140):s=self.action('submit')
        self.assertEqual(s['elapsed_seconds'],20)
    def test_timed_deadline_submits_last_saved(self):
        p=lab.prepare(self.root/'timed',self.root/'pack.json',self.root/'rubric.json',mode='timed',minutes=1);e=lab.Session(p)
        with patch.object(lab.time,'time',return_value=100):e.update('start',{'attempt_id':e.state()['attempt_id'],'revision':0})
        with patch.object(lab.time,'time',return_value=161):e.expire()
        self.assertEqual(e.state()['status'],'submitted');self.assertEqual(e.state()['submission_reason'],'deadline')
    def test_blank_answers_are_zero(self):
        self.submit();r=self.run_grade(self.evaluation());self.assertEqual(r['reference_score'],0);self.assertEqual(r['training_score'],0)
    def test_pending_not_zero(self):
        self.submit();d=self.evaluation();d['decisions'][0].update(status='pending',pending_reason='解析有争议');r=self.run_grade(d)
        self.assertIsNone(r['reference_score']);self.assertIsNone(r['training_score']);self.assertEqual(self.e.state()['status'],'submitted')
    def test_award_without_evidence_rejected(self):
        self.submit();
        with self.assertRaises(lab.LabError):self.run_grade(self.evaluation('awarded'))
    def test_bad_text_location_rejected(self):
        self.submit({'q-write':'数据库'});d=self.evaluation();d['decisions'][0].update(status='awarded',evidence=[{'kind':'text','start':0,'end':3,'quote':'错误文'}])
        with self.assertRaises(lab.LabError):self.run_grade(d)
    def test_scores_dimensions_and_dedup_penalties(self):
        text={'q-write':'先提交成功，再删除。失败不删除。额外错误','q-ttl':'最长60秒，不保证实时一致。','q-arrow':'请求客户端到服务端，响应服务端到客户端。'}
        self.submit(text);d=self.evaluation('awarded')
        for x,p in zip(d['decisions'],self.rubric['points']):
            a=text[p['question_id']];x['evidence']=[{'kind':'text','start':0,'end':len(a),'quote':a}]
        d['extra_errors']=[{'question_id':'q-write','cause_id':'e1','comment':'额外错误','source':'题干约定','evidence':{'kind':'text','start':text['q-write'].index('额外错误'),'end':len(text['q-write']),'quote':'额外错误'}}]*2
        r=self.run_grade(d);self.assertEqual(r['reference_score'],6);self.assertEqual(r['training_score'],5);self.assertEqual([x['amount'] for x in r['penalties']],[1,0]);self.assertEqual(sum(v['earned'] for v in r['dimensions'].values()),6)
    def test_lost_point_error_not_double_penalized(self):
        text={'q-write':'先删除缓存'};self.submit(text);d=self.evaluation();e={'kind':'text','start':0,'end':5,'quote':'先删除缓存'}
        d['decisions'][0].update(status='incorrect',cause_id='order',evidence=[e]);d['extra_errors']=[{'question_id':'q-write','point_id':'p-order','cause_id':'order','comment':'顺序错','source':'题干','evidence':e}]
        r=self.run_grade(d);self.assertEqual(r['penalties'][0]['amount'],0)
    def test_repeated_grading_preserves_report_and_submission(self):
        self.submit();before=(self.path/'submission.json').read_bytes();d=self.evaluation();self.run_grade(d);self.run_grade(d)
        self.assertEqual(before,(self.path/'submission.json').read_bytes());self.assertEqual(len(list((self.path/'reviews').glob('*.json'))),1)
    def test_finalize_requires_receipt_and_clears_only_current(self):
        self.submit();r=self.run_grade(self.evaluation());receipt={'attempt_id':self.e.state()['attempt_id'],'grade_hash':lab.digest(r),'covered_points':[],'files':[]};lab.atomic(self.root/'receipt.json',receipt)
        with self.assertRaises(lab.LabError):lab.finalize(self.path,self.root/'receipt.json')
        note=self.root/'note.md';note.write_text(self.e.state()['attempt_id'],encoding='utf8');receipt.update(covered_points=[p['id'] for p in self.rubric['points']],files=[{'path':str(note),'sha256':lab.hashlib.sha256(note.read_bytes()).hexdigest()}]);lab.atomic(self.root/'receipt.json',receipt)
        lab.finalize(self.path,self.root/'receipt.json');self.assertFalse((self.path.parent/'active.json').exists());self.assertTrue((self.path/'public/report.html').exists());public=(self.path/'public/index.html').read_text(encoding='utf-8');payload=json.loads(public.split('<script id="lab-data" type="application/json">')[1].split('</script>')[0]);self.assertEqual(payload['mode'],'report');self.assertEqual(payload['state']['answers'],lab.read(self.path/'submission.json')['answers']);lab.finalize(self.path,self.root/'receipt.json')

    def test_tampered_submission_cannot_finalize(self):
        self.submit();r=self.run_grade(self.evaluation());sub=lab.read(self.path/'submission.json');sub['answers']['q-write']['markdown']='changed';lab.atomic(self.path/'submission.json',sub)
        lab.atomic(self.root/'receipt.json',{'attempt_id':self.e.state()['attempt_id'],'grade_hash':lab.digest(r),'covered_points':[],'files':[]})
        with self.assertRaises(lab.LabError):lab.finalize(self.path,self.root/'receipt.json')
    def test_original_deduction_requires_frozen_rule(self):
        self.submit({'q-write':'extra error'});d=self.evaluation();d['reference_errors']=[{'rule_id':'unknown','cause_id':'e1','comment':'error','evidence':{'kind':'text','start':0,'end':5,'quote':'extra'}}]
        with self.assertRaises(lab.LabError):self.run_grade(d)
    def test_diagram_without_rendered_image_rejected(self):
        self.action('start');a=self.e.state()['answers'];a['q-arrow']['scene']={'elements':[{'id':'arrow1','type':'arrow'}],'files':{}}
        with self.assertRaises(lab.LabError):self.action('save',answers=a)
    def test_empty_canvas_can_save(self):
        self.action('start');a=self.e.state()['answers'];a['q-arrow']['scene']={'elements':[],'files':{}};self.action('save',answers=a)
    def test_unknown_question_rejected(self):
        self.action('start');a=self.e.state()['answers'];a['q-other']=a['q-write']
        with self.assertRaises(lab.LabError):self.action('save',answers=a)
    def test_submission_survives_agent_restart(self):
        self.submit();other=lab.Session(self.path);other.recover();self.assertEqual(other.state()['status'],'submitted');self.assertEqual(other.state()['submission_hash'],lab.digest(lab.read(self.path/'submission.json')))

    def test_fixed_semantic_judgments_arithmetic_and_evidence(self):
        matrix=lab.read(REPO/'tests/lab-fixtures/semantic-cases.json')
        for case in matrix['cases']:
            with self.subTest(case=case['name']):
                path=lab.prepare(self.root/'matrix',self.root/'pack.json',self.root/'rubric.json',new=True);engine=lab.Session(path);st=engine.state()
                engine.update('start',{'attempt_id':st['attempt_id'],'revision':st['revision']});st=engine.state();answers=st['answers']
                for qid in answers:answers[qid]['markdown']=case['answers'][qid]
                engine.update('submit',{'attempt_id':st['attempt_id'],'revision':st['revision'],'answers':answers});st=engine.state();sub=lab.read(path/'submission.json')
                decisions=[]
                for p,status in zip(self.rubric['points'],case['statuses']):
                    text=answers[p['question_id']]['markdown'];d={'point_id':p['id'],'status':status,'comment':'Current Agent fixed semantic baseline'}
                    if status in ('awarded','incorrect'):d['evidence']=[{'kind':'text','start':0,'end':len(text),'quote':text}]
                    if status=='pending':d['pending_reason']='Reference conflict fixture'
                    decisions.append(d)
                extras=[]
                if case.get('extra_error'):
                    text=answers['q-ttl']['markdown'];phrase=case['extra_error'];start=text.index(phrase);error={'question_id':'q-ttl','cause_id':'database-source','source':'Authored prompt','comment':'Contradicts explicit source-of-truth assumption','evidence':{'kind':'text','start':start,'end':start+len(phrase),'quote':phrase}};extras=[error]*(2 if case['name']=='重复额外错误' else 1)
                evaluation={'schema_version':1,'attempt_id':st['attempt_id'],'submission_hash':lab.digest(sub),'rubric_hash':st['rubric_hash'],'reviewer':'current-agent','self_check':{'semantic':'Manually reviewed baseline; scripts validate math only'},'decisions':decisions,'extra_errors':extras}
                file=self.root/'matrix-eval.json';lab.atomic(file,evaluation);result=lab.grade(path,file);self.assertEqual(result['reference_score'],case['reference']);self.assertEqual(result['training_score'],case['training'])

    def test_reference_answer_cannot_leak_into_public_pack(self):
        self.pack['cases'][0]['questions'][0]['answer']='private answer'
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root)
    def test_private_rubric_cannot_be_nested_in_pack(self):
        self.pack['rubric']=self.rubric
        with self.assertRaises(lab.LabError):lab.validate_pack(self.pack,self.rubric,self.root)
    def test_evaluation_cannot_override_frozen_weight(self):
        self.submit();d=self.evaluation();d['decisions'][0]['weight']=100
        with self.assertRaises(lab.LabError):self.run_grade(d)
    def test_original_deduction_arithmetic(self):
        r=copy.deepcopy(self.rubric);r['reference_deductions']=[{'id':'source-rule','question_id':'q-write','amount':0.5,'source':'Authored scoring-rule fixture'}];lab.atomic(self.root/'with-rule.json',r)
        p=lab.prepare(self.root/'with-rule',self.root/'pack.json',self.root/'with-rule.json');e=lab.Session(p);st=e.state();e.update('start',{'attempt_id':st['attempt_id'],'revision':st['revision']});st=e.state();a=st['answers']
        for q in a:a[q]['markdown']='Fixture answer and separate error'
        e.update('submit',{'attempt_id':st['attempt_id'],'revision':st['revision'],'answers':a});st=e.state();sub=lab.read(p/'submission.json');ev={'schema_version':1,'attempt_id':st['attempt_id'],'submission_hash':lab.digest(sub),'rubric_hash':st['rubric_hash'],'reviewer':'current-agent','self_check':{'arithmetic':'Provided rule only'},'decisions':[{'point_id':point['id'],'status':'awarded','comment':'Fixed judgment fixture','evidence':[{'kind':'text','start':0,'end':7,'quote':'Fixture'}]} for point in r['points']],'reference_errors':[{'rule_id':'source-rule','cause_id':'error-1','comment':'Separate provided-rule error','evidence':{'kind':'text','start':19,'end':27,'quote':'separate'}}]}
        text=a['q-write']['markdown'];start=text.index('separate');ev['reference_errors'][0]['evidence']={'kind':'text','start':start,'end':start+8,'quote':'separate'};lab.atomic(self.root/'source-eval.json',ev);result=lab.grade(p,self.root/'source-eval.json');self.assertEqual(result['reference_score'],5.5);self.assertEqual(result['training_score'],5.5)

if __name__=='__main__':unittest.main()
