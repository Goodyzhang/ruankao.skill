/* Classic script: also export pure state operations for Node contract checks. */
(function (root) {
  'use strict';
  const clean = text => String(text).replace(/\s+/g, ' ').trim();
  function keyFor(book, chapter, section) {
    const ids = [book, chapter, section];
    if (ids.some(id => typeof id !== 'string' || !id.trim())) throw new Error('缺少书册、章节或小节 ID');
    return 'ruankao-review:v1:' + ids.map(encodeURIComponent).join(':');
  }
  function validate(questions) {
    const ids = new Set();
    questions.forEach(q => {
      const values = q.options.map(option => option.value);
      if (!q.id || !q.version || ids.has(q.id) || values.length < 2 ||
          new Set(values).size !== values.length || !values.includes(q.answer)) {
        throw new Error('题目 ID、版本、选项或答案配置有误：' + q.id);
      }
      ids.add(q.id);
    });
  }
  // Only assessment content affects progress; prose and option order do not.
  function signature(q) {
    const options = q.options.map(o => [o.value, clean(o.text)])
      .sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
    return JSON.stringify([clean(q.prompt), options, q.answer]);
  }
  function restore(raw, questions) {
    if (raw === null) return { answers: Object.create(null), expired: 0 };
    const saved = JSON.parse(raw);
    if (!saved || saved.schema !== 1 || !saved.answers || typeof saved.answers !== 'object' || Array.isArray(saved.answers)) {
      throw new Error('不支持的进度格式');
    }
    const answers = Object.create(null);
    let expired = 0;
    questions.forEach(q => {
      const item = Object.hasOwn(saved.answers, q.id) ? saved.answers[q.id] : null;
      if (!item) return;
      if (item.version === q.version && item.signature === signature(q) && q.options.some(o => o.value === item.choice)) {
        answers[q.id] = item;
      } else expired += 1;
    });
    return { answers, expired };
  }
  function createSession(questions, storage, key) {
    validate(questions);
    let answers = Object.create(null);
    let status = '尚未作答。进度仅尝试保存在当前浏览器，不会跨设备同步。';
    try {
      if (!storage) throw new Error('storage unavailable');
      const result = restore(storage.getItem(key), questions);
      answers = result.answers;
      if (Object.keys(answers).length) status = '已恢复本小节进度。进度仅保存在当前浏览器。';
      if (result.expired) status = result.expired + ' 道题已修订，需要重新作答；其他题进度保留。';
    } catch (error) {
      status = '无法读取本地进度，本次从空白开始。作答后将尝试保存；刷新可能丢失。';
    }
    function save() {
      try {
        if (!storage) throw new Error('storage unavailable');
        storage.setItem(key, JSON.stringify({ schema: 1, answers }));
        status = '已保存到当前浏览器。清理浏览器数据、改用浏览器或设备可能使进度不可用。';
        return true;
      } catch (error) {
        status = '本地保存失败；本页仍可作答，但刷新或关闭后可能丢失本次进度。';
        return false;
      }
    }
    return {
      snapshot: () => JSON.parse(JSON.stringify(answers)),
      status: () => status,
      answer(id, choice) {
        const q = questions.find(item => item.id === id);
        if (!q || !q.options.some(option => option.value === choice)) throw new Error('无效题目或选项');
        answers[id] = { version: q.version, signature: signature(q), choice };
        return save();
      },
      retry(id) { delete answers[id]; return save(); },
      reset() { answers = Object.create(null); return save(); }
    };
  }
  const api = { keyFor, validate, signature, restore, createSession };
  root.ReviewQuizState = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
