const elSpeed      = document.getElementById('velocitaVal');
const elTempEng1   = document.getElementById('tempMotore1');
const elTempEng2   = document.getElementById('tempMotore2');
const elTempInv1   = document.getElementById('tempInverter1');
const elTempInv2   = document.getElementById('tempInverter2');
const elTempBatt   = document.getElementById('tempBatteryPack');
const elVoltBattHV = document.getElementById('voltageModuli');
const elVoltBattLV = document.getElementById('voltageBatteryLV');
const elSoC        = document.getElementById('percentualeCarica');
const elCurrentBMS = document.getElementById('currentBMS');
const elGPSValue   = document.getElementById('posGps');

// Timestamp last message received
let lastMessageTime = null;

const TEMP_MAX_MOTORE   = 130;   // th motors
const TEMP_MAX_INVERTER = 70;   // th inverter
const TEMP_MAX_BATTERY  = 65;   // th battery pack

const STATUS_TIMEOUT_MS = 30000; // 30 secondi senza messaggi = offline

//coordinate UNIVPM, Ancona, IT
//20 = max zoom (0-19)
let currentLat = 43.586374637187404;
let currentLon = 13.516547970917285;
var map = L.map('mapid').setView([currentLat,currentLon], 19); 

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    minZoom:0,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
});

var osmHOT = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
    maxZoom: 19,
    minZoom:0,
    attribution: ''});

var esriSatelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: "",
    minZoom: 0,
    maxZoom: 19
});

//deafult
osmLayer.addTo(map);

var baseMaps = {
    "OpenStreetMap": osmLayer,
    "OpenStreetMap_v2": osmHOT,
    "Satellite (Esri)": esriSatelliteLayer
};

var overlayMaps = {
    // "Marker Auto": carMarker 
};

L.control.layers(baseMaps, overlayMaps).addTo(map);

//car custom icon
var carIcon = L.icon({
    iconUrl: 'static/img/car.png',
    iconSize:     [40, 40], // size of the icon
    iconAnchor:   [20,20], // point of the icon which will correspond to marker's location
    popupAnchor:  [0,-40] // point from which the popup should open relative to the iconAnchor
});

var carMarker = L.marker([currentLat, currentLon],{icon:carIcon}).addTo(map)
    .bindPopup("Peacock 5")
    .openPopup();

function updateCarPosition(latitude, longitude, speed) {
    var newLatLng = new L.LatLng(latitude, longitude);
    carMarker.setLatLng(newLatLng);
    carMarker.setPopupContent(`Posizione Auto<br>Lat: ${latitude.toFixed(6)}, Lon: ${longitude.toFixed(6)}<br>Velocità: ${speed} km/h`);

    elGPSValue.innerText = `Lat: ${latitude.toFixed(6)}, Lon: ${longitude.toFixed(6)}`;
    elSpeed.innerText = `${speed} km/h`;
}

let currentSpeed = 1;

function updateValue(el, value){
    el.textContent = value;
}

//update diagnostic tile (bit = 0 -> OK, bit = 1 -> ERROR)
function updateDiag(tileId, bit) {
    const tile = document.getElementById(tileId);
    if (!tile) return;
    const dot    = tile.querySelector('.status-dot');
    const txt    = tile.querySelector('.diag-status span:last-child');
    const status = tile.querySelector('.diag-status');
    const hasError = (bit === 1);
    if (dot)    dot.className         = 'status-dot' + (hasError ? ' offline' : '');
    if (txt)    txt.textContent       = hasError ? 'ERROR' : 'OK';
    if (status) status.style.color    = hasError ? 'var(--light-red-color)' : 'var(--green-color)';
    tile.classList.toggle('error', hasError);
}

let currentState = {
    speed: 0,
    engine_1: 0
};

