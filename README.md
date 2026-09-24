# FlowMind AI

**Assistente Pessoal de Conhecimento & Automação** com Geração Aumentada por
Recuperação (RAG) e modelos de linguagem locais.

O FlowMind AI permite enviar seus próprios documentos, indexá-los automaticamente e
fazer perguntas respondidas **somente** a partir do seu material — mostrando
exatamente **quais fontes e trechos** foram usados em cada resposta. Se a base de
conhecimento não contém a resposta, o FlowMind declara isso em vez de inventar.

Tudo roda localmente: um LLM local via **Ollama**, embeddings locais e
**PostgreSQL + pgvector** para a busca vetorial. Nenhum dado sai da sua máquina.

![Painel do FlowMind AI](docs/screenshots/painel.png)

---

## Por que este projeto existe?

Este é um projeto pessoal de **Engenharia de IA**, criado para demonstrar, ponta a
ponta, os fundamentos de um sistema de RAG de produção:

- **RAG** (Retrieval-Augmented Generation) fundamentado em fontes;
- **Embeddings** e representação semântica de texto;
- **Busca vetorial** com pgvector (similaridade de cosseno);
- **Grounding** — o modelo responde apenas pelo contexto recuperado e recusa quando
  não há evidência suficiente, em vez de alucinar;
- **Avaliação** objetiva de recuperação e comportamento (Hit@K, recusas, latência);
- **LLM local** rodando offline via Ollama;
- **Arquitetura desacoplada** — LLM e embeddings atrás de interfaces, permitindo
  trocar de provedor (vLLM, OpenAI-compatible) sem reescrever o RAG.

O objetivo é mostrar não só "um chatbot", mas o entendimento de **como a recuperação
funciona** — por isso existe a tela **Explorador RAG**, que expõe os trechos e scores
sem passar pelo LLM.

---

## Demonstração

Fluxo completo: envie documentos, veja-os indexados, explore a recuperação e
converse com a sua base recebendo as fontes exatas.

| Painel | Documentos |
| :---: | :---: |
| <img src="docs/screenshots/painel.png" width="420" alt="Painel" /> | <img src="docs/screenshots/documentos.png" width="420" alt="Documentos" /> |
| **Assistente (resposta + fontes)** | **Explorador RAG (trechos + scores)** |
| <img src="docs/screenshots/assistente.png" width="420" alt="Assistente" /> | <img src="docs/screenshots/explorador-rag.png" width="420" alt="Explorador RAG" /> |

- **Painel** — quantidade de documentos, trechos, tipos de arquivo e documentos recentes.
- **Documentos** — upload por arrastar & soltar, lista, status e exclusão.
- **Assistente** — resposta fundamentada com cartões de fonte expansíveis
  (documento · seção · página · score).
- **Explorador RAG** — recuperação pura: os trechos mais próximos e seus scores de
  similaridade, **sem geração do LLM**.

---

## Como o RAG funciona aqui

```
documentos → chunks → embeddings → pgvector → retrieval → LLM → resposta com fontes
```

Cada trecho armazenado guarda os metadados necessários para a citação: `document_id`,
`filename`, `file_type`, `chunk_index`, `section`, `page`, `content`, `embedding` e
`created_at`.

**Grounding.** O prompt de sistema instrui o modelo a responder apenas com o contexto
recuperado e a devolver `INSUFFICIENT_CONTEXT` quando não conseguir. Antes mesmo de
chamar o LLM, os trechos recuperados são filtrados por um limiar de similaridade
configurável (`SIMILARITY_THRESHOLD`); se nenhum passar, a aplicação encurta o fluxo e
retorna a resposta de "informação insuficiente" sem pedir ao modelo para preencher a
lacuna.

---

## Métricas atuais

Medidas nesta versão, com os documentos de exemplo indexados:

