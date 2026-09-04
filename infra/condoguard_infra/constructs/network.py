from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class Network(Construct):
    """VPC cujo desenho varia por ambiente para otimizar custo em dev.

    prod: public (ALB) + private-egress (Fargate via NAT) + isolated (RDS), 2 NAT.
    dev:  public (ALB + Fargate com IP público) + isolated (RDS), **0 NAT** —
          o Fargate sai para ECR/SNS/Secrets pelo Internet Gateway (grátis),
          eliminando ~US$32/mês por NAT Gateway. RDS permanece isolado.
    """

    def __init__(self, scope: Construct, id: str, *, env_name: str):
        super().__init__(scope, id)
        is_prod = env_name == "prod"

        if is_prod:
            subnet_configuration = [
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="app", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24
                ),
            ]
            nat_gateways = 2
        else:
            # Sem camada private-egress => nenhum NAT é provisionado.
            subnet_configuration = [
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24
                ),
            ]
            nat_gateways = 0

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=nat_gateways,
            subnet_configuration=subnet_configuration,
        )
