from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from constructs import Construct


class Database(Construct):
    """RDS PostgreSQL 16 (pgvector) em sub-rede isolada.

    Credenciais geradas e guardadas no Secrets Manager. A extensão `vector` é
    criada pela aplicação na inicialização (CREATE EXTENSION IF NOT EXISTS vector).
    """

    def __init__(self, scope: Construct, id: str, *, vpc: ec2.IVpc, env_name: str):
        super().__init__(scope, id)
        is_prod = env_name == "prod"

        self.instance = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_4
            ),
            # Graviton (ARM). Em dev usa MICRO + gp2 (permitidos no AWS Free Plan);
            # prod usa MEDIUM + gp3. O Free Plan bloqueia tamanhos != micro no RDS.
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,
                ec2.InstanceSize.MEDIUM if is_prod else ec2.InstanceSize.MICRO,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            multi_az=is_prod,
            allocated_storage=20,
            max_allocated_storage=100 if is_prod else 20,
            storage_type=rds.StorageType.GP3 if is_prod else rds.StorageType.GP2,
            storage_encrypted=True,
            database_name="condoguard_db",
            credentials=rds.Credentials.from_generated_secret(
                "condoguard_admin", secret_name=f"condoguard/{env_name}/db"
            ),
            backup_retention=Duration.days(7 if is_prod else 1),
            deletion_protection=is_prod,
            removal_policy=RemovalPolicy.SNAPSHOT if is_prod else RemovalPolicy.DESTROY,
        )
        # Segredo com host/port/dbname/username/password (injetado no container).
        self.secret = self.instance.secret

    def allow_from(self, peer: ec2.IConnectable) -> None:
        """Libera o acesso à porta do Postgres apenas para o peer informado (ex.: Fargate)."""
        self.instance.connections.allow_default_port_from(peer, "Acesso do backend Fargate")
