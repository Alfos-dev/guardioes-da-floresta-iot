#!/usr/bin/env bash
#
# Guardiões da Floresta IoT - Instalador Automatizado (v1.0 estável)
# Instalação da versão 1.x (estável): ESP32 → serial_bridge → InfluxDB → Grafana
#
# A v1 é independente da v2 (beta, MQTT-first). Cada versão é publicada em uma
# release/tag própria e instalada separadamente.
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/Alfos-dev/guardioes-da-floresta-iot/v1.0.0/install.sh | bash
#   ou localmente: ./install.sh
#

set -e  # Sair em caso de erro
set -u  # Sair se usar variável não definida

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
INSTALL_DIR="${INSTALL_DIR:-$HOME/guardioes-iot}"
RELEASE_TAG="${RELEASE_TAG:-v1.0.0}"
REPO_URL="https://github.com/Alfos-dev/guardioes-da-floresta-iot"

# Funções de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

# Banner
show_banner() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     Guardiões da Floresta IoT - Instalador v1 (estável)   ║"
    echo "║              Monitoramento Agroecológico com IoT          ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
}

# Detectar sistema operacional
detect_os() {
    log_info "Detectando sistema operacional..."

    if [[ ! -f /etc/os-release ]]; then
        log_error "Arquivo /etc/os-release não encontrado. Sistema não suportado."
        exit 1
    fi

    source /etc/os-release

    case "$ID" in
        ubuntu|debian|pop|linuxmint)
            OS_TYPE="debian"
            log_success "Sistema detectado: $PRETTY_NAME (tipo Debian)"
            ;;
        *)
            log_warn "Sistema '$PRETTY_NAME' pode não ser totalmente suportado."
            log_warn "Esta versão do instalador foi testada em Ubuntu/Debian."
            read -p "Deseja continuar mesmo assim? (s/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Ss]$ ]]; then
                log_info "Instalação cancelada."
                exit 0
            fi
            OS_TYPE="unknown"
            ;;
    esac
}

# Verificar se Docker está instalado
check_docker() {
    log_info "Verificando instalação do Docker..."

    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0.0.0")
        log_success "Docker encontrado: versão $DOCKER_VERSION"

        if groups | grep -q docker; then
            log_success "Usuário já está no grupo 'docker'"
        else
            log_warn "Usuário não está no grupo 'docker'. Será necessário usar sudo ou fazer logout/login após instalação."
        fi

        return 0
    else
        log_warn "Docker não encontrado."
        return 1
    fi
}

# Instalar Docker
install_docker() {
    log_info "Instalando Docker..."

    if [[ "$OS_TYPE" != "debian" ]]; then
        log_error "Instalação automática do Docker suportada apenas em sistemas Debian/Ubuntu."
        log_info "Por favor, instale o Docker manualmente: https://docs.docker.com/engine/install/"
        exit 1
    fi

    log_info "Atualizando repositórios do sistema..."
    sudo apt-get update -qq

    log_info "Instalando dependências..."
    sudo apt-get install -y -qq \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    log_info "Adicionando repositório oficial do Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$ID/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID \
      $(lsb_release -cs) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    log_info "Instalando Docker Engine, CLI e plugins..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    log_info "Adicionando usuário '$USER' ao grupo 'docker'..."
    sudo usermod -aG docker "$USER"

    log_success "Docker instalado com sucesso!"
    log_warn "IMPORTANTE: Faça logout e login novamente para que as permissões do grupo 'docker' sejam aplicadas."
    log_info "Ou execute: newgrp docker"
}

# Verificar Docker Compose
check_docker_compose() {
    log_info "Verificando Docker Compose..."

    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "2.0.0")
        log_success "Docker Compose (plugin) encontrado: versão $COMPOSE_VERSION"
        return 0
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null || echo "1.0.0")
        log_warn "Docker Compose standalone encontrado: versão $COMPOSE_VERSION"
        log_warn "Recomenda-se usar o plugin 'docker compose' (v2+)"
        return 0
    else
        log_warn "Docker Compose não encontrado."
        return 1
    fi
}

# Gerar senha aleatória segura
generate_password() {
    local length=${1:-32}
    tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "$length"
}

# Gerar credenciais
generate_credentials() {
    log_info "Gerando credenciais aleatórias seguras..."

    INFLUX_USERNAME="guardioes_admin"
    INFLUX_PASSWORD=$(generate_password 32)
    INFLUX_TOKEN=$(generate_password 64)
    INFLUX_ORG="guardioes"
    INFLUX_BUCKET="sensor_data"

    log_success "Credenciais geradas com sucesso."
}

# Criar arquivo .env
create_env_file() {
    log_info "Criando arquivo .env..."

    cat > "$INSTALL_DIR/.env" << EOF
# Guardiões da Floresta IoT v1.x - Configuração
# Gerado automaticamente em $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# InfluxDB
INFLUX_URL=http://influxdb:8086
INFLUX_ORG=$INFLUX_ORG
INFLUX_BUCKET=$INFLUX_BUCKET
INFLUX_TOKEN=$INFLUX_TOKEN
INFLUX_INIT_USERNAME=$INFLUX_USERNAME
INFLUX_INIT_PASSWORD=$INFLUX_PASSWORD
EOF

    chmod 600 "$INSTALL_DIR/.env"
    log_success "Arquivo .env criado em: $INSTALL_DIR/.env"
}

