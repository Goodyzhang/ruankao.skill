"""Evidence highlights and risk notes do not modify scoring or frozen answers."""
import copy
import unittest
import test_soft_exam_lab as fixture_module

lab = fixture_module.lab


class AnnotationTests(unittest.TestCase):
    setUp = fixture_module.LabTests.setUp
    tearDown = fixture_module.LabTests.tearDown
    action = fixture_module.LabTests.action
    submit = fixture_module.LabTests.submit
    evaluation = fixture_module.LabTests.evaluation
    run_grade = fixture_module.LabTests.run_grade

    def evidence(self, text):
        phrase = '提交成功'
        start = text.index(phrase)
        return {'kind':'text', 'start':0, 'end':len(text), 'quote':text,
                'focus':[{'start':start, 'end':start+len(phrase), 'quote':phrase}]}

    def test_precise_focus_is_persisted_without_changing_the_answer(self):
        text = '😀 背景。提交成功，再删除。'
        self.submit({'q-write':text})
        frozen = (self.path/'submission.json').read_bytes()
        evaluation = self.evaluation()
        evidence = self.evidence(text)
        evaluation['decisions'][0].update(status='awarded', evidence=[evidence])
        result = self.run_grade(evaluation)
        self.assertEqual(result['results'][0]['evidence'][0]['focus'], evidence['focus'])
        self.assertEqual(result['reference_score'], 1)
        self.assertEqual((self.path/'submission.json').read_bytes(), frozen)

    def test_outside_wrong_or_empty_focus_is_rejected(self):
        text = '提交成功。'
        self.submit({'q-write':text})
        for focus in ([], [{'start':0,'end':20,'quote':text}], [{'start':0,'end':4,'quote':'没有写过'}]):
            evaluation = self.evaluation()
            evidence = self.evidence(text); evidence['focus'] = focus
            evaluation['decisions'][0].update(status='awarded', evidence=[evidence])
            with self.assertRaises(lab.LabError):
                self.run_grade(evaluation)
        self.assertFalse((self.path/'grade.json').exists())

    def test_risk_note_does_not_deduct_scores(self):
        text = '提交成功，一般不会出现问题。'
        self.submit({'q-write':text})
        evaluation = self.evaluation()
        evaluation['decisions'][0].update(status='awarded', evidence=[self.evidence(text)])
        baseline = self.run_grade(evaluation)
        evaluation['warnings'] = [{'question_id':'q-write', 'point_id':'p-order',
            'comment':'建议说明失败边界，避免把通常情况写成保证。',
            'source':'题目明确要求说明失败分支', 'evidence':self.evidence(text)}]
        result = self.run_grade(evaluation)
        for field in ('reference_score','training_score','questions','penalties','reference_penalties'):
            self.assertEqual(result[field],baseline[field])
        self.assertEqual(result['warnings'],evaluation['warnings'])

    def test_risk_note_cannot_smuggle_a_deduction_or_another_question(self):
        text = '提交成功。'
        self.submit({'q-write':text})
        base = {'question_id':'q-write','comment':'说明前提','source':'本题约定','evidence':self.evidence(text)}
        for change in ({'amount':1}, {'question_id':'unselected'}, {'point_id':'p-ttl'}):
            evaluation = self.evaluation();evaluation['warnings'] = [dict(base,**change)]
            with self.assertRaises(lab.LabError):
                self.run_grade(evaluation)

    def test_training_penalty_focus_also_requires_exact_source(self):
        text = '提交成功。'
        self.submit({'q-write':text})
        evaluation = self.evaluation()
        evidence = self.evidence(text);evidence['focus'][0]['quote'] = '错误引文'
        evaluation['extra_errors'] = [{'question_id':'q-write','cause_id':'example','comment':'验收错误',
            'source':'自编题要求','evidence':evidence}]
        with self.assertRaises(lab.LabError):
            self.run_grade(evaluation)

    def test_essay_uses_canonical_markdown_offsets(self):
        parts = {'abstract':'项目摘要😀。','body':'必须提交成功，然后删除缓存。'}
        answer = {'markdown':lab.essay_markdown(parts)}
        lab.validate_text_evidence(self.evidence(answer['markdown']),answer)
        bad = copy.deepcopy(self.evidence(answer['markdown']))
        bad['focus'][0]['start'] = parts['body'].index('提交成功')
        with self.assertRaises(lab.LabError):
            lab.validate_text_evidence(bad,answer)
