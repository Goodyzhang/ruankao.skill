const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('../skills/soft-exam-review-book/assets/reader/quiz-state.js');
function questions() {
  return ['one', 'two'].map(id => ({ id, version: '1', prompt: 'Question ' + id, answer: 'a', explanation: 'Because A.', options: [{ value: 'a', text: 'A' }, { value: 'b', text: 'B' }] }));
}
function memory() { const values = new Map(); return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) }; }
test('stable IDs survive article revisions and question reordering', () => {
  const storage = memory(); const key = api.keyFor('book', '02', 's1');
  const first = api.createSession(questions(), storage, key); first.answer('one', 'b'); first.answer('two', 'a');
  const next = api.createSession(questions().reverse(), storage, key);
  assert.equal(next.snapshot().one.choice, 'b'); assert.equal(next.snapshot().two.choice, 'a');
});
test('a content change invalidates only the revised question even if version was forgotten', () => {
  const storage = memory(); const first = api.createSession(questions(), storage, 'key'); first.answer('one', 'a'); first.answer('two', 'b');
  const changed = questions(); changed[0].prompt = 'New question';
  const next = api.createSession(changed, storage, 'key');
  assert.equal(next.snapshot().one, undefined); assert.equal(next.snapshot().two.choice, 'b'); assert.match(next.status(), /1 道题已修订/);
});
test('explicit version, option content and answer changes invalidate only their own question', () => {
  for (const revise of [q => q.version = '2', q => q.answer = 'b', q => q.options[0].text = 'Revised option']) {
    const storage = memory(); const first = api.createSession(questions(), storage, 'key'); first.answer('one', 'a'); first.answer('two', 'b');
    const changed = questions(); revise(changed[1]);
    const next = api.createSession(changed, storage, 'key'); assert.equal(next.snapshot().one.choice, 'a'); assert.equal(next.snapshot().two, undefined);
  }
});
test('explanation-only polishing restores both existing choices', () => {
  const storage = memory(); const first = api.createSession(questions(), storage, 'key'); first.answer('one', 'a'); first.answer('two', 'b');
  const changed = questions(); changed[0].explanation = 'A clearer explanation, with an extra example.';
  const next = api.createSession(changed, storage, 'key');
  assert.equal(next.snapshot().one.choice, 'a'); assert.equal(next.snapshot().two.choice, 'b'); assert.match(next.status(), /已恢复/);
});
test('reordering options with stable values restores choices without mutating input order', () => {
  const storage = memory(); const first = api.createSession(questions(), storage, 'key'); first.answer('one', 'b'); first.answer('two', 'a');
  const changed = questions(); changed[0].options.reverse();
  const next = api.createSession(changed, storage, 'key');
  assert.equal(next.snapshot().one.choice, 'b'); assert.equal(next.snapshot().two.choice, 'a');
  assert.deepEqual(changed[0].options.map(o => o.value), ['b', 'a']);
});
test('same question IDs remain independent across sections and books', () => {
  const storage = memory(); const k1 = api.keyFor('book', '02', 's1'); const k2 = api.keyFor('book', '02', 's2');
  const one = api.createSession(questions(), storage, k1); one.answer('one', 'b');
  assert.deepEqual(api.createSession(questions(), storage, k2).snapshot(), {});
  assert.notEqual(k1, api.keyFor('other-book', '02', 's1'));
  const two = api.createSession(questions(), storage, k2); two.answer('one', 'a'); two.reset();
  assert.equal(api.createSession(questions(), storage, k1).snapshot().one.choice, 'b');
});
test('storage refusal retains this-page answers and gives an honest failure message', () => {
  const unavailable = { getItem() { throw new Error('denied'); }, setItem() { throw new Error('quota'); } };
  for (const storage of [unavailable, null]) {
    const session = api.createSession(questions(), storage, 'key'); assert.match(session.status(), /无法读取/);
    assert.equal(session.answer('one', 'a'), false); assert.equal(session.snapshot().one.choice, 'a'); assert.match(session.status(), /保存失败/);
  }
});
test('corrupt or unknown storage starts blank without claiming restoration', () => {
  for (const raw of ['{bad', '{"schema":99,"answers":{}}', 'null']) {
    const storage = { getItem: () => raw, setItem() {} };
    const session = api.createSession(questions(), storage, 'key'); assert.deepEqual(session.snapshot(), {}); assert.match(session.status(), /无法读取/);
  }
});
test('retry removes only one answer; invalid choices cannot corrupt saved progress', () => {
  const session = api.createSession(questions(), memory(), 'key'); session.answer('one', 'a'); session.answer('two', 'b'); session.retry('one');
  assert.equal(session.snapshot().one, undefined); assert.equal(session.snapshot().two.choice, 'b');
  assert.throws(() => session.answer('two', 'missing')); assert.equal(session.snapshot().two.choice, 'b');
});
test('duplicate IDs fail visibly; whitespace-only edits preserve content signatures', () => {
  const bad = questions(); bad[1].id = bad[0].id; assert.throws(() => api.createSession(bad, memory(), 'key'), /配置有误/);
  const a = questions()[0]; const b = { ...a, prompt: '  Question\n one ' }; assert.equal(api.signature(a), api.signature(b));
  assert.throws(() => api.keyFor('book', '02', ''), /缺少/);
});
