from models import db
from models.base import BaseModel
from models.group import Group
from playhouse.postgres_ext import *
import questionary
from tabulate import tabulate
import csv
import json
import re
import hashlib


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

    @classmethod
    def import_from_csv(cls):
        file_path = questionary.path("Enter file path").ask()

        def process_row(row):
            email, data, groups_raw = row
            if validate_target_email(email) != True:
                raise Exception(f"Invalid email: {email}")

            if validate_target_data(data) != True:
                raise Exception(f"Invalid data: {data}")

            target = cls.create(
                email=email,
                data=json.loads(data),
                fingerprint=get_fingerprint(email),
            )

            groups = groups_raw.split(",")
            for group_name in groups:
                group, _ = Group.get_or_create(name=group_name.strip())
                TargetGroup.create(target=target, group=group)

        count = 0
        with db.transaction():
            with open(file_path, "r") as f:
                next(f)  # Skip header
                for row in csv.reader(f):
                    process_row(row)
                    count += 1

        questionary.print(f"Imported {count} targets")

    @classmethod
    def prompt_and_create(cls):
        group_choices = Group.choices()
        answers = questionary.prompt(
            [
                {
                    "type": "text",
                    "name": "email",
                    "message": "Enter target email",
                    "validate": validate_target_email,
                },
                {
                    "type": "text",
                    "name": "data",
                    "message": "Enter target data (JSON)",
                    "default": "{}",
                    "validate": validate_target_data,
                },
                {
                    "type": "checkbox",
                    "name": "groups",
                    "message": "Select target group(s)",
                    "choices": group_choices,
                    "when": lambda answers: len(group_choices) > 0,
                },
            ]
        )
        assert answers["email"].strip()
        assert answers["data"].strip()

        target = cls.create(
            email=answers["email"].strip().lower(),
            data=answers["data"],
            fingerprint=get_fingerprint(answers["email"]),
        )

        for group_id in answers.get("groups", []):
            group = Group.get(id=int(group_id))
            TargetGroup.create(target=target, group=group)

        questionary.print(f"Created {target}")
        return target


class TargetGroup(BaseModel):
    group = ForeignKeyField(Group, on_delete="CASCADE", related_name="targets")
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="groups")

    class Meta:
        unique_together = ("group", "target")
