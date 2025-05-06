import os
import re
import shutil
import uuid
from datetime import datetime

import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel


def validate_template_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Template name must be at least 3 characters long"
    elif len(name) > 100:
        return "Template name cannot be longer than 100 characters"
    elif not re.match(r"^[\w ]+$", name):
        return "Template name can only contain letters, numbers, and spaces"
    elif (
        PhishingEmailTemplate.select()
        .where(PhishingEmailTemplate.name == name)
        .exists()
    ):
        return "Template name already exists"
    else:
        return True


def validate_template_subject(subject):
    subject = subject.strip()
    if len(subject) < 3:
        return "Template subject must be at least 3 characters long"
    elif len(subject) > 100:
        return "Template subject cannot be longer than 100 characters"
    else:
        return True


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
