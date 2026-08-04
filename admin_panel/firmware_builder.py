"""
Firmware Builder - Sistema de build automatizado de firmware customizado
Gera firmware personalizado baseado na placa e sensores selecionados
"""

import os
import subprocess
import uuid
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from sensor_catalog import SENSOR_CATALOG, get_sensor_by_id


class FirmwareBuildError(Exception):
    """Erro durante o processo de build"""
    pass


class FirmwareBuilder:
    """Gerencia builds de firmware customizado"""
    
    def __init__(self, firmware_dir: str = "/firmware-v2", builds_dir: str = "/data/builds"):
        self.firmware_dir = Path(firmware_dir)
        self.builds_dir = Path(builds_dir)
        self.builds_dir.mkdir(parents=True, exist_ok=True)
        
    def create_build(self, device_id: str, board: str, sensor_ids: List[str]) -> Dict:
        """
        Cria um build customizado de firmware
        
        Args:
            device_id: ID do dispositivo
            board: Placa alvo ("ESP32-S3" ou "ESP32")
            sensor_ids: Lista de IDs de sensores a incluir
            
        Returns:
            Dict com informações do build
        """
        build_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()
        
        # Valida placa
        if board not in ["ESP32-S3", "ESP32"]:
            raise FirmwareBuildError(f"Placa não suportada: {board}")
        
        # Determina environment PlatformIO
        env = "esp32s3_v2" if board == "ESP32-S3" else "esp32_doit_v2"
        
        # Valida sensores
        sensors = []
        for sid in sensor_ids:
            sensor = get_sensor_by_id(sid)
            if not sensor:
                raise FirmwareBuildError(f"Sensor não encontrado: {sid}")
            sensors.append(sensor)
        
        # Cria diretório do build
        build_dir = self.builds_dir / build_id
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Gera código customizado
        main_cpp = self._generate_main_cpp(device_id, board, sensors)
        
        # Copia estrutura do firmware
        temp_firmware_dir = build_dir / "firmware-v2"
        shutil.copytree(self.firmware_dir, temp_firmware_dir, dirs_exist_ok=True)
        
        # Substitui main.cpp com versão customizada
        (temp_firmware_dir / "src" / "main.cpp").write_text(main_cpp)
        
        # Executa build
        try:
            result = subprocess.run(
                ["pio", "run", "-e", env],
                cwd=str(temp_firmware_dir),
                capture_output=True,
                text=True,
                timeout=180  # 3 minutos timeout
            )
            
            if result.returncode != 0:
                # Salva log de erro
                (build_dir / "build_error.log").write_text(result.stderr)
                raise FirmwareBuildError(f"Build falhou: {result.stderr[:500]}")
            
            # Copia firmware compilado
            firmware_bin = temp_firmware_dir / ".pio" / "build" / env / "firmware.bin"
            if not firmware_bin.exists():
                raise FirmwareBuildError("Arquivo firmware.bin não encontrado")
            
            output_bin = build_dir / f"{device_id}_{board.lower()}_{build_id}.bin"
            shutil.copy(firmware_bin, output_bin)
            
            # Salva metadados
            metadata = {
                "build_id": build_id,
                "device_id": device_id,
                "board": board,
                "environment": env,
                "sensors": sensor_ids,
                "timestamp": timestamp,
                "firmware_file": output_bin.name,
                "firmware_size": output_bin.stat().st_size,
                "status": "success"
            }
            
            import json
            (build_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
            
            # Remove diretório temporário de build
            shutil.rmtree(temp_firmware_dir)
            
            return metadata
            
        except subprocess.TimeoutExpired:
            raise FirmwareBuildError("Build timeout (>3min)")
        except Exception as e:
            raise FirmwareBuildError(f"Erro no build: {str(e)}")
    
    def _generate_main_cpp(self, device_id: str, board: str, sensors: List) -> str:
        """Gera código main.cpp customizado baseado nos sensores"""
        
        # Headers
        headers = [
            "#include <Arduino.h>",
            "#include <WiFi.h>",
            "#include <WebServer.h>",
            "#include \"NvsConfig.h\"",
            "#include \"MqttTransport.h\"",
        ]
        
        # Adiciona headers dos sensores
        for sensor in sensors:
            if sensor.header_file:
                headers.append(f"#include \"{sensor.header_file}\"")
        
        # Instâncias globais dos sensores
        sensor_inits = []
        for sensor in sensors:
            if sensor.init_code:
                # Substitui placeholders com GPIOs corretos
                init = sensor.init_code
                for pin in sensor.pins:
                    gpio = pin.gpio_esp32s3 if board == "ESP32-S3" else pin.gpio_esp32
                    pin_placeholder = "{" + pin.name.lower() + "_pin}"
                    init = init.replace(pin_placeholder, str(gpio))
                sensor_inits.append(init)
        
        # Código de leitura dos sensores
        read_calls = []
        for sensor in sensors:
            if "readAll" in sensor.read_code:
                read_calls.append(f"    auto {sensor.id}Readings = {sensor.read_code};")
                read_calls.append(f"    allReadings.insert(allReadings.end(), {sensor.id}Readings.begin(), {sensor.id}Readings.end());")
            elif sensor.read_code:
                read_calls.append(f"    allReadings.push_back({sensor.read_code});")
        
        # Template do main.cpp
        template = f'''// Auto-generated firmware for {device_id}
// Board: {board}
// Sensors: {", ".join([s.name for s in sensors])}
// Generated: {datetime.utcnow().isoformat()}

{chr(10).join(headers)}

// ===== Global Objects =====
NvsConfig gConfig;
MqttTransport gTransport;
WebServer gServer(80);

// Sensors
{chr(10).join(sensor_inits)}

// ===== Provisioning (Access Point) =====
const char* AP_SSID = "Guardioes-Setup";
const char* AP_IP = "192.168.4.1";

void setupProvisioningAP() {{
    Serial.println("[PROV] Iniciando modo de provisionamento...");
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID);
    WiFi.softAPConfig(IPAddress(192, 168, 4, 1), IPAddress(192, 168, 4, 1), IPAddress(255, 255, 255, 0));
    
    Serial.print("[PROV] AP ativo: ");
    Serial.println(AP_SSID);
    Serial.print("[PROV] IP: ");
    Serial.println(WiFi.softAPIP());
    
    gServer.on("/", HTTP_GET, []() {{
        String html = "<h1>Configuracao - Guardioes da Floresta</h1>";
        html += "<form method='POST' action='/save'>";
        html += "Device ID: <input name='device_id' required><br>";
        html += "WiFi SSID: <input name='ssid' required><br>";
        html += "WiFi Pass: <input name='pass' type='password' required><br>";
        html += "MQTT Host: <input name='mqtt_host' required><br>";
        html += "MQTT Port: <input name='mqtt_port' value='1883' required><br>";
        html += "MQTT User: <input name='mqtt_user' required><br>";
        html += "MQTT Pass: <input name='mqtt_pass' type='password' required><br>";
        html += "<button type='submit'>Salvar</button></form>";
        gServer.send(200, "text/html", html);
    }});
    
    gServer.on("/save", HTTP_POST, []() {{
        gConfig.setDeviceId(gServer.arg("device_id").c_str());
        gConfig.setWifi(gServer.arg("ssid").c_str(), gServer.arg("pass").c_str());
        gConfig.setMqtt(
            gServer.arg("mqtt_host").c_str(),
            gServer.arg("mqtt_port").toInt(),
            gServer.arg("mqtt_user").c_str(),
            gServer.arg("mqtt_pass").c_str()
        );
        gConfig.save();
        gServer.send(200, "text/html", "<h1>Salvo! Reiniciando...</h1>");
        delay(2000);
        ESP.restart();
    }});
    
    gServer.begin();
}}

// ===== Config Callback =====
void applyConfigJson(const String& json) {{
    Serial.print("[CONFIG] Recebido: ");
    Serial.println(json);
    
    // Parse JSON e aplica configurações
    DeviceConfig cfg = gConfig.load();
    
    // Implementar parsing de JSON para calibração, etc.
    gConfig.save();
    Serial.println("[CONFIG] Aplicado e salvo na NVS");
}}

// ===== Setup =====
void setup() {{
    Serial.begin(115200);
    delay(1000);
    Serial.println("\\n[BOOT] Guardioes da Floresta v2 - Custom Build");
    Serial.println("[BOARD] {board}");
    
    gConfig.begin();
    DeviceConfig cfg = gConfig.load();
    
    if (!gConfig.isProvisioned()) {{
        setupProvisioningAP();
        return;
    }}
    
    Serial.println("[CONFIG] Dispositivo provisionado");
    Serial.print("[CONFIG] Device ID: ");
    Serial.println(cfg.device_id);
    
    // Inicializa sensores
{chr(10).join([f"    {s.id.replace('_', '').capitalize()}Sensor.begin();" for s in sensors if hasattr(s, 'init_code')])}
    
    // Configura MQTT
    gTransport.configure(
        cfg.mqtt_host, cfg.mqtt_port,
        cfg.mqtt_user, cfg.mqtt_pass,
        cfg.device_id
    );
    gTransport.onConfig(applyConfigJson);
    gTransport.begin();
    
    Serial.println("[SETUP] Completo");
}}

// ===== Loop =====
unsigned long lastTelemetry = 0;
unsigned long lastStatus = 0;

void loop() {{
    if (!gConfig.isProvisioned()) {{
        gServer.handleClient();
        return;
    }}
    
    gTransport.loop();
    
    DeviceConfig cfg = gConfig.load();
    unsigned long now = millis();
    
    // Publica telemetria
    if (now - lastTelemetry >= cfg.publish_interval * 1000) {{
        lastTelemetry = now;
        
        std::vector<Reading> allReadings;
        
{chr(10).join(read_calls)}
        
        if (!allReadings.empty()) {{
            gTransport.publishTelemetry(allReadings);
        }}
    }}
    
    // Publica status (heartbeat a cada 30s)
    if (now - lastStatus >= 30000) {{
        lastStatus = now;
        gTransport.publishStatus();
    }}
}}
'''
        
        return template
    
    def get_build_info(self, build_id: str) -> Optional[Dict]:
        """Retorna informações de um build"""
        build_dir = self.builds_dir / build_id
        metadata_file = build_dir / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        import json
        return json.loads(metadata_file.read_text())
    
    def get_firmware_path(self, build_id: str) -> Optional[Path]:
        """Retorna caminho do arquivo .bin de um build"""
        metadata = self.get_build_info(build_id)
        if not metadata:
            return None
        
        bin_path = self.builds_dir / build_id / metadata["firmware_file"]
        return bin_path if bin_path.exists() else None
    
    def cleanup_old_builds(self, max_age_hours: int = 24):
        """Remove builds antigos"""
        import time
        cutoff = time.time() - (max_age_hours * 3600)
        
        for build_dir in self.builds_dir.iterdir():
            if build_dir.is_dir():
                if build_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(build_dir)
