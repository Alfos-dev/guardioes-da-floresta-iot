# Guia de Instalação — Guardiões da Floresta IoT v2.0

Este documento descreve o processo completo de instalação do sistema Guardiões da Floresta IoT versão 2.0.

## Requisitos Mínimos

### Hardware
- Processador: dual-core 1GHz ou superior
- RAM: 2GB (4GB recomendado)
- Armazenamento: 10GB livres
- Conectividade: Ethernet ou WiFi

### Software
- Sistema operacional: Ubuntu 20.04+ ou Debian 11+ (outras distros Linux podem funcionar)
- Conexão à internet (apenas durante instalação inicial)
- Acesso sudo/root

## Método 1: Instalação Automática (Recomendado)

### Instalação com um único comando

Execute o seguinte comando em um terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/Alfos-dev/guardioes-da-floresta-iot/v2.0.0-phase1/install.sh | bash
```

**O que o instalador faz:**
1. Detecta o sistema operacional
2. Verifica se Docker e Docker Compose estão instalados
3. Instala Docker automaticamente se necessário (Debian/Ubuntu)
4. Baixa o código do repositório (release versionada)
5. Gera credenciais aleatórias seguras para InfluxDB e MQTT
6. Cria arquivo `.env` com as credenciais
7. Gera arquivo de senha do Mosquitto (`passwd`)
8. Inicia todos os serviços via Docker Compose
9. Exibe informações de acesso e credenciais

### Personalizar diretório de instalação

Por padrão, o instalador cria o diretório `~/guardioes-iot`. Para usar outro local:

```bash
export INSTALL_DIR=/caminho/desejado
curl -fsSL https://raw.githubusercontent.com/Alfos-dev/guardioes-da-floresta-iot/v2.0.0-phase1/install.sh | bash
```

### Usar uma versão específica

Para instalar uma release específica:

```bash
export RELEASE_TAG=v2.0.0-phase2
curl -fsSL https://raw.githubusercontent.com/Alfos-dev/guardioes-da-floresta-iot/$RELEASE_TAG/install.sh | bash
```

## Método 2: Instalação Manual

### Passo 1: Instalar Docker e Docker Compose

**Ubuntu/Debian:**
```bash
# Atualizar repositórios
sudo apt-get update

# Instalar dependências
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Adicionar chave GPG do Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Adicionar repositório
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER

# Aplicar grupo (ou faça logout/login)
newgrp docker
```

### Passo 2: Clonar o repositório

```bash
cd ~
git clone --branch v2.0.0-phase1 https://github.com/Alfos-dev/guardioes-da-floresta-iot.git guardioes-iot
cd guardioes-iot
```

### Passo 3: Configurar credenciais

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Edite `.env` e defina senhas fortes para:
- `INFLUXDB_PASSWORD`
- `INFLUXDB_ADMIN_TOKEN`
- `MQTT_PASS`

**Exemplo com senhas aleatórias:**
```bash
sed -i "s/sua_senha_influx/$(openssl rand -base64 24)/g" .env
sed -i "s/seu_token_aqui/$(openssl rand -base64 48)/g" .env
sed -i "s/SUA_SENHA/$(openssl rand -base64 24)/g" .env
```

### Passo 4: Gerar arquivo de senha do Mosquitto

```bash
cd services/mosquitto
bash gen-passwd.sh
cd ../..
```

Ou manualmente:
```bash
# Usar mesmo usuário/senha do .env
MQTT_USER=$(grep MQTT_USER .env | cut -d '=' -f2)
MQTT_PASS=$(grep MQTT_PASS .env | cut -d '=' -f2)

docker run --rm -v $(pwd)/services/mosquitto:/mosquitto/config eclipse-mosquitto:2 \
  mosquitto_passwd -c -b /mosquitto/config/passwd "$MQTT_USER" "$MQTT_PASS"
```

### Passo 5: Iniciar serviços

```bash
docker compose up -d
```

### Passo 6: Verificar status

```bash
docker compose ps
docker compose logs -f
```

## Verificação Pós-Instalação

### Verificar serviços rodando

```bash
cd ~/guardioes-iot  # ou seu INSTALL_DIR
docker compose ps
```

Todos os serviços devem estar com status `Up` ou `running`:
- `influxdb`
- `grafana`
- `mosquitto`
- `ingest_service`
- `moon_service`

### Acessar interfaces web

- **Grafana**: http://localhost:3000
  - Usuário padrão: `admin`
  - Senha padrão: `admin` (será solicitado alteração no primeiro acesso)

- **InfluxDB UI**: http://localhost:8086
  - Use as credenciais geradas no `.env`

### Testar conexão MQTT

```bash
# Instalar cliente MQTT
sudo apt-get install -y mosquitto-clients

