'use strict';

(() => {
  const form = document.querySelector('.watch-workspace');
  if (!form) return;
  const controls = [...form.querySelectorAll('[name]')];
  const rows = [...form.querySelectorAll('.watch-company')];
  const search = document.getElementById('portfolioSearch');
  const cancel = document.getElementById('cancel-rules');
  const status = document.getElementById('rules-status');
  const saveState = document.getElementById('watch-save-state');
  let filter = 'all';
  const snapshot = () => controls.map(el => el.type === 'checkbox' ? el.checked : el.value);
  let saved = snapshot();
  let dirty = false;
  search.addEventListener('keydown', e => { if (e.key === 'Enter') e.preventDefault(); });

  function render() {
    const query = search.value.toLowerCase().trim();
    let visible = 0;
    rows.forEach(row => {
      const enabled = row.querySelector('input').checked;
      row.querySelector('.switch-label').textContent = enabled ? 'Active' : 'Off';
      const matchesText = [row.dataset.ticker, row.dataset.name, row.dataset.sector].some(v => v.toLowerCase().includes(query));
      row.hidden = !matchesText || (filter === 'active' && !enabled) || (filter === 'off' && enabled);
      if (!row.hidden) visible++;
    });
    document.getElementById('noMatchesState').hidden = visible !== 0;
    document.getElementById('watch-result-count').textContent = `${visible} ${visible === 1 ? 'company' : 'companies'}`;
    document.getElementById('watch-active-count').textContent = form.querySelectorAll('[name="monitored_tickers"]:checked').length;
    document.getElementById('watch-category-count').textContent = form.querySelectorAll('[name="event_types"]:checked').length;
    document.getElementById('watch-price-value').textContent = form.elements.price_threshold_pct.value ? `±${form.elements.price_threshold_pct.value}%` : '—';
    document.getElementById('watch-volume-value').textContent = form.elements.volume_multiple_threshold.value ? `${form.elements.volume_multiple_threshold.value}×` : '—';
    dirty = JSON.stringify(snapshot()) !== JSON.stringify(saved);
    cancel.disabled = !dirty || form.getAttribute('aria-busy') === 'true';
    saveState.textContent = dirty ? 'Unsaved changes · summary reflects your draft' : 'All changes saved';
    saveState.classList.toggle('dirty', dirty);
  }

  form.addEventListener('input', e => {
    if (e.target.name) { status.textContent = ''; status.dataset.error = 'false'; }
    render();
  });
  form.querySelectorAll('[data-company-filter]').forEach(button => {
    button.addEventListener('click', () => {
      filter = button.dataset.companyFilter;
      form.querySelectorAll('[data-company-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      render();
    });
  });
  document.getElementById('clear-company-search').addEventListener('click', () => {
    search.value = '';
    form.querySelector('[data-company-filter="all"]').click();
    search.focus();
  });
  cancel.addEventListener('click', () => {
    controls.forEach((el, i) => { if (el.type === 'checkbox') el.checked = saved[i]; else el.value = saved[i]; });
    status.dataset.error = 'false';
    status.textContent = 'Changes discarded. Saved preferences restored.';
    render();
  });
  form.addEventListener('monitoring:saved', () => { saved = snapshot(); render(); });
  form.addEventListener('monitoring:defaults', render);
  form.addEventListener('monitoring:idle', render);
  window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
  render();
})();
