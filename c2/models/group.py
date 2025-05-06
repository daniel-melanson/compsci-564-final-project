import re
from datetime import datetime

import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel


class Group(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(unique=True)
    created_at = DateTimeField(default=lambda: datetime.now())

    def __str__(self):
        return f"Group[{self.id}] (name={self.name})"

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("group")
        parser.add_argument("subcommand", choices=["create", "list", "clear"])

    @classmethod
    def clear(cls):
        cls.delete().execute()

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def choices(cls):
        return [
            questionary.Choice(target_group.name, target_group.id)
            for target_group in cls.select()
        ]
