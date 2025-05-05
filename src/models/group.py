from models.base import BaseModel
from playhouse.postgres_ext import *
import questionary
from tabulate import tabulate
from datetime import datetime
import re


def validate_group_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Target group name must be at least 3 characters long"
    elif len(name) > 100:
        return "Target group name cannot be longer than 100 characters"
    elif not re.match(r"^[\w ]+$", name):
        return "Target group name can only contain letters, numbers, and spaces"
    elif Group.select().where(Group.name == name).exists():
        return "Target group name already exists"
    else:
        return True


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

    @classmethod
    def prompt_and_create(cls):
        name = questionary.text(
            "Enter target group name", validate=validate_group_name
        ).ask()
        assert name.strip()

        group = cls.create(name=name.strip())
        questionary.print(f"Created {group}")
        return group