| Métrica | Valor |
| --- | --- |
| Testes do backend | **48/48** ✅ |
| Hit@5 (fonte esperada recuperada) | **100%** |
| Recusa correta em contexto insuficiente | **100%** |
| Latência média por pergunta (chat) | **~3,6 s** |

Resultados detalhados de recuperação (baseline vs reranking) estão na seção
[Laboratório de Avaliação RAG](#laboratório-de-avaliação-rag).

---

## Laboratório de Avaliação RAG

O FlowMind não é só um chatbot: é uma **bancada de avaliação e otimização de RAG**.
Você define uma configuração (chunk size, overlap, top_k, limiar, reranking),
executa um experimento reproduzível sobre um dataset e mede objetivamente **qual
configuração recupera melhor** — sem números inventados, tudo calculado a partir do
dataset esperado.

### Por que avaliar RAG?

"Parece que responde bem" não é medida. Sem métricas você não sabe se um chunk maior
ajuda, se aumentar o `top_k` melhora a cobertura, ou se o reranking realmente reordena
para melhor. A avaliação transforma intuição em número comparável e reproduzível.

### Retrieval vs reranking

A **recuperação vetorial** (pgvector) ordena os candidatos por similaridade de cosseno
do embedding. O **reranking** re-pontua os `N` melhores candidatos com um sinal
independente do embedding e devolve os `K` finais — útil quando a similaridade vetorial
sozinha coloca o trecho certo em segundo lugar.

```mermaid
flowchart LR
    Q[Query] --> VR[Vector Retrieval<br/>pgvector]
    VR --> N[Top N candidatos]
    N --> RR[Reranker]
    RR --> K[Top K]
    K --> LLM[LLM]
```

### Métricas (definições)

Métricas de **recuperação** (nível de trecho, relevância pelo nome do documento):

| Métrica | Definição |
| --- | --- |
| **Hit@K** | 1 se algum dos K trechos recuperados pertence a um documento esperado. |
| **MRR** | Recíproco da posição do primeiro trecho relevante (0 se nenhum). Média = Mean Reciprocal Rank. |
| **Precision@K** | Fração dos K trechos recuperados que pertencem a documentos esperados. |
| **Recall@K** | Fração dos documentos esperados distintos que foram recuperados. |

Métricas de **resposta / comportamento**: `answer_rate`, `correct_refusal_rate`
(recusa correta em perguntas sem resposta na base), `expected_terms_match`
(groundedness determinístico sobre a evidência recuperada) e latências
(`latency_retrieval_ms`, `latency_llm_ms`). Groundedness por LLM-as-a-judge fica como
extensão opcional, separada das métricas determinísticas.

### Baseline vs experimento — resultados reais

Dois experimentos sobre o mesmo perfil de índice (`nomic-embed-text`, chunk 700/100,
top_k 5), no dataset sintético de 8 casos (6 positivos + 2 negativos):

| Métrica | A · baseline (sem reranking) | B · com reranking (lexical) |
| --- | --- | --- |
| Hit@5 | **100%** | **100%** |
| MRR | **1,00** | **1,00** |
| Precision@5 | 0,29 | 0,29 |
| Recall@5 | **100%** | **100%** |
| Recusa correta | **100%** | **100%** |
| Latência de retrieval | ~211 ms | ~216 ms |

**Leitura honesta:** neste corpus pequeno e limpo o baseline já **satura** as métricas
de recuperação (MRR 1,00 — o primeiro trecho recuperado já é sempre do documento certo),
então o reranking **não traz ganho mensurável** e adiciona uma latência pequena. O
reranking ainda assim **reordena** os candidatos — visível no Explorador RAG — e é em
corpora maiores e mais ruidosos que ele tende a ajudar. O laboratório existe justamente
para medir isso em vez de assumir.

![Laboratório de Avaliação RAG](docs/screenshots/laboratorio-rag.png)

### Explorador RAG com reranking

Com o reranking ligado, o Explorador mostra lado a lado a ordem **original** (por
similaridade) e a ordem **após reranking** (com o score `rr` do reranker), tornando o
reordenamento explícito:

![Explorador RAG com reranking](docs/screenshots/explorador-reranking.png)

### Reprodutibilidade

Cada experimento persiste no PostgreSQL a configuração completa, o perfil de índice, o
dataset, o SHA do commit, a data/hora, a duração e as métricas — para que qualquer
resultado possa ser reproduzido.

### API de avaliação

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET`  | `/api/evaluation/experiments`        | Lista experimentos |
| `POST` | `/api/evaluation/run`                | Executa um experimento e persiste as métricas |
| `GET`  | `/api/evaluation/experiments/{id}`   | Detalhe de um experimento (config + por pergunta) |
| `POST` | `/api/evaluation/compare`            | Compara 2+ experimentos com deltas |

Também há o harness de linha de comando em `evaluation/evaluate.py` (ver
[Avaliação](#avaliação)).

---

## Automação Inteligente

Além do upload manual, o FlowMind processa arquivos **automaticamente**: você
coloca um documento em `automation/inbox/` e não clica em mais nada. Um workflow do
**n8n** dispara a API, que indexa o arquivo, gera insights com IA e move o arquivo
para `processed/` (ou `failed/`), registrando cada execução.

```mermaid
flowchart TD
    A[Arquivo em automation/inbox] --> B[n8n · Schedule Trigger]
    B --> C[POST /api/automation/scan · Bearer token]
    C --> D[FlowMind API]
    D --> E[Ingestão · dedupe SHA-256]
    E --> F[RAG · chunks + embeddings + pgvector]
    E --> G[Document Insights · LLM grounded]
    F --> H[(PostgreSQL)]
    G --> H
    D --> I[Move para processed/ ou failed/]
    H --> J[Dashboard e aba Automações]
```

### A fronteira é a API

O n8n **não acessa o PostgreSQL**. Ele só chama a API do FlowMind, que é quem move
arquivos e escreve no banco (`n8n → FastAPI → services → PostgreSQL`). Os endpoints de
automação são protegidos por um **service token** (`Authorization: Bearer ...`), que
fica em uma variável do n8n — nunca no workflow exportado.

### Document Insights (fundamentado)

Depois de indexado, o documento é analisado pelo LLM local, que retorna **apenas com
base no conteúdo**: `summary`, `category`, `tags`, `tasks` (`{text, due_date}`) e
`dates`. Nada é inventado — se não há tarefas, `tasks = []`; se não há datas,
`dates = []`. Os três documentos de exemplo em `automation/samples/` demonstram isso:
a **reunião** e o **planejamento** geram tarefas e datas reais, enquanto o **artigo
técnico** não recebe nenhuma tarefa inventada.

### Idempotência, retries e fallback

- **Idempotência** — dedupe pelo SHA-256 já usado na ingestão; reenviar o mesmo
  conteúdo resulta em `status = DUPLICATE`, sem recriar o documento.
- **Retries** — falha de ingestão mantém o arquivo na inbox e tenta de novo nos
  próximos ticks até `AUTOMATION_MAX_ATTEMPTS`; só então vai para `failed/`.
- **Fallback** — a ingestão e os insights são separados (`INGESTION_SUCCESS` ≠
  `INSIGHTS_SUCCESS`): se o LLM falhar ao gerar insights, o documento **continua
  indexado e disponível no Assistente**, e os insights ficam `FAILED` para retry
  manual. Nada é perdido; arquivos só são movidos após um resultado conhecido.

![Aba Automações](docs/screenshots/automacoes.png)

### Rodando a automação

Com a stack no ar (`docker compose up -d`, que inclui o n8n em http://localhost:5678):

1. Importe os workflows de [`n8n/workflows/`](n8n/workflows/) no n8n.
2. Ative **FlowMind · Processar Inbox** (Schedule) — ou dispare o **Manual**.
3. Copie um arquivo de `automation/samples/` para `automation/inbox/`.
4. Em até 2 minutos ele é indexado, analisado e movido para `processed/`. Acompanhe na
   aba **Automações**.

Detalhes e endpoints em [`n8n/README.md`](n8n/README.md).

---

## Funcionalidades

- **Ingestão de documentos** — arrastar & soltar PDF, DOCX, MD e TXT; extração,
  chunking, embedding e indexação automáticos.
- **Chat RAG fundamentado** — respostas restritas ao contexto recuperado, com citações
  de fonte expansíveis (documento · seção · página · score).
- **Explorador RAG** — inspeciona a recuperação pura (top-k trechos e scores) sem
  geração do LLM, e mostra o reordenamento quando o reranking está ligado.
- **Laboratório de Avaliação RAG** — executa experimentos reproduzíveis, mede Hit@K,
  MRR, Precision@K, Recall@K e latência, e compara configurações lado a lado.
- **Reranking** — reordenação dos candidatos por um reranker local (BM25 lexical),
  atrás de uma abstração `RerankerProvider`, com feature flag desligada por padrão.
- **Perfis de índice** — cada chunk é marcado com o perfil (modelo + chunk size/overlap)
  para nunca misturar embeddings incompatíveis na mesma recuperação.
- **Automação com n8n** — inbox automation orientada a eventos: detecta o arquivo,
  indexa, gera insights (resumo, categoria, tags, tarefas, datas) e move para
  processed/failed, com idempotência, retries e observabilidade.
- **Não alucina** — quando nenhum trecho passa do limiar, o LLM nunca é solicitado a
  inventar; a aplicação retorna "informação insuficiente".
- **Deduplicação** — uploads idênticos são detectados por hash de conteúdo e ignorados.
- **Provedores plugáveis** — LLM e embeddings atrás de interfaces, permitindo adicionar
  vLLM ou backends OpenAI-compatible sem tocar no código de RAG.
- **Harness de avaliação** — Hit@K, cobertura de termos esperados, precisão de recusa e
  latência sobre um dataset pequeno.
- **Observabilidade** — uma linha de log JSON por request com tempos de retrieval e LLM,
  contagem de trechos e o modelo usado.

---

## Stack tecnológica

| Camada        | Tecnologia                          |
| ------------- | ----------------------------------- |
| Backend       | Python 3.11, FastAPI, SQLAlchemy 2  |
| Banco vetorial| PostgreSQL 16 + pgvector            |
| LLM           | Ollama (`llama3.2:3b` por padrão)   |
| Embeddings    | Ollama (`nomic-embed-text`, 768-d)  |
| Frontend      | Vue 3, TypeScript, Vite, Vue Router |
| Contêineres   | Docker Compose                      |

### Por que estes embeddings?

A V1 usa **`nomic-embed-text` servido pelo Ollama**. Isso mantém um único runtime local
(sem dependência de PyTorch/`sentence-transformers`), produz vetores estáveis de 768
dimensões, roda totalmente offline e gratuito, e combina naturalmente com o LLM do
Ollama. O backend de embeddings é intercambiável atrás de `EmbeddingProvider`.

---

## Arquitetura

```
flowmind-ai/
├── backend/            App FastAPI
│   └── app/
│       ├── api/          rotas HTTP (documents, search, chat, stats, evaluation, automation)
│       ├── core/         config, database, logging
│       ├── ingestion/    extração (PDF/DOCX/MD/TXT) + chunking
│       ├── embeddings/   EmbeddingProvider + implementação Ollama
│       ├── llm/          LLMProvider + implementação Ollama
│       ├── rag/          pipeline de retrieval + chat + rag/reranker/ (RerankerProvider)
│       ├── evaluation/   métricas, perfis de índice e runner de experimentos (V2)
│       ├── models/       modelos ORM + schemas Pydantic
│       └── services/     ingestão, insights e automação (inbox)
├── frontend/           SPA Vue 3 + TS (Painel, Documentos, Assistente, Explorador RAG, Laboratório RAG, Automações, Configurações)
├── automation/         inbox/ processed/ failed/ samples/ (pastas da automação)
├── n8n/                docker + workflows JSON versionados
├── sample_documents/   documentos sintéticos para testar perguntas cruzadas
├── evaluation/         dataset.json + evaluate.py
├── fine_tuning/        fine-tuning V5 (placeholder)
└── docker-compose.yml
```

```mermaid
flowchart LR
    subgraph Ingestao
        U[Upload] --> V[Validar + hash]
        V --> X[Extrair texto]
        X --> C[Chunking + metadados]
        C --> E1[Embeddings]
        E1 --> DB[(pgvector)]
    end
    subgraph Consulta
        Q[Pergunta] --> E2[Embedding da query]
        E2 --> R[Recuperar top-k]
        R --> DB
        R --> T{Score >= limiar?}
        T -- nao --> I[INSUFFICIENT_CONTEXT]
        T -- sim --> P[Prompt fundamentado]
        P --> L[LLM via Ollama]
        L --> A[Resposta + fontes]
    end
```

---

## Executando localmente

### Pré-requisitos

- [Docker](https://www.docker.com/) + Docker Compose
- [Ollama](https://ollama.com/) rodando no host
- Python 3.11+ e Node 20+ (apenas se rodar backend/frontend fora do Docker)

### 1. Baixe os modelos

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 2. Configure

```bash
cp .env.example .env
```

Os padrões funcionam de imediato em um ambiente local.

### 3a. Tudo no Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:5180
- API + docs: http://localhost:8000/docs

O backend acessa o Ollama do host via `host.docker.internal`.

### 3b. Ou rode os serviços diretamente (desenvolvimento)

Suba apenas o Postgres no Docker:

```bash
docker compose up -d db
```

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Unix: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5180
```

> Dica: se a porta 8000 já estiver em uso na sua máquina, rode o backend em outra
> porta (ex.: `--port 8010`) e crie `frontend/.env.local` com
> `VITE_API_BASE_URL=http://localhost:8010` (esse arquivo é ignorado pelo git).

### 4. Experimente

1. Abra **Documentos** e envie os arquivos de `sample_documents/`.
2. Abra **Explorador RAG** e busque — veja os trechos ranqueados e os scores.
3. Abra **Assistente** e pergunte _"Qual é a diferença entre RAG e fine-tuning?"_
4. Pergunte algo que não esteja nos documentos e veja o sistema recusar em vez de
   adivinhar.

---

## Configuração

Todas as configurações vêm de variáveis de ambiente (veja `.env.example`):

| Variável               | Padrão             | Descrição                                     |
| ---------------------- | ------------------ | --------------------------------------------- |
| `DATABASE_URL`         | Postgres local     | String de conexão do SQLAlchemy               |
| `LLM_PROVIDER`         | `ollama`           | Seletor do backend de LLM                     |
| `OLLAMA_BASE_URL`      | `localhost:11434`  | Endpoint do Ollama                            |
| `OLLAMA_MODEL`         | `llama3.2:3b`      | Modelo de chat                                |
| `LLM_NUM_CTX`          | `4096`             | Janela de contexto (limita memória local)     |
| `EMBEDDING_PROVIDER`   | `ollama`           | Seletor do backend de embeddings              |
| `EMBEDDING_MODEL`      | `nomic-embed-text` | Modelo de embeddings                          |
| `EMBEDDING_DIM`        | `768`              | Dimensão do vetor de embedding                |
| `RETRIEVAL_TOP_K`      | `5`                | Trechos recuperados por padrão                |
| `SIMILARITY_THRESHOLD` | `0.55`             | Similaridade mínima para confiar num trecho   |
| `RERANKER_ENABLED`     | `false`            | Liga o reranking no pipeline (flag global)    |
| `RERANKER_MODEL`       | `lexical`          | Reranker (BM25 lexical local)                 |
| `RERANKER_CANDIDATES`  | `15`               | Candidatos N recuperados antes do reranking   |
| `RERANKER_TOP_K`       | `5`                | K final após reranking                        |
| `FLOWMIND_AUTOMATION_TOKEN` | _(vazio)_     | Service token da automação (vazio = auth off) |
| `AUTOMATION_INBOX_DIR` | `automation/inbox` | Pasta monitorada (arquivos novos)            |
| `AUTOMATION_MAX_ATTEMPTS` | `3`             | Tentativas antes de mover para `failed/`      |
| `MAX_UPLOAD_MB`        | `25`               | Tamanho máximo de upload                      |
| `ALLOWED_EXTENSIONS`   | `pdf,docx,md,txt`  | Whitelist de upload                           |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `900` / `150` | Janela / sobreposição do chunking (palavras) |

---

## API

| Método   | Endpoint                  | Descrição                                    |
| -------- | ------------------------- | -------------------------------------------- |
| `POST`   | `/api/documents/upload`   | Envia & indexa um documento (multipart `file`) |
| `GET`    | `/api/documents`          | Lista os documentos indexados                |
| `GET`    | `/api/documents/{id}`     | Retorna um documento                         |
| `DELETE` | `/api/documents/{id}`     | Exclui um documento e seus trechos           |
| `POST`   | `/api/search`             | Recuperação semântica (sem LLM)              |
| `POST`   | `/api/chat`               | Resposta RAG fundamentada com fontes         |
| `GET`    | `/api/stats`              | Estatísticas do painel                       |
| `GET`    | `/api/health`             | Health check                                 |
| `POST`   | `/api/documents/{id}/insights` | Gera (ou retorna) os insights do documento |
| `GET`    | `/api/documents/{id}/insights` | Insights persistidos                    |
| `POST`   | `/api/automation/scan`    | Varre a inbox e processa (token) — chamado pelo n8n |
| `GET`    | `/api/automation/runs`    | Lista as execuções de automação              |
| `GET`    | `/api/automation/stats`   | Métricas da automação                        |
| `POST`   | `/api/automation/runs/{id}/retry` | Retry manual idempotente (token)     |

Documentação interativa em `/docs`.

**Search** — `{ "query": "...", "top_k": 5 }` → trechos ranqueados com score,
documento, seção/página e conteúdo.

**Chat** — `{ "question": "...", "top_k": 5 }` →
`{ "answer": "...", "sources": [...], "status": "answered" | "insufficient_context" }`.

---

## Avaliação

Com o backend no ar e os documentos de exemplo indexados:

```bash
python evaluation/evaluate.py --api http://localhost:8000 --top-k 5
```

Relata **Hit@K** (a fonte esperada foi recuperada), **cobertura de termos esperados**,
**precisão de contexto insuficiente** (recusas corretas em perguntas sem resposta) e
**latência média**. Edite `evaluation/dataset.json` para adicionar casos.

---

## Testes

```bash
cd backend
pytest
```

Os testes unitários puros (extração, chunking, tratamento de erro dos provedores) rodam
em qualquer lugar. Os testes de integração que precisam de Postgres + Ollama são pulados
automaticamente quando a stack não está disponível.

Build / checagem de tipos do frontend:

```bash
cd frontend
npm run build
```

---

## Roadmap

| Versão  | Foco                                              | Status |
| ------- | ------------------------------------------------- | ------ |
| **V1**  | RAG + Ollama + pgvector                           | ✅ entregue |
| **Lab** | Laboratório de Avaliação RAG + reranking          | ✅ entregue |
| **Automação** | Inbox automation com n8n + Document Insights | ✅ entregue |
| V3      | Melhorias de avaliação / reranking (cross-encoder)| planejado |
| V4      | Servidor de inferência vLLM                       | próximo pilar |
| V5      | Curadoria de dataset + fine-tuning                | planejado |
| V6      | Agents / tools                                    | planejado |

---

## Licença

[MIT](LICENSE)
