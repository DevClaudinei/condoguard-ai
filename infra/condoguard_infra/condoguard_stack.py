import json

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_secretsmanager as sm
from constructs import Construct

from .constructs.compute import Compute
from .constructs.data import Database
from .constructs.frontend import Frontend
from .constructs.messaging import Messaging
from .constructs.network import Network
from .nag_suppressions import apply_nag_suppressions


class CondoGuardStack(Stack):
    def __init__(self, scope: Construct, id: str, *, env_name: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        network = Network(self, "Network", env_name=env_name)
        database = Database(self, "Database", vpc=network.vpc, env_name=env_name)
        messaging = Messaging(self, "Messaging", env_name=env_name)
        frontend = Frontend(self, "Frontend", env_name=env_name)

        # Segredo da aplicação: jwt_secret_key é GERADO; admin_password nasce VAZIO
        # (login fica fail-closed até a operação definir uma senha real):
        #   aws secretsmanager put-secret-value --secret-id condoguard/<env>/app \
        #       --secret-string '{"admin_password":"<forte>","jwt_secret_key":"<mantenha>"}'
        app_secret = sm.Secret(
            self,
            "AppSecret",
            secret_name=f"condoguard/{env_name}/app",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"admin_password": ""}),
                generate_string_key="jwt_secret_key",
                exclude_punctuation=True,
                password_length=48,
            ),
        )

        # HTTPS opcional no ALB: informe -c certificate_arn=... (ACM na região da stack).
        # Domínio custom opcional: -c domain_name=... -c hosted_zone_id=... -c hosted_zone_name=...
        certificate = None
        cert_arn = self.node.try_get_context("certificate_arn")
        if cert_arn:
            certificate = acm.Certificate.from_certificate_arn(self, "AlbCert", cert_arn)

        domain_name = self.node.try_get_context("domain_name")
        hosted_zone_id = self.node.try_get_context("hosted_zone_id")
        hosted_zone_name = self.node.try_get_context("hosted_zone_name")
        domain_zone = None
        if hosted_zone_id and hosted_zone_name:
            domain_zone = route53.HostedZone.from_hosted_zone_attributes(
                self,
                "Zone",
                hosted_zone_id=hosted_zone_id,
                zone_name=hosted_zone_name,
            )

        compute = Compute(
            self,
            "Compute",
            vpc=network.vpc,
            db=database,
            messaging=messaging,
            app_secret=app_secret,
            # CORS liberado apenas para a origem do CloudFront (frontend).
            cors_origin=f"https://{frontend.domain_name}",
            region=self.region,
            env_name=env_name,
            certificate=certificate,
            domain_name=domain_name,
            domain_zone=domain_zone,
        )

        # Governança: supressões cdk-nag documentadas (o Aspect é anexado em app.py).
        apply_nag_suppressions(self, env_name=env_name)

        if domain_name and certificate is not None:
            api_endpoint = f"https://{domain_name}"
        elif certificate is not None:
            api_endpoint = f"https://{compute.service.load_balancer.load_balancer_dns_name}"
        else:
            api_endpoint = f"http://{compute.service.load_balancer.load_balancer_dns_name}"
        CfnOutput(
            self,
            "ApiEndpoint",
            value=api_endpoint,
            description="Endpoint da API (HTTPS quando certificate_arn é informado)",
        )
        CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{frontend.domain_name}",
            description="URL pública do SPA (CloudFront)",
        )
        CfnOutput(
            self, "FrontendBucket", value=frontend.bucket.bucket_name,
            description="Bucket do SPA (destino do ng build/dist)",
        )
        CfnOutput(
            self, "DbSecretArn", value=database.secret.secret_arn,
            description="Segredo das credenciais do RDS",
        )
        CfnOutput(
            self, "P1TopicArn", value=messaging.topic.topic_arn,
            description="Tópico SNS de alertas P1",
        )
