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
├── requirements.txt     # Dependências Python
├── Dockerfile          # Container Docker
├── static/             # Frontend
│   ├── index.html     # Interface principal
│   ├── style.css      # Estilos
│   └── app.js         # Lógica JavaScript
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

### Utilitários
- `GET /api/health` - Health check (status MQTT e InfluxDB)

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