# Ler credenciais do .env
MQTT_USER=$(grep MQTT_USER ~/guardioes-iot/.env | cut -d '=' -f2)
MQTT_PASS=$(grep MQTT_PASS ~/guardioes-iot/.env | cut -d '=' -f2)

# Publicar mensagem de teste
mosquitto_pub -h localhost -p 1883 -u "$MQTT_USER" -P "$MQTT_PASS" \
  -t "guardioes/teste/telemetry" \
  -m '{"device_id":"teste","timestamp":"2026-07-30T12:00:00Z","readings":[{"sensor":"test","value":42,"unit":"C"}]}'

# Verificar se ingest_service processou
docker compose logs ingest_service | tail -20
```

## Próximos Passos

Após instalação do servidor:

1. **Configurar Grafana**
   - Adicionar datasource InfluxDB
   - Importar dashboards ou criar os seus

2. **Compilar firmware para dispositivos**
   - Consulte `firmware-v2/README.md`
   - Use PlatformIO: `cd firmware-v2 && pio run`

3. **Provisionar dispositivos**
   - Grave firmware no ESP32-S3
   - No primeiro boot, conecte-se ao Access Point do dispositivo
   - Configure WiFi e credenciais MQTT via portal web

4. **Monitorar dados**
   - Acompanhe leituras em tempo real no Grafana
   - Exporte dados históricos conforme necessário

## Comandos Úteis

### Ver logs em tempo real
```bash
cd ~/guardioes-iot
docker compose logs -f
```

### Reiniciar um serviço específico
```bash
docker compose restart ingest_service
```

### Parar todos os serviços
```bash
docker compose down
```

### Parar e remover volumes (DADOS SERÃO PERDIDOS)
```bash
docker compose down -v
```

### Atualizar para nova versão
```bash
cd ~/guardioes-iot
git fetch --tags
git checkout v2.0.0-phase2  # nova versão
docker compose pull
docker compose up -d
```

## Desinstalação

Para remover completamente o sistema:

```bash
cd ~/guardioes-iot
./uninstall.sh
```

**ATENÇÃO:** Todos os dados históricos serão perdidos!

Para remover também o código:
```bash
rm -rf ~/guardioes-iot
```

## Troubleshooting

### Docker não inicia após instalação

**Problema:** Erro "permission denied" ao executar comandos docker.

**Solução:** Faça logout e login novamente, ou execute:
```bash
newgrp docker
```

### Porta já em uso

**Problema:** `Error: bind: address already in use`

**Solução:** Verifique se outro serviço está usando a porta:
```bash
sudo lsof -i :1883  # MQTT
sudo lsof -i :8086  # InfluxDB
sudo lsof -i :3000  # Grafana
```

Pare o serviço conflitante ou edite `docker-compose.yml` para usar portas diferentes.

### Serviço não inicia

**Problema:** Container reiniciando constantemente.

**Solução:** Verifique logs:
```bash
docker compose logs <nome_do_servico>
```

### Erro de permissão em volumes

**Problema:** Container não consegue gravar em volumes.

**Solução:** Verificar permissões dos diretórios de volume ou recriar volumes:
```bash
docker compose down -v
docker compose up -d
```

### MQTT recusa conexão

**Problema:** Dispositivos não conseguem conectar ao broker.

**Solução:** 
1. Verificar se arquivo `passwd` foi gerado corretamente:
   ```bash
   ls -la services/mosquitto/passwd
   ```
2. Verificar se credenciais no `.env` correspondem ao arquivo `passwd`
3. Recriar arquivo de senha:
   ```bash
   cd services/mosquitto
   bash gen-passwd.sh
   docker compose restart mosquitto
   ```

### Sem dados no Grafana

**Problema:** Gráficos vazios mesmo com dispositivos conectados.

**Solução:**
1. Verificar logs do `ingest_service`:
   ```bash
   docker compose logs ingest_service
   ```
2. Verificar se dados estão chegando no InfluxDB:
   ```bash
   docker compose exec influxdb influx query 'from(bucket:"sensor_data") |> range(start: -1h)'
   ```
3. Verificar configuração do datasource no Grafana

## Suporte

Para problemas não listados aqui:
1. Verifique os logs: `docker compose logs`
2. Consulte issues no GitHub: https://github.com/Alfos-dev/guardioes-da-floresta-iot/issues
3. Leia a documentação completa: `README.md`
