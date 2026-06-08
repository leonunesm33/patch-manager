# Patch Manager POC Homologation Step-by-Step

Este roteiro descreve uma homologacao completa da aplicacao, incluindo instalacao/configuracao da central, instalacao dos agentes Linux e Windows, validacao do fluxo fim a fim e criterios objetivos para aceite.

Use este guia quando precisar demonstrar que o Patch Manager esta pronto para uma POC controlada ou quando outro agente de codigo precisar retomar o projeto a partir do GitHub.

## 1. Escopo da homologacao

Validar:

- central web/API/banco/Redis/gateway subindo de forma previsivel
- primeiro acesso e troca de senha do admin
- comandos de instalacao e upgrade dos agentes gerados pelo painel
- agentes Linux e Windows entrando na fila de aprovacao
- aprovacao, rejeicao, revogacao, reintegracao e agentes parados
- inventario de maquinas e updates pendentes
- aprovacao/rejeicao de patches
- agendamento por maquina, grupo e sistema operacional
- horarios separados para instalacao e reboot
- fila operacional, comandos de agente e relatorios
- backup, restore basico, logs e health checks

Fora do escopo do teste padrao:

- alta disponibilidade
- SSO corporativo
- assinatura digital do agente Windows
- apply real em larga escala
- reboot real sem aprovacao explicita do operador

## 2. Topologia recomendada

Ambiente minimo:

- 1 host Ubuntu/WSL para central
- 1 host Linux homologacao para agente Linux
- 1 host Windows homologacao para agente Windows

Ambiente local do projeto:

- repositorio Windows: `D:\Patch Manager`
- repositorio WSL/runtime: `~/patch-manager`
- painel: `https://localhost`
- API: `http://localhost:8000`

Para homologacao em rede, substitua `localhost` pelo DNS/IP da central.

## 3. Preparar o servidor central

### 3.1. Instalar via script de POC

No servidor Ubuntu:

```bash
git clone https://github.com/leonunesm33/patch-manager.git /tmp/patch-manager
cd /tmp/patch-manager
chmod +x deploy/central/install-central.sh
sudo ./deploy/central/install-central.sh
```

Resultado esperado:

- solucao copiada para `/opt/patch-manager`
- `patch-manager-central.service` instalado
- containers `gateway`, `web`, `api`, `db` e `redis` criados
- certificado self-signed gerado para a POC
- usuario admin inicial criado

### 3.2. Subir localmente sem instalador

Para validacao local no WSL:

```bash
cd ~/patch-manager
mkdir -p infra/env
cp -n infra/env/api.env.example infra/env/api.env
cd infra/compose
sudo docker compose up -d
```

Se Docker estiver instalado via snap:

```bash
cd ~/patch-manager/infra/compose
sudo /snap/bin/docker compose up -d
```

### 3.3. Validar saude da central

```bash
cd /opt/patch-manager/infra/compose
sudo docker compose ps
curl -k https://localhost/health
curl http://localhost:8000/health/detailed
```

Resultado esperado:

- todos os containers `healthy` ou `running`
- gateway responde `ok`
- API detalhada indica banco e servicos internos saudaveis

### 3.4. Primeiro acesso

1. abra `https://<central>`
2. entre com usuario `admin`
3. use a senha gerada pelo instalador ou definida em `infra/env/api.env`
4. troque a senha no primeiro login
5. confirme acesso aos menus Dashboard, Maquinas, Aprovacoes, Agendamentos, Operacoes, Relatorios, Configuracoes e Usuarios

## 4. Configuracao inicial da central

No menu `Configuracoes`:

1. confirme status de API e banco
2. valide se scheduler e worker estao ativos
3. confirme o modo Linux padrao, preferencialmente `dry-run`
4. confirme politicas Windows e Linux de scan/apply/reboot
5. gere ou confirme o bootstrap token
6. copie comandos de instalacao e upgrade dos agentes

