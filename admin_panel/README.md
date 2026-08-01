# Painel de Administração - Guardiões da Floresta IoT

Interface web para gerenciamento de dispositivos IoT e visualização de dados em tempo real.

## Funcionalidades

### Gerenciamento de Dispositivos
- **Listar dispositivos**: Visualização em grid de todos os dispositivos cadastrados
- **Cadastrar dispositivos**: Formulário para adicionar novos dispositivos (ESP32-S3, ESP32, ESP8266, Arduino Uno)
- **Status online/offline**: Indicador visual baseado no último contato (até 5 minutos = online)
- **Editar informações**: Nome, placa, tipo de transporte
- **Excluir dispositivos**: Remoção do registro (dados históricos são preservados)

### Calibração Remota
- **Umidade do solo**: Configurar valores brutos ADC para seco/molhado
- **Intervalo de publicação**: Ajustar frequência de envio de dados
- **Aplicação em tempo real**: Alterações enviadas via MQTT retained sem necessidade de reflash
- Suporte a dispositivos MQTT (WiFi) e Serial (USB)

### Visualização de Dados
- **Últimas leituras**: Dados dos últimos 5 minutos em tempo real
- **Histórico 24h**: Visualização agregada das últimas 24 horas (média a cada 5 minutos)
- **Formatação automática**: Conversão de nomes de sensores para português
- **Organização por tempo**: Ordenação das leituras mais recentes primeiro

### Dashboard de Dados em Tempo Real (Fase 5)
- **Aba Dashboard**: Nova visão dedicada à visualização de dados dos dispositivos
- **Lista lateral de dispositivos**: Sidebar com todos os dispositivos e indicador de status online/offline
- **Cards de métricas instantâneas**: Últimos valores de temperatura do ar, umidade do ar e umidade do solo, com ícone e unidade
- **Gráficos de séries temporais**: Três gráficos de linha (temperatura do ar, umidade do ar, umidade do solo) renderizados com Chart.js
- **Seletor de período**: Botões 1h / 6h / 24h / 7d que reajustam a janela de agregação dos dados
- **Auto-refresh**: Atualização automática dos cards e gráficos a cada 30 segundos
- **Chart.js local**: Biblioteca servida localmente (`static/chart.min.js`), sem dependência de CDN, mantendo o funcionamento offline

### 🆕 Firmware Builder (Fase 4)
- **Catálogo de sensores**: Biblioteca de sensores suportados (AHT10, Solo, DHT22, LDR)
- **Seleção de sensores**: Interface visual para escolher quais sensores incluir no dispositivo
- **Build automatizado**: Compilação de firmware customizado com PlatformIO
- **Suporte multi-placa**: ESP32-S3 DevKit C-1 e ESP32 DOIT DevKit V1
- **Download de firmware**: Arquivo .bin pronto para flash
- **Histórico de builds**: Visualização e download de builds anteriores
- **Configuração de pinos**: Pinagem automática baseada na placa selecionada
- **Código otimizado**: Firmware contém apenas drivers dos sensores selecionados

### Flash pelo Navegador via servidor (Fase 6)
- **Gravação sem ferramentas locais**: grava o firmware compilado direto no ESP32 pelo painel web
- **Execução no servidor**: o flash roda no servidor via `esptool`, então funciona em qualquer navegador e sem HTTPS
- **Seleção de porta serial**: lista as portas USB-Serial detectadas no servidor (CP210x, CH340, FTDI, ACM, etc.)
- **Progresso em tempo real**: barra de progresso e log ao vivo via polling (a cada 2s)
- **Velocidade configurável**: 460800 baud (recomendado) ou 115200 (compatibilidade)

**Requisitos**: o ESP32 deve estar conectado via USB à porta serial do **servidor** (ex.: `/dev/ttyUSB0` ou `/dev/ttyACM0`). No Docker, o serviço `admin_panel` roda com `privileged: true` para acessar os devices do host (ou configure `group_add` + `devices` manualmente).

### Autenticação
- Login com senha de administrador (gerada automaticamente pelo instalador)
- Tokens JWT com expiração de 24 horas
- Logout seguro com limpeza de credenciais

## Tecnologias

### Backend
- **FastAPI**: Framework web assíncrono Python
- **Paho MQTT**: Cliente MQTT para publicação de configurações
- **InfluxDB Client**: Consulta de dados históricos
- **SQLite**: Banco de metadados de dispositivos (compartilhado com ingest_service)
- **JWT**: Autenticação baseada em tokens
- **Passlib/Bcrypt**: Hash de senhas

### Frontend
- **HTML5/CSS3**: Interface responsiva sem frameworks pesados
- **JavaScript Vanilla**: Manipulação DOM e chamadas de API
- **LocalStorage**: Persistência de token de autenticação

## Estrutura de Arquivos

```
admin_panel/
├── main.py              # Backend FastAPI
├── sensor_catalog.py    # Catálogo de sensores suportados (Fase 4)
├── firmware_builder.py  # Sistema de build de firmware (Fase 4)
├── flash_service.py     # Gravação de firmware via esptool (Fase 6)
├── requirements.txt     # Dependências Python
├── Dockerfile          # Container Docker
├── static/             # Frontend
│   ├── index.html     # Interface principal
│   ├── style.css      # Estilos
│   ├── app.js         # Lógica JavaScript
│   └── chart.min.js   # Chart.js 4.x local (dashboard - Fase 5)
└── README.md          # Este arquivo
```

## API Endpoints

### Autenticação
- `POST /api/auth/login` - Login (retorna JWT token)