function applyState(updates){
        // Record the time of the last message received
    lastMessageTime = Date.now();

    // Update only the received fields
    if (updates.speed !== undefined) {
        currentState.speed = parseInt(updates.speed, 10);
        elSpeed.textContent = currentState.speed + " Km/h";
    }
    if (updates.engine_1 !== undefined) {
        currentState.engine_1 = parseInt(updates.engine_1, 10);
        elTempEng1.textContent = currentState.engine_1 + " °C";
        const b = document.getElementById('barMotore1');
        if (b) b.style.width = Math.min(100, (currentState.engine_1 / TEMP_MAX_MOTORE) * 100).toFixed(1) + '%';
    }
    if (updates.engine_2 !== undefined) {
        currentState.engine_2 = parseInt(updates.engine_2, 10);
        elTempEng2.textContent = currentState.engine_2 + " °C";
        const b = document.getElementById('barMotore2');
        if (b) b.style.width = Math.min(100, (currentState.engine_2 / TEMP_MAX_MOTORE) * 100).toFixed(1) + '%';
    }
    if (updates.inverter_1 !== undefined) {
        currentState.inverter_1 = parseInt(updates.inverter_1, 10);
        elTempInv1.textContent = currentState.inverter_1 + " °C";
        const b = document.getElementById('barInverter');
        if (b) b.style.width = Math.min(100, (currentState.inverter_1 / TEMP_MAX_INVERTER) * 100).toFixed(1) + '%';
    }
    if (updates.inverter_2 !== undefined) {
        currentState.inverter_2 = parseInt(updates.inverter_2, 10);
        elTempInv2.textContent = currentState.inverter_2 + " °C";
    }
    if (updates.battery_temp !== undefined) {
        currentState.battery_temp = parseInt(updates.battery_temp, 10);
        elTempBatt.textContent = currentState.battery_temp + " °C";
        const b = document.getElementById('barBattery');
        if (b) b.style.width = Math.min(100, (currentState.battery_temp / TEMP_MAX_BATTERY) * 100).toFixed(1) + '%';
    }
    if (updates.voltage_moduli !== undefined) {
        currentState.voltage_moduli = parseInt(updates.voltage_moduli, 10);
        elVoltBattHV.textContent = currentState.voltage_moduli + " V";
    }
    if (updates.voltage_lv !== undefined) {
        currentState.voltage_lv = parseInt(updates.voltage_lv, 10);
        elVoltBattLV.textContent = currentState.voltage_lv + " V";
    }
    if (updates.soc !== undefined) {
        currentState.soc = parseInt(updates.soc, 10);
        elSoC.textContent = currentState.soc + " %";
    }
    if (updates.current_bms !== undefined) {
        currentState.current_bms = parseFloat(updates.current_bms);
        if (elCurrentBMS) elCurrentBMS.textContent = currentState.current_bms + " A";
    }


    if (updates.latitude !== undefined && updates.longitude !== undefined) {
        currentState.latitude = updates.latitude;
        currentState.longitude = updates.longitude;
        
        // Update the car position on the map
        updateCarPosition(updates.latitude, updates.longitude, currentState.speed);
    }

    // Diagnostic bits (0 = OK, 1 = ERROR)
    const diagFields = [
        ['err_inv1',        'diag-inv1'],
        ['err_inv2',        'diag-inv2'],
        ['err_apps',        'diag-apps'],
        ['err_overcurrent', 'diag-overcurrent'],
        ['err_overvoltage', 'diag-overvoltage'],
        ['err_cell_ow',     'diag-cell-ow'],
        ['err_temp_ow',     'diag-temp-ow'],
        ['err_curr_sensor', 'diag-curr-sensor'],
        ['err_slave_sensor','diag-slave-sensor'],
    ];
    diagFields.forEach(([field, tileId]) => {
        if (updates[field] !== undefined) updateDiag(tileId, updates[field]);
    });
}

// ==========================================
// CONNECTION MONITORING     (Online / Offline)
// ==========================================
setInterval(() => {
    const dot = document.getElementById('statusDot');
    const txt = document.getElementById('statusText');
    if (!dot || !txt) return;

    const isOnline = lastMessageTime !== null && (Date.now() - lastMessageTime < STATUS_TIMEOUT_MS);
    dot.className = 'status-dot' + (isOnline ? ' pulse' : ' offline');
    txt.textContent  = isOnline ? 'Online' : 'Offline';
    const bar = dot.closest('.header-status');
    if (bar) bar.style.color = isOnline ? 'var(--green-color)' : 'var(--light-red-color)';

    // Live badge GPS
    const liveDot   = document.getElementById('liveDot');
    const liveBadge = document.getElementById('liveBadge');
    if (liveDot)   liveDot.className  = 'status-dot' + (isOnline ? ' pulse' : ' offline');
    if (liveBadge) liveBadge.style.color = isOnline ? 'var(--green-color)' : 'var(--light-red-color)';
}, 1000);


