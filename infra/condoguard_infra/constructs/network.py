from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class Network(Construct):
    """VPC com três camadas de sub-rede:

    - public:      ALB (internet-facing)
    - app (egress): ECS Fargate — privada com NAT (sai para ECR/SNS/Secrets)
    - data (isolated): RDS — privada isolada, sem rota para a internet
    """

    def __init__(self, scope: Construct, id: str, *, env_name: str):
        super().__init__(scope, id)
        is_prod = env_name == "prod"

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            # 1 NAT em dev (custo); 2 em prod (HA por AZ).
            nat_gateways=2 if is_prod else 1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="app", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24
                ),
            ],
        )
