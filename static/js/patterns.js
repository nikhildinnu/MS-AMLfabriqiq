// ─── Pattern Definitions ──────────────────────────────────────
const PATTERNS = [
  {
    id: 'structuring',
    icon: '📉',
    name: 'Structuring (Smurfing)',
    rule: 'AML-001',
    severity: 'HIGH',
    color: '#ffab00',
    description: '4 transactions from ACC-STRUCT-042, each ₹8,900–₹9,800 (below ₹10K threshold) spread over 6 hours. Total: ₹37,400.',
    events: 4,
    accountIds: ['ACC-STRUCT-042'],
  },
  {
    id: 'circular',
    icon: '🔁',
    name: 'Circular Fund Rotation',
    rule: 'AML-002',
    severity: 'CRITICAL',
    color: '#ff3d6b',
    description: '3-hop circular flow: ACC-CIRC-A → ACC-CIRC-B → ACC-CIRC-C → ACC-CIRC-A. ₹5L each leg, 48h window.',
    events: 3,
    accountIds: ['ACC-CIRC-A', 'ACC-CIRC-B', 'ACC-CIRC-C'],
  },
  {
    id: 'fanout',
    icon: '🌐',
    name: 'Fan-Out Layering (1→10)',
    rule: 'AML-002/003',
    severity: 'HIGH',
    color: '#b388ff',
    description: 'ACC-FAN-SOURCE distributes ₹1L each to 10 layer-1 accounts across different banks in 30 min.',
    events: 10,
    accountIds: ['ACC-FAN-SOURCE'],
  },
  {
    id: 'velocity',
    icon: '⚡',
    name: 'Velocity Spike',
    rule: 'AML-004',
    severity: 'MEDIUM',
    color: '#00c8ff',
    description: 'ACC-VEL-007 makes 20 UPI transactions in 30 minutes — 10x its historical average.',
    events: 20,
    accountIds: ['ACC-VEL-007'],
  },
  {
    id: 'chitfund',
    icon: '🏦',
    name: 'Chit Fund Aggregation',
    rule: 'AML-005',
    severity: 'HIGH',
    color: '#00e676',
    description: '5 unrelated accounts each deposit ₹99,000 into MERCH-CHITFUND-01 within 2 hours. Classic integration.',
    events: 5,
    accountIds: ['ACC-CF-MEMBER-1..5'],
  },
];

// ─── Pattern State ────────────────────────────────────────────
const patternStatuses = {};  // patternId → 'idle' | 'loading' | 'success' | 'error'
const patternResults  = {};  // patternId → result object

