// Estado global
let authToken = null;
let currentDeviceId = null;

// API Base URL
const API_BASE = '/api';

// Utilitários
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// Gerenciamento de autenticação
function saveToken(token) {
    authToken = token;
    localStorage.setItem('auth_token', token);
}

function loadToken() {
    authToken = localStorage.getItem('auth_token');
    return authToken;
}

function clearToken() {
    authToken = null;
    localStorage.removeItem('auth_token');
}

// Requisições HTTP
async function request(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        clearToken();
        showScreen('login');
        throw new Error('Não autorizado');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
        throw new Error(error.detail || 'Erro na requisição');
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

// Navegação
function showScreen(screenName) {
    $$('.screen').forEach(s => s.classList.add('hidden'));
    $(`#${screenName}-screen`).classList.remove('hidden');
}

function switchTab(tabName) {
    $$('.tab-btn').forEach(btn => btn.classList.remove('active'));
    $$('.tab-content').forEach(content => content.classList.remove('active'));
    
    $(`[data-tab="${tabName}"]`).classList.add('active');
    $(`#tab-${tabName}`).classList.add('active');
}

function showModal(modalId) {
    $(`#${modalId}`).classList.remove('hidden');
}

function hideModal(modalId) {
    $(`#${modalId}`).classList.add('hidden');
}

// Login
$('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const password = $('#password').value;
    $('#login-error').textContent = '';
    
    try {
        const data = await request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ password }),
        });
        
        saveToken(data.access_token);
        showScreen('dashboard');
        loadDevices();
    } catch (error) {
        $('#login-error').textContent = error.message || 'Senha incorreta';
    }
});

// Logout
$('#logout-btn').addEventListener('click', () => {
    clearToken();
    showScreen('login');
    $('#password').value = '';
});

// Tabs
$$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const tab = e.target.dataset.tab;
        switchTab(tab);
    });
});

// Modais
$$('.modal-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const modal = e.target.closest('.modal');
        modal.classList.add('hidden');
    });
});

// Clicar fora do modal fecha
$$('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
});

// Dispositivos
async function loadDevices() {
    const container = $('#devices-list');
    container.innerHTML = '<p class="loading">Carregando...</p>';
    
    try {
        const devices = await request('/devices');
        
        if (devices.length === 0) {
            container.innerHTML = '<p class="empty">Nenhum dispositivo cadastrado. Clique em "+ Novo Dispositivo" para começar.</p>';
            return;
        }
        
        container.innerHTML = devices.map(device => renderDeviceCard(device)).join('');
        
        // Adicionar event listeners aos botões
        $$('.btn-calibrate').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const deviceId = e.target.dataset.deviceId;
                openCalibrationModal(deviceId);
            });
        });
        
        $$('.btn-data').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const deviceId = e.target.dataset.deviceId;
                openDataModal(deviceId);
            });
        });
        
        $$('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const deviceId = e.target.dataset.deviceId;
                deleteDevice(deviceId);
            });
        });
        
    } catch (error) {
        container.innerHTML = `<p class="error">Erro ao carregar dispositivos: ${error.message}</p>`;
    }
}

function renderDeviceCard(device) {
    const isOnline = device.ultimo_contato && 
        (new Date() - new Date(device.ultimo_contato)) < 5 * 60 * 1000; // 5 minutos
    
    const lastContact = device.ultimo_contato 
        ? new Date(device.ultimo_contato).toLocaleString('pt-BR')
        : 'Nunca';
    
    const sensors = device.sensores && device.sensores.length > 0
        ? device.sensores.join(', ')
        : 'Não especificado';
    
    return `
        <div class="device-card">
            <div class="device-header">
                <div class="device-title">
                    <h3>${device.nome || 'Sem nome'}</h3>
                    <div class="device-id">${device.device_id}</div>
                </div>
                <div class="device-status ${isOnline ? 'online' : 'offline'}">
                    ${isOnline ? '● Online' : '○ Offline'}
                </div>
            </div>
            <div class="device-info">
                <div class="info-row">
                    <span class="info-label">Placa:</span>
                    <span class="info-value">${device.placa}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Transporte:</span>
                    <span class="info-value">${device.transporte === 'mqtt' ? 'MQTT (WiFi)' : 'Serial (USB)'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Sensores:</span>
                    <span class="info-value">${sensors}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Último contato:</span>
                    <span class="info-value">${lastContact}</span>
                </div>
            </div>
            <div class="device-actions">
                <button class="btn-calibrate" data-device-id="${device.device_id}">Calibração</button>
                <button class="btn-data" data-device-id="${device.device_id}">Dados</button>
                <button class="btn-delete" data-device-id="${device.device_id}">Excluir</button>
            </div>
        </div>
    `;
}

