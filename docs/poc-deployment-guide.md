# Patch Manager POC Deployment Guide

## Objetivo
Subir a central do Patch Manager em um Ubuntu com instalacao repetivel, TLS local, servicos persistentes e base pronta para onboard de agentes Linux e Windows.

## Componentes da central
- `gateway`: Nginx com TLS e proxy para API e frontend
- `web`: frontend React compilado em container Nginx
- `api`: FastAPI com migrations e seed controlado
- `db`: PostgreSQL 16 com volume persistente
- `redis`: Redis 7 com AOF habilitado

## Pre-requisitos
- Ubuntu 24.04 ou equivalente
- Docker Engine + Docker Compose plugin
- `openssl`
- acesso HTTP/HTTPS ao host da central

## Instalacao
No host Ubuntu:

```bash
git clone <repo> /tmp/patch-manager
cd /tmp/patch-manager
chmod +x deploy/central/install-central.sh
sudo ./deploy/central/install-central.sh
```

O instalador:
- copia a solucao para `/opt/patch-manager`
- gera segredos iniciais
- gera certificado self-signed para a POC
- sobe a stack via Docker Compose
- instala um service `patch-manager-central.service`

## Enderecos principais
- painel: `https://<host>`
- health simples: `https://<host>/health`
- health detalhado da API: `https://<host>/health/detailed`

## Credenciais iniciais
- usuario inicial: `admin`
- senha: exibida no final da instalacao
- no primeiro login, o admin deve trocar a senha

## Agentes
Depois da central subir:
- use o painel em `Configuracoes` para obter os comandos de instalacao dos agentes
- Linux e Windows suportam bootstrap token + aprovacao no console

## Persistencia
- banco e redis usam volumes Docker
- a central pode ser religada com:

```bash
sudo systemctl start patch-manager-central.service
```

## Atualizacao da central
No host:

```bash
cd /opt/patch-manager
git pull
docker compose -f infra/compose/docker-compose.yml up -d --build
```

## Rollback rapido
- restaurar codigo para o commit anterior
- subir novamente a stack
- se necessario, restaurar dump do banco com `deploy/central/restore-central.sh`
