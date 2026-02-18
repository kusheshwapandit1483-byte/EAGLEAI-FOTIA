// Path: static/js/dashboard.js

import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getDatabase, ref, onValue, update, query, limitToLast } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-database.js";

// Import config (Ensure this file exists in static/js/)
import { firebaseConfig } from './firebase_config.js';

const app = initializeApp({
    ...firebaseConfig,
    databaseURL: window.FACTORY_DB_URL || firebaseConfig.databaseURL
});
const db = getDatabase(app);

// --- 1. SETUP LISTENERS ---

// Use a Query to get only the latest entry from 'live_data'
const liveDataRef = query(ref(db, 'live_data'), limitToLast(1));



// --- 2. LISTEN FOR LIVE SENSOR DATA ---
onValue(liveDataRef, (snapshot) => {
    const rawData = snapshot.val();

    if (rawData) {
        // DATA PROCESSING LOGIC:
        // Firebase returns an object like: { "-OhOj...": { pressure: 0, ... } }
        // We extract the value *inside* that dynamic key.
        const keys = Object.keys(rawData);
        const latestKey = keys[keys.length - 1]; // Get the most recent ID
        const finalData = rawData[latestKey];    // Get the actual data inside it

        console.log("🔥 Latest Data:", finalData); // Debugging
        updateDashboard(finalData);
    } else {
        console.warn("⚠️ No data found in 'live_data'");
    }
});



// Helper for Pulse Animation
function pulse(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.classList.remove("data-updated");
        void el.offsetWidth; // Trigger reflow
        el.classList.add("data-updated");
    }
}

// ============================================================
// UI UPDATE FUNCTIONS
// ============================================================

