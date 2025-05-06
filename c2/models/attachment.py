import os
import uuid
from datetime import datetime

import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel


class Attachment(BaseModel):
    id = CharField(primary_key=True, max_length=8)
    name = CharField()
    path = CharField(unique=True)
    created_at = DateTimeField(default=lambda: datetime.now())

    def __str__(self):
        return f"Attachment[{self.id}] (name='{self.name}')"

    @classmethod
    def clear(cls):
        for attachment in cls.select():
            if os.path.exists(attachment.path):
                os.remove(attachment.path)
        cls.delete().execute()

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
