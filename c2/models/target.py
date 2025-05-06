import csv
import hashlib
import json
import re
from datetime import datetime

import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from . import db
from .base import BaseModel
from .group import Group


def get_fingerprint(email):
    return hashlib.sha256(email.encode()).hexdigest()


def validate_target_id(target_id):
    try:
        target_id = int(target_id)
    except ValueError:
        return "Target ID must be an integer"
    try:
        Target.get(id=target_id)
    except Target.DoesNotExist:
        return "Target does not exist"

    return True


def validate_target_email(email):
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        return "Invalid email address"
    elif Target.select().where(Target.email == email).exists():
        return "Target with this email already exists"
    else:
        return True


def validate_target_data(data):
    try:
        json.loads(data)
    except json.JSONDecodeError:
        return "Invalid JSON"
    else:
        return True


class Target(BaseModel):
    id = AutoField(primary_key=True)
    fingerprint = CharField(unique=True)
    email = CharField(unique=True)
    created_at = DateTimeField(default=lambda: datetime.now())
    data = JSONField(default={})
    active = BooleanField(default=False)

    def __str__(self):
        return f"Target[{self.id}] (email={self.email})"

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("target")
        parser.add_argument("subcommand", choices=["create", "import", "list", "clear"])

    @classmethod
    def clear(cls):
        cls.delete().execute()

    @classmethod
    def list(cls):
        query = (
            cls.select(
                cls.id,
                cls.email,
                cls.created_at,
                cls.data,
                cls.active,
                fn.STRING_AGG(Group.name, ",").alias("groups"),
            )
            .join(TargetGroup, JOIN.LEFT_OUTER)
            .join(Group, JOIN.LEFT_OUTER)
            .group_by(cls.id)
            .dicts()
        )
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def choices(cls):
        return [questionary.Choice(target.email, target.id) for target in cls.select()]

    @classmethod
    def select_in_groups(cls, group_ids):
        return (
            cls.select()
            .join(TargetGroup, on=(TargetGroup.target_id == cls.id))
            .where(TargetGroup.group_id << group_ids)
        )


class TargetGroup(BaseModel):
    group = ForeignKeyField(Group, on_delete="CASCADE", related_name="targets")
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="groups")

    class Meta:
        unique_together = ("group", "target")
