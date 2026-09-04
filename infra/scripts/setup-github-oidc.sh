#!/usr/bin/env bash
#
# Configura o provedor OIDC do GitHub e a IAM Role de deploy do CondoGuard.
# NADA é hardcoded: conta, repo e nome da role vêm de env vars / argumentos,
# com fallback do ID da conta para `aws sts get-caller-identity`.
#
# Uso:
#   GITHUB_REPO=owner/repo ./setup-github-oidc.sh
#   ./setup-github-oidc.sh --repo owner/repo [--role NOME] [--account 123456789012]
#
# Parâmetros (env var / flag):
#   AWS_ACCOUNT_ID / --account   default: aws sts get-caller-identity
#   GITHUB_REPO    / --repo       OBRIGATÓRIO (ex.: DevClaudinei/condoguard-ai)
#   ROLE_NAME      / --role       default: condoguard-github-deploy
#
set -euo pipefail

ROLE_NAME="${ROLE_NAME:-condoguard-github-deploy}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
GITHUB_REPO="${GITHUB_REPO:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --account) AWS_ACCOUNT_ID="$2"; shift 2 ;;
    --repo)    GITHUB_REPO="$2"; shift 2 ;;
    --role)    ROLE_NAME="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Argumento desconhecido: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$AWS_ACCOUNT_ID" ]]; then
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
fi
if [[ -z "$GITHUB_REPO" ]]; then
  echo "ERRO: defina GITHUB_REPO (env) ou --repo owner/repo" >&2
  exit 2
fi

echo "Conta: $AWS_ACCOUNT_ID | Repo: $GITHUB_REPO | Role: $ROLE_NAME"

PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

# 1) Provedor OIDC do GitHub (idempotente)
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" >/dev/null 2>&1; then
  echo "OIDC provider já existe."
else
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
  echo "OIDC provider criado."
fi

# 2) Trust policy: apenas este repositório pode assumir a role
TRUST=$(cat <<JSON
{"Version":"2012-10-17","Statement":[{
  "Effect":"Allow",
  "Principal":{"Federated":"${PROVIDER_ARN}"},
  "Action":"sts:AssumeRoleWithWebIdentity",
  "Condition":{
    "StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},
    "StringLike":{"token.actions.githubusercontent.com:sub":"repo:${GITHUB_REPO}:*"}
  }}]}
JSON
)

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam update-assume-role-policy --role-name "$ROLE_NAME" --policy-document "$TRUST"
  echo "Role existente: trust policy atualizada."
else
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST" >/dev/null
  echo "Role criada."
fi

# 3) Permissão mínima: assumir as roles do bootstrap do CDK
PERM=$(cat <<JSON
{"Version":"2012-10-17","Statement":[{
  "Effect":"Allow","Action":"sts:AssumeRole",
  "Resource":"arn:aws:iam::${AWS_ACCOUNT_ID}:role/cdk-*"
}]}
JSON
)
aws iam put-role-policy --role-name "$ROLE_NAME" \
  --policy-name assume-cdk-bootstrap --policy-document "$PERM"

echo
echo "Pronto. Configure no GitHub (Settings -> Secrets and variables -> Actions):"
echo "  secret   AWS_DEPLOY_ROLE_ARN     = arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo "  variable AWS_ALLOWED_ACCOUNT_ID  = ${AWS_ACCOUNT_ID}"
echo "  variable AWS_REGION              = <sua regiao, ex. us-east-1>"
