document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = 'http://localhost:8000';
    const WS_BASE = 'ws://localhost:8000/ws';

    let sensors = [];
    let currentSensorId = null;
    let qualityChart, tempChart;

    // --- Chart Initializations ---
    function initCharts() {
        const ctxQuality = document.getElementById('qualityChart').getContext('2d');
        const ctxTemp = document.getElementById('tempChart').getContext('2d');

        const chartConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#64748b', font: { family: 'Outfit' } }
                }
            },
            scales: {
                y: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { color: '#64748b' } },
                x: { grid: { display: false }, ticks: { color: '#64748b' } }
            }
        };

        qualityChart = new Chart(ctxQuality, {
            type: 'line',
            data: {
                labels: Array(10).fill(''),
                datasets: [
                    { label: 'pH Level', data: Array(10).fill(7), borderColor: '#0ea5e9', backgroundColor: 'rgba(14, 165, 233, 0.1)', fill: true, tension: 0.4 },
                    { label: 'TDS (scaled)', data: Array(10).fill(4.5), borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)', fill: true, tension: 0.4 }
                ]
            },
            options: chartConfig
        });

        tempChart = new Chart(ctxTemp, {
            type: 'line',
            data: {
                labels: Array(10).fill(''),
                datasets: [{ label: 'Temperature °C', data: Array(10).fill(24), borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.4 }]
            },
            options: chartConfig
        });
    }

    // --- Backend Integration ---
    async function fetchSensors() {
        try {
            const res = await fetch(`${API_BASE}/sensors`);
            const data = await res.json();
            sensors = data.sensors;
            populateVillageSelector();
            if (sensors.length > 0 && !currentSensorId) {
                selectSensor(sensors[0].id);
            }
        } catch (err) {
            console.error('Error fetching sensors:', err);
        }
    }

    function populateVillageSelector() {
        const selector = document.getElementById('village-selector');
        selector.innerHTML = '<option value="all">All Villages</option>';
        sensors.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `${s.village} (${s.id})`;
            selector.appendChild(opt);
        });
    }

    async function getPrediction(sensor) {
        try {
            const res = await fetch(`${API_BASE}/public/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sensor_id: sensor.id,
                    village: sensor.village,
                    temperature: sensor.readings.temperature,
                    ph: sensor.readings.ph,
                    turbidity: sensor.readings.turbidity,
                    tds: sensor.readings.tds
                })
            });
            const data = await res.json();
            updatePredictionUI(data);
        } catch (err) {
            console.error('Prediction error:', err);
        }
    }

    function updatePredictionUI(data) {
        const safetyEl = document.getElementById('prediction-status');
        const diseaseEl = document.getElementById('disease-status');

        // Handle both simple and advanced results
        const isSafe = data.water_safety ? data.water_safety.is_safe : (data.result === 'Safe');
        const disease = data.disease_prediction ? data.disease_prediction.predicted_disease : 'None';

        safetyEl.textContent = isSafe ? 'SAFE' : 'CONTAMINATED';
        safetyEl.className = `status ${isSafe ? 'safe' : 'danger'}`;

        diseaseEl.textContent = disease.toUpperCase();
        diseaseEl.className = `status ${disease === 'No Disease' || disease === 'None' ? 'safe' : 'danger'}`;
    }

    function updateDashboard(sensor) {
        if (sensor.id !== currentSensorId && document.getElementById('village-selector').value !== 'all') return;

        document.getElementById('val-ph').textContent = sensor.readings.ph.toFixed(1);
        document.getElementById('val-tds').textContent = Math.round(sensor.readings.tds);
        document.getElementById('val-turbidity').textContent = sensor.readings.turbidity.toFixed(1);
        document.getElementById('val-temp').textContent = sensor.readings.temperature.toFixed(1);
        document.getElementById('node-info').textContent = `Live data from ${sensor.village} (Node: ${sensor.id})`;

        // Update Charts
        qualityChart.data.datasets[0].data.push(sensor.readings.ph);
        qualityChart.data.datasets[0].data.shift();
        qualityChart.data.datasets[1].data.push(sensor.readings.tds / 100);
        qualityChart.data.datasets[1].data.shift();
        qualityChart.update();

        tempChart.data.datasets[0].data.push(sensor.readings.temperature);
        tempChart.data.datasets[0].data.shift();
        tempChart.update();

        getPrediction(sensor);
    }

    function setupWebSocket() {
        const ws = new WebSocket(WS_BASE);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'sensor_update') {
                // Backend format is slightly different from our UI format, normalize it
                const sensor = {
                    id: data.sensor.id,
                    village: data.sensor.village,
                    readings: {
                        ph: data.sensor.ph,
                        tds: data.sensor.tds,
                        turbidity: data.sensor.turbidity,
                        temperature: data.sensor.temperature
                    }
                };
                updateDashboard(sensor);
            }
        };
        ws.onclose = () => {
            console.log('WebSocket closed, retrying...');
            setTimeout(setupWebSocket, 3000);
        };
    }

    function selectSensor(id) {
        currentSensorId = id;
        const sensor = sensors.find(s => s.id === id);
        if (sensor) updateDashboard(sensor);
    }

    // --- Simulation (Pushing to Backend) ---
    function startSimulation() {
        setInterval(async () => {
            if (!currentSensorId) return;
            const sensor = sensors.find(s => s.id === currentSensorId) || sensors[0];
            
            // Randomize data
            const newData = {
                id: sensor.id,
                village: sensor.village,
                lat: sensor.location?.lat || 0,
                lng: sensor.location?.lng || 0,
                ph: sensor.readings.ph + (Math.random() - 0.5) * 0.2,
                tds: sensor.readings.tds + (Math.random() - 0.5) * 20,
                turbidity: sensor.readings.turbidity + (Math.random() - 0.5) * 0.3,
                temperature: sensor.readings.temperature + (Math.random() - 0.5) * 0.5
            };

            // Post to backend to trigger WebSocket broadcast
            try {
                await fetch(`${API_BASE}/public/sensor_data`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newData)
                });
            } catch (err) { console.error('Sim post failed', err); }
        }, 4000);
    }

    // --- Event Listeners ---
    document.getElementById('village-selector').addEventListener('change', (e) => {
        if (e.target.value !== 'all') {
            selectSensor(e.target.value);
        }
    });

    // --- Init ---
    initCharts();
    fetchSensors().then(() => {
        setupWebSocket();
        startSimulation();
    });
});
