"""Diagrama de arquitetura do CondoGuard AI (diagram-as-code).

Gera `docs/architecture/condoguard_architecture.png` com os ícones oficiais da AWS,
modelando a topologia atual: CloudFront + S3 (frontend), ALB + ECS Fargate (API/IA),
RDS pgvector (dados), SNS -> SQS(+DLQ) -> Lambda (alerta P1), Secrets Manager e
CloudWatch (segredos/observabilidade), com GitHub Actions (CI/CD) provisionando a stack.

Pré-requisitos:
    - Graphviz (binário `dot`):  sudo apt install graphviz   |   brew install graphviz
    - pip install diagrams

Renderizar:
    python docs/architecture/diagram.py
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.vcs import Github
from diagrams.aws.network import CloudFront, ELB
from diagrams.aws.storage import S3
from diagrams.aws.compute import Fargate, Lambda
from diagrams.aws.database import RDS
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.security import SecretsManager
from diagrams.aws.management import Cloudwatch
from diagrams.saas.communication import Twilio

graph_attr = {"fontsize": "18", "pad": "0.6", "splines": "ortho", "nodesep": "0.6", "ranksep": "0.9"}

with Diagram(
    "CondoGuard AI - Arquitetura (estado atual)",
    filename="docs/architecture/condoguard_architecture",
    direction="LR",
    show=False,
    graph_attr=graph_attr,
):
    user = Users("Morador / Sindico")
    gh = Github("GitHub Actions\nCI/CD (OIDC)")

    with Cluster("Edge / Frontend"):
        cf = CloudFront("CloudFront + OAC")
        spa = S3("S3 - SPA Angular")

    with Cluster("VPC"):
        alb = ELB("Application\nLoad Balancer")
        with Cluster("ECS Fargate"):
            api = Fargate("FastAPI + MiniLM")
        db = RDS("PostgreSQL 16\npgvector / HNSW")

    with Cluster("Mensageria P1 (assincrona)"):
        sns = SNS("SNS")
        sqs = SQS("SQS + DLQ")
        fn = Lambda("Notificador")

    twilio = Twilio("WhatsApp / Twilio")

    with Cluster("Seguranca & Observabilidade"):
        secrets = SecretsManager("Secrets Manager")
        cw = Cloudwatch("CloudWatch\nLogs + alarme DLQ")

    # Fluxo principal (numerado por rótulo)
    user >> Edge(label="1 HTTPS") >> cf >> Edge(label="2") >> spa
    user >> Edge(label="3 /api/v1") >> alb >> Edge(label="4") >> api
    api >> Edge(label="5 SQL + vetor") >> db
    api >> Edge(label="6 publish P1") >> sns >> Edge(label="7") >> sqs \
        >> Edge(label="8") >> fn >> Edge(label="9 webhook") >> twilio

    # Suporte (tracejado)
    secrets >> Edge(style="dashed", label="segredos") >> api
    secrets >> Edge(style="dashed") >> fn
    api >> Edge(style="dashed", label="logs") >> cw
    sqs >> Edge(style="dashed", label="alarme DLQ") >> cw

    # Entrega contínua
    gh >> Edge(style="dashed", label="cdk deploy") >> alb