// Novo dispositivo
$('#add-device-btn').addEventListener('click', () => {
    $('#modal-title').textContent = 'Novo Dispositivo';
    $('#device-form').reset();
    $('#device-id').disabled = false;
    showModal('device-modal');
});

$('#device-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const deviceData = {
        device_id: $('#device-id').value,
        nome: $('#device-nome').value || null,
        placa: $('#device-placa').value,
        transporte: $('#device-transporte').value,
    };
    
    try {
        await request('/devices', {
            method: 'POST',
            body: JSON.stringify(deviceData),
        });
        
        hideModal('device-modal');
        loadDevices();
    } catch (error) {
        alert(`Erro ao criar dispositivo: ${error.message}`);
    }
});

// Calibração
async function openCalibrationModal(deviceId) {
    currentDeviceId = deviceId;
    $('#calib-device-id').textContent = deviceId;
    
    try {
        const device = await request(`/devices/${deviceId}`);
        
        // Preencher valores atuais se existirem
        const calib = device.calibracao || {};
        $('#soil-dry').value = calib.soil_dry || '';
        $('#soil-wet').value = calib.soil_wet || '';
        $('#publish-interval').value = calib.publish_interval || '';
        
        showModal('calibration-modal');
    } catch (error) {
        alert(`Erro ao carregar dispositivo: ${error.message}`);
    }
}

$('#calibration-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const calibData = {};
    
    const soilDry = $('#soil-dry').value;
    const soilWet = $('#soil-wet').value;
    const publishInterval = $('#publish-interval').value;
    
    if (soilDry) calibData.soil_dry = parseFloat(soilDry);
    if (soilWet) calibData.soil_wet = parseFloat(soilWet);
    if (publishInterval) calibData.publish_interval = parseInt(publishInterval);
    
    if (Object.keys(calibData).length === 0) {
        alert('Preencha pelo menos um campo para atualizar');
        return;
    }
    
    try {
        await request(`/devices/${currentDeviceId}/calibration`, {
            method: 'POST',
            body: JSON.stringify(calibData),
        });
        
        hideModal('calibration-modal');
        alert('Calibração aplicada com sucesso! As alterações foram enviadas via MQTT.');
        loadDevices();
    } catch (error) {
        alert(`Erro ao aplicar calibração: ${error.message}`);
    }
});

// Visualização de dados
async function openDataModal(deviceId) {
    currentDeviceId = deviceId;
    $('#data-device-id').textContent = deviceId;
    showModal('data-modal');
    
    // Carregar últimas leituras
    const latestContainer = $('#latest-data');
    latestContainer.innerHTML = '<p class="loading">Carregando...</p>';
    
    try {
        const latest = await request(`/devices/${deviceId}/data/latest`);
        
        if (!latest.readings || latest.readings.length === 0) {
            latestContainer.innerHTML = '<p class="empty">Nenhuma leitura nos últimos 5 minutos</p>';
        } else {
            latestContainer.innerHTML = latest.readings.map(reading => renderDataItem(reading)).join('');
        }
    } catch (error) {
        latestContainer.innerHTML = `<p class="error">Erro: ${error.message}</p>`;
    }
    
    // Carregar histórico
    const historyContainer = $('#history-data');
    historyContainer.innerHTML = '<p class="loading">Carregando...</p>';
    
    try {
        const history = await request(`/devices/${deviceId}/data/history?start=-24h`);
        
        if (!history.readings || history.readings.length === 0) {
            historyContainer.innerHTML = '<p class="empty">Nenhuma leitura nas últimas 24 horas</p>';
        } else {
            // Mostrar apenas as últimas 10
            const recent = history.readings.slice(-10).reverse();
            historyContainer.innerHTML = recent.map(reading => renderDataItem(reading)).join('');
        }
    } catch (error) {
        historyContainer.innerHTML = `<p class="error">Erro: ${error.message}</p>`;
    }
}