function updateDashboard(data) {
    // 1. Timestamp
    if (data.lastUpdated) {
        const date = new Date(data.lastUpdated);
        document.getElementById('lastUpdated').textContent = "Updated: " + date.toLocaleString();
        // Mobile last updated
        const mobileLastUpdated = document.getElementById('mobileLastUpdated');
        if (mobileLastUpdated) mobileLastUpdated.textContent = date.toLocaleTimeString();
    }

    // 2. Pressure Display
    // 2. Pressure Display
    const pressure = parseFloat(data.pressure || 0);
    document.getElementById('pressureValue').textContent = pressure.toFixed(1);
    pulse('pressureValue'); // Pulse animation

    // Gauge Logic
    // Range: 0 to 9 kg/cm2
    // Angle: -135deg (0) to +135deg (9) -> Total swing 270deg
    const maxPressure = 9;
    const minAngle = -135;
    const maxAngle = 135;

    // Clamp pressure between 0 and max
    const clampedPressure = Math.max(0, Math.min(pressure, maxPressure));

    // Calculate rotation
    const rotation = minAngle + ((clampedPressure / maxPressure) * (maxAngle - minAngle));

    // Apply rotation
    const needle = document.getElementById('pressureNeedle');
    if (needle) {
        needle.style.transform = `translateX(-50%) translateY(-100%) rotate(${rotation}deg)`;

        // Color logic for needle (optional, or keep standard red)
        if (pressure >= 12) {
            needle.style.filter = "brightness(1.2) drop-shadow(0 0 2px red)";
        } else {
            needle.style.filter = "none";
        }
    }

    // Status Text Logic
    const pStatus = document.getElementById('pressureStatus');
    const pCard = document.getElementById('cardPressure');

    // Reset critical status primarily
    if (pCard) pCard.classList.remove('status-critical');

    if (pStatus) {
        if (pressure < 6) {
            pStatus.textContent = "Low Pressure";
            pStatus.style.color = "var(--accent-red)";
            if (pCard) pCard.classList.add('status-critical'); // Add Red Pulse
        } else if (pressure > 7) {
            pStatus.textContent = "High Pressure";
            pStatus.style.color = "var(--accent-red)";
            if (pCard) pCard.classList.add('status-critical'); // Add Red Pulse
        } else {
            pStatus.textContent = "Normal Pressure";
            pStatus.style.color = "var(--text-secondary)";
        }
    }

    // 3. Tank Level Display
    const tankLevel = data.waterLevel || 0;
    const tankValEl = document.getElementById('tankValue');
    if (tankValEl) {
        tankValEl.textContent = tankLevel;
        pulse('tankValue');
    }

    // Update Tank Visual Bar
    // Update Tank Visual Bar
    const tankBar = document.getElementById('tankLevelBar');
    if (tankBar) {
        // The sight glass on the chrome image is approximately 62% of the image height
        const maxVisualHeightPercentage = 62;
        const finalHeight = (tankLevel / 100) * maxVisualHeightPercentage;
        tankBar.style.height = `${finalHeight}%`;

        // Critical Level Coloring & Status Text
        const tankStatusEl = document.getElementById('tankStatus');
        const tankCard = document.getElementById('cardTank');

        // Reset
        if (tankCard) tankCard.classList.remove('status-critical');

        if (tankLevel < 95) {
            // Red for low/critical level
            tankBar.style.background = "linear-gradient(180deg, #EF4444 0%, #DC2626 100%)";
            tankBar.style.boxShadow = "0 0 8px rgba(239, 68, 68, 0.6)";

            if (tankStatusEl) {
                tankStatusEl.textContent = "Critical Level";
                tankStatusEl.style.color = "var(--accent-red)";
            }
            if (tankCard) tankCard.classList.add('status-critical'); // Red Pulse
        } else {
            // Blue for normal/optimal
            tankBar.style.background = "linear-gradient(180deg, #60A5FA 0%, #3B82F6 100%)";
            tankBar.style.boxShadow = "0 0 8px rgba(59, 130, 246, 0.6)";

            if (tankStatusEl) {
                tankStatusEl.textContent = "Optimal Level";
                tankStatusEl.style.color = "var(--text-secondary)"; // Or var(--accent-blue)
            }
        }
    }

    // 4. Update Pump Cards
    const pumps = data.pumps || data.Pumps; // Fallback for case sensitivity
    if (pumps) {
        updatePumpCard('Main', pumps.main || pumps.Main);
        updatePumpCard('Jockey', pumps.jockey || pumps.Jockey);

        updatePumpCard('Diesel', pumps.diesel || pumps.Diesel);
    }

    // 5. BATTERY & DIESEL (New Sensors)
    const batt = data.batteryVoltage || 0;
    document.getElementById('batteryValue').textContent = batt;
    pulse('batteryValue');

    // Simple visual check for battery status
    // Simple visual check for battery status
    const batStatus = document.getElementById('batteryStatus');
    const batCard = document.getElementById('cardBattery');

    // Reset critical status
    if (batCard) batCard.classList.remove('status-critical');

    if (batt < 11.8) {
        batStatus.textContent = "Low Voltage";
        batStatus.style.color = "var(--accent-red)";
        if (batCard) batCard.classList.add('status-critical'); // Add Red Pulse
    } else if (batt > 14.2) {
        batStatus.textContent = "High Voltage";
        batStatus.style.color = "var(--accent-red)";
        if (batCard) batCard.classList.add('status-critical'); // Add Red Pulse
    } else {
        batStatus.textContent = "Normal Voltage";
        batStatus.style.color = "var(--text-secondary)";
    }

    // Dynamic Battery Indicators (Removed for Solid Battery)


    const diesel = data.dieselLevel || 0;
    const dieselUnitEl = document.getElementById('dieselUnit');
    const dieselValEl = document.getElementById('dieselLevelValue');

    if (dieselValEl) {
        if (diesel < 95) {
            dieselValEl.textContent = "Low";
            dieselValEl.style.color = "#DC2626"; // Red
            if (dieselUnitEl) dieselUnitEl.style.display = 'none';
        } else {
            dieselValEl.textContent = "Above 95%";
            dieselValEl.style.color = "#10B981"; // Green (success)
            if (dieselUnitEl) dieselUnitEl.style.display = 'none';
        }
    }

    // Needle logic removed as per user request

    // Color Logic & Status Text
    const dieselStatusEl = document.getElementById('dieselStatus');
    const dieselCard = document.getElementById('cardDieselLevel');

    // Reset
    if (dieselCard) dieselCard.classList.remove('status-critical');

    if (diesel < 95) {
        // Critical Level
        if (dieselStatusEl) {
            dieselStatusEl.textContent = "Critical Level";
            dieselStatusEl.style.color = "var(--accent-red)";
        }
        if (dieselCard) dieselCard.classList.add('status-critical'); // Red Pulse
    } else {
        // Normal Level
        if (dieselStatusEl) {
            dieselStatusEl.textContent = "Normal Level";
            dieselStatusEl.style.color = "var(--text-secondary)";
        }
    }



    function updatePumpCard(type, pumpData) {
        if (!pumpData) return;

        // Card ID
        const cardEl = document.getElementById(`card${type}`);
        // Status Text ID
        const statusTextEl = document.getElementById(`statusText${type}`);

        if (!cardEl || !statusTextEl) return;

        // Determine Mode
        const mode = pumpData.mode || "AUTO";

        // Reset classes
        cardEl.className = "pump-card"; // Keep base class
        statusTextEl.className = "pump-status-text";

        // Logic
        if (mode === "MANUAL") {
            cardEl.classList.add("status-manual");
            statusTextEl.classList.add("status-text-manual");
            statusTextEl.textContent = "MANUAL";
        } else if (mode === "OFF") {
            cardEl.classList.add("status-off");
            statusTextEl.classList.add("status-text-off");
            statusTextEl.textContent = "OFF";
        } else {
            // Default to AUTO or STANDBY (treated as green/good)
            cardEl.classList.add("status-auto");
            statusTextEl.classList.add("status-text-auto");
            statusTextEl.textContent = "AUTO";
        }
    }



    // 6. Update Alarm Count (Synchronization)
    calculateAlarms(data);

} // End updateDashboard

