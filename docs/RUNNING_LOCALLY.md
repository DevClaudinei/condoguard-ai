# Executando o CondoGuard AI localmente

Guia reprodutível para subir a stack completa (PostgreSQL + FastAPI + Angular) e
validar o funcionamento ponta a ponta — triagem por IA, deduplicação semântica,
alertas P1 e o Painel do Síndico.

> Arquitetura em [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 1. Pré-requisitos

- **Docker** (para o PostgreSQL + pgvector)
- **Python 3.11+**
- **Node.js 18/20 LTS** + npm

---

## 2. Setup do ambiente

Use **três terminais** (banco, backend, frontend).

### 2.1 · Banco de dados (PostgreSQL 16 + pgvector)
```bash
docker compose up -d
```
Sobe o container `condoguard-db` em `localhost:5432` (`postgres` / `condopassword123` /
db `condoguard_db`), já compatível com o `DATABASE_URL` padrão. A extensão `vector`, as
tabelas e os índices (**HNSW** + B-Tree composto) são criados automaticamente pelo backend
no startup.

> Alternativa sem Docker: um PostgreSQL 16 local com a extensão `pgvector` instalada e um
> banco `condoguard_db`; ajuste o `DATABASE_URL` no `.env`.

### 2.2 · Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```
(Windows PowerShell: `.\.venv\Scripts\Activate.ps1`)

**Baixe o modelo de embeddings uma vez** — o classificador roda com `local_files_only=True`,
então o modelo precisa estar no cache local antes do primeiro request:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```
Configure o `.env` (ver §3) e suba a API:
```bash
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
Verifique:
```bash
curl http://localhost:8000/health
```
→ `{"status":"ok"}` · documentação interativa em `http://localhost:8000/docs`.

### 2.3 · Frontend (Angular)
```bash
cd frontend
npm install
npm start
```
Abra **`http://localhost:4200`** — use `localhost` (não `127.0.0.1`): o CORS do backend
libera apenas a origem `http://localhost:4200` por padrão. A URL base da API
(`http://127.0.0.1:8000`) vem de `src/environments/environment.ts`.

> O aviso de vulnerabilidades no `npm install` é esperado (dependências transitivas do
> toolchain do Angular 16) e **não bloqueia** o desenvolvimento. **Não** rode
> `npm audit fix --force` — ele quebra o build do Angular 16.

---

## 3. Variáveis de ambiente essenciais (`backend/.env`)

Mínimo para desenvolvimento (o restante pode ficar no default do `.env.example`):

| Variável | Valor (dev) | Observação |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres:condopassword123@localhost:5432/condoguard_db` | Bate com o `docker-compose.yml` |
| `JWT_SECRET_KEY` | qualquer segredo com **≥ 32 bytes** | Em produção vem do Secrets Manager |
| `ADMIN_USERNAME` | `sindico` | Usuário da gestão |
| `ADMIN_PASSWORD` | defina uma senha | **Fail-closed:** vazio ⇒ login desabilitado (401) |
| `CORS_ORIGINS` | `http://localhost:4200` | Origem do frontend |
| `RATE_LIMIT_TRIAGEM` | `10/minute` | Limite do endpoint público de triagem |

### Modelo MiniLM (`all-MiniLM-L6-v2`)
- Em runtime, o classificador usa `local_files_only=True` (não baixa nada).
- No **primeiro uso**, baixe o modelo **sem** essa flag para popular o cache do Hugging Face
  (`~/.cache/...`), com o one-liner de `python -c "..."` do §2.2 (equivale a `local_files_only=False`).
- Nos usos seguintes, o modelo é lido do cache — offline e determinístico.

---

## 4. Roteiro de validação funcional

### 4.1 · Login administrativo (Painel do Síndico)
1. No topo, clique em **"Painel do Síndico"**.
2. Faça login com `ADMIN_USERNAME` / `ADMIN_PASSWORD` do `.env` (ex.: `sindico` / sua senha).
3. O token JWT é guardado no navegador e anexado automaticamente (`Authorization: Bearer`)
   pelo `AuthInterceptor`. Sem senha configurada, o login retorna **401** (fail-closed).

### 4.2 · Abrir chamados (aba "Área do Morador")
Preencha **Apartamento** (obrigatório) e use os exemplos calibrados abaixo. Depois, no painel,
clique em **🔄 Atualizar Lista**.

**🔴 P1 — Crítico** (gatilho determinístico ⇒ confiança 95% + notificação)
| Título | Descrição |
| :--- | :--- |
| Vazamento de gás | Cheiro forte de gás no hall do térreo |
| Pessoa presa no elevador | Morador preso no elevador da Torre A há 10 minutos |
| Princípio de incêndio | Fumaça saindo do quadro elétrico, cheiro de curto |
| Cano rompido | Cano estourou e está alagando a garagem inteira |

**🟡 P2 — Urgente** (semântico, sem gatilho)
| Título | Descrição |
| :--- | :--- |
| Interfone sem funcionar | O interfone da portaria parou de funcionar na torre inteira |
| Lâmpada queimada | A lâmpada da escadaria principal está queimada |
| Barulho tarde da noite | Som alto no salão após o horário de silêncio |
| Trinco emperrado | A porta de acesso de pedestres está com o trinco emperrado |

**🔵 P3 — Rotina**
| Título | Descrição |
| :--- | :--- |
| Segunda via de boleto | Preciso da segunda via do boleto deste mês |
| Reserva do salão | Quero reservar o salão de festas para sábado |
| Agendar mudança | Gostaria de agendar minha mudança para o fim de semana |
| Dúvida no aplicativo | Tenho uma dúvida cadastral no app do condomínio |

### 4.3 · Deduplicação semântica (combate à fadiga de alertas)
Envie **em sequência** (dentro da janela de 4h), **de propósito em torre/apto diferentes**:
1. Título `Vazamento de gás` · Desc `Cheiro forte de gás no hall do térreo` · Torre A / Apt 105
2. Título `Cheiro de gás` · Desc `Sentindo forte cheiro de gás perto da portaria` · Torre B / Apt 1102

**Esperado:**
- O **1º** é classificado **P1** e dispara a notificação (`⚡ Notificação enviada via WhatsApp`).
- O **2º** é agrupado como **🔗 Ocorrência Agrupada**, exibe *"Similar ao incidente principal:
  CMD-XXXXXX"* e mostra **🛡️ Notificação suprimida (duplicidade semântica)**.
- Como a deduplicação é **semântica (pgvector/HNSW)** e não por localização, o agrupamento
  ocorre mesmo em torres/apartamentos diferentes — vários moradores reportando o **mesmo
  incidente físico** geram **um único alerta** ao síndico.

### 4.4 · Comportamento esperado no painel
- **KPIs** (Críticos P1 / Urgentes P2 / Rotina P3 / Total) somam conforme os chamados enviados.
- **Filtros reativos:** clicar num card de KPI filtra a lista; "Limpar filtro" volta para *TODOS*.
- **Confiança da IA:** ~95% nos P1 com gatilho; ~70–78% nos P2; ~60–68% nos P3.
- **Badges:** P1 inédito → `⚡ Notificação enviada`; duplicado → `🛡️ Notificação suprimida`.
- **Alertas P1 no console do backend:** sem `SNS_TOPIC_P1_ARN` configurado, o `AlertaPublisher`
  cai no modo local e registra `[ALERTA P1][LOCAL] {...}` — um por P1 **inédito** (agrupados não notificam).

---

## 5. Testes automatizados (opcional)
```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
cd frontend && npm run test:ci   # requer Chrome headless
```

## 6. Solução de problemas
| Sintoma | Causa provável | Correção |
| :--- | :--- | :--- |
| Backend quebra no 1º `/triagem` | Modelo não baixado (`local_files_only`) | Rode o `python -c "..."` do §2.2 |
| Login retorna 401 | `ADMIN_PASSWORD` vazio (fail-closed) | Defina no `.env` e reinicie o `uvicorn` |
| Erro de CORS no navegador | Abriu `127.0.0.1:4200` | Use `http://localhost:4200` |
| `uvicorn` falha ao subir | Banco ainda não está de pé | `docker compose up -d` antes do backend |
| `429 Too Many Requests` na triagem | Rate limit (10/min) | Aguarde ou ajuste `RATE_LIMIT_TRIAGEM` |
