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

        # Domínio custom (opcional): CloudFront serve o SPA e roteia /api/* ao ALB
        # sob o MESMO host (mesma origem, sem CORS). O certificado ACM DEVE estar
        # em us-east-1 (exigência do CloudFront) e cobrir o host do frontend.
        #   -c certificate_arn=... -c frontend_domain=condoguard.bluphy.com.br \
        #   -c hosted_zone_id=... -c hosted_zone_name=bluphy.com.br
        cert_arn = self.node.try_get_context("certificate_arn")
        certificate = (
            acm.Certificate.from_certificate_arn(self, "SiteCert", cert_arn)
            if cert_arn else None
        )

        # Aceita frontend_domain (preferido) com fallback ao antigo domain_name.
        frontend_domain = (
            self.node.try_get_context("frontend_domain")
            or self.node.try_get_context("domain_name")
        )
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

        # Só ativa domínio custom quando cert + host + zona estão presentes juntos.
        use_custom_domain = bool(certificate and frontend_domain and domain_zone)
        frontend = Frontend(
            self,
            "Frontend",
            env_name=env_name,
            certificate=certificate if use_custom_domain else None,
            domain_names=[frontend_domain] if use_custom_domain else None,
            hosted_zone=domain_zone if use_custom_domain else None,
        )

        compute = Compute(
            self,
            "Compute",
            vpc=network.vpc,
            db=database,
            messaging=messaging,
            app_secret=app_secret,
            # Mesma origem elimina CORS; ainda assim declaramos o host público.
            cors_origin=f"https://{frontend.public_domain}",
            region=self.region,
            env_name=env_name,
        )

        # Liga /api/* -> ALB DEPOIS que o Compute existe (evita dependência circular).
        # O ALB fica HTTP-only interno; o CloudFront termina o TLS com o viewer.
        frontend.add_api_behavior(compute.service.load_balancer)

        # Governança: supressões cdk-nag documentadas (o Aspect é anexado em app.py).
        apply_nag_suppressions(self, env_name=env_name)

        CfnOutput(
            self,
            "ApiEndpoint",
            value=f"https://{frontend.public_domain}/api/v1",
            description="Base da API (mesma origem do SPA; roteada via CloudFront /api/*)",
        )
        CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{frontend.public_domain}",
            description="URL pública do SPA (domínio custom quando configurado)",
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
