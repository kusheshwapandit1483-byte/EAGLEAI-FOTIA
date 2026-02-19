import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getDatabase, ref, onValue, query, limitToLast, orderByChild } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-database.js";
import { firebaseConfig } from './firebase_config.js';

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

let allHistoryData = [];

// DOM Elements
const tableBody = document.getElementById('historyBody');
const searchInput = document.getElementById('logSearch');
const loader = document.getElementById('loader'); // Get loader
let currentFilter = 'all';

// Show loader initially
if (loader) loader.style.display = 'flex';

// --- FETCH DATA ---
const historyRef = query(ref(db, 'history'), limitToLast(100)); // Limit to last 100 for performance

onValue(historyRef, (snapshot) => {
    const data = snapshot.val();
    tableBody.innerHTML = ''; // Clear loading/old data
    allHistoryData = [];

    if (data) {
        // Convert object to array and reverse (newest first)
        Object.keys(data).forEach(key => {
            allHistoryData.push(data[key]);
        });

        // Sort descending (newest first). Handle both 'timestamp' and 'start_time'
        allHistoryData.sort((a, b) => {
            const timeA = a.timestamp || a.start_time || 0;
            const timeB = b.timestamp || b.start_time || 0;
            return timeB - timeA;
        });

        renderTable();
    } else {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No history records found.</td></tr>';
    }

    // Hide loader after render
    if (loader) loader.style.display = 'none';
});

// --- RENDER TABLE (Advanced) ---
function renderTable() {
    tableBody.innerHTML = '';
    const searchTerm = searchInput.value.toLowerCase();

    // 1. Filter Data
    const filteredData = allHistoryData.filter(item => {
        // Tab Filter
        let matchesTab = true;
        if (currentFilter === 'ALARM') matchesTab = item.event_type === 'ALARM';
        else if (currentFilter === 'STATUS') matchesTab = item.event_type === 'STATUS_CHANGE' || item.event_type === 'MODE_CHANGE';
        else if (currentFilter === 'SYSTEM') matchesTab = !item.event_type || (item.pump_name && (item.pump_name.includes('Pressure') || item.pump_name.includes('Battery') || item.pump_name.includes('Tank')));

        // Search Filter
        let matchesSearch = true;
        if (searchTerm) {
            const str = ((item.pump_name || '') + (item.event_type || '') + (item.message || '') + (item.date_formatted || '')).toLowerCase();
            matchesSearch = str.includes(searchTerm);
        }

        return matchesTab && matchesSearch;
    });

    if (filteredData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="empty-state">No matching records found.</td></tr>';
        return;
    }

    // 2. Group by Date
    let lastDateHeader = null;

    filteredData.forEach(item => {
        // Determine Date String for Header
        const timeVal = item.timestamp || item.start_time || 0;
        const dateObj = new Date(timeVal);
        const dateKey = dateObj.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

        // Insert Header if new date
        if (dateKey !== lastDateHeader) {
            const headerRow = document.createElement('tr');
            headerRow.className = 'date-header';

            // "Today" / "Yesterday" Logic
            const today = new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            let displayDate = dateKey;
            if (dateKey === today) displayDate = "Today, " + dateKey;

            headerRow.innerHTML = `<td colspan="4">${displayDate}</td>`;
            tableBody.appendChild(headerRow);
            lastDateHeader = dateKey;
        }

        // 3. Render Row (Same logic as before, just generating TR)
        const row = document.createElement('tr');

        // ... (Logic for Icon/Badge/Cols - Reuse from previous step) ...
        // Re-implementing concise row generation here to ensure connection
        let dateStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        let sourceIcon, eventTypeHtml, description, sourceName;

        const name = (item.pump_name || '').toLowerCase();
        sourceName = item.pump_name;

        if (name.includes('diesel')) sourceIcon = 'local_gas_station';
        else if (name.includes('tank')) sourceIcon = 'water_drop';
        else if (name.includes('battery')) sourceIcon = 'battery_alert';
        else if (name.includes('pressure')) sourceIcon = 'speed';
        else if (name.includes('jockey') || name.includes('main') || name.includes('sprinkler')) sourceIcon = 'water';
        else sourceIcon = 'dns';

        if (item.event_type) {
            let badgeClass = 'info';
            let icon = 'info';

            if (item.event_type === 'ALARM') { badgeClass = 'danger'; icon = 'warning'; }
            if (item.event_type === 'STATUS_CHANGE') { badgeClass = 'success'; icon = 'check_circle'; }
            if (item.event_type === 'MODE_CHANGE') { badgeClass = 'warning'; icon = 'settings'; }

            eventTypeHtml = `
                <span class="event-badge ${badgeClass}">
                    <span class="material-icons-round" style="font-size:14px;">${icon}</span>
                    ${item.event_type === 'ALARM' ? 'ALERT' : item.event_type.replace('_', ' ')}
                </span>
            `;
            description = item.message;
        } else {
            // Legacy
            const mins = Math.floor((item.duration_seconds || 0) / 60);
            eventTypeHtml = `<span class="event-badge success"><span class="material-icons-round" style="font-size:14px;">history</span> RUN CYCLE</span>`;
            description = `Ran for ${mins}m ${(item.duration_seconds || 0) % 60}s`;
        }

        row.innerHTML = `
            <td class="time-col">${dateStr}</td>
            <td>
                <div class="source-cell">
                    <div class="source-icon"><span class="material-icons-round">${sourceIcon}</span></div>
                    ${sourceName}
                </div>
            </td>
            <td>${eventTypeHtml}</td>
            <td>${description}</td>
        `;
        tableBody.appendChild(row);
    });
}

