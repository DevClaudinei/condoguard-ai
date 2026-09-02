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

---

## ⚡ 3. Classificação Semântica por Baldes (Few-Shot Semantic Router)

A categorização divide os chamados em três classes operacionais de urgência:

| Nível de Urgência | Descrição Operacional | Critérios de Disparo | Ação do Sistema |
| :--- | :--- | :--- | :--- |
| **P1_CRITICO** | Risco iminente à integridade física, patrimonial ou interrupção de serviço essencial. | Vazamentos graves, cheiro de gás, pessoas presas em elevador, portão principal quebrado aberto, faíscas elétricas. | Gravação no banco + **Disparo imediato de alerta aos gestores via WhatsApp**. |
| **P2_URGENTE** | Falhas estruturais parciais ou perturbação de média gravidade que exigem ação no mesmo dia. | Falhas no interfone de torre, iluminação de rota de emergência apagada, perturbação sonora após horário de silêncio. | Gravação com destaque amarelo no Dashboard para triagem prioritária no mesmo dia. |
| **P3_ROTINA** | Demandas administrativas, agendamentos, dúvidas de rateio ou solicitações gerais. | Reserva de quiosque/salão, emissão de segunda via de boleto, agendamento de mudança. | Inserção na fila regular de atendimento do condomínio. |

### Mecanismo Híbrido e Deduplicação Inteligente:
1. **Representação Vetorial:** O texto concatenado (`titulo + descricao`) é transformado em um vetor denso de 384 dimensões através do modelo `all-MiniLM-L6-v2`.
2. **Deduplicação Semântica via pgvector:** Antes de enviar notificações repetidas, o sistema consulta os registros recentes (últimas 4 horas). Se encontrar ocorrência correlata com distância de cosseno `< 0.35`, o chamado é marcado como `🔗 Ocorrência Agrupada`, associado ao `parent_id` inicial e a notificação é suprimida para evitar spam ao corpo diretivo.
3. **Guardrails Determinísticos:** Expressões críticas operacionais (*alagamento*, *vazamento*, *cano*, *fogo*, *gás*, *preso*) garantem elevação imediata para `P1_CRITICO`, evitando falsos negativos.

---

## 💻 4. Stack Tecnológica

### Backend & Inteligência Artificial
* **Linguagem:** Python 3.11+
* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com)
* **Servidor ASGI:** [Uvicorn](https://www.uvicorn.org)
* **Validação de Dados:** [Pydantic v2](https://docs.pydantic.dev) & Pydantic-Settings
* **ORM & Banco:** [SQLAlchemy](https://www.sqlalchemy.org) com driver `psycopg2-binary`
* **Embeddings & Similaridade:** [sentence-transformers](https://www.sbert.net) (`all-MiniLM-L6-v2`) e [scikit-learn](https://scikit-learn.org)

### Banco de Dados & Infraestrutura
* **Banco Relacional com Busca Vetorial:** PostgreSQL 16 com extensão nativa [`pgvector`](https://github.com/pgvector/pgvector)
* **Virtualização e Containers:** [Docker](https://www.docker.com) & Docker Compose

### Frontend
* **Framework:** [Angular](https://angular.dev) (Single Page Application)
* **Linguagem:** TypeScript
* **Estilização:** SCSS modularizado
* **Arquitetura de Componentes:** Formulários reativos (`ReactiveFormsModule`), injeção de dependência e integração HTTP (`HttpClientModule`).

---

## 📁 5. Estrutura do Repositório

PEX V/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           └── chamados.py
│   │   ├── core/
│   │   │   └── classifier.py
│   │   ├── models/
│   │   │   └── chamado.py
│   │   ├── schemas/
│   │   │   └── chamado.py
│   │   ├── services/
│   │   │   └── notifier.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   │   ├── novo-chamado/
│   │   │   │   └── painel-sindico/
│   │   │   ├── models/
│   │   │   ├── services/
│   │   │   ├── app.component.html
│   │   │   └── app.module.ts
│   │   └── styles.scss
│   ├── angular.json
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── .gitignore
└── README.md

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

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/chamados/triagem` | Recebe a ocorrência, realiza vetorização semântica, valida similaridade para deduplicação, persiste no PostgreSQL e aciona notificação se for P1 inédito. |
| `GET` | `/api/v1/chamados` | Retorna todos os chamados com status, prioridade e metadados de agrupamento para o painel do síndico. |
| `GET` | `/health` | Healthcheck de integridade da API. |

---

## 🔒 8. Segurança e Boas Práticas

* **Proteção de Segredos:** Credenciais de banco de dados e chaves de API são gerenciadas via `.env`, mantidas fora do controle de versão pelo `.gitignore`.
* **CORS Restrito:** O backend aceita origens parametrizadas para consumo seguro pelo cliente web.
* **Modelagem Estrita:** Uso de Pydantic v2 para assegurar que apenas payloads válidos e higienizados alcancem o motor de inferência.

---

## 🎓 9. Relevância Acadêmica e Social (PEX)

O projeto atende aos requisitos de Extensão Universitária ao aproximar a inteligência artificial da resolução de problemas comunitários reais:
* **Impacto Comunitário:** Elimina tempos de resposta críticos em ocorrências condominiais de emergência.
* **Combate à Fadiga de Alertas:** A busca vetorial no pgvector evita que o síndico seja bombardeado por dezenas de avisos idênticos durante um mesmo incidente.
* **Acessibilidade:** Interface desacoplada e intuitiva com suporte a fluxos rápidos de atendimento para qualquer morador.

---

## 📄 10. Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.

