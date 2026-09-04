#!/usr/bin/env python3
import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from condoguard_infra.condoguard_stack import CondoGuardStack


def enforce_account_guard(resolved_account: str | None, allowed_account: str | None) -> None:
    """Trava fail-closed para deploy LOCAL: aborta se as credenciais ativas
    apontarem para uma conta não autorizada (ou não declarada).

    - Sem conta resolvida (sem credenciais, ex.: `cdk synth` no CI): não bloqueia
      — é síntese env-agnostic, incapaz de tocar a nuvem.
    - Com credenciais ativas: exige ALLOWED_ACCOUNT_ID (env) ou -c allowed_account_id
      e que a conta ativa seja exatamente essa; caso contrário, encerra.
    """
    if not resolved_account:
        return
    if not allowed_account:
        raise SystemExit(
            f"[SEGURANÇA] Credenciais AWS ativas (conta {resolved_account}), mas a conta "
            "autorizada não foi declarada. Defina ALLOWED_ACCOUNT_ID (env) ou "
            "-c allowed_account_id=<ID> antes de qualquer operação. Abortando."
        )
    if resolved_account != allowed_account:
        raise SystemExit(
            f"[SEGURANÇA] Conta ativa ({resolved_account}) difere da autorizada "
            f"({allowed_account}). Abortando para não tocar em conta não autorizada "
            "(ex.: a do trabalho)."
        )


app = cdk.App()

# Blindagem de deploy local: compara a conta resolvida pelo CDK/AWS CLI
# (CDK_DEFAULT_ACCOUNT) com a conta explicitamente autorizada.
enforce_account_guard(
    resolved_account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    allowed_account=(
        app.node.try_get_context("allowed_account_id") or os.getenv("ALLOWED_ACCOUNT_ID")
    ),
)

# Ambiente lógico (dev|prod) controla Multi-AZ, tamanho de instância, contagem
# de tasks e políticas de remoção. Passe via: cdk deploy -c env=prod
env_name = app.node.try_get_context("env") or "dev"

CondoGuardStack(
    app,
    f"CondoGuard-{env_name}",
    env_name=env_name,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
    ),
    description="CondoGuard AI - infraestrutura (VPC, RDS pgvector, ECS Fargate, SNS/SQS, S3/CloudFront)",
)

# Auditoria de conformidade cdk-nag (AwsSolutionsChecks). Desative com -c nag=false.
if app.node.try_get_context("nag") != "false":
    cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()
