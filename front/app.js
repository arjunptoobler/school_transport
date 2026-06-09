// --- API ENDPOINT URL ---
const API_URL = "http://localhost:8000/api";

// Helper to handle API requests with fallback
async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_URL}${endpoint}`, {
      headers: { "Content-Type": "application/json" },
      ...options
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API error at ${endpoint}, falling back to mock:`, err);
    return null;
  }
}

// --- SYSTEM TIME ---
function updateTime() {
  const now = new Date();
  document.getElementById('live-time').innerText = now.toLocaleTimeString();
}
setInterval(updateTime, 1000);
updateTime();

// --- STATE MANAGEMENT ---
let activeTab = 'command';
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-section').forEach(sec => sec.classList.remove('active'));
  
  document.getElementById(`tab-${tabId}`).classList.add('active');
  document.getElementById(`section-${tabId}`).classList.add('active');
  activeTab = tabId;
  
  if (tabId === 'fleet') {
    initMap();
    loadFleetData();
  }
  if (tabId === 'compliance') {
    loadFleetData();
    loadComplianceData();
  }
  if (tabId === 'incidents') {
    loadIncidentsData();
  }
  if (tabId === 'command') {
    loadKPIs();
  }
}

// --- MOCK FALLBACK DATA ---
const MOCK_DRIVERS = [
  { driver_id: 'DRV-1024', name: 'Zayed Al Mansoori', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Complete', operator: 'Emirates Transport' },
  { driver_id: 'DRV-2089', name: 'Ahmed Al Hashimi', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Complete', operator: 'Al Ghazal Transport' },
  { driver_id: 'DRV-1152', name: 'Mustafa Mahmoud', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Complete', operator: 'Hafilat School' },
  { driver_id: 'DRV-3041', name: 'John Doe', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Pending Refresher', operator: 'Abu Dhabi Transport' },
  { driver_id: 'DRV-4412', name: 'Yousef Hassan', permit_status: 'Suspended', medical_status: 'Expired', training_status: 'Failed Evaluation', operator: 'Emirates Transport' }
];

const MOCK_VEHICLES = [
  { vehicle_id: 'AU-BUS-101', license_plate: 'AD 12093', age: 3, gps_status: 'online', inspection_status: 'valid' },
  { vehicle_id: 'AU-BUS-102', license_plate: 'AD 88301', age: 1, gps_status: 'online', inspection_status: 'valid' },
  { vehicle_id: 'AU-BUS-103', license_plate: 'AD 44521', age: 5, gps_status: 'online', inspection_status: 'valid' },
  { vehicle_id: 'AU-BUS-104', license_plate: 'AD 10294', age: 7, gps_status: 'offline', inspection_status: 'failed' },
  { vehicle_id: 'AU-BUS-105', license_plate: 'AD 90912', age: 9, gps_status: 'online', inspection_status: 'valid' }
];

const MOCK_INCIDENTS = [
  { incident_id: 'INC-2026-882', severity: 'high', type: 'Driver Distraction', driver_id: 'DRV-4412', vehicle_id: 'AU-BUS-105', timestamp: '10 mins ago', description: 'Safety Agent detected driver using mobile device via cabin camera.' },
  { incident_id: 'INC-2026-881', severity: 'med', type: 'Missing Guardian', driver_id: 'DRV-2089', vehicle_id: 'AU-BUS-102', timestamp: '25 mins ago', description: 'No guardian present at Handover Point 4. Student retained on vehicle.' },
  { incident_id: 'INC-2026-880', severity: 'med', type: 'Inspection Failure', driver_id: 'DRV-3041', vehicle_id: 'AU-BUS-104', timestamp: '1 hour ago', description: 'Pre-trip compliance check failed. Braking pressure below ADEK safety threshold.' }
];

// Load driver/vehicle tables from API
async function loadFleetData() {
  const data = await apiFetch("/fleet/status");
  const tbody = document.getElementById('driver-tbody');
  const vlist = document.getElementById('vehicle-list');
  
  if (!tbody || !vlist) return;
  tbody.innerHTML = '';
  vlist.innerHTML = '';
  
  const drivers = (data && data.drivers) ? data.drivers : MOCK_DRIVERS;
  const vehicles = (data && data.vehicles) ? data.vehicles : MOCK_VEHICLES;
  
  drivers.forEach(drv => {
    let stClass = 'sp-ok';
    if (drv.training_status.includes('Pending')) stClass = 'sp-warn';
    if (drv.permit_status === 'Suspended') stClass = 'sp-fail';
    
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${drv.driver_id}</strong></td>
      <td>${drv.name}</td>
      <td>${drv.permit_status}</td>
      <td>${drv.medical_status}</td>
      <td>${drv.training_status}</td>
      <td><span class="status-pill ${stClass}">${drv.permit_status === 'Valid' ? 'Compliant' : drv.permit_status}</span></td>
    `;
    tbody.appendChild(tr);
  });

  vehicles.forEach(veh => {
    let stClass = 'vs-ok';
    if (veh.gps_status === 'offline') stClass = 'vs-warn';
    if (veh.inspection_status === 'failed') stClass = 'vs-bad';
    const cap = veh.capacity || 40;
    const occ = veh.current_occupancy || 0;
    const util = cap > 0 ? Math.round((occ / cap) * 100) : 0;
    
    const item = document.createElement('div');
    item.className = 'veh-item';
    item.innerHTML = `
      <span class="veh-plate">${veh.license_plate}</span>
      <span>${occ}/${cap} <small>(${util}%)</small></span>
      <span class="veh-status ${stClass}">${veh.inspection_status.toUpperCase()}</span>
    `;
    vlist.appendChild(item);
  });
}

// Load incident queue from API
let activeIncidents = [];
async function loadIncidentsData() {
  const data = await apiFetch("/incidents/");
  activeIncidents = data || MOCK_INCIDENTS;
  renderIncidentsList();
}

function renderIncidentsList() {
  const list = document.getElementById('incident-list');
  if (!list) return;
  list.innerHTML = '';
  
  activeIncidents.forEach(inc => {
    const item = document.createElement('div');
    item.className = 'incident-item';
    item.onclick = () => selectIncident(inc);
    
    const timeDisplay = inc.timestamp.includes('T') ? inc.timestamp.split('T')[1].substring(0, 5) : inc.timestamp;
    
    item.innerHTML = `
      <div class="ii-header">
        <span class="ii-id">${inc.incident_id}</span>
        <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
      </div>
      <div class="ii-title">${inc.type}</div>
      <div class="ii-meta">Bus: ${inc.vehicle_id} · Driver: ${inc.driver_id} · ${timeDisplay}</div>
    `;
    list.appendChild(item);
  });
  
  const badge = document.getElementById('incident-count-badge');
  if (badge) badge.innerText = `${activeIncidents.length} Open`;
}

async function selectIncident(inc) {
  document.querySelectorAll('.incident-item').forEach(el => el.classList.remove('selected'));
  const items = document.querySelectorAll('.incident-item');
  items.forEach(el => {
    if (el.innerHTML.includes(inc.incident_id)) el.classList.add('selected');
  });

  const detail = document.getElementById('incident-detail');
  detail.innerHTML = `
    <div class="card-header">
      <span class="card-title">🚨 ${inc.type} — ${inc.incident_id}</span>
      <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
    </div>
    <div class="incident-detail-content">
      <p style="color:var(--text2);margin-bottom:.5rem">${inc.description}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-bottom:1rem;font-size:.78rem">
        <div><strong>Driver:</strong> ${inc.driver_id}</div>
        <div><strong>Vehicle:</strong> ${inc.vehicle_id}</div>
        <div><strong>Status:</strong> ${inc.status || 'Detected'}</div>
      </div>
      <div class="ai-thinking"><span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span> Running multi-agent analysis via LangGraph...</div>
    </div>`;

  // Call real agent API with incident context
  const query = `Analyze incident ${inc.incident_id}: ${inc.type} involving driver ${inc.driver_id} on vehicle ${inc.vehicle_id}. ${inc.description}`;
  const res = await apiFetch('/agents/run_scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: 99, query: query })
  });

  const messages = (res && res.success) ? res.history : [{ agent: 'Supervisor Agent', text: 'Analysis pipeline coordinated.', tool: 'LangGraph' }];
  let flowHtml = '';
  messages.forEach((msg, idx) => {
    const cls = idx === messages.length - 1 ? 'fs-active' : 'fs-done';
    flowHtml += `<div class="flow-step ${cls}"><span class="fs-icon">${getAgentIcon(msg.agent)}</span><div><strong>${msg.agent}</strong><div style="font-size:.75rem;color:var(--text2)">${msg.text}</div><div style="font-size:.65rem;color:var(--accent1);margin-top:2px">🛠️ ${msg.tool}</div></div></div>`;
  });

  detail.innerHTML = `
    <div class="card-header">
      <span class="card-title">🚨 ${inc.type} — ${inc.incident_id}</span>
      <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
    </div>
    <div class="incident-detail-content">
      <p style="color:var(--text2);margin-bottom:.5rem">${inc.description}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-bottom:1rem;font-size:.78rem">
        <div><strong>Driver:</strong> ${inc.driver_id}</div>
        <div><strong>Vehicle:</strong> ${inc.vehicle_id}</div>
        <div><strong>Status:</strong> ${inc.status || 'Detected'}</div>
      </div>
      <strong style="font-size:.8rem;display:block;margin-top:.5rem">🤖 Live Multi-Agent Analysis (${messages.length} steps):</strong>
      <div class="agent-flow-viz">${flowHtml}</div>
    </div>`;
}

function getAgentIcon(name) {
  if (name.includes('Supervisor')) return '🧠';
  if (name.includes('Safety')) return '🛡️';
  if (name.includes('Compliance')) return '✅';
  if (name.includes('Route')) return '🗺️';
  if (name.includes('Fleet')) return '🚌';
  if (name.includes('Incident')) return '🚨';
  if (name.includes('Executive')) return '📊';
  return '🤖';
}

// Simulate new incident by calling POST endpoint
async function triggerNewIncident() {
  const payload = {
    severity: "high",
    type: "Speed Violation",
    driver_id: "DRV-1024",
    vehicle_id: "AU-BUS-101",
    description: "Speed violation: Bus exceeded school zone speed limit on Sultan Bin Zayed St."
  };
  
  const res = await apiFetch("/incidents/simulate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  
  if (res && res.success) {
    activeIncidents.unshift(res.incident);
    renderIncidentsList();
    selectIncident(res.incident);
    addAlertItem({ type: 'crit', text: `INCIDENT TRIPPED: Speeding violation on vehicle ${res.incident.vehicle_id}` });
  } else {
    // Local fallback
    const localInc = {
      incident_id: 'INC-2026-' + Math.floor(1000 + Math.random() * 9000),
      severity: 'high',
      type: 'Speed Violation',
      driver_id: 'DRV-1024',
      vehicle_id: 'AU-BUS-101',
      timestamp: 'Just now',
      description: 'Speed violation: Bus exceeded school zone speed limit on Sultan Bin Zayed St.'
    };
    activeIncidents.unshift(localInc);
    renderIncidentsList();
    selectIncident(localInc);
    addAlertItem({ type: 'crit', text: `INCIDENT TRIPPED: Speeding violation on vehicle ${localInc.vehicle_id}` });
  }
}

// --- CHARTS ---
let complianceChart, violationChart, execChart, riskChart;

function initCharts() {
  const ctxComp = document.getElementById('compliance-chart');
  if (ctxComp) {
    complianceChart = new Chart(ctxComp, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'Compliance Rate (%)',
          data: [93.1, 93.5, 93.2, 94.0, 93.8, 94.1, 94.2],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { min: 90, max: 100 } }
      }
    });
  }

  const ctxViol = document.getElementById('violation-chart');
  if (ctxViol) {
    violationChart = new Chart(ctxViol, {
      type: 'doughnut',
      data: {
        labels: ['Permit Issues', 'Speed Limits', 'Seatbelt', 'Distraction', 'Route Deviation'],
        datasets: [{
          data: [5, 12, 18, 4, 9],
          backgroundColor: ['#f59e0b', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6']
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'right', labels: { color: '#94a3b8' } } }
      }
    });
  }

  const ctxExec = document.getElementById('exec-trend-chart');
  if (ctxExec) {
    execChart = new Chart(ctxExec, {
      type: 'bar',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [
          { label: 'Violations logged', data: [12, 14, 25, 15, 8, 5], backgroundColor: '#ef4444' },
          { label: 'Compliant runs', data: [980, 990, 940, 985, 1020, 1050], backgroundColor: '#10b981' }
        ]
      },
      options: {
        responsive: true,
        scales: { y: { stacked: false } }
      }
    });
  }

  const ctxRisk = document.getElementById('risk-chart');
  if (ctxRisk) {
    riskChart = new Chart(ctxRisk, {
      type: 'radar',
      data: {
        labels: ['Speeding', 'Distraction', 'Equipment Failure', 'Permit Expiry', 'Delay Rate'],
        datasets: [{
          label: 'Risk Vector',
          data: [65, 40, 80, 20, 55],
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.2)'
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } }
      }
    });
  }
}

// --- RAG POLICY QUERY ---
async function runRAGQuery() {
  const query = document.getElementById('rag-query').value;
  const resDiv = document.getElementById('rag-result');
  if (!query) return;
  
  resDiv.innerHTML = "Searching Vector Database (ChromaDB index of ADEK policies)...";
  
  const res = await apiFetch("/policy/query", {
    method: "POST",
    body: JSON.stringify({ query })
  });
  
  if (res && res.success && res.results && res.results.length > 0) {
    let html = "";
    res.results.forEach(doc => {
      html += `<strong>${doc.authority} — ${doc.filename} (Chunk #${doc.chunk_index}):</strong><br>
               ${doc.text}<br><br>`;
    });
    resDiv.innerHTML = html;
  } else {
    // Fallback search logic
    setTimeout(() => {
      if (query.toLowerCase().includes("handover") || query.toLowerCase().includes("guardian")) {
        resDiv.innerHTML = `<strong>ADEK Regulation 14.2 (Guardian Handover Policy):</strong><br>
          - Students under Grade 3 / Age 9 MUST NOT be left unattended at drop-off points.<br>
          - If no authorized guardian is present, the driver/supervisor must retain the student on the vehicle.`;
      } else {
        resDiv.innerHTML = "No matching regulatory chunk found. Defaulting to general ADEK Transport Guideline (2026).";
      }
    }, 500);
  }
}

// --- MAP SIMULATOR ---
let mapBuses = [];
function initMap() {
  const mapContainer = document.getElementById('map-buses');
  if (!mapContainer) return;
  mapContainer.innerHTML = '';
  mapBuses = [];
  
  for (let i = 0; i < 15; i++) {
    const bus = document.createElement('div');
    bus.className = 'map-bus moving';
    const left = 10 + Math.random() * 80;
    const top = 10 + Math.random() * 80;
    bus.style.left = `${left}%`;
    bus.style.top = `${top}%`;
    
    const statusRand = Math.random();
    if (statusRand > 0.9) {
      bus.className = 'map-bus alert';
    } else if (statusRand > 0.7) {
      bus.className = 'map-bus stopped';
    }
    
    mapContainer.appendChild(bus);
    mapBuses.push({ el: bus, l: left, t: top, status: bus.className });
  }
}

// Map ticker
setInterval(() => {
  if (activeTab !== 'fleet') return;
  mapBuses.forEach(b => {
    if (b.status.includes('moving')) {
      b.l += (Math.random() - 0.5) * 2;
      b.t += (Math.random() - 0.5) * 2;
      if (b.l < 5) b.l = 5; if (b.l > 95) b.l = 95;
      if (b.t < 5) b.t = 5; if (b.t > 95) b.t = 95;
      b.el.style.left = `${b.l}%`;
      b.el.style.top = `${b.t}%`;
    }
  });
}, 2000);

// --- ALERTS AND FEED ---
const LIVE_ALERTS = [
  { type: 'info', text: 'Route AU-402 started successfully.' },
  { type: 'ok', text: 'Driver Zayed Al Mansoori completed pre-trip verification.' },
  { type: 'warn', text: 'Bus AU-BUS-104 report: Air conditioning output degrading.' },
  { type: 'crit', text: 'Bus AU-BUS-105: Cabin camera safety flag triggered.' }
];

function addAlertItem(alert) {
  const feed = document.getElementById('alert-feed');
  if (!feed) return;
  const item = document.createElement('div');
  item.className = `alert-item ${alert.type}`;
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  item.innerHTML = `<span class="alert-time">[${timeStr}]</span><div>${alert.text}</div>`;
  feed.prepend(item);
  if (feed.children.length > 20) feed.removeChild(feed.lastChild);
}

// --- RUN AGENT SCENARIOS VIA FASTAPI ---
let scenarioRunning = false;
async function runScenario(num) {
  if (scenarioRunning) return;
  scenarioRunning = true;
  
  document.querySelectorAll('.scenario-card').forEach(c => c.classList.remove('running'));
  document.getElementById(`scenario-${num}`).classList.add('running');
  
  const conv = document.getElementById('agent-conversation');
  conv.innerHTML = '';
  const monitor = document.getElementById('agent-monitor');
  monitor.innerHTML = '';
  
  resetDiagramHighlights();
  
  // Call API Endpoint
  const res = await apiFetch("/agents/run_scenario", {
    method: "POST",
    body: JSON.stringify({ scenario_id: num })
  });
  
  const messages = (res && res.success) ? res.history : getFallbackHistory(num);
  let idx = 0;
  
  function nextStep() {
    if (idx >= messages.length) {
      scenarioRunning = false;
      document.getElementById(`scenario-${num}`).classList.remove('running');
      return;
    }
    
    const msg = messages[idx];
    const mDiv = document.createElement('div');
    mDiv.className = 'conv-msg';
    mDiv.innerHTML = `
      <span class="conv-agent">${msg.agent}</span>
      <div class="conv-text">${msg.text}</div>
      <div class="conv-tool">🛠️ ${msg.tool}</div>
    `;
    conv.appendChild(mDiv);
    conv.scrollTop = conv.scrollHeight;
    
    const monitorItem = document.createElement('div');
    let badgeClass = 'ab-supervisor';
    if (msg.agent.includes('Compliance')) badgeClass = 'ab-compliance';
    if (msg.agent.includes('Safety')) badgeClass = 'ab-safety';
    if (msg.agent.includes('Incident')) badgeClass = 'ab-incident';
    if (msg.agent.includes('Executive')) badgeClass = 'ab-executive';
    if (msg.agent.includes('Route')) badgeClass = 'ab-route';
    if (msg.agent.includes('Fleet')) badgeClass = 'ab-fleet';
    
    monitorItem.className = 'agent-item';
    monitorItem.innerHTML = `
      <span class="agent-badge ${badgeClass}">${msg.agent}</span>
      <div>${msg.text}</div>
    `;
    monitor.prepend(monitorItem);
    
    highlightDiagramNode(msg.agent);
    
    idx++;
    setTimeout(nextStep, 1500);
  }
  
  nextStep();
}

function getFallbackHistory(num) {
  const history = [
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router' },
      { agent: 'Safety Agent', text: '⚠️ [Distraction Triggered] Cabin camera feed on Bus AU-BUS-105 shows driver looking at phone for >4 seconds.', tool: 'Cabin Camera Edge Sensor, Incident MCP' },
      { agent: 'Compliance Agent', text: '✅ Checked permit registry via PASS MCP. Driver Yousef Hassan (DRV-4412) has 3 previous compliance warnings.', tool: 'Driver Database, PASS MCP' },
      { agent: 'Incident Agent', text: '🚨 Creating emergency ticket INC-2026-882.', tool: 'Notification MCP, Incident Database' },
      { agent: 'Executive Agent', text: '📊 Logged. Fleet safety score reduced to 94.2%.', tool: 'Analytics MCP' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router' },
      { agent: 'Safety Agent', text: '⚠️ [Missing Guardian] Supervisor on Route AU-102 reports Grade 2 student Guardian not present at stop #4.', tool: 'Route Supervisor SOP App' },
      { agent: 'Compliance Agent', text: '📚 RAG Query: "guardian handover rules". Result: Pupil must be retained.', tool: 'Shared Policy RAG (ChromaDB)' },
      { agent: 'Incident Agent', text: '🚨 Alerting parent via WhatsApp: Student remains safely on bus.', tool: 'Notification MCP, Incident Database' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router' },
      { agent: 'Compliance Agent', text: '❌ Pre-trip checklist failure: Bus AU-BUS-104 reported low brake pressure.', tool: 'Fleet MCP, Pre-trip Forms' },
      { agent: 'Incident Agent', text: '🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106.', tool: 'Route Optimization MCP' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router' },
      { agent: 'Compliance Agent', text: '✅ Querying weekly violation logs. 18 driver training renewals missed during Ramadan shift adjustments.', tool: 'Driver MCP, Policy RAG' },
      { agent: 'Incident Agent', text: '🚨 Incident correlation: High incident volumes matched with newer routes launched.', tool: 'Incident MCP' },
      { agent: 'Executive Agent', text: '📊 Synthesizing executive report.', tool: 'Analytics MCP' }
    ]
  ];
  return history[num] || [];
}

function clearAgentLog() {
  document.getElementById('agent-conversation').innerHTML = '<div class="conv-placeholder">Run a scenario or ask a question to see live agent-to-agent communication</div>';
  document.getElementById('agent-monitor').innerHTML = '';
  resetDiagramHighlights();
}

function resetDiagramHighlights() {
  document.querySelectorAll('.arch-node').forEach(n => n.classList.remove('active'));
}

function highlightDiagramNode(agentName) {
  resetDiagramHighlights();
  document.getElementById('arch-supervisor').classList.add('active');
  if (agentName.includes('Compliance')) document.getElementById('arch-compliance').classList.add('active');
  else if (agentName.includes('Safety')) document.getElementById('arch-safety').classList.add('active');
  else if (agentName.includes('Incident')) document.getElementById('arch-incident').classList.add('active');
  else if (agentName.includes('Route')) document.getElementById('arch-route').classList.add('active');
  else if (agentName.includes('Fleet')) { const el = document.getElementById('arch-fleet'); if (el) el.classList.add('active'); }
  else if (agentName.includes('Executive')) document.getElementById('arch-exec').classList.add('active');
}

// --- EXECUTIVE INSIGHTS QUESTIONS (LIVE API) ---
async function runExecScenario(queryText) {
  const flowDiv = document.getElementById('exec-agent-flow');
  flowDiv.innerHTML = '<div class="ai-thinking"><span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span> Running multi-agent pipeline...</div>';

  const res = await apiFetch('/agents/run_scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: 99, query: queryText })
  });

  const messages = (res && res.success) ? res.history : [{ agent: 'Executive Agent', text: 'Unable to reach agent pipeline. Please try again.', tool: 'Fallback' }];
  let html = '';
  messages.forEach(msg => {
    html += `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:.75rem;margin-bottom:.5rem;font-size:.82rem;line-height:1.5">
      <strong style="color:var(--accent1)">${msg.agent}</strong> <span style="color:var(--text3);font-size:.7rem">🛠️ ${msg.tool}</span><br>
      <span style="color:var(--text2)">${msg.text}</span>
    </div>`;
  });
  flowDiv.innerHTML = html;
}

async function runExecQuery() {
  const input = document.getElementById('exec-query');
  const query = input.value.trim();
  if (!query) return;
  await runExecScenario(query);
}

// Initialize tables
function initRouteGrid() {
  const rgrid = document.getElementById('route-grid');
  if (!rgrid) return;
  rgrid.innerHTML = '';
  for (let i = 1; i <= 9; i++) {
    let rClass = 'active';
    let rStatus = 'ON ROUTE';
    if (i === 3) { rClass = 'delayed'; rStatus = '+12m DELAY'; }
    if (i === 6) { rClass = 'alert'; rStatus = 'ALERT'; }
    const item = document.createElement('div');
    item.className = `route-item ${rClass}`;
    item.innerHTML = `<div class="ri-id">AU-Route-${i * 10}</div><div class="ri-status">${rStatus}</div>`;
    rgrid.appendChild(item);
  }
}

// --- DYNAMIC KPIs FROM API ---
async function loadKPIs() {
  const data = await apiFetch('/fleet/kpis');
  if (!data) return;
  const el = (id) => document.getElementById(id);
  if (el('kpi-active-buses')) el('kpi-active-buses').textContent = data.active_buses;
  const busBar = document.querySelector('#kpi-buses .kpi-fill');
  if (busBar) busBar.style.width = `${(data.active_buses / data.total_buses) * 100}%`;
  const busSub = document.querySelector('#kpi-buses .kpi-sub');
  if (busSub) busSub.textContent = `of ${data.total_buses} fleet`;

  if (el('kpi-comp-score')) el('kpi-comp-score').innerHTML = `${data.compliance_score}<span class="kpi-unit">%</span>`;
  const compBar = document.querySelector('#kpi-compliance .kpi-fill');
  if (compBar) compBar.style.width = `${data.compliance_score}%`;

  if (el('kpi-open-incidents')) el('kpi-open-incidents').textContent = data.open_incidents;
  const incSub = document.querySelector('#kpi-incidents .kpi-sub');
  if (incSub) incSub.textContent = `${data.high_incidents} High · ${data.med_incidents} Medium`;
  const incBar = document.querySelector('#kpi-incidents .kpi-fill');
  if (incBar) incBar.style.width = `${Math.min(100, data.open_incidents)}%`;

  if (el('kpi-students-count')) el('kpi-students-count').textContent = data.students_in_transit.toLocaleString();

  if (el('hbar-gps')) el('hbar-gps').style.width = `${data.gps_active_pct}%`;
  if (el('hval-gps')) el('hval-gps').textContent = `${data.gps_active_pct}%`;
  if (el('hbar-insp')) el('hbar-insp').style.width = `${data.inspection_valid_pct}%`;
  if (el('hval-insp')) el('hval-insp').textContent = `${data.inspection_valid_pct}%`;
}

// --- COMPLIANCE DATA: FINES, SLAs, BOARDINGS ---
async function loadComplianceData() {
  const [fines, slas, boardings, fleetData] = await Promise.all([
    apiFetch('/fleet/fines'),
    apiFetch('/fleet/slas'),
    apiFetch('/fleet/boardings'),
    apiFetch('/fleet/status')
  ]);

  // Compliance KPI cards
  if (fleetData && fleetData.summary) {
    const s = fleetData.summary;
    const el = (id) => document.getElementById(id);
    if (el('ck-compliant')) el('ck-compliant').textContent = s.valid_drivers;
    if (el('ck-violations')) el('ck-violations').textContent = s.total_drivers - s.valid_drivers;
    if (el('ck-vehicles')) el('ck-vehicles').textContent = s.valid_vehicles;
  }

  // Fines table
  if (fines && fines.length) {
    const tbody = document.getElementById('fines-tbody');
    const badge = document.getElementById('fines-count-badge');
    if (badge) badge.textContent = `${fines.length} records`;
    if (tbody) {
      tbody.innerHTML = '';
      fines.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${f.fine_id}</td><td>${f.driver_id}</td><td>${f.violation_type}</td><td style="color:#ef4444;font-weight:600">${f.amount.toLocaleString()}</td><td>${f.authority}</td>`;
        tbody.appendChild(tr);
      });
    }
  }

  // SLAs list
  if (slas && slas.length) {
    const slaList = document.getElementById('sla-list');
    const badge = document.getElementById('sla-count-badge');
    if (badge) badge.textContent = `${slas.length} pending`;
    if (document.getElementById('ck-slas')) document.getElementById('ck-slas').textContent = slas.length;
    if (slaList) {
      slaList.innerHTML = '';
      slas.forEach(s => {
        const item = document.createElement('div');
        item.className = 'veh-item';
        item.innerHTML = `<span class="veh-plate">${s.driver_id}</span><span>Deadline: ${s.deadline_date.split('T')[0]}</span><span class="veh-status vs-warn">${s.status}</span>`;
        slaList.appendChild(item);
      });
    }
  }

  // Boardings table
  if (boardings && boardings.length) {
    const tbody = document.getElementById('boardings-tbody');
    if (tbody) {
      tbody.innerHTML = '';
      boardings.forEach(b => {
        const tr = document.createElement('tr');
        const evtClass = b.event_type === 'boarding' ? 'sp-ok' : 'sp-warn';
        tr.innerHTML = `<td>${b.boarding_id}</td><td>${b.student_id}</td><td>${b.vehicle_id}</td><td><span class="status-pill ${evtClass}">${b.event_type}</span></td><td>${b.timestamp.split('T')[1] || b.timestamp}</td>`;
        tbody.appendChild(tr);
      });
    }
  }
}

// --- FREE-TEXT CUSTOM QUERY ---
async function runCustomQuery() {
  const input = document.getElementById('custom-agent-query');
  const query = input.value.trim();
  if (!query) return;

  const conv = document.getElementById('agent-conversation');
  const monitor = document.getElementById('agent-monitor');
  conv.innerHTML = '<div class="ai-thinking"><span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span> Supervisor routing query to specialist agents...</div>';
  if (monitor) monitor.innerHTML = '';
  resetDiagramHighlights();

  const res = await apiFetch('/agents/run_scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: 99, query: query })
  });

  conv.innerHTML = '';
  const messages = (res && res.success) ? res.history : [{ agent: 'Supervisor Agent', text: 'Unable to reach agent pipeline.', tool: 'Fallback' }];
  let idx = 0;
  function nextStep() {
    if (idx >= messages.length) return;
    const msg = messages[idx];
    const mDiv = document.createElement('div');
    mDiv.className = 'conv-msg';
    mDiv.innerHTML = `<span class="conv-agent">${msg.agent}</span><div class="conv-text">${msg.text}</div><div class="conv-tool">🛠️ ${msg.tool}</div>`;
    conv.appendChild(mDiv);
    conv.scrollTop = conv.scrollHeight;
    highlightDiagramNode(msg.agent);
    idx++;
    setTimeout(nextStep, 1200);
  }
  nextStep();
  input.value = '';
}

// Window load init
window.onload = function() {
  initRouteGrid();
  loadFleetData();
  loadIncidentsData();
  initCharts();
  loadKPIs();

  // Executive summary from real API
  (async () => {
    const summaryDiv = document.getElementById('ai-exec-summary');
    if (!summaryDiv) return;
    const res = await apiFetch('/agents/run_scenario', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: 3, query: 'Generate a brief executive compliance summary for the Abu Dhabi school transport fleet' })
    });
    if (res && res.success && res.history.length) {
      const last = res.history[res.history.length - 1];
      summaryDiv.innerHTML = `<p style="margin-bottom:.5rem"><strong>${last.agent}:</strong></p><p>${last.text}</p>`;
    } else {
      summaryDiv.innerHTML = `<p>Executive summary unavailable. Run a scenario to generate insights.</p>`;
    }
  })();

  LIVE_ALERTS.forEach(al => addAlertItem(al));
};
