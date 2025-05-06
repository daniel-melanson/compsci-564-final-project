import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel


def validate_email_account_name(name: str):
    name = name.strip()
    if name == "":
        return "Name cannot be empty"
    elif len(name) < 3:
        return "Name must be at least 3 characters long"
    elif len(name) > 32:
        return "Name must be at most 32 characters long"
    elif EmailAccount.select().where(EmailAccount.name == name).exists():
        return "Name already exists"
    return True


class EmailAccount(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(unique=True)
    password = CharField()
    username = CharField()
    smtp_server = CharField()
    smtp_port = IntegerField()

    def __str__(self):
        return f"EmailAccount[{self.id}] (name={self.name})"

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("email-account")
        parser.add_argument("subcommand", choices=["create", "list", "clear"])

    @classmethod
    def clear(cls):
        cls.delete().execute()

    @classmethod
    def choices(cls):
        return [
            questionary.Choice(account.name, account.id) for account in cls.select()
        ]

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))
