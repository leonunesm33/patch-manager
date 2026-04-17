# Patch Manager Basic Compliance Notes

## LGPD e dados pessoais
- limitar cadastro de usuarios ao minimo necessario
- evitar incluir dados pessoais em nomes de host, grupos ou observacoes
- revisar retencao de logs antes de uso em ambiente real

## Segregacao de acesso
- usar perfis `admin`, `operator` e `viewer`
- compartilhar o menor privilegio necessario
- trocar segredos iniciais apos a instalacao

## Logs e retencao
- manter politica de retencao definida para:
  - logs do gateway
  - logs da API
  - eventos operacionais
  - historico de execucao

## Segredos
- JWT secret, bootstrap token e senhas devem ser gerados por instalacao
- nao versionar arquivos finais `api.env`, `.env` e certificados

## TLS
- a POC sobe com certificado self-signed
- para cliente real, substituir por certificado valido da organizacao

## Auditoria
- a plataforma registra eventos operacionais e historico por host
- para ambiente regulado, ampliar trilha de auditoria e tempo de retencao
