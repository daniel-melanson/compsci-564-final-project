from datetime import datetime

from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel
from .attachment import Attachment
from .phishing_email_template import PhishingEmailTemplate
from .target import Target


class PhishingEmail(BaseModel):
    id = AutoField(primary_key=True)
    target = ForeignKeyField(
        Target, on_delete="CASCADE", related_name="phishing_emails"
    )
    template = ForeignKeyField(
        PhishingEmailTemplate, on_delete="CASCADE", related_name="phishing_emails"
    )
    created_at = DateTimeField(default=lambda: datetime.now())
    attachment = ForeignKeyField(
        Attachment, on_delete="CASCADE", related_name="phishing_emails"
    )
    celery_task_id = CharField(unique=True)
    sent_at = DateTimeField(null=True)
    status = CharField()

    def __str__(self):
        return f"PhishingEmail[{self.id}] (target='{self.target.email}', template='{self.template.name}')"

    @classmethod
    def clear(cls):
        cls.delete().execute()

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("phishing-email", help="Manage phishing emails")
        parser.add_argument("subcommand", choices=["send", "list", "clear"])
