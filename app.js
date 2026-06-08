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
  
  // Re-render maps/charts if visible
  if (tabId === 'fleet') {
    initMap();
  }
}

// --- MOCK DATA ---
const DRIVERS = [
  { id: 'DRV-1024', name: 'Zayed Al Mansoori', permit: 'Valid', medical: 'Passed', training: 'Complete', status: 'Compliant' },
  { id: 'DRV-2089', name: 'Ahmed Al Hashimi', permit: 'Valid', medical: 'Passed', training: 'Complete', status: 'Compliant' },
  { id: 'DRV-1152', name: 'Mustafa Mahmoud', permit: 'Valid', medical: 'Passed', training: 'Complete', status: 'Compliant' },
  { id: 'DRV-3041', name: 'John Doe', permit: 'Valid', medical: 'Passed', training: 'Pending Refresher', status: 'Warning' },
  { id: 'DRV-4412', name: 'Yousef Hassan', permit: 'Suspended', medical: 'Expired', training: 'Failed Evaluation', status: 'Non-Compliant' },
  { id: 'DRV-1982', name: 'Saeed Al Remeithi', permit: 'Valid', medical: 'Passed', training: 'Complete', status: 'Compliant' },
  { id: 'DRV-2201', name: 'Khalid Al Zaabi', permit: 'Valid', medical: 'Passed', training: 'Complete', status: 'Compliant' },
  { id: 'DRV-1044', name: 'Tareq Al Junaibi', permit: 'Valid', medical: 'Passed', training: 'Complete', status: 'Compliant' }
];

const VEHICLES = [
  { id: 'AU-BUS-101', plate: 'AD 12093', age: 3, gps: 'online', status: 'ok' },
  { id: 'AU-BUS-102', plate: 'AD 88301', age: 1, gps: 'online', status: 'ok' },
  { id: 'AU-BUS-103', plate: 'AD 44521', age: 5, gps: 'online', status: 'ok' },
  { id: 'AU-BUS-104', plate: 'AD 10294', age: 7, gps: 'offline', status: 'warn' },
  { id: 'AU-BUS-105', plate: 'AD 90912', age: 9, gps: 'online', status: 'bad' }, // Needs replacement soon
  { id: 'AU-BUS-106', plate: 'AD 33291', age: 2, gps: 'online', status: 'ok' },
  { id: 'AU-BUS-107', plate: 'AD 77102', age: 4, gps: 'online', status: 'ok' }
];

const INCIDENTS = [
  { id: 'INC-2026-882', severity: 'high', type: 'Driver Distraction', driver: 'Yousef Hassan', vehicle: 'AU-BUS-105', time: '10 mins ago', desc: 'Safety Agent detected driver using mobile device via cabin camera.' },
  { id: 'INC-2026-881', severity: 'med', type: 'Missing Guardian', driver: 'Ahmed Al Hashimi', vehicle: 'AU-BUS-102', time: '25 mins ago', desc: 'No guardian present at Handover Point 4. Student retained on vehicle.' },
  { id: 'INC-2026-880', severity: 'med', type: 'Inspection Failure', driver: 'John Doe', vehicle: 'AU-BUS-104', time: '1 hour ago', desc: 'Pre-trip compliance check failed. Braking pressure below ADEK safety threshold.' },
  { id: 'INC-2026-879', severity: 'low', type: 'Minor Delay', driver: 'Mustafa Mahmoud', vehicle: 'AU-BUS-115', time: '2 hours ago', desc: 'Heavy traffic on Sheikh Zayed Bin Sultan St. Route updated.' }
];

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

