from models.base import BaseModel
import uuid
import questionary
from playhouse.postgres_ext import CharField
from tabulate import tabulate


def validate_attachment_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Attachment name must be at least 3 characters long"
    elif len(name) > 100:
        return "Attachment name cannot be longer than 100 characters"
    elif Attachment.select().where(Attachment.name == name).exists():
        return "Attachment name already exists"
    else:
        return True


class Attachment(BaseModel):
    id = CharField(primary_key=True, max_length=8)
    name = CharField()
    path = CharField(unique=True)

    def __str__(self):
        return f"Attachment[{self.id}] (name='{self.name}')"

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("attachment", help="Manage attachments")
        parser.add_argument("subcommand", choices=["create", "list", "clear"])

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def choices(cls):
        return [
            questionary.Choice(attachment.name, attachment.id)
            for attachment in cls.select()
        ]

    @classmethod
    def prompt_and_create(cls):
        id = uuid.uuid4().hex[:8]
        name = questionary.text(
            "Enter the attachment name as seen by the target",
            validate=validate_attachment_name,
        ).ask()
        attachment = cls.create(
            id=id, name=name.strip(), path=f"attachments/{id}_{name.strip()}"
        )
        with open(attachment.path, "w") as f:
            f.write("")

        questionary.print(f"Created {attachment}")
        questionary.print(f"Write attachment contents to: {attachment.path}")
        return attachment
