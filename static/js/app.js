// ─── Global State ────────────────────────────────────────────
const state = {
  activeTab: 'transaction',
  eventLog: [],
  totalSent: 0,
};

// ─── Tab Switching ────────────────────────────────────────────
function switchTab(tabId) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById(`tab-${tabId}`);
  if (panel) panel.classList.remove('hidden');
  const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  if (btn) btn.classList.add('active');
  state.activeTab = tabId;
  if (tabId === 'log') renderEventLog();
  if (tabId === 'patterns') renderPatterns();
}

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ─── Event Logging ────────────────────────────────────────────
function onEventSent(entry) {
  state.eventLog.push({ ...entry, sentAt: new Date().toISOString() });
  state.totalSent++;
  updateStats();
  if (state.activeTab === 'log') renderEventLog();
}

// ─── Stats Update ─────────────────────────────────────────────
function updateStats() {
  document.getElementById('stat-total').textContent = state.totalSent;
  document.getElementById('stat-transactions').textContent =
    state.eventLog.filter(e => e.type === 'TRANSACTION').length;
  document.getElementById('stat-seeds').textContent =
    state.eventLog.filter(e => e.type === 'SEED').length;
  document.getElementById('stat-entities').textContent =
    state.eventLog.filter(e => ['CUSTOMER', 'ACCOUNT', 'MERCHANT'].includes(e.type)).length;
}

// ─── Health Check ─────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const badge  = document.getElementById('health-badge');
    const dot    = document.getElementById('health-dot');
    const text   = document.getElementById('health-text');
    const uptime = document.getElementById('uptime-display');

    badge.classList.remove('hidden');
    uptime.classList.remove('hidden');

    const isLive = data.mode === 'LIVE';
    dot.className = `dot ${isLive ? 'dot-green' : 'dot-amber'} animate-blink`;
    text.textContent = isLive ? 'LIVE · EVENT HUB' : 'DEMO MODE';
    text.style.color = isLive ? '#00e676' : '#ffab00';
    badge.style.borderColor = isLive ? '#00e67633' : '#ffab0033';
    uptime.textContent = `UPTIME ${data.uptime}s`;
  } catch {
    // silently fail — server may not be ready yet
  }
}

// ─── Form Helpers ─────────────────────────────────────────────
function resetForm(name) {
  const form = document.getElementById(`form-${name}`);
  if (!form) return;
  form.reset();
  form.querySelectorAll('.field-error').forEach(el => { el.textContent = ''; });
  form.querySelectorAll('input, select').forEach(el => { el.style.borderColor = ''; });
  const result = document.getElementById(`result-${name}`);
  if (result) { result.classList.add('hidden'); result.innerHTML = ''; result.className = 'result-box hidden'; }
  // Reset KYC display if present
  const kycDisplay = document.getElementById('kyc-score-display');
  if (kycDisplay) { kycDisplay.textContent = '0'; kycDisplay.style.color = '#00e676'; }
  // Reset structuring warning
  const warn = document.getElementById('structuring-warn');
  if (warn) warn.classList.add('hidden');
}

function showFieldErrors(formName, errors) {
  const form = document.getElementById(`form-${formName}`);
  if (!form) return;
  Object.entries(errors).forEach(([field, msg]) => {
    const errEl = form.querySelector(`.field-error[data-field="${field}"]`);
    if (errEl) errEl.textContent = msg;
    const input = form.querySelector(`[name="${field}"]`);
    if (input) input.style.borderColor = '#ff3d6b';
  });
}

function clearFieldErrors(formName) {
  const form = document.getElementById(`form-${formName}`);
  if (!form) return;
  form.querySelectorAll('.field-error').forEach(el => { el.textContent = ''; });
  form.querySelectorAll('input, select').forEach(el => { el.style.borderColor = ''; });
}

function showResult(name, data, isSuccess) {
  const box = document.getElementById(`result-${name}`);
  if (!box) return;
  box.innerHTML = `
    <div class="result-status ${isSuccess ? 'result-success' : 'result-error'}">
      ${isSuccess ? '✅ Event sent successfully' : '❌ Error'}
    </div>
    <pre class="result-json">${JSON.stringify(data, null, 2)}</pre>
  `;
  box.className = `result-box ${isSuccess ? 'result-box-success' : 'result-box-error'}`;
}

function setButtonLoading(btnId, loading, originalText) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    btn.innerHTML = `<span class="spinner"></span> Sending...`;
  } else {
    btn.textContent = originalText;
  }
}

// ─── KYC Slider ───────────────────────────────────────────────
function updateKycDisplay(value) {
  const score = parseInt(value, 10);
  const display = document.getElementById('kyc-score-display');
  if (!display) return;
  display.textContent = score;
  display.style.color = score > 70 ? '#ff3d6b' : score > 40 ? '#ffab00' : '#00e676';
}

// ─── MCC Quick Pick ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.mcc-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const code = btn.dataset.mcc;
      const input = document.getElementById('mcc-input');
      if (input) input.value = code;
      document.querySelectorAll('.mcc-btn').forEach(b => {
        b.style.borderColor = b.dataset.mcc === code ? '#00c8ff' : '';
        b.style.color = b.dataset.mcc === code ? '#00c8ff' : '';
      });
    });
  });

  // Structuring warning on amount input
  const amountInput = document.querySelector('#form-transaction [name="amount"]');
  if (amountInput) {
    amountInput.addEventListener('input', () => {
      const amt = Number(amountInput.value);
      const warn = document.getElementById('structuring-warn');
      if (warn) warn.classList.toggle('hidden', !(amt >= 8000 && amt < 10000));
    });
  }

  checkHealth();
  renderPatterns();
  renderEventLog();
});
