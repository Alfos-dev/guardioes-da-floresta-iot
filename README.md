# Guardiões da Floresta — Sistema IoT de Monitoramento Ambiental

Sistema de monitoramento ambiental em tempo real desenvolvido para apoiar a agricultura familiar local. O projeto utiliza sensores de baixo custo conectados a um microcontrolador ESP32 para coletar dados de temperatura, umidade do ar e umidade do solo, transmitindo essas informações a um servidor local que processa, armazena e exibe os dados em um dashboard interativo — sem depender de internet.

A proposta é oferecer ao pequeno agricultor uma ferramenta acessível e confiável para acompanhar as condições do ambiente de cultivo em tempo real, auxiliando na tomada de decisões sobre irrigação, ventilação e manejo da plantação.

---

## 1. Arquitetura do Sistema

O sistema **Guardiões da Floresta** opera de forma autônoma e local, garantindo o monitoramento contínuo das condições ambientais sem a necessidade de conexão com a internet. A arquitetura é modular e baseada em contêineres Docker, facilitando a implantação e o gerenciamento.

```
+-------------------------------------------------------------+
|                     ESP32 (Nó Sensor)                       |
|  AHT10 (Temp + Umidade do Ar) + Sensor Capacitivo de Solo  |
|                 Envia JSON via Serial USB                   |
+-------------------------+-----------------------------------+
                          | USB Serial
+-------------------------v-----------------------------------+
|                   Servidor (Mini PC)                        |
|  +----------------+   +--------------+   +-------------+   |
|  | serial_bridge  |-->|   InfluxDB   |-->|   Grafana   |   |
|  |   (Python)     |   |  (banco de   |   | (dashboard) |   |
|  +----------------+   |    dados)    |   +-------------+   |
|  +----------------+   +--------------+                     |
|  | moon_service   |-->  fase da lua em tempo real           |
|  |   (Python)     |                                        |
|  +----------------+                                        |
|        Tudo containerizado com Docker Compose              |
+-------------------------+-----------------------------------+
                          | Wi-Fi Local (sem internet)
+-------------------------v-----------------------------------+
|             Notebook / Celular (Visualização)               |
|             http://IP_DO_SERVIDOR:3000                      |
+-------------------------------------------------------------+
```

**Fluxo de Dados:**
1.  **Coleta**: O microcontrolador ESP32-S3, equipado com sensores AHT10 (temperatura e umidade do ar) e um sensor capacitivo de umidade do solo, coleta dados ambientais em intervalos regulares.
2.  **Transmissão**: Os dados são formatados em JSON e enviados via comunicação Serial USB para um servidor local.
3.  **Processamento e Armazenamento**: No servidor, o script `serial_to_influx.py` (parte do `serial_bridge`) lê os dados da porta serial, faz o parse do JSON e os armazena no InfluxDB, um banco de dados de séries temporais. Paralelamente, o `moon_from_json.py` (parte do `moon_service`) lê informações sobre as fases lunares de um arquivo JSON pré-definido e também as insere no InfluxDB.
4.  **Visualização**: O Grafana consome os dados do InfluxDB e os exibe em um dashboard interativo, permitindo que o agricultor visualize as condições ambientais e as fases lunares em tempo real através de um navegador web (via Wi-Fi local).

---

## 2. Tecnologias Utilizadas

Este projeto integra diversas tecnologias para criar uma solução robusta e de baixo custo:

