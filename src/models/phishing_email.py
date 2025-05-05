from datetime import datetime
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
    created_at = DateTimeField(default=lambda: datetime.now())
    attachments = ManyToManyField(Attachment, backref="phishing_emails")
    celery_task_id = CharField(unique=True)
    sent_at = DateTimeField(null=True)
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
        if Target.select().count() == 0:
            raise ValueError("No targets found")
        if Group.select().count() == 0:
            raise ValueError("No groups found")

        answers = questionary.prompt(
            [
                {
                    "type": "select",
                    "name": "single_or_group",
                    "message": "Send a phishing email to a specific target or a group?",
                    "choices": ["specific", "group"],
                },
                {
                    "type": "checkbox",
                    "name": "target_ids",
                    "message": "Select target(s)",
                    "choices": Target.choices(),
                    "validate": lambda targets: (
                        True
                        if len(targets) > 0
                        else "Please select at least one target"
                    ),
                    "when": lambda answers: answers["single_or_group"] == "specific",
                },
                {
                    "type": "checkbox",
                    "name": "target_groups",
                    "message": "Select target group(s)",
                    "choices": Group.choices(),
                    "validate": lambda groups: (
                        True if len(groups) > 0 else "Please select at least one group"
                    ),
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

        if answers["single_or_group"] == "specific":
            targets = Target.select().where(Target.id << answers["target_ids"])
        else:
            assert answers["target_groups"] and len(answers["target_groups"]) > 0
            targets = Target.select_in_groups(answers["target_groups"])

        template = PhishingEmailTemplate.get(id=int(answers["template"]))
        attachments = Attachment.select().where(Attachment.id << answers["attachments"])

        for target in targets:
            phishing_email = cls.create(
                target=target,
                template=template,
                attachments=attachments,
                celery_task_id=uuid.uuid4().hex,
                status="pending",
            )

            task = send_phishing_email.delay(phishing_email.id)
            phishing_email.celery_task_id = task.id
            phishing_email.save()

            questionary.print(f"Created {phishing_email}")

        return phishing_email
