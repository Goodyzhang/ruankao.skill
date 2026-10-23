(function () {
  'use strict';
  const panels = [...document.querySelectorAll('[data-panel]')];
  const tabs = [...document.querySelectorAll('[data-tab]')];
  function visitHash(scroll) {
    let id = '';
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (error) { /* Invalid hash: show the article. */ }
    const target = document.getElementById(id);
    const active = target && target.closest('[data-panel]') || panels[0];
    panels.forEach(panel => { panel.hidden = panel !== active; });
    tabs.forEach(tab => {
      const selected = active && tab.getAttribute('aria-controls') === active.id;
      tab.setAttribute('aria-selected', String(Boolean(selected)));
      tab.tabIndex = selected ? 0 : -1;
    });
    if (target) {
      for (let parent = target.parentElement; parent; parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS') parent.open = true;
      }
      if (scroll) requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
    }
    document.querySelectorAll('.outline a').forEach(link => {
      const url = new URL(link.href);
      const current = url.pathname === location.pathname && url.hash === location.hash;
      if (current) link.setAttribute('aria-current', 'location');
      else if (link.getAttribute('aria-current') === 'location') link.removeAttribute('aria-current');
    });
  }
  if (panels.length) {
    document.querySelector('[data-tabs]').hidden = false;
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const hash = '#' + tab.getAttribute('aria-controls');
        if (location.hash === hash) visitHash(true);
        else location.hash = hash;
      });
      tab.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        let index = tabs.indexOf(tab);
        if (event.key === 'Home') index = 0;
        else if (event.key === 'End') index = tabs.length - 1;
        else index = (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
        tabs[index].click(); tabs[index].focus();
      });
    });
    window.addEventListener('hashchange', () => visitHash(true));
    visitHash(Boolean(location.hash));
  }

  const zoomLinks = [...document.querySelectorAll('a[data-zoom]')];
  if (zoomLinks.length && typeof HTMLDialogElement !== 'undefined') {
    const dialog = document.createElement('dialog');
    dialog.className = 'image-dialog';
    dialog.setAttribute('aria-label', '放大图片');
    dialog.innerHTML = '<div class="dialog-bar"><button type="button" data-size>原尺寸</button><button type="button" data-close>关闭 ×</button></div><div class="dialog-scroll"><img alt=""></div>';
    document.body.append(dialog);
    let opener;
    let previousOverflow;
    const image = dialog.querySelector('img');
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.querySelector('[data-size]').addEventListener('click', event => {
      const actual = dialog.classList.toggle('actual-size');
      event.target.textContent = actual ? '适合窗口' : '原尺寸';
    });
    dialog.addEventListener('close', () => {
      document.body.style.overflow = previousOverflow;
      if (opener) opener.focus();
    });
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
    zoomLinks.forEach(link => link.addEventListener('click', event => {
      if (!dialog.showModal || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      image.src = link.href;
      image.alt = link.querySelector('img')?.alt || '知识图解';
      dialog.classList.remove('actual-size');
      dialog.querySelector('[data-size]').textContent = '原尺寸';
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      dialog.showModal();
      dialog.querySelector('[data-close]').focus();
    }));
  }

  const questionElements = [...document.querySelectorAll('[data-question-id]')];
  if (!questionElements.length) return;
  const note = document.querySelector('[data-storage-note]');
  try {
    const questions = questionElements.map(field => ({
      id: field.dataset.questionId,
      version: field.dataset.questionVersion,
      answer: field.dataset.answer,
      prompt: field.querySelector('[data-prompt]').textContent,
      options: [...field.querySelectorAll('input[type="radio"]')].map(input => ({ value: input.value, text: input.closest('label').textContent }))
    }));
    let storage = null;
    try { storage = window.localStorage; } catch (error) { /* Opaque or blocked storage: retain an in-memory session. */ }
    const data = document.body.dataset;
    const key = ReviewQuizState.keyFor(data.bookId, data.chapterId, data.sectionId);
    const session = ReviewQuizState.createSession(questions, storage, key);
    function render() {
      const saved = session.snapshot();
      let done = 0; let correct = 0;
      questionElements.forEach((field, index) => {
        const q = questions[index];
        const entry = saved[q.id];
        if (entry) { done += 1; if (entry.choice === q.answer) correct += 1; }
        field.querySelectorAll('input[type="radio"]').forEach(input => {
          input.disabled = Boolean(entry);
          input.checked = Boolean(entry && entry.choice === input.value);
          input.closest('label').classList.toggle('correct', Boolean(entry && input.value === q.answer));
          input.closest('label').classList.toggle('incorrect', Boolean(entry && entry.choice === input.value && input.value !== q.answer));
        });
        field.querySelector('[data-feedback]').hidden = !entry;
        field.querySelector('[data-result]').textContent = entry ? (entry.choice === q.answer ? '答对了。' : '答错了。') : '';
        field.querySelector('[data-retry-question]').hidden = !entry;
      });
      const progress = document.querySelector('[data-quiz-progress]');
      progress.max = questions.length; progress.value = done;
      document.querySelector('[data-quiz-score]').textContent = '已答 ' + done + ' / ' + questions.length + ' · 答对 ' + correct + ' 题';
      note.textContent = session.status();
    }
    questionElements.forEach((field, index) => {
      field.addEventListener('change', event => {
        if (!event.target.matches('input[type="radio"]')) return;
        session.answer(questions[index].id, event.target.value); render();
      });
      field.querySelector('[data-retry-question]').addEventListener('click', () => {
        session.retry(questions[index].id); render(); field.querySelector('input').focus();
      });
    });
    document.querySelector('[data-reset-quiz]').addEventListener('click', () => {
      session.reset(); render(); questionElements[0].querySelector('input').focus();
    });
    render();
  } catch (error) {
    questionElements.forEach(field => { field.disabled = true; });
    if (note) note.textContent = '自测暂不可用：' + error.message + '。正文和速查仍可阅读。';
  }
})();
