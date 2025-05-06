import os
import re
import shutil
import uuid
from datetime import datetime

import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel


class PhishingEmailTemplate(BaseModel):
    id = CharField(primary_key=True, max_length=8)
    name = CharField(unique=True)
    subject = CharField()
    created_at = DateTimeField(default=lambda: datetime.now())
    path = CharField(unique=True)

    def __str__(self):
        return f"PhishingEmailTemplate[{self.id}] (name={self.name})"

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("template")
        parser.add_argument("subcommand", choices=["create", "list", "clear"])

    @classmethod
    def clear(cls):
        for template in cls.select():
            if os.path.exists(template.path):
                os.remove(template.path)

        cls.delete().execute()

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def choices(cls):
        return [
            questionary.Choice(template.name, template.id) for template in cls.select()
        ]
