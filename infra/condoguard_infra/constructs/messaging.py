import os

from aws_cdk import Duration
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as les
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk import aws_sqs as sqs
from constructs import Construct

_LAMBDA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "notificador")


class Messaging(Construct):
    """Mensageria desacoplada de alertas P1.

        Fargate --publish--> SNS --> SQS (+DLQ) --> Lambda --> Twilio/WhatsApp

    A DLQ tem alarme no CloudWatch: qualquer mensagem visível nela significa que
    um alerta P1 falhou após as retentativas — deve paginar a operação.
    """

    def __init__(self, scope: Construct, id: str, *, env_name: str):
        super().__init__(scope, id)

        self.topic = sns.Topic(self, "P1Topic", display_name="CondoGuard alertas P1")

        self.dlq = sqs.Queue(
            self,
            "P1Dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,  # SSE-SQS (sem custo de KMS)
            enforce_ssl=True,
        )
        self.queue = sqs.Queue(
            self,
            "P1Queue",
            visibility_timeout=Duration.seconds(60),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=5, queue=self.dlq),
        )
        # raw_message_delivery: entrega o JSON do evento sem o envelope SNS.
        self.topic.add_subscription(
            subs.SqsSubscription(self.queue, raw_message_delivery=True)
        )

        # Credenciais do provedor externo (Twilio/WhatsApp) no Secrets Manager.
        self.twilio_secret = sm.Secret(
            self, "TwilioSecret", secret_name=f"condoguard/{env_name}/twilio"
        )

        self.notifier = lambda_.Function(
            self,
            "Notifier",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset(_LAMBDA_DIR),
            timeout=Duration.seconds(30),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment={"TWILIO_SECRET_ARN": self.twilio_secret.secret_arn},
        )
        # Event source mapping com relato de falhas parciais (retry item a item).
        self.notifier.add_event_source(
            les.SqsEventSource(self.queue, batch_size=10, report_batch_item_failures=True)
        )
        self.twilio_secret.grant_read(self.notifier)

        # Alarme: mensagens na DLQ => alerta P1 não entregue.
        cw.Alarm(
            self,
            "P1DlqAlarm",
            alarm_description="Alertas P1 caíram na DLQ (falha de entrega ao provedor externo)",
            metric=self.dlq.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(1), statistic="Maximum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