function renderDataItem(reading) {
    const time = new Date(reading.time).toLocaleString('pt-BR');
    const values = Object.entries(reading.values)
        .filter(([key]) => !['_start', '_stop', '_field', '_measurement'].includes(key))
        .map(([key, value]) => {
            const label = formatSensorName(key);
            const formattedValue = typeof value === 'number' ? value.toFixed(2) : value;
            return `
                <div class="data-value">
                    <span class="data-label">${label}:</span>
                    <span class="data-num">${formattedValue}</span>
                </div>
            `;
        })
        .join('');
    
    return `
        <div class="data-item">
            <div class="data-time">${time}</div>
            <div class="data-values">${values}</div>
        </div>
    `;
}

function formatSensorName(name) {
    const map = {
        'soil_moisture': 'Umidade do Solo',
        'air_temp': 'Temperatura do Ar',
        'air_humidity': 'Umidade do Ar',
        'temperature': 'Temperatura',
        'humidity': 'Umidade',
    };
    return map[name] || name;
}

// Excluir dispositivo
async function deleteDevice(deviceId) {
    if (!confirm(`Tem certeza que deseja excluir o dispositivo "${deviceId}"?\n\nIsso NÃO removerá os dados históricos, apenas o registro do dispositivo.`)) {
        return;
    }
    
    try {
        await request(`/devices/${deviceId}`, {
            method: 'DELETE',
        });
        
        loadDevices();
    } catch (error) {
        alert(`Erro ao excluir dispositivo: ${error.message}`);
    }
}

// Inicialização
window.addEventListener('DOMContentLoaded', () => {
    if (loadToken()) {
        showScreen('dashboard');
        loadDevices();
    } else {
        showScreen('login');
    }
});



// ===== FASE 4: Firmware Builder =====

let sensorsCatalog = [];
let selectedSensors = [];

// Carrega catálogo de sensores
async function loadSensorsCatalog() {
    try {
        const response = await apiRequest('/api/sensors');
        sensorsCatalog = response.sensors;
        renderSensorsCatalog();
    } catch (error) {
        showError('Erro ao carregar catálogo de sensores: ' + error.message);
    }
}

// Renderiza catálogo de sensores
function renderSensorsCatalog() {
    const catalogEl = document.getElementById('sensors-catalog');
    
    if (sensorsCatalog.length === 0) {
        catalogEl.innerHTML = '<p class="loading">Nenhum sensor disponível</p>';
        return;
    }
    
    catalogEl.innerHTML = sensorsCatalog.map(sensor => `
        <div class="sensor-card" data-sensor-id="${sensor.id}" onclick="toggleSensor('${sensor.id}')">
            <div class="sensor-card-header">
                <span class="sensor-card-title">${sensor.name}</span>
                <span class="sensor-card-badge">${sensor.interface}</span>
            </div>
            <p class="sensor-card-description">${sensor.description}</p>
            <div class="sensor-card-details">
                <span class="sensor-detail-tag">📊 ${sensor.readings.join(', ')}</span>
                ${sensor.calibration ? '<span class="sensor-detail-tag">🔧 Requer calibração</span>' : ''}
            </div>
        </div>
    `).join('');
}

