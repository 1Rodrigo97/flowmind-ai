# n8n — Automação Inteligente

Esta pasta contém a automação orientada a eventos do FlowMind AI, construída com
[n8n](https://n8n.io/). O n8n roda em contêiner (ver `docker-compose.yml`), com
volume próprio, sem depender de instalação global.

## Arquitetura

O n8n **não acessa o PostgreSQL diretamente**. Ele apenas chama a API do FlowMind,
que é a fronteira do sistema e é quem move arquivos e escreve no banco:

```
n8n (schedule)  ->  POST /api/automation/scan  ->  FastAPI  ->  services  ->  PostgreSQL
```

O backend varre a `automation/inbox`, ingere cada arquivo (dedupe por SHA-256), gera
os insights e move o arquivo para `processed/` ou `failed/`, registrando um
`automation_run`.

## Workflows

Exportados como JSON versionado em `workflows/`:

- **`flowmind-processar-inbox.json`** — Schedule Trigger (a cada 2 min) → HTTP Request
  `POST /api/automation/scan`. É a automação agendada principal.
- **`flowmind-processar-manual.json`** — Manual Trigger → mesma chamada com
  `?workflow=manual`, para demonstração sob demanda.

Ambos usam `retryOnFail` (3 tentativas) no nó HTTP.

## Autenticação

O token de serviço **não** fica no workflow exportado. Os nós leem variáveis de
ambiente do n8n:

- `FLOWMIND_API_URL` — base da API (no compose: `http://backend:8000`).
- `FLOWMIND_AUTOMATION_TOKEN` — token enviado como `Authorization: Bearer ...`.

Defina o token no `.env` da raiz (`FLOWMIND_AUTOMATION_TOKEN=...`); o compose o injeta
no backend e você o adiciona ao n8n (Settings → Variables, ou via env). Se o token
ficar vazio, a autenticação da automação fica desligada (modo dev local).

## Como usar

1. Suba a stack: `docker compose up -d` (inclui db, backend, frontend e n8n).
2. Abra o n8n em http://localhost:5678 e importe os arquivos de `workflows/`.
3. Ative o workflow **Processar Inbox** (ou dispare o **Manual**).
4. Copie um arquivo de `automation/samples/` para `automation/inbox/`.
5. Não clique em mais nada: em até 2 minutos o arquivo é indexado, analisado e movido
   para `automation/processed/`. Veja o resultado na aba **Automações** da interface.

Exemplo de resposta do `scan` em [`exemplos/scan-response.json`](exemplos/scan-response.json).
