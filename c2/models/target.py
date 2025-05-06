from datetime import datetime
from cryptography.fernet import Fernet

import questionary
from playhouse.postgres_ext import *
from tabulate import tabulate

from . import db
from .base import BaseModel
from .group import Group


def get_fingerprint(email):
    return Fernet.generate_key().decode()


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
