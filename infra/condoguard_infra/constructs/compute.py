import os

from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as sm
from constructs import Construct

from .data import Database
from .messaging import Messaging

# infra/condoguard_infra/constructs -> repo_root/backend
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")


class Compute(Construct):
    """ECS Fargate atrás de um ALB público, com Auto Scaling por CPU e req/target.

    Dimensionamento pensado para inferência CPU do MiniLM/Torch: 1 vCPU / 3 GB
    por task (o modelo residente + numpy cabem com folga). Escala horizontal
    absorve picos (ex.: incidente P1 gera muitos chamados simultâneos).
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        vpc: ec2.IVpc,
        db: Database,
        messaging: Messaging,
        app_secret: sm.ISecret,
        cors_origin: str,
        region: str,
        env_name: str,
    ):
        super().__init__(scope, id)
        is_prod = env_name == "prod"

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)

        image = ecs.ContainerImage.from_asset(_BACKEND_DIR)

        self.service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "Api",
            cluster=cluster,
            cpu=1024,
            memory_limit_mib=3072,
            desired_count=2 if is_prod else 1,
            public_load_balancer=True,
            # Tasks em sub-rede privada com egress; só o ALB é público.
            task_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            health_check_grace_period=Duration.seconds(120),
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=image,
                container_port=8000,
                environment={
                    "APP_ENV": "production",
                    "AWS_REGION": region,
                    "SNS_TOPIC_P1_ARN": messaging.topic.topic_arn,
                    "CORS_ORIGINS": cors_origin,
                    "RATE_LIMIT_TRIAGEM": "10/minute",
                },
                secrets={
                    "POSTGRES_HOST": ecs.Secret.from_secrets_manager(db.secret, "host"),
                    "POSTGRES_PORT": ecs.Secret.from_secrets_manager(db.secret, "port"),
                    "POSTGRES_DB": ecs.Secret.from_secrets_manager(db.secret, "dbname"),
                    "POSTGRES_USER": ecs.Secret.from_secrets_manager(db.secret, "username"),
                    "POSTGRES_PASSWORD": ecs.Secret.from_secrets_manager(db.secret, "password"),
                    "JWT_SECRET_KEY": ecs.Secret.from_secrets_manager(app_secret, "jwt_secret_key"),
                    "ADMIN_PASSWORD": ecs.Secret.from_secrets_manager(app_secret, "admin_password"),
                },
                log_driver=ecs.LogDriver.aws_logs(
                    stream_prefix="condoguard-api",
                    log_retention=logs.RetentionDays.ONE_MONTH,
                ),
            ),
        )

        self.service.target_group.configure_health_check(
            path="/health", healthy_http_codes="200"
        )

        # IAM mínimo: acesso ao banco (SG) e publish no tópico SNS.
        db.allow_from(self.service.service)
        messaging.topic.grant_publish(self.service.task_definition.task_role)

        # Auto Scaling por CPU e por requisições/target no ALB.
        scaling = self.service.service.auto_scale_task_count(
            min_capacity=2 if is_prod else 1, max_capacity=6
        )
        scaling.scale_on_cpu_utilization(
            "Cpu",
            target_utilization_percent=60,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )
        scaling.scale_on_request_count(
            "Req",
            requests_per_target=1000,
            target_group=self.service.target_group,
        )
