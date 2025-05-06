import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel


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
