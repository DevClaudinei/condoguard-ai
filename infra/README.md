# CondoGuard AI — Infraestrutura (AWS CDK · Python)

Stack única (`CondoGuard-<env>`) que provisiona toda a plataforma:

| Camada | Recursos |
| :--- | :--- |
| **Networking** | VPC (2 AZ) · subnets public (ALB) / private-egress (Fargate) / isolated (RDS) · NAT |
| **Persistência** | RDS PostgreSQL 16 + pgvector (isolada) · credenciais no Secrets Manager |
| **Computação** | ECS Fargate (1 vCPU / 3 GB) atrás de ALB · Auto Scaling (CPU 60% + req/target) |
| **Mensageria** | SNS → SQS (+DLQ) → Lambda notificadora · alarme CloudWatch na DLQ |
| **Frontend** | S3 privado + CloudFront (OAC) · SPA rewrite 403/404 → /index.html |
| **Segurança** | IAM least-privilege (grants) · segredos no Secrets Manager · headers/HTTPS |

## Pré-requisitos
- AWS CDK v2 (`npm i -g aws-cdk`) e credenciais AWS ativas
- Python 3.11+ e Docker (para o build da imagem do backend)

## Setup
```bash
cd infra
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1
cdk bootstrap
```

## Deploy
```bash
# (opcional) buildar o SPA antes, para o CloudFront já servir os assets:
( cd ../frontend && npm ci && npm run build )

cdk synth                 # gera o template (valide antes)
cdk diff                  # revise as mudanças
cdk deploy -c env=dev     # ou: -c env=prod (Multi-AZ, deletion protection, 2 NAT)
```

## Pós-deploy (obrigatório — login fail-closed)
`admin_password` nasce vazio (login desabilitado). Defina uma senha real:
```bash
aws secretsmanager put-secret-value \
  --secret-id condoguard/dev/app \
  --secret-string '{"admin_password":"<senha-forte>","jwt_secret_key":"<mantenha o gerado>"}'
```
Credenciais do provedor de WhatsApp/Twilio:
```bash
aws secretsmanager put-secret-value \
  --secret-id condoguard/dev/twilio \
  --secret-string '{"account_sid":"...","auth_token":"...","from":"..."}'
```

Os outputs (`ApiEndpoint`, `FrontendUrl`, `FrontendBucket`, `DbSecretArn`, `P1TopicArn`)
são impressos ao fim do deploy.

## Governança (cdk-nag)
`AwsSolutionsChecks` roda no `synth` por padrão (desative com `-c nag=false`).
Supressões documentadas ficam em `condoguard_infra/nag_suppressions.py` — cada uma
com justificativa. Após o primeiro `synth`, revise anotações restantes e prefira
corrigir a suprimir.

## HTTPS / domínio customizado (opcional)
O ALB sobe em HTTP por padrão. Para HTTPS, informe um certificado ACM **na região
da stack** (para o CloudFront o certificado deve estar em us-east-1):
```bash
cdk deploy -c env=prod \
  -c certificate_arn=arn:aws:acm:us-east-1:123456789012:certificate/xxxx \
  -c domain_name=api.seudominio.com \
  -c hosted_zone_id=Z0123456ABC \
  -c hosted_zone_name=seudominio.com
```
Com `certificate_arn`, o ALB expõe 443 e **redireciona 80 → 443**. Com
`domain_name` + hosted zone, cria o registro Route53 (alias) apontando para o ALB.

## CI/CD (GitHub Actions)
- **CI** (`.github/workflows/ci.yml`) roda em PR/push para `main`: backend
  (compileall + pytest), frontend (build + testes headless) e infra
  (`cdk synth -c nag=true`). O `synth` **não** builda a imagem Docker (assets de
  imagem só são construídos no deploy), então não exige Docker no CI.
- **CD** (`.github/workflows/deploy.yml`) é manual (`workflow_dispatch`, escolhe
  `dev`/`prod`) e usa **OIDC** (sem access keys). Pré-requisitos na conta/repo:
  1. Provedor OIDC `token.actions.githubusercontent.com` na conta AWS.
  2. IAM Role de deploy com trust para este repositório e permissão de assumir
     os roles do bootstrap do CDK (`cdk-*-deploy-role`, `-cfn-exec-role`, etc.).
  3. Repo **secret** `AWS_DEPLOY_ROLE_ARN` e **variables** `AWS_REGION` e
     `AWS_ALLOWED_ACCOUNT_ID` (conta autorizada — trava de segurança).
  4. (Opcional) GitHub Environments `dev`/`prod` com required reviewers.
  O CDK builda a imagem do backend e publica no ECR do bootstrap durante o deploy.

  > **Trava de conta (fail-closed):** o job aborta se a conta autenticada via OIDC
  > não for igual a `AWS_ALLOWED_ACCOUNT_ID`, ou se essa variable não estiver
  > definida — impedindo deploy acidental em outra conta (ex.: a do trabalho).

  Para provisionar o OIDC + role de forma repetível (sem nada hardcoded):
  ```bash
  GITHUB_REPO=owner/repo bash infra/scripts/setup-github-oidc.sh
  ```

## Notas
- **pgvector no RDS:** a extensão é criada pela aplicação na inicialização.
- **1 worker por task:** o container roda `uvicorn --workers 1` (uma cópia do
  modelo na RAM); escale horizontalmente via `desired_count`/Auto Scaling de tasks.
- **Custo:** em `dev`, **0 NAT** (Fargate em subnet pública com IP público, egress
  via IGW) + RDS SMALL single-AZ + 1 task Fargate — economiza ~US$32/mês por NAT.
  `prod` ativa VPC isolada + NAT + Multi-AZ + ≥2 tasks. Mesmo em dev, prefira
  `deploy` → testar → `cdk destroy` para preservar créditos.
- **Isolamento em dev:** a task recebe IP público apenas para egress; o ingress
  continua restrito ao Security Group do ALB (nada aberto para 0.0.0.0/0 na task).
