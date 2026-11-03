/* FINN monitoring.js
 * Handles:
 *   1. Alert acknowledgement (Done ✓ buttons)
 *   2. Monitoring settings form (Watch page)
 *   3. Hash-link reveal for routine filings
 */

'use strict';

// ── Shared fetch helper ──────────────────────────────────────
async function monitoringRequest(url, method, body) {
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string' ? data.detail : 'Request failed — check values and try again.'
    );
  }
  return data;
}

// ── Acknowledgement buttons ──────────────────────────────────
// Works on both Today and Alerts pages.
document.querySelectorAll('.acknowledgement').forEach(button => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    const statusEl = document.getElementById('monitor-status');
    try {
      const newAck = button.dataset.acknowledged !== 'true';
      await monitoringRequest(
        '/api/monitoring/alerts/' + encodeURIComponent(button.dataset.alertId),
        'PUT',
        { acknowledged: newAck, reference_date: button.dataset.referenceDate }
      );
      // Reload preserving the current URL (window param etc.)
      window.location.reload();
    } catch (error) {
      if (statusEl) statusEl.textContent = 'Not saved: ' + error.message;
      button.disabled = false;
    }
  });
});

// ── Hash-link: open any containing <details> ────────────────
function revealMonitorTarget() {
  const id = window.location.hash.slice(1);
  if (!id) return;
  const target = document.getElementById(id);
  if (!target) return;
  let parent = target.parentElement;
  while (parent) {
    if (parent.tagName === 'DETAILS') parent.open = true;
    parent = parent.parentElement;
  }
  target.tabIndex = -1;
  target.focus({ preventScroll: true });
  // Also open Filed Away list if target is inside it
  const filedList = document.getElementById('filedAwayList');
  if (filedList && filedList.contains(target)) {
    filedList.classList.add('open');
    const btn = document.getElementById('filedAwayToggle');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}
window.addEventListener('hashchange', revealMonitorTarget);
revealMonitorTarget();

// ── Monitoring settings form (Watch / settings page) ────────
const rulesForm = document.getElementById('monitoring-settings-form');
if (rulesForm) {
  const status = document.getElementById('rules-status');

  function formRules() {
    return {
      price_threshold_pct: Number(rulesForm.elements.price_threshold_pct.value),
      volume_multiple_threshold: Number(rulesForm.elements.volume_multiple_threshold.value),
      trigger_mode: rulesForm.elements.trigger_mode.value,
      event_types: [...rulesForm.querySelectorAll('input[name="event_types"]:checked')].map(el => el.value),
      ...(rulesForm.querySelector('input[name="monitored_tickers"]') ? {
        monitored_tickers: [...rulesForm.querySelectorAll('input[name="monitored_tickers"]:checked')].map(el => el.value)
      } : {}),
    };
  }

  async function submitRules(preview) {
    if (!rulesForm.reportValidity()) return;
    const buttons = rulesForm.querySelectorAll('button, input, select');
    const previousDisabled = [...buttons].map(b => b.disabled);
    const payload = formRules();
    buttons.forEach(b => (b.disabled = true));
    rulesForm.setAttribute('aria-busy', 'true');
    if (status) status.dataset.error = 'false';
    if (status) status.textContent = preview ? 'Testing…' : 'Saving…';
    try {
      const data = await monitoringRequest(
        '/api/monitoring/' + (preview ? 'preview' : 'settings'),
        preview ? 'POST' : 'PUT',
        payload
      );
      if (!preview) rulesForm.dispatchEvent(new CustomEvent('monitoring:saved', { detail: data.rules }));
      if (status) {
        status.textContent = preview
          ? `Preview · ${data.reference_date}: ${data.alert_count} alerts (${data.event_alerts} events, ${data.market_alerts} signals). Holdings: ${data.holdings.join(', ') || 'none'}. Not saved.`
          : 'Preferences saved. Today will use these rules on next visit or refresh.';
      }
    } catch (error) {
      if (status) status.dataset.error = 'true';
      if (status) status.textContent = 'Not saved: ' + error.message;
    } finally {
      buttons.forEach((b, i) => (b.disabled = previousDisabled[i]));
      rulesForm.removeAttribute('aria-busy');
      rulesForm.dispatchEvent(new Event('monitoring:idle'));
    }
  }

  rulesForm.addEventListener('submit', e => { e.preventDefault(); submitRules(false); });

  const previewBtn = document.getElementById('preview-rules');
  if (previewBtn) previewBtn.addEventListener('click', () => submitRules(true));

  const defaultBtn = document.getElementById('default-rules');
  if (defaultBtn) {
    defaultBtn.addEventListener('click', () => {
      const buttons = rulesForm.querySelectorAll('button');
      buttons.forEach(b => (b.disabled = true));
      fetch('/api/monitoring/defaults')
        .then(r => { if (!r.ok) throw new Error('Defaults unavailable'); return r.json(); })
        .then(rules => {
          rulesForm.elements.price_threshold_pct.value = rules.price_threshold_pct;
          rulesForm.elements.volume_multiple_threshold.value = rules.volume_multiple_threshold;
          rulesForm.elements.trigger_mode.value = rules.trigger_mode;
          rulesForm.querySelectorAll('input[name="event_types"]').forEach(el => {
            el.checked = rules.event_types.includes(el.value);
          });
          rulesForm.querySelectorAll('input[name="monitored_tickers"]').forEach(el => {
            el.checked = rules.monitored_tickers === null || rules.monitored_tickers.includes(el.value);
          });
          rulesForm.dispatchEvent(new Event('monitoring:defaults'));
          if (status) status.textContent = 'Defaults loaded. Save preferences to apply.';
        })
        .catch(err => { if (status) status.textContent = err.message; })
        .finally(() => { buttons.forEach(b => (b.disabled = false)); rulesForm.dispatchEvent(new Event('monitoring:idle')); });
    });
  }
}