// ==========================================
// AWS SERVERLESS CONFIGURATION
// ==========================================
const API_GATEWAY_URL = 'https://ky7mwyoqf5.execute-api.us-east-1.amazonaws.com/alpha/auth';

document.getElementById('loginBtn').addEventListener('click', function() {
    const matricola = document.getElementById('matricolaInput').value;
    const errorMsg = document.getElementById('loginError');

    if (!matricola) {
        errorMsg.textContent = "Inserisci una matricola.";
        errorMsg.style.display = 'block';
        return;
    }

    // Call the API Gateway to get the secure URL for MQTT connection
    fetch(API_GATEWAY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matricola: matricola })
    })
    .then(response => {
        if (response.status === 403) throw new Error('403');
        if (!response.ok) throw new Error('HTTP_' + response.status);
        return response.json();
    })
    .then(data => {
        
        // Check if the Lambda reported an internal error (400 or 403)
        if (data.statusCode && data.statusCode !== 200) {
            throw new Error(data.body); 
        }
        
        // Extract the URL
        let urlSicuro = data.url;
        if (!urlSicuro && data.body) {
            let parsedBody = typeof data.body === 'string' ? JSON.parse(data.body) : data.body;
            urlSicuro = parsedBody.url;
        }

        if (!urlSicuro) {
            throw new Error("Errore del server: URL non generato.");
        }

        document.getElementById('login-overlay').style.display = 'none';
        
        startTelemetria(urlSicuro);
    })
    .catch(error => {
        let msg;
        if (error.message === '403') {
            // matricola not in whitelist
            msg = "Accesso negato: matricola non autorizzata dal team.";
        } else if (error instanceof TypeError) {
            // CORS block (origin not allowed or network error)
            msg = "Errore di rete: impossibile raggiungere il server.";
        } else {
            msg = error.message.replace(/"/g, '') || "Errore sconosciuto.";
        }
        errorMsg.textContent = msg;
        errorMsg.style.display = 'block';
        console.error("Accesso fallito:", error);
    });
});

function startTelemetria(presignedUrl) {
    const clientId = 'telemetry_web_' + Math.floor(Math.random() * 100000);

    const client = mqtt.connect(presignedUrl, {
        clientId: clientId,
        protocol: 'wss',
        protocolVersion: 4 
    });

    client.on('connect', function() {
        console.log('Connected to MQTT broker with clientId:', clientId);
        client.subscribe('P5/telemetry');
    });

    client.on('message', function(topic, payload) {
        try {
            const telemetryData = JSON.parse(payload.toString());
            applyState({
                speed:          telemetryData.speed,
                engine_1:       telemetryData.T_engine_1,
                engine_2:       telemetryData.T_engine_2,
                inverter_1:     telemetryData.T_inverter_1,
                inverter_2:     telemetryData.T_inverter_2,
                battery_temp:   telemetryData.T_battery,
                voltage_moduli: telemetryData.V_Moduli,
                voltage_lv:     telemetryData.V_LV,
                soc:            telemetryData.SoC,
                current_bms:        telemetryData.I_BMS,
                latitude:           telemetryData.latitude,
                longitude:          telemetryData.longitude,
                err_inv1:           telemetryData.err_inv1,
                err_inv2:           telemetryData.err_inv2,
                err_apps:           telemetryData.err_apps,
                err_overcurrent:    telemetryData.err_overcurrent,
                err_overvoltage:    telemetryData.err_overvoltage,
                err_cell_ow:        telemetryData.err_cell_ow,
                err_temp_ow:        telemetryData.err_temp_ow,
                err_curr_sensor:    telemetryData.err_curr_sensor,
                err_slave_sensor:   telemetryData.err_slave_sensor,
            });
        } catch (error) {
            console.error("Errore parsing JSON:", error);
        }
    });

    client.on('error', (err) => console.error("Errore MQTT:", err));
}

