// Path: static/js/analytics.js

import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getDatabase, ref, query, limitToLast, onValue } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-database.js";
import { firebaseConfig } from './firebase_config.js';

const app = initializeApp({
    ...firebaseConfig,
    databaseURL: window.FACTORY_DB_URL || firebaseConfig.databaseURL
});
const db = getDatabase(app);

// Globals
let pressureChart, tankChart, dieselChart;
let dataLimit = 3000; // Increased to ensure enough data for 24h hourly view

// --- INITIALIZE CHARTS ---
function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 } } },
            y: { grid: { color: '#f0f0f0' }, beginAtZero: true }
        },
        elements: {
            point: { radius: 3, hoverRadius: 6 },
            line: { tension: 0.4 } // Makes the line smooth/curved
        }
    };

    // 1. Pressure Chart (Orange)
    const pCanvas = document.getElementById('pressureChart');
    if (pCanvas) {
        const ctx1 = pCanvas.getContext('2d');
        pressureChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: [], datasets: [{
                    data: [],
                    borderColor: '#ff9500',
                    backgroundColor: 'rgba(255, 149, 0, 0.1)',
                    fill: true, borderWidth: 2
                }]
            },
            options: commonOptions
        });
    }

    // 2. Tank Chart (Blue)
    const tCanvas = document.getElementById('tankChart');
    if (tCanvas) {
        const ctx2 = tCanvas.getContext('2d');
        tankChart = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: [], datasets: [{
                    data: [],
                    borderColor: '#0071e3',
                    backgroundColor: 'rgba(0, 113, 227, 0.1)',
                    fill: true, borderWidth: 2
                }]
            },
            options: {
                ...commonOptions,
                scales: { y: { min: 0, max: 100 } } // Fix tank scale 0-100%
            }
        });
    }

    // 3. Diesel Chart (Amber)
    const dCanvas = document.getElementById('dieselChart');
    if (dCanvas) {
        const ctx3 = dCanvas.getContext('2d');
        dieselChart = new Chart(ctx3, {
            type: 'line',
            data: {
                labels: [], datasets: [{
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    fill: true, borderWidth: 2
                }]
            },
            options: {
                ...commonOptions,
                scales: { y: { min: 0, max: 100 } } // Fix tank scale 0-100%
            }
        });
    }
}

// --- FETCH DATA ---
function loadData(limit) {
    const liveDataRef = query(ref(db, 'live_data'), limitToLast(limit));

    onValue(liveDataRef, (snapshot) => {
        const raw = snapshot.val();
        if (!raw) return;

        const labels = [];
        const pressureData = [];
        const tankData = [];
        const dieselData = [];

        // Helper to parse dates manually if standard parsing fails
        function parseDate(dateString) {
            // Try standard parsing first
            let date = new Date(dateString);
            if (!isNaN(date.getTime())) return date;

            // Handle DD-MM-YYYY HH:mm:ss
            if (typeof dateString === 'string') {
                const parts = dateString.split(/[- :]/); // Split by - or : or space
                if (parts.length >= 6) {
                    return new Date(parts[2], parts[1] - 1, parts[0], parts[3], parts[4], parts[5]);
                }
            }
            return new Date(0);
        }

        const now = Date.now();
        // Snap to the start of the current hour to make buckets clean
        const currentHourStart = new Date(now).setMinutes(0, 0, 0);

        // We want the last 24 hours (or 48, based on user preference, but "hourly graph" usually implies a clearer recent trend).
        // Let's stick to the previous range logic but bucket it. 
        // 1000 points raw is a lot. Let's show the last 24 hours in hourly buckets.
        const durationHours = 24;
        const startTimestamp = currentHourStart - ((durationHours - 1) * 60 * 60 * 1000);
        const bucketSize = 60 * 60 * 1000; // 1 hour

        const totalBuckets = durationHours;

        // Initialize buckets
        const buckets = new Array(totalBuckets).fill(null).map(() => ({
            count: 0,
            pressureSum: 0,
            tankSum: 0,
            dieselSum: 0
        }));

        // Process Raw Data
        Object.values(raw).forEach(entry => {
            if (entry.lastUpdated) {
                const date = parseDate(entry.lastUpdated);
                const time = date.getTime();

                if (time < startTimestamp) return;

                // Determine Bucket Index
                const bucketIndex = Math.floor((time - startTimestamp) / bucketSize);

                if (bucketIndex >= 0 && bucketIndex < totalBuckets) {
                    const b = buckets[bucketIndex];
                    b.count++;
                    b.pressureSum += parseFloat(entry.pressure || 0);
                    const wLevel = (entry.waterLevel !== undefined) ? entry.waterLevel : (entry.tankLevel || 0);
                    b.tankSum += parseFloat(wLevel);
                    const dLevel = (entry.dieselLevel !== undefined) ? entry.dieselLevel : (entry.diesel_level || 0);
                    b.dieselSum += parseFloat(dLevel);
                }
            }
        });

        // Generate Labels and Data
        for (let i = 0; i < totalBuckets; i++) {
            const bucketTime = new Date(startTimestamp + (i * bucketSize));
            // Label: HH:00
            labels.push(bucketTime.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }));

            const b = buckets[i];
            if (b.count > 0) {
                pressureData.push(b.pressureSum / b.count);
                tankData.push(b.tankSum / b.count);
                dieselData.push(b.dieselSum / b.count);
            } else {
                // Return null instead of 0 to avoid "collapsing to zero"
                // This will create a gap or stop the line, rather than showing "Empty Tank"
                pressureData.push(null);
                tankData.push(null);
                dieselData.push(null);
            }
        }

        // Update Header Time
        const headerTime = document.getElementById('lastUpdated');
        if (headerTime) headerTime.textContent = "Last 24 Hours (Hourly Average)";

        // Update Charts
        // Update Charts
        if (pressureChart) {
            pressureChart.data.labels = labels;
            pressureChart.data.datasets[0].data = pressureData;
            pressureChart.update();
        }

        if (tankChart) {
            tankChart.data.labels = labels;
            tankChart.data.datasets[0].data = tankData;
            tankChart.update();
        }

        if (dieselChart) {
            dieselChart.data.labels = labels;
            dieselChart.data.datasets[0].data = dieselData;
            dieselChart.update();
        }
    });
}

// --- CONTROLS ---
window.updateTimeRange = (limit) => {
    dataLimit = limit;

    // Update button styling
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes(limit)) btn.classList.add('active');
    });

    // Reload Data with new limit
    // Note: We create a new listener. Ideally, we should detach old ones, 
    // but for a simple dashboard, this overwrite is acceptable.
    loadData(limit);
};

// Start
initCharts();
loadData(dataLimit);