Recomendacao para homologacao:

- manter apply real bloqueado ate validar inventario e agendamento
- manter reboot em simulacao ate aprovar teste real
- usar grupos de maquinas para separar `homologacao` e `producao`

## 5. Instalar e aprovar agente Linux

No host Linux homologacao:

```bash
curl -fsSL "https://<central>/api/v1/agents/install/linux.sh?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>" | sudo bash
```

Se a central local estiver em HTTP:

```bash
curl -fsSL "http://<central>:8000/api/v1/agents/install/linux.sh?server_url=http%3A%2F%2F<central>%3A8000&bootstrap_token=<token>" | sudo bash
```

Validar servico:

```bash
sudo systemctl status patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -n 80
sudo cat /etc/patch-manager/agent-linux.env
```

No painel:

1. abra `Operacoes` ou `Configuracoes`
2. valide que o agente aparece em `Agentes aguardando aprovacao`
3. aprove o agente
4. confirme que ele aparece como conectado
5. abra `Maquinas` e valide hostname, IP, SO, grupo, status e ultimo check-in

Resultado esperado:

- agente entra em pendentes
- apos aprovacao, passa para conectado
- maquina aparece no inventario
- updates pendentes aparecem como contador quando houver updates no host

## 6. Instalar e aprovar agente Windows

No host Windows homologacao, execute PowerShell como administrador:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://<central>/api/v1/agents/install/windows.ps1?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>' | iex"
```

Se a central local estiver em HTTP:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'http://<central>:8000/api/v1/agents/install/windows.ps1?server_url=http%3A%2F%2F<central>%3A8000&bootstrap_token=<token>' | iex"
```

Validar instalacao:

```powershell
Get-ScheduledTask -TaskName PatchManagerAgentWindows
Get-ScheduledTaskInfo -TaskName PatchManagerAgentWindows
Get-Content C:\ProgramData\PatchManager\agent-windows.env
dir C:\ProgramData\PatchManager\agent-windows
```

Validar execucao manual, se necessario:

```powershell
cd C:\ProgramData\PatchManager\agent-windows
powershell -ExecutionPolicy Bypass -File .\agent\run-agent.ps1
```

No painel:

1. confirme agente em `Agentes aguardando aprovacao`
2. aprove o agente
3. confirme agente conectado
4. abra `Maquinas` e valide inventario Windows
5. confirme se updates pendentes do Windows aparecem com nome amigavel quando disponivel

Resultado esperado:

- task `PatchManagerAgentWindows` registrada
- agente entra em pendentes
- apos aprovacao, maquina aparece no inventario
- updates pendentes aparecem na central quando detectados pelo agente

## 7. Validar lifecycle dos agentes

Para cada agente:

1. pare o servico/task e aguarde a janela de heartbeat expirar
2. confirme exibicao como agente parado
3. reinicie o servico/task
4. confirme retorno para conectado sem nova aprovacao
5. revogue o agente
6. confirme remocao de conectado e retorno para aprovacao quando o agente tentar reconectar
7. rejeite o agente
8. confirme que o processo para e nao fica gerando novas tentativas
9. use `Reabrir aprovacao` e valide retorno para a fila

Comandos uteis Linux:

```bash
sudo systemctl stop patch-manager-agent-linux.service
sudo systemctl start patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -n 120
```

Comandos uteis Windows:

```powershell
Stop-ScheduledTask -TaskName PatchManagerAgentWindows
Start-ScheduledTask -TaskName PatchManagerAgentWindows
Get-ScheduledTaskInfo -TaskName PatchManagerAgentWindows
```

## 8. Validar maquinas e grupos

No menu `Maquinas`:

1. confirme lista de hosts Linux e Windows
2. valide filtros
3. abra detalhes operacionais por host
4. valide patches pendentes, jobs, execucoes e comandos recentes
5. crie um grupo de maquinas pelo popup de grupos
6. associe hosts ao grupo quando aplicavel
7. clique no contador de patches pendentes e confirme abertura de `Aprovacoes` filtrado por maquina

