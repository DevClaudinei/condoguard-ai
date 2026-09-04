# 🏢 CondoGuard AI — Triagem Inteligente e Gestão de Chamados Condominiais

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Angular](https://img.shields.io/badge/Angular-16%2B-DD0031.svg?style=flat&logo=angular&logoColor=white)](https://angular.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#licença)

---

## 📌 1. Visão Geral e Contexto do Projeto

O **CondoGuard AI** é uma solução *full-stack* desenvolvida como **Projeto de Extensão Universitária (PEX)** para sanar um gargalo crítico em condomínios residenciais de médio e grande porte: a sobrecarga e a ausência de triagem imediata de demandas direcionadas ao corpo diretivo (síndico e subsíndico).

Em condomínios compostos por múltiplas torres, ocorrências emergenciais que ameaçam a integridade predial ou a segurança física dos moradores (ex.: rompimento de tubulações hidráulicas, vazamento de gás, curto-circuitos e pessoas presas em elevadores) costumam concorrer na mesma fila que solicitações rotineiras (dúvidas de boletos, reservas de salão de festas ou barulho).

A plataforma implementa um pipeline de **Processamento de Linguagem Natural (PLN)** baseado em **embeddings semânticos e busca vetorial**, associado a um mecanismo de salvaguarda (*guardrails* determinísticos). O sistema classifica instantaneamente a gravidade do relato em baldes de prioridade e aciona canais de mensageria ativa (WhatsApp/Webhook) de prontidão nos casos mais graves.

---

## 🏛️ 2. Arquitetura da Solução

```text
               ┌───────────────────────────────┐
               │    Morador / Interface Web    │
               │       (Angular Client)        │
               └──────────────┬────────────────┘
                              │ HTTP POST (Payload)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Engine                    │
│                                                              │
│  1. Ingestão & Validação de Contrato (Pydantic DTOs)         │
│  2. Vetorização Semântica (Sentence-Transformers MiniLM)     │
│  3. Roteamento Semântico (Cosine Similarity vs. Centroides)  │
│  4. Guardrails Determinísticos (Palavras-chave de pânico)    │
│  5. Background Task: Disparo Imediato (WhatsApp/Webhook)     │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
               │ Armazenamento Relacional      │ Notificação Assíncrona
               │ & Vetores de Embedding        │
               ▼                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│  PostgreSQL 16 + pgvector    │ │ Webhook Notifier / WhatsApp  │
│      (Docker Container)      │ │   (Síndico & Subsíndico)     │
└──────────────────────────────┘ └──────────────────────────────┘
               │
               │ Consulta de Dados (HTTP GET)
               ▼
┌───────────────────────────────┐
│       Painel do Síndico       │
│  (Dashboard, KPIs e Filtros)  │
└───────────────────────────────┘
```

### Topologia de Produção (AWS · IaC com CDK)

```text
 CloudFront + OAC ──► S3 (SPA Angular)          [distribuição global do frontend]
 Application Load Balancer ──► ECS Fargate (FastAPI + MiniLM, Auto Scaling)
        │                              │ publish
        │ RDS Proxy/SG                 ▼
        ▼                          SNS ──► SQS (+DLQ, alarme CW) ──► Lambda ──► WhatsApp/Twilio
 RDS PostgreSQL 16 + pgvector (isolado, Multi-AZ em prod)
 Segredos: AWS Secrets Manager · Deploy: GitHub Actions (OIDC, sem chaves)
```

> Perfil **dev** econômico: Fargate em subnet pública (egress via IGW, **0 NAT**),
> RDS single-AZ — reduz o custo em ambiente de estudo. **prod** ativa VPC isolada,
> NAT, Multi-AZ e ≥2 tasks. Detalhes em [`infra/README.md`](infra/README.md).

---

## ⚡ 3. Classificação Semântica por Baldes (Few-Shot Semantic Router)

A categorização divide os chamados em três classes operacionais de urgência:

| Nível de Urgência | Descrição Operacional | Critérios de Disparo | Ação do Sistema |
| :--- | :--- | :--- | :--- |
| **P1_CRITICO** | Risco iminente à integridade física, patrimonial ou interrupção de serviço essencial. | Vazamentos graves, cheiro de gás, pessoas presas em elevador, portão principal quebrado aberto, faíscas elétricas. | Gravação no banco + **Disparo imediato de alerta aos gestores via WhatsApp**. |
| **P2_URGENTE** | Falhas estruturais parciais ou perturbação de média gravidade que exigem ação no mesmo dia. | Falhas no interfone de torre, iluminação de rota de emergência apagada, perturbação sonora após horário de silêncio. | Gravação com destaque amarelo no Dashboard para triagem prioritária no mesmo dia. |
| **P3_ROTINA** | Demandas administrativas, agendamentos, dúvidas de rateio ou solicitações gerais. | Reserva de quiosque/salão, emissão de segunda via de boleto, agendamento de mudança. | Inserção na fila regular de atendimento do condomínio. |

### Mecanismo Híbrido e Deduplicação Inteligente:
1. **Representação Vetorial (inferência única):** O texto concatenado (`titulo + descricao`) é vetorizado **uma só vez** (384 dimensões, `all-MiniLM-L6-v2`, embeddings normalizados) e o vetor resultante é reutilizado tanto na classificação quanto na deduplicação e na persistência — sem chamadas redundantes ao modelo.
2. **Deduplicação Semântica via pgvector + HNSW:** Antes de renotificar, o sistema consulta os registros recentes dentro de uma **janela e um limiar de cosseno configuráveis** (defaults: 4h e `< 0.35`), acelerada por um índice **HNSW** (`vector_cosine_ops`) mais um B-Tree composto `(urgencia, created_at)`. Ocorrências correlatas viram `🔗 Ocorrência Agrupada`, ligadas ao `parent_id` raiz, com a notificação suprimida para evitar spam ao corpo diretivo.
3. **Guardrails Determinísticos:** Gatilhos críticos (*alagamento*, *vazamento*, *cano*, *fogo*, *gás*, *preso*…) — comparados com **normalização de acentos e por fronteira de palavra** — garantem elevação imediata para `P1_CRITICO`, evitando falsos negativos (e falsos positivos como *"represado"*).

---

## 💻 4. Stack Tecnológica

### Backend & Inteligência Artificial
* **Linguagem:** Python 3.11+
* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com) · **Servidor ASGI:** [Uvicorn](https://www.uvicorn.org)
* **Validação de Dados:** [Pydantic v2](https://docs.pydantic.dev) & Pydantic-Settings
* **ORM & Banco:** [SQLAlchemy](https://www.sqlalchemy.org) com driver `psycopg2-binary`
* **Embeddings & Similaridade:** [sentence-transformers](https://www.sbert.net) (`all-MiniLM-L6-v2`) — similaridade por produto interno (NumPy)
* **Arquitetura em camadas (Clean Architecture):** endpoint fino → **`TriagemService`** (regra de negócio) → **`ChamadoRepository`** (acesso a dados). O serviço depende de um **`Protocol`** de classificador, o que permite **testes unitários com mocks sem carregar o modelo de IA**.
* **Autenticação & Proteção:** JWT ([PyJWT](https://pyjwt.readthedocs.io), HS256, pronto para migrar a Cognito/JWKS) e **rate-limiting** por IP ([slowapi](https://github.com/laurentS/slowapi)).
* **Mensageria (AWS SDK):** [boto3](https://boto3.amazonaws.com) publicando alertas P1 em SNS (com fallback local em log).

### Banco de Dados & Infraestrutura
* **Banco Relacional com Busca Vetorial:** PostgreSQL 16 + [`pgvector`](https://github.com/pgvector/pgvector) com índice **HNSW**.
* **Containers:** [Docker](https://www.docker.com) & Docker Compose (dev) · imagem de inferência com o modelo *baked* no build.
* **Cloud (IaC):** [AWS CDK v2](https://docs.aws.amazon.com/cdk/) (Python) — VPC, **RDS pgvector**, **ECS Fargate + ALB** (Auto Scaling), **SNS/SQS + DLQ**, **S3 + CloudFront (OAC)**, Secrets Manager, governança com **cdk-nag**.
* **CI/CD:** GitHub Actions (CI em todo PR: pytest, build/test Angular, `cdk synth` + cdk-nag, **varredura anti-segredos**) e CD via **OIDC** (sem chaves estáticas) com **trava de conta** fail-closed.

### Frontend
* **Framework:** [Angular](https://angular.dev) (SPA) · **Linguagem:** TypeScript · **Estilização:** SCSS modularizado
* **Reatividade:** view-models com RxJS + `async pipe` e **`OnPush`**; formulários reativos.
* **Autenticação:** `AuthService` + `AuthInterceptor` (Bearer JWT) + tela de login e guarda do Painel do Síndico.

---

## 📁 5. Estrutura do Repositório

```text
condoguard-ai/
├── backend/                         # API FastAPI + pipeline de IA
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py               # providers FastAPI (engine lazy, repo, service)
│   │   │   ├── auth_deps.py          # get_current_user / requer_sindico (JWT)
│   │   │   └── v1/endpoints/
│   │   │       ├── auth.py           # POST /auth/login
│   │   │       └── chamados.py       # POST /triagem (rate-limited) · GET /chamados (JWT)
│   │   ├── core/
│   │   │   ├── classifier.py         # TriagemEngine (encode único, centroides, guardrails)
│   │   │   ├── security.py           # JWT + verificação de senha
│   │   │   ├── rate_limit.py         # limiter (slowapi)
│   │   │   └── middleware.py         # headers de segurança
│   │   ├── models/chamado.py         # ORM SQLAlchemy + pgvector
│   │   ├── schemas/chamado.py        # DTOs Pydantic v2
│   │   ├── repositories/             # ChamadoRepository (acesso a dados)
│   │   ├── services/
│   │   │   ├── triagem_service.py    # Service Layer (orquestração)
│   │   │   ├── messaging.py          # AlertaPublisher (SNS / log local)
│   │   │   └── notifier.py
│   │   ├── workers/                  # notificador_handler.py (consumidor SQS/Lambda)
│   │   ├── config.py · database.py · main.py
│   ├── migrations/                   # SQL (created_at -> timestamptz)
│   ├── scripts/run_migration.py
│   ├── tests/                        # pytest (TriagemService + segurança)
│   ├── Dockerfile · .dockerignore
│   ├── requirements.txt · requirements-dev.txt
│   └── .env.example
├── frontend/                         # SPA Angular
│   └── src/app/
│       ├── components/               # novo-chamado · painel-sindico · login
│       ├── services/                 # chamado.service.ts · auth.service.ts
│       ├── interceptors/             # auth.interceptor.ts (Bearer JWT)
│       ├── models/ · environments/
│       └── app.module.ts · app.component.*
├── infra/                            # Infraestrutura AWS CDK (Python)
│   ├── app.py                        # entrypoint + enforce_account_guard (trava de conta)
│   ├── condoguard_infra/
│   │   ├── condoguard_stack.py
│   │   ├── nag_suppressions.py       # governança cdk-nag
│   │   └── constructs/               # network · data · compute · messaging · frontend
│   ├── lambda/notificador/index.py   # consumidor SQS -> Twilio/WhatsApp
│   └── scripts/setup-github-oidc.sh
├── scripts/secret-scan.sh            # varredura anti-segredos (CI + pre-commit)
├── .github/workflows/                # ci.yml · deploy.yml (OIDC)
├── .pre-commit-config.yaml
├── docker-compose.yml
└── README.md
```

---

## 🚀 6. Como Executar o Projeto Localmente

### Pré-requisitos
* Git
* Docker Desktop instalado e em execução
* Python 3.11+
* Node.js (LTS) & npm

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/DevClaudinei/condoguard-ai.git
cd condoguard-ai
```

### Passo 2: Subir o Banco de Dados
```bash
docker compose up -d
```

---

### Passo 3: Configurar e Executar o Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

---

### Passo 4: Configurar e Executar o Frontend

```bash
cd ../frontend
npm install
ng serve
```

Acesse no navegador: `http://localhost:4200`

---

## 📡 7. Endpoints da API

| Método | Rota | Auth | Descrição |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Pública | Autentica a gestão (síndico) e emite o token JWT de acesso. |
| `POST` | `/api/v1/chamados/triagem` | Pública · rate-limited | Recebe a ocorrência, vetoriza (encode único), deduplica via pgvector/HNSW, persiste e publica alerta se for P1 inédito. |
| `GET` | `/api/v1/chamados` | 🔒 JWT (síndico) | Retorna os chamados com status, prioridade e metadados de agrupamento para o painel do síndico. |
| `GET` | `/health` | Pública | Healthcheck de integridade da API. |

---

## 🔒 8. Segurança e Boas Práticas

* **Autenticação & Autorização:** `GET /chamados` é restrito à gestão via **JWT** (papel síndico); `POST /triagem` é público, porém protegido por **rate-limiting** por IP. Login **fail-closed** (desabilitado enquanto a senha não é definida).
* **Proteção de Segredos:** Em dev via `.env` (fora do versionamento); em produção via **AWS Secrets Manager** (DB, JWT, Twilio) injetados no container. **Nenhum ID de conta, ARN ou credencial é versionado.**
* **Varredura Anti-Segredos (CI + pre-commit):** `scripts/secret-scan.sh` bloqueia commits/PRs com access keys, chaves privadas, tokens ou ARNs de conta real — no pipeline e, opcionalmente, no hook local.
* **Trava de Conta AWS (fail-closed):** deploy só prossegue na conta explicitamente autorizada — no pipeline (`AWS_ALLOWED_ACCOUNT_ID`) **e** em execuções locais do CDK (`enforce_account_guard` em `infra/app.py`).
* **Hardening:** CORS restrito por ambiente, headers de segurança (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS), sessão SQLAlchemy com rollback seguro e IAM least-privilege na infraestrutura (cdk-nag).
* **Modelagem Estrita:** Pydantic v2 assegura que apenas payloads válidos e higienizados alcancem o motor de inferência.

---

## 🎓 9. Relevância Acadêmica e Social (PEX)

O projeto atende aos requisitos de Extensão Universitária ao aproximar a inteligência artificial da resolução de problemas comunitários reais:
* **Impacto Comunitário:** Elimina tempos de resposta críticos em ocorrências condominiais de emergência.
* **Combate à Fadiga de Alertas:** A busca vetorial no pgvector evita que o síndico seja bombardeado por dezenas de avisos idênticos durante um mesmo incidente.
* **Acessibilidade:** Interface desacoplada e intuitiva com suporte a fluxos rápidos de atendimento para qualquer morador.

---

## 📄 10. Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.

