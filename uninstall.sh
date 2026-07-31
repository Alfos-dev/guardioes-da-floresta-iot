#!/usr/bin/env bash
#
# Guardiões da Floresta IoT - Desinstalador
# Remove containers, volumes e dados do projeto
#
# ATENÇÃO: Este script irá remover TODOS os dados coletados!
#

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="${INSTALL_DIR:-$HOME/guardioes-iot}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

show_warning() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║                    ATENÇÃO - DESINSTALAÇÃO                ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    log_warn "Este script irá:"
    echo "  - Parar todos os containers do projeto"
    echo "  - Remover os containers"
    echo "  - Remover os volumes Docker (DADOS SERÃO PERDIDOS)"
    echo ""
    log_warn "Os seguintes dados serão removidos:"
    echo "  - Dados históricos do InfluxDB"
    echo "  - Registro de dispositivos (SQLite)"
    echo "  - Configurações do Grafana"
    echo "  - Mensagens persistentes do MQTT"
    echo ""
    log_warn "O diretório de instalação ($INSTALL_DIR) será preservado."
    log_warn "Você pode removê-lo manualmente depois, se desejar."
    echo ""
}

confirm_uninstall() {
    read -p "Tem certeza que deseja desinstalar? Digite 'sim' para confirmar: " -r
    echo
    if [[ ! $REPLY == "sim" ]]; then
        log_info "Desinstalação cancelada."
        exit 0
    fi
}

stop_and_remove() {
    log_info "Parando e removendo containers..."
    
    cd "$INSTALL_DIR"
    
    # Parar serviços
    docker compose down -v 2>/dev/null || {
        log_warn "Erro ao parar containers. Continuando..."
    }
    
    log_info "Containers removidos."
}

remove_volumes() {
    log_info "Removendo volumes Docker..."
    
    local volumes=(
        "guardioes-da-floresta-iot_influxdb_data"
        "guardioes-da-floresta-iot_grafana_data"
        "guardioes-da-floresta-iot_mosquitto_data"
        "guardioes-da-floresta-iot_devices_data"
    )
    
    for vol in "${volumes[@]}"; do
        if docker volume ls | grep -q "$vol"; then
            docker volume rm "$vol" 2>/dev/null || log_warn "Não foi possível remover volume $vol"
            log_info "Volume $vol removido."
        fi
    done
}

show_final_message() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║           Desinstalação concluída com sucesso!            ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    log_info "Containers e volumes removidos."
    echo ""
    log_warn "O diretório de instalação foi preservado em: $INSTALL_DIR"
    log_warn "Se desejar removê-lo completamente, execute:"
    echo "  rm -rf $INSTALL_DIR"
    echo ""
    log_info "Para reinstalar, execute novamente o script de instalação."
    echo ""
}

main() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_error "Diretório de instalação não encontrado: $INSTALL_DIR"
        exit 1
    fi
    
    show_warning
    confirm_uninstall
    
    stop_and_remove
    remove_volumes
    
    show_final_message
}

main "$@"
