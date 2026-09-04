#!/usr/bin/env python3
import os

import aws_cdk as cdk

from condoguard_infra.condoguard_stack import CondoGuardStack

app = cdk.App()

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

app.synth()
