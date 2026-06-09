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
  }
  if (tabId === 'compliance') {
    loadFleetData();
  }
  if (tabId === 'incidents') {
    loadIncidentsData();
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
    
    const item = document.createElement('div');
    item.className = 'veh-item';
    item.innerHTML = `
      <span class="veh-plate">${veh.license_plate}</span>
      <span>Age: ${veh.age}y</span>
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

function selectIncident(inc) {
  document.querySelectorAll('.incident-item').forEach(el => el.classList.remove('selected'));
  
  const items = document.querySelectorAll('.incident-item');
  items.forEach(el => {
    if (el.innerHTML.includes(inc.incident_id)) el.classList.add('selected');
  });
  
  const detail = document.getElementById('incident-detail');
  detail.innerHTML = `
    <div class="card-header">
      <span class="card-title">🚨 Incident Details & Agent Flow</span>
      <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
    </div>
    <div class="incident-detail-content">
      <p style="font-size:1rem;font-weight:700;margin-bottom:.5rem">${inc.type}</p>
      <p style="color:var(--text2);margin-bottom:1rem">${inc.description}</p>
      
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:1rem;font-size:.78rem">
        <div><strong>Driver ID:</strong> ${inc.driver_id}</div>
        <div><strong>Vehicle ID:</strong> ${inc.vehicle_id}</div>
      </div>
      
      <strong style="font-size:.8rem;display:block;margin-top:1rem">🤖 Multi-Agent Escalation Flow:</strong>
      <div class="agent-flow-viz">
        <div class="flow-step fs-done">
          <span class="fs-icon">🛡️</span>
          <div>
            <strong>Safety Agent (Evaluated)</strong>
            <div style="font-size:.7rem">Risk evaluation score: High. Mobile phone usage verified.</div>
          </div>
        </div>
        <div class="flow-step fs-active">
          <span class="fs-icon">✅</span>
          <div>
            <strong>Compliance Agent (Reviewing)</strong>
            <div style="font-size:.7rem">Reviewing history logs in fleet db. 3 past entries.</div>
          </div>
        </div>
        <div class="flow-step fs-pending">
          <span class="fs-icon">🚨</span>
          <div>
            <strong>Incident Agent (Pending)</strong>
            <div style="font-size:.7rem">Awaiting policy assessment confirmation.</div>
          </div>
        </div>
      </div>
      
      <strong style="font-size:.8rem;display:block;margin-top:1rem">🛠️ Remediation Tasks:</strong>
      <div class="action-items">
        <div class="action-item">SMS sent to ADEK Central Dispatch</div>
        <div class="action-item">Driver compliance status marked: SUSPENDED</div>
        <div class="action-item">Automated retraining task queued in LMS portal</div>
      </div>
    </div>
  `;
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
  document.getElementById('agent-conversation').innerHTML = '<div class="conv-placeholder">Run a scenario above to see live agent-to-agent communication</div>';
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
  else if (agentName.includes('Executive')) document.getElementById('arch-exec').classList.add('active');
}

// --- EXECUTIVE INSIGHTS QUESTIONS ---
const EXEC_RESPONSES = [
  "<strong>Query: Why did compliance decrease in March?</strong><br><br>Compliance dropped by 3.2% in March. Analysis points to a high renewal backlog of passenger supervisor permits at the start of the academic term. Additionally, 12 vehicles failed HVAC pre-trip tests as outdoor temperatures began rising. <em>Recommendation: Schedule HVAC preventative maintenance cycles in February.</em>",
  "<strong>Query: What are top 3 risk drivers this week?</strong><br><br>1. <strong>Summer Heat Indexes:</strong> High passenger cabin temperature warnings.<br>2. <strong>Route Deviations:</strong> Secondary road works in Khalifa City.<br>3. <strong>Late Permits:</strong> Expiring safety checks for 8 drivers.",
  "<strong>Query: Predict next month's incident rate.</strong><br><br>Our predictive model (using historical trends and current road closure indices) forecasts a 12% drop in minor incidents next month as major road works in Sector SE-45 are scheduled for completion.",
  "<strong>Query: Generate board summary report.</strong><br><br>Weekly Safety & Compliance Summary:<br>- Overall Score: 94.2%<br>- Total Active Buses: 247<br>- Compliance Violations Resolved: 18<br>- Critical Incidents Opened: 1"
];

function runExecScenario(idx) {
  const flowDiv = document.getElementById('exec-agent-flow');
  flowDiv.innerHTML = '<div class="ai-thinking"><span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span> Querying supervisor agent...</div>';
  setTimeout(() => {
    flowDiv.innerHTML = `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:1rem;font-size:.82rem;line-height:1.5;color:var(--text2)">${EXEC_RESPONSES[idx]}</div>`;
  }, 1000);
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

// Window load init
window.onload = function() {
  initRouteGrid();
  loadFleetData();
  loadIncidentsData();
  initCharts();
  
  // Executive summary simulation
  setTimeout(() => {
    const summaryDiv = document.getElementById('ai-exec-summary');
    if (summaryDiv) {
      summaryDiv.innerHTML = `
        <p style="margin-bottom:.5rem"><strong>Abu Dhabi Mobility Compliance Insights:</strong></p>
        <p>This week fleet compliance improved to <strong>94.2%</strong>. Driver permit audit logs verify that 98% of active drivers have completed the latest ADEK safety induction training.</p>
        <p style="margin-top:.5rem"><em>Key Alert:</em> Heavy road closures around Yas Island may impact morning drop-off times for routes AU-31 through AU-35.</p>
      `;
    }
  }, 1500);

  LIVE_ALERTS.forEach(al => addAlertItem(al));
};