Resultado esperado:

- lista sem rolagem horizontal indevida
- grupo aparece em agendamentos e filtros
- contador de patches direciona corretamente para aprovacao filtrada

## 9. Validar aprovacoes

No menu `Aprovacoes`:

1. abra filtros pelo botao `Filtros`
2. filtre por status, criticidade, categoria e plataforma
3. confirme area `Patches pendentes`
4. aprove um patch de teste
5. rejeite outro patch de teste, se disponivel
6. confirme area `Patches ja gerenciados`
7. edite um patch pelo menu de acoes e confirme popup central

Resultado esperado:

- patches pendentes e gerenciados ficam separados
- filtros aplicam e limpam corretamente
- coluna de maquinas afetadas mostra quantidade
- patch aprovado fica disponivel para agendamento/fila

## 10. Validar agendamentos

No menu `Agendamentos`:

1. crie uma janela por maquina
2. crie uma janela por grupo
3. crie uma janela por SO `Windows`
4. crie uma janela por SO `Linux`
5. defina horario de instalacao futuro
6. defina horario de reboot diferente do horario de instalacao
7. teste frequencia `unica`
8. teste frequencia `diaria`, `semanal` ou `mensal` em uma janela segura
9. edite uma janela existente
10. confirme que a lista reflete escopo, frequencia, instalacao e reboot

Resultado esperado:

- scheduler gera jobs ou comandos apenas quando a janela e atingida
- reboot respeita politica configurada
- comando aparece em `Operacoes` e resultado aparece em `Relatorios`

Importante:

- aguarde pelo menos um intervalo do scheduler apos o horario configurado
- use sempre um horario futuro novo durante testes repetidos
- horarios ja processados podem ser ignorados por deduplicacao

## 11. Validar reboot com seguranca

Antes de qualquer reboot real, valide simulacao.

Windows:

```env
PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=true
PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=true
```

Linux:

```env
PATCH_MANAGER_ENABLE_HOST_REBOOT=true
PATCH_MANAGER_SIMULATE_HOST_REBOOT=true
```

Depois reinicie agente/task e crie um agendamento de reboot futuro.

Resultado esperado em simulacao:

- comando de reboot e enfileirado
- agente consome o comando
- relatorio indica sucesso simulado
- host nao reinicia

Para reboot real:

1. use apenas host de homologacao
2. confirme janela com o operador
3. desative simulacao
4. reinicie o agente
5. agende horario futuro
6. acompanhe logs ate o reboot

## 12. Validar Operacoes

No menu `Operacoes`:

1. confirme indicadores operacionais
2. use `Gerar jobs agora`
3. confirme retorno visual de sucesso ou erro
4. use `Executar proximo ciclo`
5. acompanhe fila de jobs
6. valide agentes aguardando aprovacao, conectados, rejeitados, revogados e parados
7. teste acoes em lote somente quando houver itens selecionaveis

Resultado esperado:

- todos os botoes retornam mensagem
- jobs aparecem como pending/running/completed/failed
- comandos de agente aparecem com status
- falhas ficam visiveis para diagnostico

## 13. Validar Relatorios

No menu `Relatorios`:

1. confirme historico de jobs
2. confirme execucoes recentes
3. confirme falhas e guardrails
4. exporte CSV
5. exporte JSON
6. exporte HTML
7. exporte PDF via impressao do navegador
8. exporte Excel-compativel

Resultado esperado:

- exportacoes baixam/abrem sem erro
- dados exportados batem com a tela
- acoes de fila nao aparecem em Relatorios; ficam em Operacoes

Observacao:

- exportacao Excel atual e compatibilidade via HTML/XLS, nao `.xlsx` nativo
- PDF atual depende da janela de impressao do browser