# Baixar código do repositório (release v1.0.0, independente da v2)
download_code() {
    log_info "Preparando código do projeto..."

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Repositório já existe em $INSTALL_DIR. Atualizando..."
        cd "$INSTALL_DIR"
        git fetch --tags
        git checkout "$RELEASE_TAG" 2>/dev/null || {
            log_warn "Tag $RELEASE_TAG não encontrada. Usando branch release/v1..."
            git checkout release/v1
            git pull origin release/v1
        }
    else
        log_info "Clonando repositório (release $RELEASE_TAG)..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --depth 1 --branch "$RELEASE_TAG" "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || {
            log_warn "Tag $RELEASE_TAG não encontrada. Clonando branch release/v1..."
            git clone --depth 1 --branch release/v1 "$REPO_URL" "$INSTALL_DIR"
        }
    fi

    cd "$INSTALL_DIR"
    log_success "Código preparado em: $INSTALL_DIR"
}

# Iniciar serviços
start_services() {
    log_info "Iniciando serviços Docker..."

    cd "$INSTALL_DIR"

    if [[ ! -f .env ]]; then
        log_error "Arquivo .env não encontrado!"
        exit 1
    fi

    docker compose down 2>/dev/null || true

    log_info "Executando 'docker compose up -d'..."
    docker compose up -d

    log_success "Serviços iniciados!"
}

# Verificar saúde dos serviços
check_services_health() {
    log_info "Verificando saúde dos serviços..."
    sleep 5

    cd "$INSTALL_DIR"

    docker compose ps

    local services=("influxdb" "serial_bridge" "grafana")
    local all_healthy=true

    for service in "${services[@]}"; do
        if docker compose ps | grep -q "$service.*running"; then
            log_success "Serviço $service está rodando"
        else
            log_error "Serviço $service não está rodando!"
            all_healthy=false
        fi
    done

    if $all_healthy; then
        log_success "Todos os serviços principais estão rodando!"
    else
        log_warn "Alguns serviços podem não ter iniciado corretamente."
        log_info "Verifique os logs com: cd $INSTALL_DIR && docker compose logs"
    fi
}

# Mostrar informações finais
show_final_info() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║           Instalação concluída com sucesso!                ║"
    echo "║                     (v1.0 - estável)                       ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Diretório de instalação: $INSTALL_DIR"
    echo ""
    echo "Credenciais geradas (salvas em $INSTALL_DIR/.env):"
    echo ""
    echo "  InfluxDB:"
    echo "    Usuário: $INFLUX_USERNAME"
    echo "    Senha: $INFLUX_PASSWORD"
    echo "    Token: $INFLUX_TOKEN"
    echo ""
    echo "Serviços disponíveis:"
    echo "  - Grafana: http://localhost:3000 (admin/admin na primeira vez)"
    echo "  - InfluxDB UI: http://localhost:8086"
    echo ""
    echo "Próximos passos:"
    echo "  1. Configure o Grafana com o datasource InfluxDB"
    echo "  2. Compile e grave o firmware v1 no ESP32-S3 (pasta src/, platformio.ini)"
    echo "  3. Conecte o ESP32 via USB ao servidor (serial_bridge lê /dev/ttyUSB0)"
    echo "  4. Monitore os dados em tempo real no Grafana"
    echo ""
    echo "Comandos úteis:"
    echo "  Ver logs:        cd $INSTALL_DIR && docker compose logs -f"
    echo "  Parar serviços:  cd $INSTALL_DIR && docker compose down"
    echo "  Reiniciar:       cd $INSTALL_DIR && docker compose restart"
    echo ""
    echo "Para instalar a v2 (beta, MQTT-first) em outro diretório, use o"
    echo "instalador da release v2.0.0-beta:"
    echo "  INSTALL_DIR=\$HOME/guardioes-iot-v2 bash -c 'curl -fsSL https://raw.githubusercontent.com/Alfos-dev/guardioes-da-floresta-iot/v2.0.0-beta.1/install.sh | bash'"
    echo ""
}

# Função principal
main() {
    show_banner

    detect_os

    if ! check_docker; then
        read -p "Docker não está instalado. Deseja instalar agora? (S/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            install_docker
        else
            log_error "Docker é necessário para executar o projeto."
            exit 1
        fi
    fi

    if ! check_docker_compose; then
        log_info "Docker Compose será instalado junto com o Docker."
    fi

    # Baixar código (release v1.0.0)
    download_code

    # Gerar configurações
    generate_credentials
    create_env_file

    # Iniciar stack
    start_services
    check_services_health

    # Informações finais
    show_final_info

    log_success "Instalação da v1.0 completa! 🌱"
}

# Executar instalador
main "$@"