// ─── Seed a single pattern ────────────────────────────────────
async function seedPattern(patternId) {
  patternStatuses[patternId] = 'loading';
  updatePatternCard(patternId);

  try {
    const res    = await fetch(`/api/events/seed/${patternId}`, { method: 'POST' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || result.error || 'Failed');

    patternStatuses[patternId] = 'success';
    patternResults[patternId]  = result;
    onEventSent({ type: 'SEED', pattern: patternId, result });
    setTimeout(() => {
      patternStatuses[patternId] = 'idle';
      updatePatternCard(patternId);
    }, 5000);
  } catch (err) {
    patternStatuses[patternId] = 'error';
    patternResults[patternId]  = { error: err.message };
  }
  updatePatternCard(patternId);
}

// ─── Seed all patterns ────────────────────────────────────────
async function seedAllPatterns() {
  const btn = document.getElementById('btn-seed-all');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Seeding...'; }
  for (const p of PATTERNS) {
    await seedPattern(p.id);
    await new Promise(r => setTimeout(r, 600));
  }
  if (btn) { btn.disabled = false; btn.textContent = 'Seed All Patterns'; }
}

// ─── Update a single card ─────────────────────────────────────
function updatePatternCard(patternId) {
  const p      = PATTERNS.find(x => x.id === patternId);
  if (!p) return;
  const status = patternStatuses[patternId] || 'idle';
  const result = patternResults[patternId];
  const card   = document.getElementById(`pattern-card-${patternId}`);
  if (!card) return;

  // Update button
  const btn = document.getElementById(`btn-pattern-${patternId}`);
  if (btn) {
    btn.disabled = status === 'loading';
    if (status === 'loading') {
      btn.innerHTML = `<span class="spinner spinner-sm" style="border-top-color:${p.color}"></span> Seeding...`;
    } else if (status === 'success') {
      btn.textContent = '✅ Seeded';
    } else {
      btn.textContent = '▶ Seed Pattern';
    }
  }

  // Update card shadow on success
  card.style.boxShadow = status === 'success' ? `0 0 20px ${p.color}22` : 'none';

  // Update/render result section
  let resultEl = document.getElementById(`pattern-result-${patternId}`);
  if (!result) {
    if (resultEl) resultEl.style.display = 'none';
    return;
  }

  if (!resultEl) {
    resultEl = document.createElement('div');
    resultEl.id = `pattern-result-${patternId}`;
    resultEl.className = 'pattern-result';
    card.appendChild(resultEl);
  }

  const isOk = status === 'success' || (status !== 'error' && result.success);
  resultEl.style.background = isOk ? 'rgba(0,230,118,0.05)' : 'rgba(255,61,107,0.05)';
  resultEl.style.border      = `1px solid ${isOk ? '#00e67622' : '#ff3d6b22'}`;
  resultEl.style.display     = 'block';

  if (isOk && result.eventIds) {
    const idsHtml = result.eventIds.map(id =>
      `<span style="margin-right:6px;color:${p.color}">${id}</span>`
    ).join('');
    resultEl.innerHTML = `
      <div class="pattern-result-ids">
        <span style="color:#00e676;font-weight:700">IDs to quote on stage: </span>${idsHtml}
      </div>
      <div class="pattern-result-status" style="color:#00e676">
        ✅ ${result.eventsSeeded} events → Event Hub (${result.demo ? 'DEMO mode' : 'LIVE'})
      </div>
    `;
  } else {
    resultEl.innerHTML = `
      <div class="pattern-result-status" style="color:#ff3d6b">❌ ${result.error}</div>
    `;
  }
}

// ─── Render the full patterns tab ────────────────────────────
function renderPatterns() {
  const container = document.getElementById('tab-patterns');
  if (!container || container.dataset.rendered) return;
  container.dataset.rendered = '1';

  const severityColor = (s) => s === 'CRITICAL' ? '#ff3d6b' : s === 'HIGH' ? '#ffab00' : '#00c8ff';
  const severityBg    = (s) => s === 'CRITICAL' ? '#ff3d6b11' : s === 'HIGH' ? '#ffab0011' : '#00c8ff11';
  const severityBorder= (s) => s === 'CRITICAL' ? '#ff3d6b44' : s === 'HIGH' ? '#ffab0044' : '#00c8ff44';

  container.innerHTML = `
    <div class="panel-header">
      <div class="panel-title-row">
        <span class="panel-icon">🎯</span>
        <h2>AML Pattern Seeder</h2>
        <span class="tag tag-red">DEMO</span>
      </div>
      <p class="panel-desc">Inject pre-built AML patterns with known transaction IDs into the stream for demo and testing purposes.</p>
    </div>

    <div class="seed-all-bar">
      <div>
        <div class="seed-all-title">🚨 Seed All 5 Patterns</div>
        <div class="seed-all-desc">Injects 42 total events covering all AML patterns. Use before your hackathon demo.</div>
      </div>
      <button id="btn-seed-all" class="btn btn-danger" onclick="seedAllPatterns()">Seed All Patterns</button>
    </div>

    <div class="pattern-cards">
      ${PATTERNS.map(p => `
        <div class="pattern-card" id="pattern-card-${p.id}"
             style="border:1px solid ${p.color}33; border-left:3px solid ${p.color}">
          <div class="pattern-card-inner">
            <div class="pattern-info">
              <div class="pattern-title-row">
                <span style="font-size:18px">${p.icon}</span>
                <span class="pattern-name">${p.name}</span>
                <span class="tag" style="color:${p.color};border-color:${p.color}44;background:${p.color}11">${p.rule}</span>
                <span class="tag" style="color:${severityColor(p.severity)};border-color:${severityBorder(p.severity)};background:${severityBg(p.severity)}">${p.severity}</span>
              </div>
              <p class="pattern-desc">${p.description}</p>
              <div class="pattern-meta">
                <span>📦 ${p.events} events</span>
                <span>🔑 ${p.accountIds.join(', ')}</span>
              </div>
            </div>
            <button
              id="btn-pattern-${p.id}"
              class="btn btn-ghost"
              onclick="seedPattern('${p.id}')"
              style="border-color:${p.color}55;color:${p.color};white-space:nowrap;min-width:100px"
            >▶ Seed Pattern</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}
