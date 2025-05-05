from models.base import BaseModel
from models.target import Target, validate_target_id
from models.phishing_email_template import PhishingEmailTemplate
from models.attachment import Attachment
from models.group import Group
import uuid
import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from tasks import send_phishing_email


class PhishingEmail(BaseModel):
    id = AutoField(primary_key=True)
    subject = CharField()
    target = ForeignKeyField(
        Target, on_delete="CASCADE", related_name="phishing_emails"
    )
    template = ForeignKeyField(
        PhishingEmailTemplate, on_delete="CASCADE", related_name="phishing_emails"
    )
    attachments = ManyToManyField(Attachment, backref="phishing_emails")
    celery_task_id = CharField(unique=True)
    status = CharField()

    def __str__(self):
        return f"PhishingEmail[{self.id}] (subject='{self.subject}')"

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

    @classmethod
    def prompt_and_create(cls):
        result = questionary.prompt(
            [
                {
                    "type": "select",
                    "name": "single_or_group",
                    "message": "Send a phishing email to a single target or a group?",
                    "choices": ["single", "group"],
                },
                {
                    "type": "text",
                    "name": "target_id",
                    "message": "Enter target ID",
                    "validate": validate_target_id,
                    "when": lambda answers: answers["single_or_group"] == "single",
                },
                {
                    "type": "checkbox",
                    "name": "target_groups",
                    "message": "Select target group(s)",
                    "choices": Group.choices(),
                    "when": lambda answers: answers["single_or_group"] == "group",
                },
                {
                    "type": "select",
                    "name": "template",
                    "message": "Select template",
                    "choices": PhishingEmailTemplate.choices(),
                },
                {
                    "type": "checkbox",
                    "name": "attachments",
                    "message": "Select attachment",
                    "choices": Attachment.choices(),
                },
            ]
        )

        if result["single_or_group"] == "single":
            targets = [Target.get(id=int(result["target_id"]))]
        else:
            targets = Target.select_in_groups(result["target_groups"])

        template = PhishingEmailTemplate.get(id=int(result["template"]))
        attachments = Attachment.select().where(Attachment.id << result["attachments"])

        for target in targets:
            phishing_email = cls.create(
                target=target,
                template=template,
                attachments=attachments,
                celery_task_id=uuid.uuid4().hex,
                status="pending",
            )

            task = send_phishing_email.delay(phishing_email)
            phishing_email.celery_task_id = task.id
            phishing_email.save()

            questionary.print(f"Created {phishing_email}")

        return phishing_email