// Toggle seleção de sensor
function toggleSensor(sensorId) {
    const card = document.querySelector(`.sensor-card[data-sensor-id="${sensorId}"]`);
    
    if (selectedSensors.includes(sensorId)) {
        // Remove
        selectedSensors = selectedSensors.filter(id => id !== sensorId);
        card.classList.remove('selected');
    } else {
        // Adiciona
        selectedSensors.push(sensorId);
        card.classList.add('selected');
    }
}

// Constrói firmware customizado
async function buildFirmware() {
    const deviceId = document.getElementById('fw-device-id').value.trim();
    const board = document.getElementById('fw-board').value;
    const statusEl = document.getElementById('build-status');
    const buildBtn = document.getElementById('build-firmware-btn');
    
    // Validações
    if (!deviceId) {
        alert('Por favor, informe o Device ID');
        return;
    }
    
    if (selectedSensors.length === 0) {
        alert('Por favor, selecione pelo menos um sensor');
        return;
    }
    
    // Status: building
    statusEl.textContent = '🔧 Compilando firmware... isso pode levar alguns minutos.';
    statusEl.className = 'build-status building';
    buildBtn.disabled = true;
    
    try {
        const response = await apiRequest('/api/firmware/build', 'POST', {
            device_id: deviceId,
            board: board,
            sensor_ids: selectedSensors
        });
        
        // Sucesso!
        statusEl.textContent = `✅ Firmware compilado com sucesso! Build ID: ${response.build_id}`;
        statusEl.className = 'build-status success';
        
        // Atualiza lista de builds
        loadBuilds();
        
        // Limpa seleções após 3 segundos
        setTimeout(() => {
            document.getElementById('fw-device-id').value = '';
            selectedSensors = [];
            renderSensorsCatalog();
            statusEl.textContent = '';
            statusEl.className = 'build-status';
        }, 3000);
        
    } catch (error) {
        statusEl.textContent = `❌ Erro ao compilar firmware: ${error.message}`;
        statusEl.className = 'build-status error';
    } finally {
        buildBtn.disabled = false;
    }
}

// Carrega histórico de builds
async function loadBuilds() {
    try {
        const response = await apiRequest('/api/firmware/builds');
        renderBuilds(response.builds);
    } catch (error) {
        showError('Erro ao carregar builds: ' + error.message);
    }
}

// Renderiza lista de builds
function renderBuilds(builds) {
    const buildsEl = document.getElementById('builds-list');
    
    if (builds.length === 0) {
        buildsEl.innerHTML = '<p class="loading">Nenhum build disponível</p>';
        return;
    }
    
    buildsEl.innerHTML = builds.map(build => {
        const date = new Date(build.timestamp);
        const size = (build.firmware_size / 1024).toFixed(1);
        
        return `
            <div class="build-card">
                <div class="build-card-info">
                    <h4>📦 ${build.device_id}</h4>
                    <div class="build-card-meta">
                        <span>🖥️ ${build.board}</span>
                        <span>📅 ${date.toLocaleDateString('pt-BR')} ${date.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}</span>
                        <span>💾 ${size} KB</span>
                    </div>
                    <div class="build-card-sensors">
                        ${build.sensors.map(s => `<span class="build-sensor-tag">${s}</span>`).join('')}
                    </div>
                </div>
                <div class="build-card-actions">
                    <button class="btn-download" onclick="downloadFirmware('${build.build_id}', '${build.firmware_file}')">
                        ⬇️ Download
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Download de firmware
async function downloadFirmware(buildId, filename) {
    try {
        const token = getToken();
        const response = await fetch(`/api/firmware/download/${buildId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Erro ao fazer download');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        alert('Erro ao fazer download: ' + error.message);
    }
}

// Event listener para botão de build
document.getElementById('build-firmware-btn')?.addEventListener('click', buildFirmware);

// Inicializa aba de firmware quando ativada
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        if (tab === 'firmware') {
            if (sensorsCatalog.length === 0) {
                loadSensorsCatalog();
            }
            loadBuilds();
        }
    });
});
