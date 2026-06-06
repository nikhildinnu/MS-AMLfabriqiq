// ─── Event Log ────────────────────────────────────────────────
const TYPE_COLORS = {
  TRANSACTION: '#00c8ff',
  CUSTOMER:    '#00e676',
  ACCOUNT:     '#ffab00',
  MERCHANT:    '#b388ff',
  SEED:        '#ff3d6b',
};

let logFilter = 'ALL';

function renderEventLog() {
  const container = document.getElementById('tab-log');
  if (!container) return;

  const types    = ['ALL', 'TRANSACTION', 'CUSTOMER', 'ACCOUNT', 'MERCHANT', 'SEED'];
  const filtered = logFilter === 'ALL'
    ? state.eventLog
    : state.eventLog.filter(e => e.type === logFilter);
  const reversed = [...filtered].reverse();

  container.innerHTML = `
    <div class="panel-header">
      <div class="log-header">
        <div class="log-title-row">
          <span class="panel-icon">📋</span>
          <h2>Event Log</h2>
          <span class="log-count">${state.eventLog.length} TOTAL</span>
        </div>
        ${state.eventLog.length > 0
          ? `<button class="btn btn-ghost" onclick="clearLog()" style="font-size:11px;padding:5px 12px">Clear Log</button>`
          : ''}
      </div>
      <p class="panel-desc" style="margin-top:6px">All events sent in this session. Persists until page refresh.</p>
    </div>

    <div class="log-filter-bar">
      ${types.map(t => {
        const count = t === 'ALL' ? state.eventLog.length : state.eventLog.filter(e => e.type === t).length;
        const color = TYPE_COLORS[t] || '#5a8aaa';
        const active = logFilter === t;
        return `
          <button
            class="filter-btn"
            onclick="setLogFilter('${t}')"
            style="${active ? `background:${color}18;border-color:${color}66;color:${color}` : ''}"
          >${t}${count > 0 ? ` <span style="opacity:0.7">(${count})</span>` : ''}</button>
        `;
      }).join('')}
    </div>

    ${reversed.length === 0
      ? `<div class="log-empty">No events yet. Send a transaction or seed a pattern to see entries here.</div>`
      : `<div class="log-entries">${reversed.map((entry, i) => renderLogEntry(entry, i)).join('')}</div>`
    }
  `;
}

function renderLogEntry(entry, i) {
  const color = TYPE_COLORS[entry.type] || '#5a8aaa';
  const time  = new Date(entry.sentAt || Date.now()).toLocaleTimeString();
  const isNew = i === 0;

  return `
    <div class="log-entry"
         style="border:1px solid ${color}22;border-left:3px solid ${color};${isNew ? 'animation:fadeUp 0.3s ease' : ''}">
      <div class="log-entry-header">
        <div class="log-entry-left">
          <span class="tag" style="color:${color};border-color:${color}44;background:${color}11">${entry.type}</span>
          ${entry.result?.eventId
            ? `<span class="log-entry-id">${entry.result.eventId}</span>`
            : ''}
          ${entry.pattern
            ? `<span class="log-entry-pattern">pattern: ${entry.pattern}</span>`
            : ''}
        </div>
        <div class="log-entry-right">
          ${entry.result?.demo ? `<span class="log-demo-badge">DEMO</span>` : ''}
          <span class="log-time">${time}</span>
        </div>
      </div>
      ${entry.data
        ? `<div class="log-payload">
             <details>
               <summary>▸ View payload</summary>
               <pre>${JSON.stringify(entry.data, null, 2)}</pre>
             </details>
           </div>`
        : ''}
    </div>
  `;
}

function setLogFilter(filter) {
  logFilter = filter;
  renderEventLog();
}

function clearLog() {
  state.eventLog = [];
  state.totalSent = 0;
  updateStats();
  renderEventLog();
}