## 14. Validar usuarios e seguranca minima

No menu `Usuarios`:

1. altere nome do usuario logado
2. altere senha
3. ajuste avatar/iniciais quando aplicavel
4. com usuario admin, crie usuario com perfil `user`
5. valide que apenas admin gerencia usuarios/perfis
6. faca logout pelo perfil no canto inferior esquerdo
7. faca login novamente

Resultado esperado:

- senha alterada passa a valer imediatamente
- usuario comum nao altera configuracoes administrativas sensiveis
- primeiro acesso exige troca de senha quando configurado

## 15. Validar persistencia e recuperacao

Central:

```bash
cd /opt/patch-manager/infra/compose
sudo docker compose restart
sudo docker compose ps
curl -k https://localhost/health
```

Service:

```bash
sudo systemctl restart patch-manager-central.service
sudo systemctl status patch-manager-central.service
```

Backup:

```bash
cd /opt/patch-manager
chmod +x deploy/central/backup-central.sh
deploy/central/backup-central.sh
```

Restore em ambiente controlado:

```bash
cd /opt/patch-manager
chmod +x deploy/central/restore-central.sh
deploy/central/restore-central.sh /opt/patch-manager/backups/<arquivo>.sql
```

Resultado esperado:

- dados preservados apos restart
- agentes reconectam sem reenrollment indevido
- backup gera arquivo SQL
- restore funciona em ambiente de teste

## 16. Evidencias da homologacao

Colete:

- URL e versao/commit testado
- print do health da central
- print de agentes pendentes/conectados
- print do inventario de maquinas
- print de patches aprovados/rejeitados
- print de agendamentos criados
- print de operacoes/jobs/comandos
- print de relatorios/exportacoes
- logs relevantes de API e agentes
- resultado de backup/smoke test

## 17. Criterios de aceite

A POC pode ser considerada homologada quando:

- central sobe e fica saudavel
- login e troca de senha funcionam
- agente Linux instala, aparece pendente, e pode ser aprovado
- agente Windows instala, aparece pendente, e pode ser aprovado
- agentes reportam heartbeat e inventario
- maquinas aparecem com status e updates pendentes
- patches podem ser aprovados/rejeitados
- agendamentos por maquina, grupo e SO funcionam
- jobs ou comandos sao gerados na janela correta
- reboot simulado funciona sem reiniciar host
- relatorios mostram jobs, execucoes e falhas
- exportacoes principais funcionam
- backup basico e logs estao disponiveis

## 18. Troubleshooting rapido

Portal nao abre:

```bash
cd /opt/patch-manager/infra/compose
sudo docker compose ps
sudo docker compose logs --tail=120 gateway
```

API com erro:

```bash
sudo docker compose logs --tail=160 api
curl http://localhost:8000/health/detailed
```

Banco indisponivel:

```bash
sudo docker compose logs --tail=120 db
sudo docker compose exec api alembic upgrade head
```

Agente Linux:

```bash
sudo systemctl status patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -n 120
```

Agente Windows:

```powershell
Get-ScheduledTaskInfo -TaskName PatchManagerAgentWindows
Get-Content C:\ProgramData\PatchManager\agent-windows.env
cd C:\ProgramData\PatchManager\agent-windows
powershell -ExecutionPolicy Bypass -File .\agent\run-agent.ps1
```

Agendamento nao executou:

- confirme horario local da central e do host
- aguarde intervalo do scheduler
- use horario futuro novo
- confira logs da API
- confira comandos em `Operacoes`
- confira logs do agente

## 19. Proximos passos apos homologacao

- implementar `.xlsx` nativo e PDF server-side
- ampliar testes automatizados de scheduler/reboot
- reforcar RBAC por recurso
- assinar pacote do agente Windows
- homologar apply real Linux em host descartavel
- homologar instalacao Windows em VM dedicada
- configurar TLS corporativo
- testar backup/restore em rotina recorrente