| Camada | Tecnologia | Descrição |
| :--- | :--- |
| **Hardware** | ESP32-S3 DevKitC-1 | Microcontrolador principal, responsável pela coleta de dados dos sensores. |
| | AHT10 | Sensor de temperatura e umidade relativa do ar, conhecido pela precisão e baixo custo. |
| | Sensor Capacitivo de Solo | Mede a umidade do solo de forma não invasiva, evitando corrosão. |
| **Firmware** | C++ (PlatformIO / Arduino Framework) | Código embarcado no ESP32 para leitura dos sensores e comunicação serial. |
| **Bridge Serial** | Python 3 + `pyserial` + `influxdb-client` | Script (`serial_to_influx.py`) que faz a ponte entre a porta serial do ESP32 e o InfluxDB. |
| **Serviço Lunar** | Python 3 + `influxdb-client` | Script (`moon_from_json.py`) que insere dados de fases lunares no InfluxDB a partir de um arquivo JSON. |
| **Banco de Dados** | InfluxDB 2.7 (Séries Temporais) | Armazena eficientemente os dados de sensores e fases lunares. |
| **Visualização** | Grafana | Plataforma de código aberto para visualização e análise de métricas. |
| **Infraestrutura** | Docker + Docker Compose | Orquestração de todos os serviços (InfluxDB, Grafana, `serial_bridge`, `moon_service`) em contêineres. |
| **Rede** | Roteador Wi-Fi isolado | Cria uma rede local para acesso ao dashboard sem dependência de internet externa. |

---

## 3. Hardware e Conexões

Para replicar o projeto, você precisará dos seguintes componentes e deverá realizar as conexões conforme o diagrama e a tabela abaixo.

### Lista de Materiais (BOM - Bill of Materials)

| Componente | Quantidade | Observações |
| :--- | :--- | :--- |
| ESP32-S3 DevKitC-1 | 1 | Microcontrolador principal. |
| Sensor de Temperatura e Umidade AHT10 | 1 | Conexão I2C. |
| Sensor Capacitivo de Umidade do Solo | 1 | Conexão analógica. |
| Jumpers (Macho-Fêmea e Macho-Macho) | Suficiente | Para as conexões entre ESP32 e sensores. |
| Protoboard (opcional) | 1 | Para facilitar as conexões. |
| Cabo USB-C | 1 | Para alimentação e comunicação serial do ESP32. |
| Mini PC (ou Raspberry Pi/PC com Linux) | 1 | Para rodar os serviços Docker. |
| Roteador Wi-Fi (isolado) | 1 | Para criar a rede local de acesso ao Grafana. |

### Diagrama de Conexões (ESP32-S3)

```mermaid
graph TD
    A[ESP32-S3 DevKitC-1] --> B{Sensor AHT10}
    A --> C{Sensor de Umidade do Solo}

    B -- SDA --> A
    B -- SCL --> A
    B -- VCC --> A
    B -- GND --> A

    C -- AOUT --> A
    C -- VCC --> A
    C -- GND --> A

    subgraph AHT10_I2C [AHT10 - I2C]
        B_SDA[GPIO 17] -- SDA --> B
        B_SCL[GPIO 18] -- SCL --> B
        B_VCC[3.3V] -- VCC --> B
        B_GND[GND] -- GND --> B
    end

    subgraph Solo_Analogico [Sensor de Umidade do Solo - Analógico]
        C_AOUT[GPIO 4 (ADC)] -- AOUT --> C
        C_VCC[3.3V] -- VCC --> C
        C_GND[GND] -- GND --> C
    end
```

**Tabela de Pinagem:**

| Sensor | Pino do Sensor | Pino do ESP32-S3 | Função |
| :--- | :--- | :--- | :--- |
| AHT10 | VCC | 3.3V | Alimentação |
| | GND | GND | Terra |
| | SDA | GPIO 17 | Dados I2C |
| | SCL | GPIO 18 | Clock I2C |
| Sensor de Umidade do Solo | VCC | 3.3V | Alimentação |
| | GND | GND | Terra |
| | AOUT | GPIO 4 (ADC) | Saída Analógica |

---

## 4. Configuração do Ambiente (Servidor)

Para configurar o servidor local que irá receber os dados do ESP32 e hospedar o dashboard do Grafana, siga os passos abaixo.

