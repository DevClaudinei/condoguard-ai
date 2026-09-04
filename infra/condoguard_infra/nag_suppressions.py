"""Supressões cdk-nag (AwsSolutionsChecks) com justificativa por regra.

Cada supressão documenta um trade-off consciente. As de dev afrouxam apenas o
que é reforçado em prod (Multi-AZ, deletion protection). Após o primeiro
`cdk synth`, revise as anotações restantes e prefira corrigir a suprimir.
"""

from cdk_nag import NagSuppressions
from constructs import Construct


def apply_nag_suppressions(stack: Construct, *, env_name: str) -> None:
    is_prod = env_name == "prod"

    NagSuppressions.add_stack_suppressions(
        stack,
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Roles de execução gerenciados pela AWS (ECS execution role, "
                "AWSLambdaBasicExecutionRole em custom resources da CDK) — aceitos.",
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Wildcards restritos gerados por constructs L2/custom resources "
                "(LogRetention, BucketDeployment, grants de SNS/Secrets), escopados ao recurso.",
            },
            {
                "id": "AwsSolutions-ECS2",
                "reason": "Variáveis de ambiente não sensíveis (APP_ENV, CORS_ORIGINS, ARNs). "
                "Segredos (DB, JWT, admin) são injetados via Secrets Manager em 'secrets'.",
            },
            {
                "id": "AwsSolutions-ELB2",
                "reason": "Access logs do ALB adiados; observabilidade via CloudWatch/Container "
                "Insights. Habilitar bucket de logs em prod.",
            },
            {
                "id": "AwsSolutions-EC23",
                "reason": "ALB público é o ponto de entrada web; ingress 80/443 de 0.0.0.0/0 é intencional.",
            },
            {
                "id": "AwsSolutions-SQS3",
                "reason": "A própria DLQ não requer outra DLQ; a fila principal já possui DLQ.",
            },
            {
                "id": "AwsSolutions-SNS2",
                "reason": "Criptografia SNS via CMK adiada (custo de KMS) em dev; tráfego interno à VPC.",
            },
            {
                "id": "AwsSolutions-SNS3",
                "reason": "Publish ocorre exclusivamente por HTTPS (SDK); enforcement adicional em prod.",
            },
            {
                "id": "AwsSolutions-CFR1",
                "reason": "Geo restriction não se aplica ao público-alvo (condôminos locais).",
            },
            {
                "id": "AwsSolutions-CFR2",
                "reason": "WAF planejado para o refinamento seguinte (junto de HTTPS/ACM).",
            },
            {
                "id": "AwsSolutions-CFR3",
                "reason": "Access logging do CloudFront adiado (custo em dev).",
            },
            {
                "id": "AwsSolutions-CFR4",
                "reason": "Sem domínio custom/ACM no CloudFront, usa o certificado padrão "
                "(TLS mínimo não configurável).",
            },
            {
                "id": "AwsSolutions-S1",
                "reason": "Server access logs do S3 adiados; bucket é privado (OAC) com enforce_ssl.",
            },
            {
                "id": "AwsSolutions-SMG4",
                "reason": "Rotação automática dos segredos planejada; habilitar rotação gerenciada em prod.",
            },
            {
                "id": "AwsSolutions-VPC7",
                "reason": "VPC Flow Logs adiados para prod (custo de armazenamento/observabilidade).",
            },
            {
                "id": "AwsSolutions-L1",
                "reason": "Runtime da Lambda fixado em Python 3.12 (versão suportada).",
            },
        ],
    )

    if not is_prod:
        NagSuppressions.add_stack_suppressions(
            stack,
            [
                {
                    "id": "AwsSolutions-RDS3",
                    "reason": "Multi-AZ desativado em dev por custo; ativo em prod.",
                },
                {
                    "id": "AwsSolutions-RDS10",
                    "reason": "Deletion protection desativado em dev; ativo em prod.",
                },
                {
                    "id": "AwsSolutions-RDS11",
                    "reason": "Porta padrão do Postgres em ambiente não-prod; acesso restrito ao SG isolado.",
                },
            ],
        )
