import os

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as route53_targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

# infra/condoguard_infra/constructs -> repo_root/frontend/dist/app-client
_DIST_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "frontend", "dist", "app-client"
)


class Frontend(Construct):
    """SPA Angular em S3 privado, distribuída via CloudFront + OAC.

    O bucket não é público: o CloudFront acessa via Origin Access Control.
    Rotas do SPA: 403/404 do S3 são reescritas para /index.html (client-side routing).

    Domínio custom opcional: se `certificate` (ACM em us-east-1) e `domain_names`
    forem informados, a distribuição responde pelo host próprio e um alias A/AAAA é
    criado na `hosted_zone`. O comportamento `/api/*` (mesma origem, sem CORS) é
    anexado depois via `add_api_behavior(alb)`, pois depende do ALB (Compute).
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        env_name: str,
        certificate: acm.ICertificate | None = None,
        domain_names: list[str] | None = None,
        hosted_zone: route53.IHostedZone | None = None,
    ):
        super().__init__(scope, id)
        is_prod = env_name == "prod"

        self.bucket = s3.Bucket(
            self,
            "SpaBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN if is_prod else RemovalPolicy.DESTROY,
            auto_delete_objects=not is_prod,
        )

        self.distribution = cf.Distribution(
            self,
            "Cdn",
            default_root_object="index.html",
            # Domínio custom (opcional). O CloudFront exige o certificado em us-east-1.
            domain_names=domain_names or None,
            certificate=certificate,
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
            ),
            error_responses=[
                cf.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cf.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
            comment=f"CondoGuard SPA ({env_name})",
        )

        # Faz o upload do build do Angular se ele já existir (ng build gerou dist/).
        if os.path.isdir(_DIST_DIR):
            s3deploy.BucketDeployment(
                self,
                "DeploySpa",
                sources=[s3deploy.Source.asset(_DIST_DIR)],
                destination_bucket=self.bucket,
                distribution=self.distribution,
                distribution_paths=["/index.html"],
            )

        # Alias Route 53 -> CloudFront (só quando há domínio custom + zona).
        self.custom_domain = domain_names[0] if domain_names else None
        if domain_names and hosted_zone:
            target = route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(self.distribution)
            )
            for i, fqdn in enumerate(domain_names):
                record_name = fqdn.replace(f".{hosted_zone.zone_name}", "")
                route53.ARecord(
                    self, f"SpaAliasA{i}", zone=hosted_zone,
                    record_name=record_name, target=target,
                )
                route53.AaaaRecord(
                    self, f"SpaAliasAAAA{i}", zone=hosted_zone,
                    record_name=record_name, target=target,
                )

        # Domínio interno do CloudFront (fallback quando não há domínio custom).
        self.domain_name = self.distribution.distribution_domain_name
        # Host público final (custom quando disponível, senão o do CloudFront).
        self.public_domain = self.custom_domain or self.domain_name

    def add_api_behavior(self, load_balancer: elbv2.IApplicationLoadBalancer) -> None:
        """Roteia /api/* para o ALB pela MESMA origem do SPA (elimina CORS).

        O CloudFront termina o TLS com o viewer e fala com o ALB por HTTP (hop
        interno à AWS). A API não é cacheada e o cabeçalho Authorization é repassado.
        """
        self.distribution.add_behavior(
            "/api/*",
            origins.LoadBalancerV2Origin(
                load_balancer,
                protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
            ),
            allowed_methods=cf.AllowedMethods.ALLOW_ALL,
            viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cache_policy=cf.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        )
