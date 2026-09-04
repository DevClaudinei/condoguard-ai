import os

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
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
    """

    def __init__(self, scope: Construct, id: str, *, env_name: str):
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

        self.domain_name = self.distribution.distribution_domain_name
