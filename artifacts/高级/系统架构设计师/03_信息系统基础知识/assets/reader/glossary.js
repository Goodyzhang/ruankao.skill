(() => {
  'use strict';
  const input = document.getElementById('glossary-search');
  const items = [...document.querySelectorAll('[data-glossary-item]')];
  const count = document.getElementById('glossary-count');
  if (!input || !count) return;
  function filter() {
    const terms = input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const item of items) {
      const text = item.textContent.toLocaleLowerCase();
      item.hidden = !terms.every(term => text.includes(term));
      if (!item.hidden) visible += 1;
    }
    count.textContent = visible + ' / ' + items.length + ' 个词条';
  }
  input.addEventListener('input', filter);
  filter();
})();