// --- RAG DEMO ---
const RAG_RESPONSES = {
  'guardian handover': `<strong>ADEK Regulation 14.2 (Guardian Handover Policy):</strong><br>
    - Students under Grade 3 / Age 9 MUST NOT be left unattended at drop-off points.<br>
    - If no authorized guardian is present, the driver/supervisor must retain the student on the vehicle.<br>
    - Notify control room immediately. Return student to school after finishing the route or to the designated precinct security.`,
  'mobile usage': `<strong>Abu Dhabi Mobility Driver Rules (Violations & Fines):</strong><br>
    - Direct phone usage or device viewing while operating a school bus incurs a AED 5,000 fine and immediate suspension of the transport permit.<br>
    - Re-evaluation by Abu Dhabi Mobility board is mandatory before permit reinstatement.`,
  'inspection': `<strong>ADEK Compliance Checklist (Daily Pre-trip):</strong><br>
    - Weekly tire pressure, brake systems, seatbelts, safety cameras, and HVAC operation checks.<br>
    - Failing key items (e.g. brakes or HVAC during summer months) automatically marks the vehicle as "Grounded" under ADEK safety directive.`
};

function runRAGQuery() {
  const query = document.getElementById('rag-query').value.toLowerCase();
  const resDiv = document.getElementById('rag-result');
  resDiv.innerHTML = "Searching vector database (ChromaDB index of ADEK policies)...";
  
  setTimeout(() => {
    let matched = false;
    for (const key in RAG_RESPONSES) {
      if (query.includes(key)) {
        resDiv.innerHTML = RAG_RESPONSES[key];
        matched = true;
        break;
      }
    }
    if (!matched) {
      resDiv.innerHTML = `<strong>Search Result:</strong> No exact match. Showing nearest document chunks:<br>
        - <em>ADEK Pupil Transportation Regulations Sec 5:</em> All buses must be equipped with active GPS and interior cameras.<br>
        - <em>Abu Dhabi Department of Transport Policy Circular 2:</em> Summer cabin temperature must not exceed 24°C.`;
    }
  }, 800);
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
    
    // Position inside container coordinates
    const left = 10 + Math.random() * 80;
    const top = 10 + Math.random() * 80;
    bus.style.left = `${left}%`;
    bus.style.top = `${top}%`;
    
    // Random status
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

// Move the buses slightly to simulate GPS tracking
setInterval(() => {
  if (activeTab !== 'fleet') return;
  mapBuses.forEach(b => {
    if (b.status.includes('moving')) {
      b.l += (Math.random() - 0.5) * 2;
      b.t += (Math.random() - 0.5) * 2;
      
      // Keep within bounds
      if (b.l < 5) b.l = 5; if (b.l > 95) b.l = 95;
      if (b.t < 5) b.t = 5; if (b.t > 95) b.t = 95;
      
      b.el.style.left = `${b.l}%`;
      b.el.style.top = `${b.t}%`;
    }
  });
}, 2000);

// --- ALERTS & FEED ---
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
  
  item.innerHTML = `
    <span class="alert-time">[${timeStr}]</span>
    <div>${alert.text}</div>
  `;
  
  feed.prepend(item);
  if (feed.children.length > 20) {
    feed.removeChild(feed.lastChild);
  }
}

// Automatically add streaming logs to Command Center alert feed
setInterval(() => {
  const templates = [
    { type: 'info', text: 'GPS heartbeat received from Route ' + Math.floor(Math.random() * 500) },
    { type: 'ok', text: 'Compliance check passed for driver DRV-' + Math.floor(1000 + Math.random() * 4000) },
    { type: 'info', text: 'Parent notified of ETA for Route AU-190' },
    { type: 'warn', text: 'Traffic slowdown detected on Al Khaleej Al Arabi St.' }
  ];
  const choice = templates[Math.floor(Math.random() * templates.length)];
  addAlertItem(choice);
}, 5000);

