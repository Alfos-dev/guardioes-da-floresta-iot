# Guardiões da Floresta — Sistema IoT de Monitoramento Ambiental

Sistema de monitoramento ambiental em tempo real desenvolvido para apoiar a agricultura familiar local. O projeto utiliza sensores de baixo custo conectados a um microcontrolador ESP32 para coletar dados de temperatura, umidade do ar e umidade do solo, transmitindo essas informações a um servidor local que processa, armazena e exibe os dados em um dashboard interativo — sem depender de internet.

A proposta é oferecer ao pequeno agricultor uma ferramenta acessível e confiável para acompanhar as condições do ambiente de cultivo em tempo real, auxiliando na tomada de decisões sobre irrigação, ventilação e manejo da plantação.

---

## Arquitetura do Sistema

```
+-------------------------------------------------------------+
|                     ESP32 (No Sensor)                       |
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
|             Notebook / Celular (Visualizacao)               |
|             http://IP_DO_SERVIDOR:3000                      |
+-------------------------------------------------------------+
```

---

## Tecnologias Utilizadas

| Camada | Tecnologia |
|---|---|
| Hardware | ESP32, AHT10, Sensor Capacitivo de Solo |
| Firmware | C++ (PlatformIO / Arduino Framework) |
| Bridge Serial | Python 3 + pyserial + influxdb-client |
| Banco de Dados | InfluxDB 2.7 (series temporais) |
| Visualizacao | Grafana (dashboard em tempo real) |
| Fase da Lua | Python 3 (calculo astronomico local) |
| Infraestrutura | Docker + Docker Compose |
| Rede | Roteador Wi-Fi isolado (sem internet) |

---

## Estrutura do Repositório

```
guardioes-da-floresta-iot/
├── docker-compose.yml       # Orquestração dos containers
├── .env.example             # Variáveis de ambiente (template)
├── .gitignore
│
├── bridge/                  # Serviço de leitura serial -> InfluxDB
│   ├── serial_bridge.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── moon/                    # Serviço de fase da lua
│   ├── moon_service.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── app/                     # API FastAPI (legado)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── src/                     # Firmware ESP32 (PlatformIO)
    └── main.cpp
```

---

## Como Executar o Servidor

### Pré-requisitos
- Linux (Debian/Ubuntu recomendado)
- Docker + Docker Compose instalados
- ESP32 conectado via USB

### 1. Clone o repositório
```bash
git clone https://github.com/Alfos-dev/guardioes-da-floresta-iot.git
cd guardioes-da-floresta-iot
```

### 2. Configure as variáveis de ambiente
```bash
cp .env.example .env
nano .env  # edite com seus valores
```

### 3. Suba os containers
```bash
docker compose up -d --build
```

### 4. Acesse o Grafana
Abra no navegador:
```
http://IP_DO_SERVIDOR:3000
```
- **Usuario:** `admin`
- **Senha:** definida no `.env`

---

## Hardware — Conexões do ESP32

### AHT10 (Temperatura + Umidade do Ar) — I2C
| AHT10 | ESP32 |
|-------|-------|
| VCC   | 3.3V  |
| GND   | GND   |
| SDA   | GPIO 17 |
| SCL   | GPIO 18 |

### Sensor Capacitivo de Solo — Analógico
| Sensor | ESP32 |
|--------|-------|
| VCC    | 3.3V  |
| GND    | GND   |
| AOUT   | GPIO 4 (ADC) |

---

## Dados Coletados

| Campo | Descrição | Unidade |
|-------|-----------|---------|
| `t` | Temperatura do ar | C |
| `ha` | Umidade relativa do ar | % |
| `s` | Umidade do solo (normalizada) | % |
| `soil_raw` | Leitura bruta do ADC | 1150-4065 |
| `moon_phase` | Fase da lua atual | texto |

---

## Funcionamento Offline

O sistema foi projetado para funcionar sem internet, ideal para ambientes rurais e remotos:

- O roteador Wi-Fi cria uma rede local isolada
- O servidor, sensores e dispositivos de visualização se comunicam apenas na rede local
- Nenhum dado é enviado para a nuvem
- O sistema reinicia automaticamente apos quedas de energia

---

## Equipe

| | |
|---|---|
| Alessandro Vinicius Torres Do Couto | Ana Clara Flores Monteiro |
| Andre Gustavo Osorio Bezerra | Andre Luiz Falcao Otaviano da Silva |
| Andrew Soares Teixeira | Caio Maxwel Silva Moraes |
| Davi Cruz Da Costa | Douglas Almeida Menezes De Oliveira |
| Emerson Henrique Soeiro Cutrim | Erick Martins De Carvalho |
| Frank Ryan Da Silva Braga | Gabriel Benoliel Malcher |
| Gracieide Guimaraes Barbosa | Janff Henrique Guedes De Souza |
| Joao Pedro Marques Nascimento | Joao Vitor Pereira Dos Santos |
| Joao Luiz Carneiro Chistama | Kevyn Willian Oliveira Da Silva |
| Lucas Vasques Dos Santos | Luiz Cristiano Ferreira de Oliveira |
| Luiz Eduardo Custodio Duarte | Luiz Gustavo De Souza Feitosa |
| Perter Jofre Ribeiro Jati Junior | Richard Oliver Cabral Melo |
| Talyson Alves | |

---

## Licenca

Este projeto é livre para uso acadêmico e educacional, desenvolvido como iniciativa de apoio à agricultura local.