// --- CONTROLS ---
window.filterLogs = function (type) {
    currentFilter = type;

    // Update Active Button UI
    document.querySelectorAll('.segment-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes(type) || (type === 'all' && btn.textContent.includes('All'))) {
            // Simple hack for demo, ideally ID match
        }
    });
    // Hard reset for safety
    const buttons = document.querySelectorAll('.segment-btn');
    buttons.forEach(b => b.classList.remove('active'));

    if (type === 'all') buttons[0].classList.add('active');
    if (type === 'ALARM') buttons[1].classList.add('active');
    if (type === 'STATUS') buttons[2].classList.add('active');
    if (type === 'SYSTEM') buttons[3].classList.add('active');

    renderTable();
}

searchInput.addEventListener('input', renderTable);

// --- EXPORT CSV ---
window.exportToCSV = function () {
    if (allHistoryData.length === 0) {
        alert("No data to export!");
        return;
    }

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Date,Source,Event Type,Description,Duration (New/Old)\n";

    allHistoryData.forEach(item => {
        const timeVal = item.timestamp || item.start_time || 0;
        const dateObj = new Date(timeVal);
        const dateStr = dateObj.toLocaleString().replace(',', '');

        let source, event, desc, dur = "";

        if (item.event_type) {
            source = item.pump_name;
            event = item.event_type;
            desc = item.message;
        } else {
            source = item.pump_name;
            event = "RUN_CYCLE";
            desc = "Run Duration";
            dur = item.duration_seconds;
        }

        csvContent += `${dateStr},${source},${event},${desc},${dur}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "pump_history_export.csv");
    document.body.appendChild(link); // Required for FF
    link.click();
    document.body.removeChild(link);
}

// --- LIVE ALERTS BADGE (Synced with Dashboard) ---
const liveDataRef = query(ref(db, 'live_data'), limitToLast(1));

onValue(liveDataRef, (snapshot) => {
    const rawData = snapshot.val();
    if (rawData) {
        const keys = Object.keys(rawData);
        const latestKey = keys[keys.length - 1];
        const finalData = rawData[latestKey];
        calculateAlarms(finalData);
    }
});

function calculateAlarms(data) {
    let count = 0;

    // 1. Pressure < 4.15
    if ((parseFloat(data.pressure) || 0) < 4.15) count++;

    // 2-4. Pumps ON
    const pumps = data.pumps || data.Pumps || {};
    const isRunning = (p) => (p && (p.status === 'ON'));
    if (isRunning(pumps.jockey || pumps.Jockey)) count++;
    if (isRunning(pumps.main || pumps.Main)) count++;
    if (isRunning(pumps.sprinkler || pumps.Sprinkler)) count++;
    if (isRunning(pumps.diesel || pumps.Diesel)) count++;

    // 5. Tank Level < 95
    const tank = parseFloat(data.waterLevel || data.tank_level || 0);
    if (tank < 95) count++;

    // 6. Manual Mode
    const getMode = (p) => (p && p.mode) ? p.mode : 'AUTO';
    const jMode = getMode(pumps.jockey || pumps.Jockey);
    const mMode = getMode(pumps.main || pumps.Main);
    const sMode = getMode(pumps.sprinkler || pumps.Sprinkler);
    const dMode = getMode(pumps.diesel || pumps.Diesel);
    if (jMode === 'MANUAL' || mMode === 'MANUAL' || sMode === 'MANUAL' || dMode === 'MANUAL') count++;

    // 7. Diesel Level < 95
    const diesel = parseFloat(data.dieselLevel || data.diesel_level || 0);
    if (diesel < 95) count++;

    // 8. Battery Voltage ( < 11.8 or > 14.2 )
    const batt = parseFloat(data.batteryVolts || data.batteryVoltage || data.battery_voltage || 0);
    if (batt < 11.8 || batt > 14.2) count++;

    // Update UI
    const alarmCountEl = document.getElementById('alarmCount');
    if (alarmCountEl) alarmCountEl.innerText = count;
}
