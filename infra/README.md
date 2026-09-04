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

## Notas
- **HTTPS na API:** o ALB sobe em HTTP. Para produção, associe um certificado ACM
  e um listener 443 (ou coloque a API atrás do CloudFront/API Gateway).
- **pgvector no RDS:** a extensão é criada pela aplicação na inicialização.
- **Custo:** em `dev`, 1 NAT + RDS SMALL single-AZ + 1 task Fargate. `prod` ativa
  Multi-AZ, 2 NAT e ≥2 tasks — ver seção de custo no PR.