// --- ALARM COUNTING LOGIC (Synced with alarms.html) ---
function calculateAlarms(data) {
    let count = 0;

    // 1. Pressure < 6
    if ((parseFloat(data.pressure) || 0) < 6) count++;

    // 2-4. Pumps ON (Check inside data.pumps)
    const pumps = data.pumps || data.Pumps || {};

    const isRunning = (p) => (p && (p.status === 'ON'));

    if (isRunning(pumps.jockey || pumps.Jockey)) count++;
    if (isRunning(pumps.main || pumps.Main)) count++;

    if (isRunning(pumps.diesel || pumps.Diesel)) count++;

    // 5. Tank Level < 95
    const tank = parseFloat(data.waterLevel || data.tank_level || 0);
    if (tank < 95) count++;

    // 6. Manual Mode (Aggregate)
    const getMode = (p) => (p && p.mode) ? p.mode : 'AUTO';
    const jMode = getMode(pumps.jockey || pumps.Jockey);
    const mMode = getMode(pumps.main || pumps.Main);

    const dMode = getMode(pumps.diesel || pumps.Diesel);

    if (jMode === 'MANUAL' || mMode === 'MANUAL' || dMode === 'MANUAL') {
        count++;
    }

    // 7. Diesel Level < 95
    const diesel = parseFloat(data.dieselLevel || data.diesel_level || 0);
    if (diesel < 95) count++;

    // 8. Battery Voltage ( < 11.8 or > 14.2 )
    const batt = parseFloat(data.batteryVoltage || data.battery_voltage || 0);
    if (batt < 11.8 || batt > 14.2) count++;

    // Update UI
    const alarmCountEl = document.getElementById('alarmCount');
    if (alarmCountEl) alarmCountEl.innerText = count;
    // Mobile alarm count
    const mobileAlarmCount = document.getElementById('mobileAlarmCount');
    if (mobileAlarmCount) mobileAlarmCount.innerText = count;
}
