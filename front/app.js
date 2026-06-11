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
  { driver_id: 'DRV-1024', name: 'Zayed Al Mansoori', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Complete', operator: 'Emirates Transport', incident_count: 0, is_repeat_offender: false },
  { driver_id: 'DRV-2089', name: 'Ahmed Al Hashimi', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Complete', operator: 'Al Ghazal Transport', incident_count: 1, is_repeat_offender: false },
  { driver_id: 'DRV-1152', name: 'Mustafa Mahmoud', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Complete', operator: 'Hafilat School', incident_count: 0, is_repeat_offender: false },
  { driver_id: 'DRV-3041', name: 'John Doe', permit_status: 'Valid', medical_status: 'Passed', training_status: 'Pending Refresher', operator: 'Abu Dhabi Transport', incident_count: 2, is_repeat_offender: false },
  { driver_id: 'DRV-4412', name: 'Yousef Hassan', permit_status: 'Suspended', medical_status: 'Expired', training_status: 'Failed Evaluation', operator: 'Emirates Transport', incident_count: 4, is_repeat_offender: true }
];

const MOCK_VEHICLES = [
  { vehicle_id: 'AU-BUS-101', license_plate: 'AD 12093', age: 3, gps_status: 'online', inspection_status: 'valid' },
  { vehicle_id: 'AU-BUS-102', license_plate: 'AD 88301', age: 1, gps_status: 'online', inspection_status: 'valid' },
  { vehicle_id: 'AU-BUS-103', license_plate: 'AD 44521', age: 5, gps_status: 'online', inspection_status: 'valid' },
  { vehicle_id: 'AU-BUS-104', license_plate: 'AD 10294', age: 7, gps_status: 'offline', inspection_status: 'failed' },
  { vehicle_id: 'AU-BUS-105', license_plate: 'AD 90912', age: 9, gps_status: 'online', inspection_status: 'valid' }
];

const MOCK_SLAS = [
  { sla_id: 'SLA-2026-001', driver_id: 'DRV-3041', deadline_date: '2026-06-16T00:00:00', status: 'Pending' },
  { sla_id: 'SLA-2026-002', driver_id: 'DRV-4412', deadline_date: '2026-06-08T00:00:00', status: 'Overdue' },
  { sla_id: 'SLA-2026-003', driver_id: 'DRV-1024', deadline_date: '2026-06-20T00:00:00', status: 'Pending' },
  { sla_id: 'SLA-2026-004', driver_id: 'DRV-2089', deadline_date: '2026-06-09T00:00:00', status: 'Overdue' },
];

const MOCK_INCIDENTS = [];

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
  const driverCountBadge = document.getElementById('driver-count-badge');
  if (driverCountBadge) driverCountBadge.textContent = `${drivers.length} drivers`;
  
  drivers.forEach(drv => {
    let stClass = 'sp-ok';
    if (drv.training_status.includes('Pending')) stClass = 'sp-warn';
    if (drv.permit_status === 'Suspended') stClass = 'sp-fail';
    const incCount = drv.incident_count || drv.total_incidents || 0;
    const repeatBadge = (drv.is_repeat_offender || incCount >= 3)
      ? ' <span class="status-pill sp-fail" style="font-size:.6rem;padding:.1rem .35rem;">Repeat</span>' : '';

    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.title = `Click to see ${drv.name}'s compliance summary`;
    tr.innerHTML = `
      <td><strong>${drv.driver_id}</strong></td>
      <td>${drv.name}</td>
      <td>${drv.permit_status}</td>
      <td>${drv.medical_status}</td>
      <td>${drv.training_status}</td>
      <td>${incCount}${repeatBadge}</td>
      <td><span class="status-pill ${stClass}">${drv.permit_status === 'Valid' ? 'Compliant' : drv.permit_status}</span></td>
    `;
    tr.onclick = () => showDriverDetail(tr, drv, incCount);
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

  // Grounded vehicles table (compliance tab)
  const grounded = vehicles.filter(v => v.inspection_status === 'failed');
  const groundedBadge = document.getElementById('grounded-count-badge');
  if (groundedBadge) groundedBadge.textContent = grounded.length > 0 ? `${grounded.length} grounded` : '0 grounded';
  const groundedTbody = document.getElementById('grounded-tbody');
  if (groundedTbody) {
    groundedTbody.innerHTML = '';
    if (grounded.length === 0) {
      groundedTbody.innerHTML = '<tr><td colspan="6" style="color:var(--accent3);text-align:center;padding:.75rem;">No vehicles currently grounded</td></tr>';
    } else {
      grounded.forEach(v => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td><strong>${v.vehicle_id}</strong></td><td>${v.license_plate || '—'}</td><td><span class="status-pill sp-fail">FAILED</span></td><td><span class="status-pill ${v.gps_status === 'online' ? 'sp-ok' : 'vs-warn'}">${(v.gps_status || 'unknown').toUpperCase()}</span></td><td>${v.age || '—'}y</td><td style="color:var(--accent3);font-size:.72rem;">Compliance Agent</td>`;
        groundedTbody.appendChild(tr);
      });
    }
  }
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
  
  const openCount = activeIncidents.filter(inc => inc.status !== 'Resolved').length;
  const badge = document.getElementById('incident-count-badge');
  if (badge) badge.innerText = `${openCount} Open`;
}

async function selectIncident(inc) {
  document.querySelectorAll('.incident-item').forEach(el => el.classList.remove('selected'));
  const items = document.querySelectorAll('.incident-item');
  items.forEach(el => {
    if (el.innerHTML.includes(inc.incident_id)) el.classList.add('selected');
  });

  const detail = document.getElementById('incident-detail');
  
  let evidenceHtml = '';
  if (inc.evidence_url && inc.evidence_url !== 'None') {
    if (inc.evidence_url.endsWith('.jpg') || inc.evidence_url.endsWith('.png')) {
      evidenceHtml = `<div style="margin-top:1rem"><strong style="font-size:.8rem;display:block;margin-bottom:.5rem">📸 Visual Evidence:</strong><img src="${inc.evidence_url}" style="max-width:100%;border-radius:6px;border:1px solid var(--border)"></div>`;
    } else {
      evidenceHtml = `<div style="margin-top:1rem;background:var(--bg3);padding:.5rem;border-radius:6px;border:1px solid var(--border);font-size:.75rem"><strong style="color:var(--text1)">📎 Evidence Attached:</strong> <a href="${inc.evidence_url}" target="_blank" style="color:var(--accent1)">${inc.evidence_url.split('/').pop()}</a></div>`;
    }
  }

  detail.innerHTML = `
    <div class="card-header">
      <span class="card-title">🚨 ${inc.type} — ${inc.incident_id}</span>
      <span class="sev-badge sev-${inc.severity}">${inc.severity.toUpperCase()}</span>
    </div>
    <div class="incident-detail-content">
      <p style="color:var(--text2);margin-bottom:.5rem">${inc.description}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-bottom:.5rem;font-size:.78rem">
        <div><strong>Driver:</strong> ${inc.driver_id}</div>
        <div><strong>Vehicle:</strong> ${inc.vehicle_id}</div>
        <div><strong>Status:</strong> ${inc.status || 'Detected'}</div>
      </div>
      ${evidenceHtml}
      <div class="ai-thinking" style="margin-top:1rem"><span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span> Fetching incident audit trail...</div>
    </div>`;

  // Fetch audit log
  const res = await apiFetch(`/incidents/${inc.incident_id}/audit`);
  const logs = (res && res.success && res.audit_log) ? res.audit_log : [];

  let flowHtml = '';
  if (logs.length === 0) {
    flowHtml = `<div style="font-size:.8rem;color:var(--text2);padding:1rem;">No agent actions recorded for this incident yet.</div>`;
  } else {
    logs.forEach((log, idx) => {
      const cls = idx === logs.length - 1 ? 'fs-active' : 'fs-done';
      flowHtml += `<div class="flow-step ${cls}"><span class="fs-icon">${getAgentIcon(log.agent)}</span><div><strong>${log.agent}</strong><div style="font-size:.75rem;color:var(--text2)">${log.action}</div><div style="font-size:.65rem;color:var(--accent1);margin-top:2px">🛠️ ${log.detail}</div><div style="font-size:.6rem;color:var(--text3);margin-top:4px">${log.timestamp.replace('T', ' ').substring(0, 19)}</div></div></div>`;
    });
  }

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
        <div><strong>Status:</strong> <span class="status-pill ${inc.status === 'Resolved' ? 'vs-ok' : 'vs-bad'}">${inc.status || 'Detected'}</span></div>
      </div>
      ${evidenceHtml}
      <strong style="font-size:.8rem;display:block;margin-top:.5rem">🤖 Immutable Agent Audit Trail (${logs.length} actions):</strong>
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

async function initCharts() {
  const chartData = await apiFetch("/incidents/charts");
  let violLabels = ['Permit Issues', 'Speed Limits', 'Seatbelt', 'Distraction', 'Route Deviation'];
  let violData = [5, 12, 18, 4, 9];
  let riskData = [65, 40, 80, 20, 55];
  let compBase = 94.0;

  if (chartData && chartData.success) {
    violLabels = chartData.violation_breakdown.labels;
    violData = chartData.violation_breakdown.data;
    riskData = chartData.risk_matrix.data;
    compBase = chartData.compliance_base;
  }

  // Derive a pseudo-historical 7-day trend ending at the current compliance base score
  const compTrend = [
    (compBase - 1.2).toFixed(1),
    (compBase - 0.8).toFixed(1),
    (compBase - 1.5).toFixed(1),
    (compBase - 0.3).toFixed(1),
    (compBase - 0.5).toFixed(1),
    (compBase + 0.1).toFixed(1),
    compBase.toFixed(1)
  ];

  const ctxComp = document.getElementById('compliance-chart');
  if (ctxComp) {
    complianceChart = new Chart(ctxComp, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'Compliance Rate (%)',
          data: compTrend,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { min: Math.floor(compBase - 5), max: 100 } }
      }
    });
  }

  const ctxViol = document.getElementById('violation-chart');
  if (ctxViol) {
    violationChart = new Chart(ctxViol, {
      type: 'doughnut',
      data: {
        labels: violLabels,
        datasets: [{
          data: violData,
          backgroundColor: ['#f59e0b', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6']
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12, padding: 10, font: { size: 11 } } } }
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
          { label: 'Violations logged', data: [12, 14, 25, 15, 8, violData.reduce((a,b)=>a+b,0)], backgroundColor: '#ef4444' },
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
        labels: ['High Severity', 'Distraction', 'Equipment Failure', 'Missing Guardian', 'Med Severity'],
        datasets: [{
          label: 'Risk Vector',
          data: riskData,
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.2)'
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { r: { min: 0, max: 100 } }
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

// --- LEAFLET REAL MAP SYSTEM ---
let leafletMap = null;
let routeLayers = [];
let markerLayers = [];

function initMap() {
  const mapContainer = document.getElementById('map-leaflet');
  if (!mapContainer || leafletMap) return;
  
  // London center: 51.5060, -0.1360
  leafletMap = L.map('map-leaflet').setView([51.5060, -0.1360], 14);
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
  }).addTo(leafletMap);
  
  // Load initial normal state
  updateMapLayers(0);
}

async function updateMapLayers(scenarioNum) {
  if (!leafletMap) return;
  
  // Clear existing layers
  routeLayers.forEach(l => leafletMap.removeLayer(l));
  markerLayers.forEach(m => leafletMap.removeLayer(m));
  routeLayers = [];
  markerLayers = [];
  
  // Fetch route and roadblock data from backend API
  const data = await apiFetch("/fleet/routes");
  if (!data || !data.success) return;
  
  const depot = [51.5030, -0.1500];
  const school = [51.5120, -0.1220];
  const roadblockCoords = [51.5070, -0.1420];
  
  // 1. Add School and Depot Markers
  const depotMarker = L.marker(depot, {
    icon: L.divIcon({
      html: '<span style="font-size: 24px;">🏢</span>',
      className: 'map-marker-emoji',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    })
  }).bindPopup("<b>Bus Depot</b><br>Hyde Park Corner").addTo(leafletMap);
  
  const schoolMarker = L.marker(school, {
    icon: L.divIcon({
      html: '<span style="font-size: 24px;">🏫</span>',
      className: 'map-marker-emoji',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    })
  }).bindPopup("<b>Covent Garden School</b>").addTo(leafletMap);
  
  markerLayers.push(depotMarker, schoolMarker);

  // 2. Render routes based on scenario
  if (scenarioNum === 2) {
    // Scenario 2: Grounded / Breakdown Student Merge
    // Draw Grounded Bus 2 (AU-BUS-104) at Piccadilly
    const groundedBus = L.marker([51.5075, -0.1400], {
      icon: L.divIcon({
        html: '<span style="font-size: 24px;">🚨</span>',
        className: 'map-marker-emoji',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      })
    }).bindPopup("<b>Grounded Bus (AU-BUS-104)</b><br>Brake pressure failure.<br>12 students stranded.").addTo(leafletMap);
    
    // Draw Standby Bus 1 (AU-BUS-106) route (merge route)
    const mergeGeoJSON = L.geoJSON(data.paths.merge, {
      style: { color: '#f97316', weight: 5, opacity: 0.85, dashArray: '5, 10' }
    }).bindPopup("<b>Standby Bus Route</b><br>Detouring to pick up stranded students.").addTo(leafletMap);
    
    const standbyBus = L.marker(depot, {
      icon: L.divIcon({
        html: '<span style="font-size: 24px;">🚌</span>',
        className: 'map-marker-emoji',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      })
    }).bindPopup("<b>Standby Bus (AU-BUS-106)</b><br>Dispatched from Depot.").addTo(leafletMap);

    routeLayers.push(mergeGeoJSON);
    markerLayers.push(groundedBus, standbyBus);
    
  } else if (scenarioNum === 99) { // Custom Event (like roadblock detour)
    // Draw roadblock marker
    const rb = L.marker(roadblockCoords, {
      icon: L.divIcon({
        html: '<span style="font-size: 24px;">🚧</span>',
        className: 'map-marker-emoji',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      })
    }).bindPopup("<b>Piccadilly Roadblock Closure</b>").addTo(leafletMap);
    
    // Draw detour route
    const detourGeoJSON = L.geoJSON(data.paths.detour, {
      style: { color: '#f97316', weight: 5, opacity: 0.85 }
    }).bindPopup("<b>Detour Route</b><br>Avoiding Piccadilly").addTo(leafletMap);
    
    const bus = L.marker(depot, {
      icon: L.divIcon({
        html: '<span style="font-size: 24px;">🚌</span>',
        className: 'map-marker-emoji',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      })
    }).bindPopup("<b>Bus on Detour (AU-BUS-104)</b>").addTo(leafletMap);

    routeLayers.push(detourGeoJSON);
    markerLayers.push(rb, bus);
    
  } else {
    // Normal / Scenario 0 & 1
    const normalGeoJSON = L.geoJSON(data.paths.normal, {
      style: { color: '#8b5cf6', weight: 5, opacity: 0.8 }
    }).bindPopup("<b>Standard Route</b><br>Depot to Covent Garden").addTo(leafletMap);
    
    const bus = L.marker(depot, {
      icon: L.divIcon({
        html: '<span style="font-size: 24px;">🚌</span>',
        className: 'map-marker-emoji',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      })
    }).bindPopup("<b>Active Bus (AU-BUS-104)</b>").addTo(leafletMap);

    routeLayers.push(normalGeoJSON);
    markerLayers.push(bus);
  }
}

// --- ALERTS AND FEED ---
const LIVE_ALERTS = [];

function getEventTag(scenarioId, queryText = "") {
  if (scenarioId === 0) return "Distraction";
  if (scenarioId === 1) return "Missing Guardian";
  if (scenarioId === 2) return "Pre-Trip Compliance";
  if (scenarioId === 3) return "Executive Summary";
  if (scenarioId === 4) return "Pre-Departure Check";
  
  const q = queryText.toLowerCase();
  if (q.includes("distract") || q.includes("phone") || q.includes("seatbelt") || q.includes("mobile")) {
    return "Distraction";
  } else if (q.includes("guardian") || q.includes("parent") || q.includes("boarding") || q.includes("student")) {
    return "Missing Guardian";
  } else if (q.includes("compliance") || q.includes("inspection") || q.includes("permit") || q.includes("pressure") || q.includes("braking")) {
    return "Pre-Trip Compliance";
  } else if (q.includes("summary") || q.includes("executive") || q.includes("kpi")) {
    return "Executive Summary";
  } else if (q.includes("route") || q.includes("deviation") || q.includes("block") || q.includes("closure")) {
    return "Route Deviation";
  }
  return "System Event";
}

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

const agentConfig = {
  'Supervisor': { icon: '🧠', accent: '#8b5cf6', bg: 'rgba(139,92,246,.08)', border: 'rgba(139,92,246,.25)' },
  'Safety':     { icon: '🛡️', accent: '#f59e0b', bg: 'rgba(245,158,11,.08)', border: 'rgba(245,158,11,.25)' },
  'Evidence':   { icon: '👁️', accent: '#06b6d4', bg: 'rgba(6,182,212,.08)',   border: 'rgba(6,182,212,.25)' },
  'Compliance': { icon: '✅', accent: '#10b981', bg: 'rgba(16,185,129,.08)', border: 'rgba(16,185,129,.25)' },
  'Route':      { icon: '🗺️', accent: '#f97316', bg: 'rgba(249,115,22,.08)', border: 'rgba(249,115,22,.25)' },
  'Fleet':      { icon: '🚌', accent: '#3b82f6', bg: 'rgba(59,130,246,.08)', border: 'rgba(59,130,246,.25)' },
  'Incident':   { icon: '🚨', accent: '#ef4444', bg: 'rgba(239,68,68,.08)',   border: 'rgba(239,68,68,.25)' },
  'Executive':  { icon: '📊', accent: '#a78bfa', bg: 'rgba(167,139,250,.08)', border: 'rgba(167,139,250,.25)' },
};

function getConfig(agentName) {
  for (const [key, cfg] of Object.entries(agentConfig)) {
    if (agentName.includes(key)) return cfg;
  }
  return { icon: '🤖', accent: '#6b7280', bg: 'rgba(107,114,128,.08)', border: 'rgba(107,114,128,.25)' };
}

const SEEN_RUNS = new Set();

function processApiRun(run) {
  const baseTag = getEventTag(run.scenario_id, run.event_payload);
  const uid = run.run_id ? run.run_id.substring(run.run_id.length - 4) : Math.random().toString(36).substring(2, 6).toUpperCase();
  const fullTag = `[${baseTag}-${uid}]`;
  const messages = run.history || [];
  
  // 1. Initial Alert Received
  let alertType = 'info';
  if (baseTag === 'Distraction' || baseTag === 'Pre-Trip Compliance') alertType = 'crit';
  else if (baseTag === 'Missing Guardian' || baseTag === 'Route Deviation') alertType = 'warn';
  addAlertItem({
    type: alertType,
    text: `📢 ${fullTag} ALERT RECEIVED: ${run.event_payload}`
  });

  // 2. Refresh dashboard data
  loadKPIs();
  loadIncidentsData();
  loadFleetData();
  updateMapLayers(run.scenario_id);

  // Setup Workflow Trace UI
  const traceCard = document.getElementById('workflow-trace-card');
  const badge = document.getElementById('workflow-status-badge');
  const stepsDiv = document.getElementById('agent-conversation');
  if (traceCard && stepsDiv && badge) {
    traceCard.style.display = 'block';
    stepsDiv.innerHTML = '';
    badge.textContent = '● Pipeline Running (API)';
    badge.style.background = 'rgba(59,130,246,.2)';
    badge.style.color = '#60a5fa';
    const evtTextEl = document.getElementById('workflow-event-text');
    if (evtTextEl) evtTextEl.textContent = run.event_payload;
  }

  // 3. Chronologically display agent actions
  let idx = 0;
  function nextStep() {
    if (idx >= messages.length) return;
    const msg = messages[idx];
    
    const isLast = idx === messages.length - 1;
    if (isLast) {
      addAlertItem({
        type: 'ok',
        text: `✅ ${fullTag} OUTCOME: Final state achieved - ${msg.action || msg.text}`
      });
      // Refresh KPIs again at the end of workflow
      loadKPIs();
      loadIncidentsData();
      if (badge) {
        badge.textContent = '✓ Workflow Complete';
        badge.style.background = 'rgba(16,185,129,.2)';
        badge.style.color = '#34d399';
      }
    }
    
    // Add to Agent Activity Monitor (Workflow Trace)
    if (stepsDiv) {
      const cfg = getConfig(msg.agent);
      const step = document.createElement('div');
      step.style.cssText = `display:flex;gap:0;opacity:0;transform:translateY(8px);transition:all .4s ease;`;

      const connector = document.createElement('div');
      connector.style.cssText = `display:flex;flex-direction:column;align-items:center;width:48px;flex-shrink:0;`;
      connector.innerHTML = `
        <div style="width:36px;height:36px;border-radius:50%;background:${cfg.bg};border:2px solid ${cfg.accent};display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;box-shadow:0 0 12px ${cfg.accent}44;">${cfg.icon}</div>
        ${!isLast ? `<div style="width:2px;flex:1;min-height:20px;background:linear-gradient(to bottom,${cfg.accent}88,transparent);margin-top:4px;"></div>` : ''}
      `;

      const content = document.createElement('div');
      content.style.cssText = `flex:1;background:${cfg.bg};border:1px solid ${cfg.border};border-radius:10px;padding:1rem 1.1rem;margin-bottom:${isLast?'0':'12px'};`;

      const actionPill = msg.action ? `
        <div style="display:inline-flex;align-items:center;gap:.4rem;background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.35);border-radius:20px;padding:.25rem .75rem;font-size:.72rem;font-weight:700;color:#34d399;margin-top:.6rem;">
          ⚡ Action Executed: ${msg.action}
        </div>` : '';

      content.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
          <span style="font-weight:700;font-size:.85rem;color:${cfg.accent};">${msg.agent} <span style="font-size:.7rem;color:var(--text3);margin-left:8px;">${fullTag}</span></span>
          <span style="font-size:.72rem;color:var(--text3);background:var(--bg2);border:1px solid var(--border);border-radius:20px;padding:.2rem .6rem;">🛠️ ${msg.tool}</span>
        </div>
        <div style="font-size:.84rem;line-height:1.6;color:var(--text1);">${msg.text}</div>
        ${actionPill}
        ${!isLast ? `<div style="font-size:.72rem;color:var(--text3);margin-top:.6rem;">↳ Handing off to next agent…</div>` : '<div style="font-size:.72rem;color:#34d399;margin-top:.6rem;font-weight:600;">✓ Workflow Completed</div>'}
      `;

      step.appendChild(connector);
      step.appendChild(content);
      stepsDiv.appendChild(step);

      requestAnimationFrame(() => {
        step.style.opacity = '1';
        step.style.transform = 'translateY(0)';
      });
      stepsDiv.scrollTop = stepsDiv.scrollHeight;
      highlightDiagramNode(msg.agent);
    }

    idx++;
    setTimeout(nextStep, 1500);
  }
  nextStep();
}

async function pollRecentRuns() {
  try {
    const res = await apiFetch('/agents/recent_runs');
    if (res && res.success && res.runs) {
      // Sort runs by run_id ascending to process in order
      const sortedRuns = [...res.runs].sort((a, b) => a.run_id.localeCompare(b.run_id));
      sortedRuns.forEach(run => {
        if (!SEEN_RUNS.has(run.run_id)) {
          SEEN_RUNS.add(run.run_id);
          // Only animate/process if this is not the initial page load check
          if (SEEN_RUNS.size > 1) {
            processApiRun(run);
          }
        }
      });
    }
  } catch (err) {
    console.error("Error polling recent runs:", err);
  }
}

// --- RUN AGENT SCENARIOS VIA FASTAPI ---
let scenarioRunning = false;
async function runScenario(num) {
  if (scenarioRunning) return;
  scenarioRunning = true;
  
  document.querySelectorAll('.scenario-card').forEach(c => c.classList.remove('running'));
  const scenarioCard = document.getElementById(`scenario-${num}`);
  if (scenarioCard) scenarioCard.classList.add('running');

  const conv = document.getElementById('agent-conversation');
  if (conv) conv.innerHTML = '';
  const monitor = document.getElementById('agent-monitor');
  monitor.innerHTML = '';
  
  resetDiagramHighlights();
  
  // Update map layers to visually show the scenario route
  updateMapLayers(num);

  // --- Workflow Trace Renderer ---
  const demoPayloads = [
    "System Event: Driver using mobile device via cabin camera on Bus AU-BUS-105.",
    "Webhook Alert: Guardian not present at stop #4 for Bus AU-BUS-102. Student retained.",
    "Pre-trip compliance check failed. Braking pressure below ADEK safety threshold for Bus AU-BUS-104.",
    "System trigger: Generate Executive C-Level Summary of platform metrics.",
    "Pre-departure check: Driver DRV-4412 starting vehicle AU-BUS-105. Verify permit, medical, and training compliance before departure."
  ];
  const payload = demoPayloads[num] || "";

  // Show and reset the trace card
  const traceCard = document.getElementById('workflow-trace-card');
  const stepsDiv = document.getElementById('workflow-steps');
  const badge = document.getElementById('workflow-status-badge');
  traceCard.style.display = 'block';
  stepsDiv.innerHTML = '';
  badge.textContent = 'Running…';
  badge.style.background = 'rgba(59,130,246,.2)';
  badge.style.color = '#60a5fa';
  document.getElementById('workflow-event-text').textContent = payload;
  traceCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  // Call API Endpoint
  const res = await apiFetch("/agents/run_scenario", {
    method: "POST",
    body: JSON.stringify({ scenario_id: num, event_payload: payload })
  });

  const messages = (res && res.success) ? res.history : getFallbackHistory(num);

  // Agent colour config and getConfig moved to global scope

  const baseTag = getEventTag(num, payload);
  const uid = Math.random().toString(36).substring(2, 6).toUpperCase();
  const fullTag = `[${baseTag}-${uid}]`;
  let idx = 0;
  function nextStep() {
    if (idx === 0) {
      let alertType = 'info';
      if (baseTag === 'Distraction' || baseTag === 'Pre-Trip Compliance') alertType = 'crit';
      else if (baseTag === 'Missing Guardian' || baseTag === 'Route Deviation') alertType = 'warn';
      addAlertItem({
        type: alertType,
        text: `📢 ${fullTag} ALERT RECEIVED: ${payload}`
      });
    }

    if (idx >= messages.length) {
      scenarioRunning = false;
      if (scenarioCard) scenarioCard.classList.remove('running');
      badge.textContent = '✓ Workflow Complete';
      badge.style.background = 'rgba(16,185,129,.2)';
      badge.style.color = '#34d399';
      if (scenarioCard) scenarioCard.classList.remove('running');
      return;
    }

    const msg = messages[idx];
    const cfg = getConfig(msg.agent);
    const isLast = idx === messages.length - 1;

    if (isLast) {
      addAlertItem({
        type: 'ok',
        text: `✅ ${fullTag} OUTCOME: Final state achieved - ${msg.action || msg.text}`
      });
    }

    const step = document.createElement('div');
    step.style.cssText = `display:flex;gap:0;opacity:0;transform:translateY(8px);transition:all .4s ease;`;

    // Connector line + node circle
    const connector = document.createElement('div');
    connector.style.cssText = `display:flex;flex-direction:column;align-items:center;width:48px;flex-shrink:0;`;
    connector.innerHTML = `
      <div style="width:36px;height:36px;border-radius:50%;background:${cfg.bg};border:2px solid ${cfg.accent};display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;box-shadow:0 0 12px ${cfg.accent}44;">${cfg.icon}</div>
      ${!isLast ? `<div style="width:2px;flex:1;min-height:20px;background:linear-gradient(to bottom,${cfg.accent}88,transparent);margin-top:4px;"></div>` : ''}
    `;

    // Step content
    const content = document.createElement('div');
    content.style.cssText = `flex:1;background:${cfg.bg};border:1px solid ${cfg.border};border-radius:10px;padding:1rem 1.1rem;margin-bottom:${isLast?'0':'12px'};`;

    // Action pill (if action was taken by an agent)
    const actionPill = msg.action ? `
      <div style="display:inline-flex;align-items:center;gap:.4rem;background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.35);border-radius:20px;padding:.25rem .75rem;font-size:.72rem;font-weight:700;color:#34d399;margin-top:.6rem;">
        ⚡ Action Executed: ${msg.action}
      </div>` : '';

    // Ground vehicle pill — shown when compliance agent outputs GROUND_VEHICLE: YES
    const groundPill = (msg.text && /GROUND_VEHICLE:\s*YES/i.test(msg.text)) ? `
      <div style="display:inline-flex;align-items:center;gap:.4rem;background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.35);border-radius:20px;padding:.25rem .75rem;font-size:.72rem;font-weight:700;color:#f87171;margin-top:.4rem;margin-left:.4rem;">
        🚨 Vehicle Grounded
      </div>` : '';

    content.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
        <span style="font-weight:700;font-size:.85rem;color:${cfg.accent};">${msg.agent} <span style="font-size:.7rem;color:var(--text3);margin-left:8px;">${fullTag}</span></span>
        <span style="font-size:.72rem;color:var(--text3);background:var(--bg2);border:1px solid var(--border);border-radius:20px;padding:.2rem .6rem;">🛠️ ${msg.tool}</span>
      </div>
      <div style="font-size:.84rem;line-height:1.6;color:var(--text1);">${msg.text}</div>
      <div style="display:flex;flex-wrap:wrap;gap:.4rem;">${actionPill}${groundPill}</div>
      ${idx < messages.length - 1 ? `<div style="font-size:.72rem;color:var(--text3);margin-top:.6rem;">↳ Handing off to next agent…</div>` : '<div style="font-size:.72rem;color:#34d399;margin-top:.6rem;font-weight:600;">✓ Workflow Completed</div>'}
    `;

    step.appendChild(connector);
    step.appendChild(content);
    stepsDiv.appendChild(step);

    // Animate in
    requestAnimationFrame(() => {
      step.style.opacity = '1';
      step.style.transform = 'translateY(0)';
    });

    stepsDiv.scrollTop = stepsDiv.scrollHeight;
    highlightDiagramNode(msg.agent);
    idx++;
    setTimeout(nextStep, 1800);
  }

  nextStep();
}

function getFallbackHistory(num) {
  const history = [
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router', action: 'Routed workflow autonomously to Safety Agent.' },
      { agent: 'Safety Agent', text: '⚠️ [Distraction Triggered] Cabin camera feed on Bus AU-BUS-105 shows driver looking at phone for >4 seconds.', tool: 'Cabin Camera Edge Sensor, Incident MCP', action: 'Flagged unsafe cabin behavior (distraction).' },
      { agent: 'Compliance Agent', text: '✅ [Compliance] Safety Risk: High · Evidence Confidence: 94% · Driver DRV-4412 (Yousef Hassan): 4 prior incidents — REPEAT OFFENDER. ADEK Reg 4.2.1 (Mobile Device Use While Driving) violated. ACTION: SUSPEND. GROUND_VEHICLE: NO. Permit suspended & synced to ADEK Gov Portal.', tool: 'RAG + Incident History DB + Driver & Vehicle MCPs', action: 'Suspended DRV-4412 & synced with ADEK Gov Portal' },
      { agent: 'Incident Agent', text: '🚨 Creating emergency ticket INC-2026-882.', tool: 'Notification MCP, Incident Database', action: 'Auto-logged incident ticket INC-2026-882.' },
      { agent: 'Executive Agent', text: '📊 Logged. Fleet safety score reduced to 94.2%.', tool: 'Analytics MCP', action: 'Updated safety scorecard metrics.' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router', action: 'Routed workflow autonomously to Safety Agent.' },
      { agent: 'Safety Agent', text: '⚠️ [Missing Guardian] Supervisor on Route AU-102 reports Grade 2 student Guardian not present at stop #4.', tool: 'Route Supervisor SOP App', action: 'Activated student retention safety protocol.' },
      { agent: 'Compliance Agent', text: '✅ [Compliance] RAG: ADEK Reg 14.2 — students under Grade 3 must not be left unattended at drop-off. Driver DRV-2089: 1 prior incident (first offence, low risk). ACTION: ASSIGN_TRAINING. GROUND_VEHICLE: NO. Remedial training assigned, ADEK notified.', tool: 'RAG + Incident History DB + Driver & Vehicle MCPs', action: 'Assigned training to DRV-2089 & notified ADEK' },
      { agent: 'Incident Agent', text: '🚨 Alerting parent via WhatsApp: Student remains safely on bus.', tool: 'Notification MCP, Incident Database', action: 'Sent automated SMS notification to registered parent.' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router', action: 'Routed workflow autonomously to Route Optimization Agent.' },
      { agent: 'Compliance Agent', text: '✅ [Compliance] ADEK Fleet Rule 9.1 — pre-trip inspection failure. Vehicle AU-BUS-104: inspection_status=FAILED, GPS=offline. Driver first offence. ACTION: ASSIGN_TRAINING. GROUND_VEHICLE: YES. Vehicle grounded, training SLA assigned to driver.', tool: 'RAG + Incident History DB + Driver & Vehicle MCPs', action: 'Grounded AU-BUS-104 & assigned training SLA' },
      { agent: 'Incident Agent', text: '🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106.', tool: 'Route Optimization MCP', action: 'Dynamically recalculated alternative bus route corridor.' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Supervisor coordinated execution pipeline.', tool: 'LangGraph State Router', action: 'Routed workflow autonomously to Executive Agent.' },
      { agent: 'Compliance Agent', text: '✅ [Compliance] Weekly SLA audit: 18 pending training SLAs (3 overdue → auto-suspend triggered). 5 drivers flagged as repeat offenders (3+ incidents). Vehicle fleet: 1 grounded (inspection failed). ROUTE: executive.', tool: 'RAG + Incident History DB + Driver & Vehicle MCPs', action: 'SLA audit complete — 3 auto-suspensions triggered' },
      { agent: 'Incident Agent', text: '🚨 Incident correlation: High incident volumes matched with newer routes launched.', tool: 'Incident MCP', action: 'Mapped launching incident rates to route density.' },
      { agent: 'Executive Agent', text: '📊 Synthesizing executive report.', tool: 'Analytics MCP', action: 'Compiled strategic ADEK executive brief.' }
    ],
    [
      { agent: 'Supervisor Agent', text: '🧠 Pre-departure check initiated for DRV-4412 on AU-BUS-105. Running deterministic compliance gate before LLM pipeline.', tool: 'LangGraph State Router', action: 'Routed to Compliance Agent — Pre-departure gate.' },
      { agent: 'Compliance Agent', text: '🚫 [Pre-Departure FAILED] Driver DRV-4412 (Yousef Hassan) · Permit: Suspended · Medical: Expired · Training: Failed Evaluation. ADEK Operator Reg 3.1 — driver banned immediately. Permit status set to Suspended, ADEK Gov Portal synced.', tool: 'mcp_update_driver_status + mcp_sync_permit_status_with_gov + mcp_find_available_driver', action: 'Banned DRV-4412 — synced with ADEK Gov Portal' },
      { agent: 'Compliance Agent', text: '🔄 Replacement driver search: Found DRV-1024 (Zayed Al Mansoori, Emirates Transport) — fully compliant. Permit: Valid · Medical: Passed · Training: Complete. Route AU-BUS-105 re-assigned. Departure cleared.', tool: 'mcp_find_available_driver', action: 'Replacement DRV-1024 allocated to AU-BUS-105' },
      { agent: 'Incident Agent', text: '🚨 Incident ticket INC-2026-PRE-001 created. Operator Emirates Transport notified. Replacement driver dispatched. Route delay: ~8 minutes.', tool: 'Incident MCP + Notification MCP', action: 'Auto-logged pre-departure violation — operator notified.' }
    ]
  ];
  return history[num] || [];
}

function clearAgentLog() {
  const traceCard = document.getElementById('workflow-trace-card');
  const stepsDiv = document.getElementById('workflow-steps');
  if (stepsDiv) stepsDiv.innerHTML = '';
  if (traceCard) traceCard.style.display = 'none';
  document.querySelectorAll('.scenario-card').forEach(c => c.classList.remove('running'));
  resetDiagramHighlights();
  scenarioRunning = false;
}

function toggleArch() {
  const wrapper = document.getElementById('arch-diagram-wrapper');
  const icon = document.getElementById('arch-toggle-icon');
  if (wrapper.style.display === 'none') {
    wrapper.style.display = 'block';
    icon.textContent = '▼ Hide';
  } else {
    wrapper.style.display = 'none';
    icon.textContent = '▶ Show';
  }
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
    body: JSON.stringify({ scenario_id: 99, event_payload: queryText })
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

  if (el('kpi-open-incidents')) el('kpi-open-incidents').textContent = data.manual_overrides !== undefined ? data.manual_overrides.toString() : '0';
  if (el('kpi-resolved-count')) el('kpi-resolved-count').textContent = data.resolved_incidents !== undefined ? data.resolved_incidents.toString() : '0';
  const incSub = document.querySelector('#kpi-incidents .kpi-sub');
  if (incSub) incSub.textContent = `Escalated by Supervisor Agent`;
  const incBar = document.querySelector('#kpi-incidents .kpi-fill');
  if (incBar) {
    const total = (data.open_incidents || 0) + (data.resolved_incidents || 0);
    const pct = total > 0 ? Math.round(((data.manual_overrides || 0) / total) * 100) : 0;
    incBar.style.width = `${pct}%`;
  }

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
    const totalAed = fines.reduce((sum, f) => sum + (f.amount || 0), 0);
    if (badge) badge.textContent = `${fines.length} fines · AED ${totalAed.toLocaleString()}`;
    if (tbody) {
      tbody.innerHTML = '';
      fines.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${f.fine_id}</td><td>${f.driver_id}</td><td>${f.violation_type}</td><td style="color:#ef4444;font-weight:600">${f.amount.toLocaleString()}</td><td>${f.authority}</td>`;
        tbody.appendChild(tr);
      });
    }
  }

  // SLAs list — use mock fallback if API returns nothing
  const slaData = (slas && slas.length) ? slas : MOCK_SLAS;
  const slaList = document.getElementById('sla-list');
  const slaBadge = document.getElementById('sla-count-badge');
  const overdueCount = slaData.filter(s => s.status === 'Overdue' || (s.deadline_date && new Date(s.deadline_date) < new Date())).length;
  if (slaBadge) slaBadge.textContent = `${slaData.length} active · ${overdueCount} overdue`;
  if (document.getElementById('ck-slas')) document.getElementById('ck-slas').textContent = slaData.length;
  if (slaList) {
    slaList.innerHTML = '';
    slaData.forEach(s => {
      const item = document.createElement('div');
      item.className = 'veh-item';
      const isOverdue = s.status === 'Overdue' || (s.deadline_date && new Date(s.deadline_date) < new Date());
      const deadline = s.deadline_date.split('T')[0];
      const daysLeft = Math.ceil((new Date(s.deadline_date) - new Date()) / (1000 * 60 * 60 * 24));
      const daysLabel = isOverdue ? `<span style="color:#f87171;font-size:.68rem;">${Math.abs(daysLeft)}d overdue</span>` : `<span style="color:#fbbf24;font-size:.68rem;">${daysLeft}d left</span>`;
      item.innerHTML = `<span class="veh-plate">${s.driver_id}</span><span style="font-size:.75rem;">Due ${deadline} ${daysLabel}</span><span class="veh-status ${isOverdue ? 'vs-bad' : 'vs-warn'}">${s.status}</span>`;
      slaList.appendChild(item);
    });
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

// --- FREE-TEXT CUSTOM EVENT TRIGGER ---
async function runCustomQuery() {
  const input = document.getElementById('custom-agent-query');
  const query = input.value.trim();
  if (!query) return;
  
  // If query mentions roadblocks or routing deviation, trigger detour on map
  if (query.toLowerCase().includes("block") || query.toLowerCase().includes("closure") || query.toLowerCase().includes("deviation")) {
    updateMapLayers(99);
  } else {
    updateMapLayers(0);
  }

  const conv = document.getElementById('agent-conversation');
  const monitor = document.getElementById('agent-monitor');
  conv.innerHTML = '<div class="ai-thinking"><span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span> Supervisor routing incoming event payload to specialist agents...</div>';
  if (monitor) monitor.innerHTML = '';
  resetDiagramHighlights();

  const res = await apiFetch('/agents/run_scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: 99, event_payload: query })
  });

  conv.innerHTML = '';
  const baseTag = getEventTag(99, query);
  const uid = Math.random().toString(36).substring(2, 6).toUpperCase();
  const fullTag = `[${baseTag}-${uid}]`;
  const messages = (res && res.success) ? res.history : [{ agent: 'Supervisor Agent', text: 'Unable to reach agent pipeline.', tool: 'Fallback' }];
  let idx = 0;
  function nextStep() {
    if (idx === 0) {
      let alertType = 'info';
      if (baseTag === 'Distraction' || baseTag === 'Pre-Trip Compliance') alertType = 'crit';
      else if (baseTag === 'Missing Guardian' || baseTag === 'Route Deviation') alertType = 'warn';
      addAlertItem({
        type: alertType,
        text: `📢 ${fullTag} ALERT RECEIVED: ${query}`
      });
    }

    if (idx >= messages.length) return;
    const msg = messages[idx];

    const isLast = idx === messages.length - 1;
    if (isLast) {
      addAlertItem({
        type: 'ok',
        text: `✅ ${fullTag} OUTCOME: Final state achieved - ${msg.action || msg.text}`
      });
    }

    const mDiv = document.createElement('div');
    mDiv.className = 'conv-msg';
    mDiv.innerHTML = `<span class="conv-agent">${msg.agent} <span style="font-size:.7rem;color:var(--text3);margin-left:8px;">${fullTag}</span></span><div class="conv-text">${msg.text}</div><div class="conv-tool">🛠️ ${msg.tool}</div>`;
    conv.appendChild(mDiv);
    conv.scrollTop = conv.scrollHeight;
    highlightDiagramNode(msg.agent);
    idx++;
    setTimeout(nextStep, 1200);
  }
  nextStep();
  input.value = '';
}

// --- DRIVER TABLE FILTER ---
function filterDriverTable() {
  const q = (document.getElementById('driver-search').value || '').toLowerCase();
  document.querySelectorAll('#driver-tbody tr:not(.driver-detail-row)').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
  // Also hide any open detail rows
  document.querySelectorAll('.driver-detail-row').forEach(r => r.remove());
}

// --- DRIVER ROW EXPAND ---
function showDriverDetail(tr, drv, incCount) {
  // Remove any existing detail row
  const existing = tr.nextSibling;
  if (existing && existing.classList && existing.classList.contains('driver-detail-row')) {
    existing.remove();
    tr.style.background = '';
    return;
  }
  document.querySelectorAll('.driver-detail-row').forEach(r => r.remove());
  document.querySelectorAll('#driver-tbody tr').forEach(r => r.style.background = '');

  tr.style.background = 'rgba(59,130,246,.08)';
  const detail = document.createElement('tr');
  detail.className = 'driver-detail-row';
  const riskColor = drv.is_repeat_offender || incCount >= 3 ? '#ef4444' : incCount >= 1 ? '#f59e0b' : '#10b981';
  const riskLabel = drv.is_repeat_offender || incCount >= 3 ? 'HIGH — Repeat Offender' : incCount >= 1 ? 'MEDIUM' : 'LOW';
  detail.innerHTML = `
    <td colspan="7" style="background:var(--bg3);padding:.75rem 1rem;font-size:.78rem;border-left:3px solid ${riskColor};">
      <div style="display:flex;gap:2rem;flex-wrap:wrap;">
        <div><strong style="color:var(--text2)">Operator</strong><br>${drv.operator || '—'}</div>
        <div><strong style="color:var(--text2)">Prior Incidents</strong><br><span style="color:${riskColor};font-weight:700">${incCount}</span></div>
        <div><strong style="color:var(--text2)">Risk Profile</strong><br><span style="color:${riskColor};font-weight:700">${riskLabel}</span></div>
        <div><strong style="color:var(--text2)">Compliance Agent Action</strong><br>${drv.permit_status === 'Suspended' ? '🔴 Suspended by Compliance Agent' : incCount >= 1 ? '🟡 Training SLA assigned' : '🟢 Compliant — No action required'}</div>
      </div>
    </td>`;
  tr.after(detail);
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
      body: JSON.stringify({ scenario_id: 3, event_payload: 'Generate a brief executive compliance summary for the Abu Dhabi school transport fleet' })
    });
    if (res && res.success && res.history.length) {
      const last = res.history[res.history.length - 1];
      summaryDiv.innerHTML = `<p style="margin-bottom:.5rem"><strong>${last.agent}:</strong></p><p>${last.text}</p>`;
    } else {
      summaryDiv.innerHTML = `<p>Executive summary unavailable. Run a scenario to generate insights.</p>`;
    }
  })();

  // Poll for API events in the background
  (async () => {
    try {
      const res = await apiFetch('/agents/recent_runs');
      if (res && res.success && res.runs) {
        res.runs.forEach(run => SEEN_RUNS.add(run.run_id));
      }
    } catch (e) {}
    setInterval(pollRecentRuns, 2000);
  })();

  LIVE_ALERTS.forEach(al => addAlertItem(al));
};