// --- AGENT CONVERSATION & SIMULATION LOGIC ---
const AGENT_MESSAGES = {
  // Scenario 1: Driver Mobile Usage
  0: [
    { agent: 'Safety Agent', text: '⚠️ [Distraction Triggered] Cabin camera feed on Bus AU-BUS-105 shows driver looking at phone for >4 seconds. Alert issued to driver console.', tool: 'Tools used: Cabin Camera Edge Sensor, Incident MCP' },
    { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinating. Querying Compliance Agent for driver history on DRV-4412.', tool: 'Tools used: A2A Direct Messaging' },
    { agent: 'Compliance Agent', text: '✅ Checked permit registry via PASS MCP. Driver Yousef Hassan (DRV-4412) has 3 previous compliance warnings this quarter. Permit is subject to suspension.', tool: 'Tools used: Driver Database, PASS MCP' },
    { agent: 'Safety Agent', text: '🛡️ Esculating risk profile: Severity HIGH based on repeated compliance failures.', tool: 'Tools used: Risk Evaluation engine' },
    { agent: 'Incident Agent', text: '🚨 Creating emergency ticket INC-2026-882. Sending SMS alerts to Operator Command and preparing safety training assignment.', tool: 'Tools used: Notification MCP, Incident Database' },
    { agent: 'Executive Agent', text: '📊 Logged. Fleet safety score reduced to 94.2%. Recommending immediate driver stand-down.', tool: 'Tools used: Analytics MCP' }
  ],
  // Scenario 2: Missing Guardian
  1: [
    { agent: 'Safety Agent', text: '⚠️ [Missing Guardian] Supervisor on Route AU-102 reports Grade 2 student Guardian not present at stop #4.', tool: 'Tools used: Route Supervisor SOP App' },
    { agent: 'Supervisor Agent', text: '🧠 Directing Safety Agent to query policy guidelines from Regulations RAG database.', tool: 'Tools used: LangGraph State Router' },
    { agent: 'Compliance Agent', text: '📚 RAG Query: "Guardian handover rules". Result: Pupil must be retained on board. DO NOT release without guardian.', tool: 'Tools used: Shared Policy RAG (ChromaDB)' },
    { agent: 'Incident Agent', text: '🚨 Alerting parent via WhatsApp: "Student remains safely on bus. Bus will return student to School Guard hub at 16:30."', tool: 'Tools used: Notification MCP' },
    { agent: 'Incident Agent', text: '🎫 Incident ticket INC-2026-881 filed with operator.', tool: 'Tools used: Incident Database' }
  ],
  // Scenario 3: Vehicle Inspection Failure
  2: [
    { agent: 'Compliance Agent', text: '❌ Pre-trip checklist failure: Bus AU-BUS-104 reported low brake pressure.', tool: 'Tools used: Pre-trip Forms MCP' },
    { agent: 'Compliance Agent', text: '🚫 Auto-grounding vehicle in Fleet MCP registry. Operating permit marked: Suspended.', tool: 'Tools used: Fleet MCP' },
    { agent: 'Supervisor Agent', text: '🧠 Fleet alert: AU-BUS-104 grounded. Routing Safety and Route Optimization agents.', tool: 'Tools used: LangGraph Orchestrator' },
    { agent: 'Route Agent', text: '🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106 to pick up passengers from Sheikha Fatima School.', tool: 'Tools used: Route Optimization MCP' },
    { agent: 'Incident Agent', text: '🚨 Triggered dispatch notification to transport operator maintenance.', tool: 'Tools used: Fleet Service Desk MCP' }
  ],
  // Scenario 4: Executive analysis
  3: [
    { agent: 'Supervisor Agent', text: '🧠 Question received: "Why did compliance decrease in March?"', tool: 'Tools used: LangGraph State Registry' },
    { agent: 'Compliance Agent', text: '✅ Querying weekly violation logs. 18 driver training renewals missed during Ramadan shift adjustments.', tool: 'Tools used: Driver MCP, Policy RAG' },
    { agent: 'Incident Agent', text: '🚨 Incident correlation: High incident volumes matched with newer routes launched in Khalifa City.', tool: 'Tools used: Incident MCP' },
    { agent: 'Executive Agent', text: '📊 Synthesizing executive report. Compliance fell to 91% due to: 1. Training backlogs (60%), 2. Route delays in Khalifa City (40%). Recommending split shifts.', tool: 'Tools used: Analytics MCP' }
  ]
};

let scenarioRunning = false;
function runScenario(num) {
  if (scenarioRunning) return;
  scenarioRunning = true;
  
  // Highlight card
  document.querySelectorAll('.scenario-card').forEach(c => c.classList.remove('running'));
  document.getElementById(`scenario-${num}`).classList.add('running');
  
  // Clear conversation
  const conv = document.getElementById('agent-conversation');
  conv.innerHTML = '';
  
  const monitor = document.getElementById('agent-monitor');
  monitor.innerHTML = '';
  
  // Highlight diagram
  resetDiagramHighlights();
  
  const messages = AGENT_MESSAGES[num];
  let idx = 0;
  
  function nextStep() {
    if (idx >= messages.length) {
      scenarioRunning = false;
      document.getElementById(`scenario-${num}`).classList.remove('running');
      return;
    }
    
    const msg = messages[idx];
    
    // Add to conversation log
    const mDiv = document.createElement('div');
    mDiv.className = 'conv-msg';
    mDiv.innerHTML = `
      <span class="conv-agent">${msg.agent}</span>
      <div class="conv-text">${msg.text}</div>
      <div class="conv-tool">🛠️ ${msg.tool}</div>
    `;
    conv.appendChild(mDiv);
    conv.scrollTop = conv.scrollHeight;
    
    // Add to top monitor
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
    
    // Highlight diagram node
    highlightDiagramNode(msg.agent);
    
    idx++;
    setTimeout(nextStep, 1500);
  }
  
  nextStep();
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
  
  if (agentName.includes('Compliance')) {
    document.getElementById('arch-compliance').classList.add('active');
  } else if (agentName.includes('Safety')) {
    document.getElementById('arch-safety').classList.add('active');
  } else if (agentName.includes('Incident')) {
    document.getElementById('arch-incident').classList.add('active');
  } else if (agentName.includes('Route')) {
    document.getElementById('arch-route').classList.add('active');
  } else if (agentName.includes('Executive')) {
    document.getElementById('arch-exec').classList.add('active');
  }
}

// --- INCIDENT CENTER ACTIONS ---
function renderIncidents() {
  const list = document.getElementById('incident-list');
  if (!list) return;
  list.innerHTML = '';
  
  INCIDENTS.forEach(inc => {
    const item = document.createElement('div');
    item.className = 'incident-item';
    item.onclick = () => selectIncident(inc);
    
    item.innerHTML = `
      <div class="ii-header">
        <span class="ii-id">${inc.id}</span>
        <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
      </div>
      <div class="ii-title">${inc.type}</div>
      <div class="ii-meta">Bus: ${inc.vehicle} · Driver: ${inc.driver} · ${inc.time}</div>
    `;
    list.appendChild(item);
  });
  
  document.getElementById('incident-count-badge').innerText = `${INCIDENTS.length} Open`;
}

function selectIncident(inc) {
  document.querySelectorAll('.incident-item').forEach(el => el.classList.remove('selected'));
  
  // Highlight clicked
  const items = document.querySelectorAll('.incident-item');
  items.forEach(el => {
    if (el.innerHTML.includes(inc.id)) el.classList.add('selected');
  });
  
  const detail = document.getElementById('incident-detail');
  detail.innerHTML = `
    <div class="card-header">
      <span class="card-title">🚨 Incident Details & Agent Flow</span>
      <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
    </div>
    <div class="incident-detail-content">
      <p style="font-size:1rem;font-weight:700;margin-bottom:.5rem">${inc.type}</p>
      <p style="color:var(--text2);margin-bottom:1rem">${inc.desc}</p>
      
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:1rem;font-size:.78rem">
        <div><strong>Driver:</strong> ${inc.driver}</div>
        <div><strong>Vehicle:</strong> ${inc.vehicle}</div>
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

function triggerNewIncident() {
  const newInc = {
    id: 'INC-2026-' + Math.floor(883 + Math.random() * 100),
    severity: 'high',
    type: 'Speeding Alert',
    driver: 'Zayed Al Mansoori',
    vehicle: 'AU-BUS-101',
    time: 'Just now',
    desc: 'Speed violation: Bus reached 92 km/h in 80 km/h school zone on Sultan Bin Zayed the First St.'
  };
  
  INCIDENTS.unshift(newInc);
  renderIncidents();
  selectIncident(newInc);
  
  addAlertItem({ type: 'crit', text: `INCIDENT TRIPPED: Speeding violation on vehicle ${newInc.vehicle}` });
}

// --- EXEC SCENARIOS ---
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
    flowDiv.innerHTML = `
      <div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:1rem;font-size:.82rem;line-height:1.5;color:var(--text2)">
        ${EXEC_RESPONSES[idx]}
      </div>
    `;
  }, 1000);
}

// --- INITIALIZE TABLES & INITIAL VALUES ---
function initTables() {
  const tbody = document.getElementById('driver-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    DRIVERS.forEach(drv => {
      let stClass = 'sp-ok';
      if (drv.status === 'Warning') stClass = 'sp-warn';
      if (drv.status === 'Non-Compliant') stClass = 'sp-fail';
      
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${drv.id}</strong></td>
        <td>${drv.name}</td>
        <td>${drv.permit}</td>
        <td>${drv.medical}</td>
        <td>${drv.training}</td>
        <td><span class="status-pill ${stClass}">${drv.status}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  const vlist = document.getElementById('vehicle-list');
  if (vlist) {
    vlist.innerHTML = '';
    VEHICLES.forEach(veh => {
      let stClass = 'vs-ok';
      if (veh.status === 'warn') stClass = 'vs-warn';
      if (veh.status === 'bad') stClass = 'vs-bad';
      
      const item = document.createElement('div');
      item.className = 'veh-item';
      item.innerHTML = `
        <span class="veh-plate">${veh.plate}</span>
        <span>Age: ${veh.age}y</span>
        <span class="veh-status ${stClass}">${veh.status.toUpperCase()}</span>
      `;
      vlist.appendChild(item);
    });
  }

  const rgrid = document.getElementById('route-grid');
  if (rgrid) {
    rgrid.innerHTML = '';
    for (let i = 1; i <= 9; i++) {
      let rClass = 'active';
      let rStatus = 'ON ROUTE';
      if (i === 3) { rClass = 'delayed'; rStatus = '+12m DELAY'; }
      if (i === 6) { rClass = 'alert'; rStatus = 'ALERT'; }
      
      const item = document.createElement('div');
      item.className = `route-item ${rClass}`;
      item.innerHTML = `
        <div class="ri-id">AU-Route-${i * 10}</div>
        <div class="ri-status">${rStatus}</div>
      `;
      rgrid.appendChild(item);
    }
  }
}

// --- INIT APP ---
window.onload = function() {
  initTables();
  initCharts();
  renderIncidents();
  
  // Prep the executive summary text
  setTimeout(() => {
    const summaryDiv = document.getElementById('ai-exec-summary');
    if (summaryDiv) {
      summaryDiv.innerHTML = `
        <p style="margin-bottom:.5rem"><strong>Abu Dhabi Mobility Compliance Insights:</strong></p>
        <p>This week fleet compliance improved to <strong>94.2%</strong>. Driver permit audit logs verify that 98% of active drivers have completed the latest ADEK safety induction training.</p>
        <p style="margin-top:.5rem"><em>Key Alert:</em> Heavy road closures around Yas Island may impact morning drop-off times for routes AU-31 through AU-35. Route Optimization Agent has sent proactive rescheduling suggestions to operators.</p>
      `;
    }
  }, 1500);

  // Initial alerts in feed
  LIVE_ALERTS.forEach(al => addAlertItem(al));
};