### Dispositivos
- `GET /api/devices` - Listar todos os dispositivos
- `GET /api/devices/{device_id}` - Obter dispositivo específico
- `POST /api/devices` - Cadastrar novo dispositivo
- `PATCH /api/devices/{device_id}` - Atualizar informações
- `DELETE /api/devices/{device_id}` - Excluir dispositivo

### Calibração
- `POST /api/devices/{device_id}/calibration` - Atualizar calibração (publica via MQTT)

### Dados
- `GET /api/devices/{device_id}/data/latest` - Últimas leituras (5 min)
- `GET /api/devices/{device_id}/data/history?start=-24h` - Histórico

### Dashboard (Fase 5)
- `GET /api/dashboard/overview` - Visão geral de todos os dispositivos com última leitura e status online/offline
- `GET /api/devices/{device_id}/data/chart?sensors=...&start=-24h&window=10m` - Séries temporais agregadas formatadas para Chart.js (labels + datasets por sensor)

### 🆕 Sensores e Firmware (Fase 4)
- `GET /api/sensors` - Listar todos os sensores do catálogo
- `GET /api/sensors/{sensor_id}` - Obter detalhes de um sensor
- `PUT /api/devices/{device_id}/sensors` - Atualizar sensores de um dispositivo
- `POST /api/firmware/build` - Construir firmware customizado (device_id, board, sensor_ids)
- `GET /api/firmware/download/{build_id}` - Download do firmware .bin
- `GET /api/firmware/builds` - Listar histórico de builds

### Flash pelo Navegador (Fase 6)
- `GET /api/flash/ports` - Listar portas seriais disponíveis no servidor
- `POST /api/flash/start` - Iniciar gravação (body: build_id, port, baud) — retorna flash_id
- `GET /api/flash/status/{flash_id}` - Consultar status/progresso/log da gravação (polling)

### Utilitários
- `GET /api/health` - Health check (status MQTT, InfluxDB, Firmware Builder e Flash Service)

## Uso

### Desenvolvimento Local

```bash
cd admin_panel

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
export ADMIN_PASSWORD="sua_senha"
export JWT_SECRET="seu_secret"
export MQTT_HOST="localhost"
export MQTT_USER="guardioes"
export MQTT_PASS="senha_mqtt"
export INFLUX_URL="http://localhost:8086"
export INFLUXDB_ADMIN_TOKEN="seu_token"
export SQLITE_PATH="/data/devices.db"

# Iniciar servidor
python main.py
```

Acesse: http://localhost:8000

### Produção (Docker Compose)

O painel é iniciado automaticamente pelo `docker-compose.yml`:

```bash
cd ~/guardioes-iot
docker compose up -d admin_panel
```

Acesse: http://localhost:8000

## Fluxo de Calibração Remota

1. Usuário acessa o painel e clica em "Calibração" em um dispositivo
2. Formulário é preenchido com valores atuais (do SQLite)
3. Usuário edita os valores desejados (ex: `soil_dry: 3200`, `soil_wet: 1500`)
4. Backend salva no SQLite e publica em `guardioes/{device_id}/config` (QoS 1, retained)
5. Dispositivo recebe a mensagem MQTT e atualiza NVS + aplica imediatamente
6. Próximas leituras já usam a nova calibração

**Importante**: A calibração é aplicada em tempo real via MQTT, sem necessidade de regravar o firmware.

## Segurança

- Senha de administrador gerada aleatoriamente (16 caracteres) pelo instalador
- JWT secret gerado aleatoriamente (64 caracteres)
- Tokens JWT com expiração de 24 horas
- Todas as rotas (exceto login) protegidas por autenticação
- CORS não configurado (acesso apenas local)
- Arquivo `.env` com permissões 600

## Troubleshooting

### Erro "MQTT não disponível"
Verifique se o container `mosquitto` está rodando:
```bash
docker compose ps mosquitto
```

### Erro "InfluxDB não disponível"
Verifique se o container `influxdb` está rodando:
```bash
docker compose ps influxdb
```

### Nenhum dado nas leituras
1. Confirme que o dispositivo está enviando dados (verifique logs do `ingest_service`)
2. Verifique se o `device_id` está correto
3. Confirme que há dados no InfluxDB:
   ```bash
   docker compose exec influxdb influx query 'from(bucket:"sensor_data") |> range(start: -1h)'
   ```

### Token expirado
Faça logout e login novamente. O token expira após 24 horas.

### Calibração não aplicada
1. Confirme que o dispositivo está online (verificar último contato)
2. Para dispositivos MQTT: verifique se está conectado ao broker
3. Para dispositivos Serial: a calibração deve ser enviada via comando serial (ainda não implementado)
4. Verifique logs do dispositivo para confirmar recebimento da mensagem

## Limitações Conhecidas

- Calibração remota via MQTT funciona apenas para dispositivos WiFi (ESP32/ESP8266)
- Dispositivos Serial (Arduino Uno) requerem implementação de comando serial dedicado
- Interface não atualiza automaticamente (requer refresh manual)
- Sem suporte a WebSocket para dados em tempo real (usa polling)
- Grafana integrado apenas via link externo (sem iframe embutido devido a CORS)

## Próximas Melhorias

- Auto-refresh da lista de dispositivos
- WebSocket para dados em tempo real
- Gráficos inline usando Chart.js
- Exportação de dados em CSV
- Notificações/alertas de dispositivos offline
- Logs de ações do administrador
- Suporte a múltiplos usuários com permissões
