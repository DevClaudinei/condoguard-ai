# Arquitetura — CondoGuard AI

Documento de referência da arquitetura da plataforma de triagem de chamados
condominiais. Cobre o **estado atual** (implementado em código + IaC) e o
**alvo final** (com o que falta do próximo ciclo).

O diagrama oficial "as-code" é gerado por [`architecture/diagram.py`](architecture/diagram.py)
(biblioteca [`diagrams`](https://diagrams.mingrammer.com)); abaixo há a versão ASCII
para leitura direta no GitHub.

---

## 1. Visão em camadas

| Camada | Responsabilidade | Componentes |
| :--- | :--- | :--- |
| **Edge / Frontend** | Entrega global do SPA e proteção de borda | Amazon **CloudFront** (OAC) · Amazon **S3** (SPA Angular) |
| **Ingress / VPC** | Ponto de entrada da API e isolamento de rede | **Application Load Balancer** · VPC (subnets public / private-egress / isolated) |
| **Compute / IA** | Inferência e regra de negócio (triagem) | **ECS Fargate** — FastAPI + Sentence-Transformers (`all-MiniLM-L6-v2`); JWT + rate-limiting |
| **Dados / Vetores** | Persistência relacional + busca semântica | Amazon **RDS PostgreSQL 16** + `pgvector` (índice **HNSW**) |
| **Mensageria P1** | Desacoplamento do alerta crítico | Amazon **SNS** → Amazon **SQS** (+ DLQ) → **AWS Lambda** → WhatsApp/Twilio |
| **Observabilidade & Segredos** | Telemetria, alarmes e credenciais | Amazon **CloudWatch** (logs, alarme da DLQ) · AWS **Secrets Manager** |
| **CI/CD** | Integração e entrega contínuas | **GitHub Actions** (CI em PR; CD via **OIDC**) → `cdk deploy` |

**Fluxo de uma triagem (P1 inédito):**
1. O morador envia o chamado pelo SPA (CloudFront/S3) → `POST /api/v1/chamados/triagem` no ALB.
2. O Fargate vetoriza o texto **uma única vez** (`all-MiniLM-L6-v2`, embeddings normalizados).
3. Classifica por similaridade de cosseno contra centroides + guardrails determinísticos.
4. Deduplica no RDS via `pgvector`/HNSW (janela + limiar configuráveis).
5. Se for **P1 inédito**, publica um evento no **SNS** → **SQS** (+DLQ) → **Lambda** → WhatsApp/Twilio.
6. Persiste o chamado; o Painel do Síndico consulta via `GET /api/v1/chamados` (protegido por JWT).

---

## 2. Estado atual (implementado)

```text
                       ┌──────────────────────────────┐
   GitHub Actions ─────┤ CI (PR): pytest · ng test ·   │
   (CI/CD via OIDC)     │      cdk synth+nag · secrets  │
        │               └──────────────────────────────┘
        │ cdk deploy
        ▼
┌───────────────────────────── AWS ──────────────────────────────────────────┐
│                                                                             │
│  Edge / Frontend                         Mensageria P1 (assíncrona)         │
│  ┌───────────────┐   ┌───────────┐       ┌─────┐   ┌───────────┐  ┌───────┐ │
│  │ CloudFront+OAC│──▶│ S3 (SPA)  │       │ SNS │──▶│ SQS + DLQ │─▶│Lambda │ │
│  └───────▲───────┘   └───────────┘       └──▲──┘   └─────▲─────┘  └───┬───┘ │
│          │ (1) HTTPS                        │ (6)        │ alarme     │(9)  │
│  Morador │                                  │            └────────┐   ▼     │
│  /Síndico│         ┌──────── VPC ───────────┼─────────┐  │   WhatsApp/Twilio│
│      │   │ (3)/api │  ┌─────┐   ┌─────────┐ │(5)      │  │                  │
│      └───┴────────▶│  │ ALB │──▶│ Fargate │─┼──▶ RDS  │  │                  │
│                    │  └─────┘(4)│ FastAPI │ │  pgvector│ │                  │
│                    │            │ +MiniLM │ │  /HNSW   │ │                  │
│                    │            └────┬────┘ └──────────┘ │                  │
│                    └─────────────────┼────────────────── ┘                 │
│                                      │ segredos / logs                     │
│                    ┌─────── Segurança & Observabilidade ───────┐           │
│                    │  Secrets Manager        CloudWatch          │          │
│                    └─────────────────────────────────────────── ┘          │
└─────────────────────────────────────────────────────────────────────────── ┘

Fluxo P1: (1) HTTPS → CloudFront/S3 · (3) /api → ALB · (4) → Fargate ·
(5) SQL+vetor → RDS · (6) publish → SNS → SQS(+DLQ) → (9) Lambda → WhatsApp/Twilio.
```

---

## 3. Alvo final (a implementar)

Camadas adicionais do próximo ciclo, isoladas para não alterar o núcleo consolidado:

- **Borda & Auth:** **AWS WAF** (regras gerenciadas), **ACM + Route 53** (HTTPS 443 e domínio
  próprio — hoje o ALB sobe em HTTP) e **Amazon Cognito** (auth gerenciada via JWKS, evoluindo
  o JWT HS256 atual).
- **Observabilidade & Testes:** **X-Ray / ADOT** + **CloudWatch Dashboards** (tracing distribuído
  e alarmes de latência), **rotação automática** de segredos no Secrets Manager e **testes de carga**
  para calibrar o Auto Scaling (CPU / req-target).

```text
[ Borda & Auth ]  WAF ─▶ CloudFront/ALB   ·   ACM+Route53 ─▶ ALB (HTTPS 443)
                  Cognito ─▶ Fargate (valida token, JWKS)

        (núcleo do Estado 2 — idêntico ao Estado atual)

[ Obs. & Testes ] X-Ray/ADOT + Dashboards  ·  Rotação de segredos  ·  Testes de carga
```

---

## 4. Perfis de ambiente

| Dimensão | `dev` (econômico) | `prod` |
| :--- | :--- | :--- |
| NAT Gateway | **0** (Fargate em subnet pública, egress via IGW) | 2 (HA por AZ) |
| RDS | `t4g.small`, single-AZ | `t4g.medium`, **Multi-AZ**, deletion protection |
| Fargate | 1 task | ≥2 tasks (Auto Scaling → 6) |
| Remoção | `DESTROY` | `RETAIN` / `SNAPSHOT` |

Detalhes de provisionamento em [`../infra/README.md`](../infra/README.md).