### Pré-requisitos
*   Um sistema operacional baseado em Linux (Debian/Ubuntu é recomendado).
*   **Docker** e **Docker Compose** instalados. Se não tiver, siga as instruções oficiais:
    *   [Instalar Docker Engine](https://docs.docker.com/engine/install/ubuntu/)
    *   [Instalar Docker Compose](https://docs.docker.com/compose/install/)
*   O ESP32 deve estar conectado ao Mini PC via cabo USB.

### Passos de Instalação

1.  **Clone o Repositório:**
    ```bash
    git clone https://github.com/Alfos-dev/guardioes-da-floresta-iot.git
    cd guardioes-da-floresta-iot
    ```

2.  **Configure as Variáveis de Ambiente:**
    Crie um arquivo `.env` a partir do exemplo fornecido e edite-o com suas credenciais e configurações. Este arquivo é crucial para a segurança e o funcionamento dos serviços.
    ```bash
    cp .env.example .env
    nano .env # Ou seu editor de texto preferido
    ```
    **Conteúdo esperado do `.env`:**
    ```ini
    # InfluxDB Configuration
    INFLUXDB_URL=http://localhost:8086
    INFLUXDB_TOKEN=seu_token_influxdb_aqui # Gere um token de leitura/escrita no InfluxDB
    INFLUXDB_ORG=sua_organizacao_influxdb # Ex: ads
    INFLUXDB_BUCKET=monitoramento

    # Grafana Configuration
    GF_SECURITY_ADMIN_USER=admin
    GF_SECURITY_ADMIN_PASSWORD=sua_senha_admin_grafana_aqui

    # Serial Port Configuration
    SERIAL_PORT=/dev/ttyUSB0 # Verifique a porta serial do seu ESP32 (pode ser /dev/ttyACM0 ou similar)
    BAUD_RATE=115200
    ```
    *   **`INFLUXDB_TOKEN`**: Você precisará gerar um token de API no InfluxDB após a primeira inicialização. Certifique-se de que ele tenha permissões de leitura e escrita para o bucket `monitoramento`.
    *   **`SERIAL_PORT`**: Verifique qual porta serial seu ESP32 está utilizando. No Linux, geralmente é `/dev/ttyUSB0` ou `/dev/ttyACM0`. Você pode verificar com `ls /dev/tty*` antes e depois de conectar o ESP32.

3.  **Suba os Contêineres Docker:**
    Este comando irá construir as imagens Docker (se necessário) e iniciar todos os serviços definidos no `docker-compose.yml` em segundo plano.
    ```bash
    docker compose up -d --build
    ```

4.  **Verifique os Logs (Opcional):**
    Para garantir que todos os serviços estão funcionando corretamente, você pode verificar os logs:
    ```bash
    docker compose logs -f
    ```

---

## 5. Firmware ESP32

O firmware do ESP32 é responsável por ler os dados dos sensores e enviá-los via serial. Ele é desenvolvido utilizando o PlatformIO, uma extensão para VS Code que facilita o desenvolvimento embarcado.

### Pré-requisitos
*   **VS Code** com a extensão **PlatformIO IDE** instalada.
*   Drivers USB para o ESP32 (geralmente CP210x ou CH340).

### Compilação e Upload

1.  **Abra o Projeto no PlatformIO:**
    No VS Code, abra a pasta `src/` do repositório como um projeto PlatformIO.

2.  **Verifique as Dependências:**
    O projeto utiliza a biblioteca `Adafruit AHTX0`. Certifique-se de que ela está instalada no seu ambiente PlatformIO. O arquivo `platformio.ini` já deve conter as dependências necessárias.

3.  **Configure o `platformio.ini` (Opcional):**
    Se você tiver problemas com a porta de upload, pode especificar explicitamente no `platformio.ini`:
    ```ini
    [env:esp32-s3-devkitc-1]
    platform = espressif32
    board = esp32-s3-devkitc-1
    framework = arduino
    lib_deps =
        adafruit/Adafruit AHTX0@^1.1.4
    upload_port = /dev/ttyUSB0 # Ajuste conforme sua porta serial
    monitor_port = /dev/ttyUSB0 # Ajuste conforme sua porta serial
    monitor_speed = 115200
    ```

4.  **Compile e Faça o Upload:**
    Use os botões de **Build** (✓) e **Upload** (→) na barra de status do PlatformIO no VS Code para compilar o código e fazer o upload para o seu ESP32.

5.  **Monitore a Saída Serial:**
    Após o upload, utilize o **Serial Monitor** (ícone de plug) do PlatformIO para verificar se o ESP32 está enviando os dados JSON corretamente.
    Exemplo de saída JSON:
    ```json
    {"device_id":"esp32_1","seq":1,"t":25.5,"ha":60.2,"s":45,"soil_raw":2500}
    ```

---

## 6. Scripts de Integração Python

Os scripts Python são essenciais para a ingestão de dados no InfluxDB. Eles são executados como serviços Docker, mas é útil entender seu funcionamento.

### `serial_to_influx.py` (Bridge Serial)

Este script lê a porta serial onde o ESP32 está conectado, parseia as mensagens JSON e as escreve no InfluxDB.

*   **Localização**: `bridge/serial_to_influx.py`
*   **Função**: Conecta-se à porta serial especificada em `.env`, decodifica as linhas recebidas como JSON e cria pontos de dados no InfluxDB para temperatura (`t`), umidade do ar (`ha`), umidade do solo normalizada (`s`) e umidade do solo bruta (`soil_raw`).
*   **Configuração**: As variáveis de ambiente (`INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`, `SERIAL_PORT`, `BAUD_RATE`) são lidas do arquivo `.env`.

### `moon_from_json.py` (Serviço Lunar)

Este script lê um arquivo JSON contendo o calendário lunar e insere a fase atual da lua no InfluxDB.

*   **Localização**: `moon/moon_from_json.py`
*   **Função**: Carrega o `calendario_lunar_2026.json`, determina a fase lunar atual com base na data e hora do sistema, e insere essa informação no InfluxDB como um ponto de dado (`moon_data`).
*   **Configuração**: O caminho para o arquivo JSON (`JSON_FILE`) e as configurações do InfluxDB são definidas no script e podem ser influenciadas pelas variáveis de ambiente.

---

## 7. Dados no InfluxDB e Grafana

O dashboard do Grafana é alimentado pelos dados armazenados no InfluxDB. Abaixo, detalhamos como os dados são estruturados e as queries Flux utilizadas para acessá-los.

### Estrutura dos Dados no InfluxDB

Todos os dados são armazenados no bucket `monitoramento`.

*   **Medição `sensor_data` (do ESP32):**
    *   **Tags**: `device_id` (ex: `esp32_1`)
    *   **Campos**: 
        *   `t`: Temperatura do ar (float, °C)
        *   `ha`: Umidade relativa do ar (float, %)
        *   `s`: Umidade do solo normalizada (float, %)
        *   `soil_raw`: Leitura bruta do ADC do sensor de solo (int)

*   **Medição `moon_data` (do Serviço Lunar):**
    *   **Campos**: 
        *   `phase`: Fase da lua (string, ex: `Lua Cheia`)
        *   `phase_date`: Data de início da fase (string, ex: `2026-01-01`)
        *   `phase_time`: Hora de início da fase (string, ex: `12:00`)

### Exemplos de Queries Flux (Grafana)

Para visualizar os dados no Grafana, as seguintes queries Flux são utilizadas:

*   **Umidade do Solo Atual:**
    ```flux
    from(bucket: "monitoramento")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "sensor_data" and r._field == "s")
      |> last()
    ```
    *Esta query busca a última leitura da umidade do solo nos últimos 5 minutos.*

*   **Temperatura Atual:**
    ```flux
    from(bucket: "monitoramento")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "sensor_data" and r._field == "t")
      |> last()
    ```
    *Esta query busca a última leitura da temperatura do ar nos últimos 5 minutos.*

*   **Fase da Lua Atual:**
    ```flux
    from(bucket: "monitoramento")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "moon_data" and r._field == "phase")
      |> last()
    ```
    *Esta query busca a última fase da lua registrada nas últimas 24 horas.*

*   **Histórico de Temperatura e Umidade do Ar:**
    ```flux
    from(bucket: "monitoramento")
      |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
      |> filter(fn: (r) => r._measurement == "sensor_data" and (r._field == "t" or r._field == "ha"))
      |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
      |> yield(name: "mean")
    ```
    *Esta query busca o histórico de temperatura e umidade do ar para o período selecionado no Grafana, calculando a média para cada janela de tempo.*

---

## 8. Funcionamento Offline

O sistema foi projetado para funcionar sem internet, ideal para ambientes rurais e remotos:

*   O roteador Wi-Fi cria uma rede local isolada.
*   O servidor, sensores e dispositivos de visualização se comunicam apenas na rede local.
*   Nenhum dado é enviado para a nuvem.
*   O sistema reinicia automaticamente após quedas de energia.

---

## 9. Troubleshooting (Problemas Comuns)

*   **ESP32 não aparece na porta serial (`/dev/ttyUSB0` ou similar):**
    *   Verifique se o cabo USB está funcionando e se o ESP32 está alimentado.
    *   Instale os drivers USB corretos para o chip serial do seu ESP32 (CP210x ou CH340).
    *   Verifique as permissões: seu usuário precisa ter acesso à porta serial. Adicione seu usuário ao grupo `dialout` com `sudo usermod -a -G dialout $USER` e reinicie a sessão.

*   **`serial_to_influx.py` não consegue conectar à porta serial:**
    *   Certifique-se de que o `SERIAL_PORT` no seu arquivo `.env` está correto.
    *   Verifique se nenhum outro programa (como o Serial Monitor do PlatformIO) está usando a porta serial.

*   **Serviços Docker não iniciam ou apresentam erros:**
    *   Verifique os logs com `docker compose logs` para identificar a causa do erro.
    *   Certifique-se de que as variáveis no `.env` estão configuradas corretamente, especialmente o `INFLUXDB_TOKEN` e as credenciais do Grafana.
    *   Verifique se as portas 8086 (InfluxDB) e 3000 (Grafana) não estão sendo usadas por outros serviços na sua máquina.

*   **Dados não aparecem no Grafana:**
    *   Verifique se o InfluxDB está recebendo dados. Você pode usar a interface web do InfluxDB (geralmente `http://localhost:8086`) para verificar o bucket `monitoramento`.
    *   Confira as queries Flux no Grafana para garantir que estão corretas e apontando para o bucket certo.

---

## 10. Equipe

*   Alessandro Vinicius Torres Do Couto
*   Ana Clara Flores Monteiro
*   Andre Gustavo Osorio Bezerra
*   Andre Luiz Falcao Otaviano da Silva
*   Andrew Soares Teixeira
*   Caio Maxwel Silva Moraes
*   Davi Cruz Da Costa
*   Douglas Almeida Menezes De Oliveira
*   Emerson Henrique Soeiro Cutrim
*   Erick Martins De Carvalho
*   Frank Ryan Da Silva Braga
*   Gabriel Benoliel Malcher
*   Gracieide Guimaraes Barbosa
*   Janff Henrique Guedes De Souza
*   Joao Pedro Marques Nascimento
*   Joao Vitor Pereira Dos Santos
*   Joao Luiz Carneiro Chistama
*   Kevyn Willian Oliveira Da Silva
*   Lucas Vasques Dos Santos
*   Luiz Cristiano Ferreira de Oliveira
*   Luiz Eduardo Custodio Duarte
*   Luiz Gustavo De Souza Feitosa
*   Perter Jofre Ribeiro Jati Junior
*   Richard Oliver Cabral Melo
*   Talyson Alves

---

## 11. Licença

Este projeto é livre para uso acadêmico e educacional, desenvolvido como iniciativa de apoio à agricultura local.

---
