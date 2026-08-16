# Código legado — v1 (estável)

Esta pasta contém os arquivos da **v1.0** (estável) que foram movidos da raiz
do repositório quando a **v2.0 (beta)** assumiu o `main` como padrão de
desenvolvimento.

## O que está aqui

| Caminho            | O que é                                                        |
|--------------------|----------------------------------------------------------------|
| `src/`             | Firmware v1 do ESP32-S3 (AHT10 + sensor de solo, JSON via serial) |
| `lib/`, `include/` | Diretórios de apoio do PlatformIO (v1)                         |
| `test/`            | Esqueleto de testes (v1)                                       |
| `app/`             | Antigo endpoint HTTP de ingestão (não usado pelo docker-compose v1) |
| `platformio.ini`   | Projeto PlatformIO v1 (abra esta pasta para compilar)          |

## Relação com as releases

- A **v1.0 (estável)** continua sendo publicada e instalada de forma
  **independente** na release/tag `v1.0.0` (branch `release/v1`), que contém a
  árvore completa da v1 sem nenhum código da v2.
- O conteúdo desta pasta no `main` é mantido apenas como referência/consultas;
  o código canônico da v1 vive na branch `release/v1` e na tag `v1.0.0`.

## Instalando a v1 (a partir da release)

```bash
curl -fsSL https://raw.githubusercontent.com/Alfos-dev/guardioes-da-floresta-iot/v1.0.0/install.sh | bash
```