from playhouse.postgres_ext import *
import re
import json
import hashlib
import questionary
import psycopg2

conn = psycopg2.connect(
    host="db", user="postgres", password="postgres", database="postgres"
)
conn.autocommit = True
cursor = conn.cursor()
cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'c2_server'")
exists = cursor.fetchone()
if not exists:
    cursor.execute("CREATE DATABASE c2_server")
conn.close()

db = PostgresqlExtDatabase(
    "c2_server", user="postgres", password="postgres", host="db", port=5432
)


class BaseModel(Model):
    class Meta:
        database = db


class Target(BaseModel):
    id = AutoField(primary_key=True)
    fingerprint = CharField(unique=True)
    email = CharField(unique=True)
    data = JSONField(default={})
    active = BooleanField(default=False)

    def __str__(self):
        return f"Target[{self.id}] (email={self.email})"

    @classmethod
    def import_from_csv(cls):
        file_path = questionary.path("Enter file path").ask()
        users = []

        def process_row(row):
            email = row[0].strip().lower()
            try:
                validate_email(email)
            except questionary.ValidationError:
                questionary.print(f"Invalid email: {email}")
                return

            data = row[1].strip() or "{}"
            try:
                validate_data(data)
            except questionary.ValidationError:
                questionary.print(f"Invalid data: {data}")
                return

            users.append(
                cls(
                    email=email,
                    data=data,
                    fingerprint=hashlib.sha256(email.encode()).hexdigest(),
                )
            )

        with open(file_path, "r") as f:
            for row in csv.reader(f):
                process_row(row)

        cls.bulk_create(users)
        questionary.print(f"Imported {len(users)} targets")

    @classmethod
    def prompt_and_create(cls):
        group_choices = TargetGroup.choices()
        questionary.prompt(
            {
                {
                    "type": "text",
                    "name": "email",
                    "message": "Enter target email",
                    "validate": validate_email,
                },
                {
                    "type": "text",
                    "name": "data",
                    "message": "Enter target data (JSON, optional)",
                    "default": "{}",
                    "validate": validate_data,
                },
                {
                    "type": "checkbox",
                    "name": "groups",
                    "message": "Select target group(s)",
                    "choices": group_choices,
                    "default": [],
                    "when": lambda answers: group_choices,
                },
            }
        )

        target = cls.create(
            email=answers["email"].strip().lower(),
            data=answers["data"],
            fingerprint=hashlib.sha256(answers["email"].encode()).hexdigest(),
        )

        for group_id in answers["groups"]:
            group = TargetGroup.get(id=int(group_id))
            group.targets.add(target)

        questionary.print(f"Created {target}")
        return target


class TargetGroup(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(unique=True)
    targets = ManyToManyField(Target, backref="groups")

    def __str__(self):
        return f"TargetGroup[{self.id}] (name={self.name})"

    @classmethod
    def choices(cls):
        return [
            questionary.Choice(target_group.name, target_group.id)
            for target_group in cls.select()
        ]

    @classmethod
    def prompt_and_create(cls):
        def validate_name(name):
            name = name.strip()
            if len(name) < 3:
                raise questionary.ValidationError(
                    "Target group name must be at least 3 characters long"
                )
            elif len(name) > 100:
                raise questionary.ValidationError(
                    "Target group name cannot be longer than 100 characters"
                )
            elif TargetGroup.select().where(TargetGroup.name == name).exists():
                raise questionary.ValidationError("Target group name already exists")

        name = questionary.text("Enter target group name", validate=validate_name).ask()
        group = cls.create(name=name.strip())
        questionary.print(f"Created {group}")
        return group


class Implant(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField()
    path = CharField()


class Template(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField()
    path = CharField()


class Execution(BaseModel):

    id = AutoField(primary_key=True)
    target = ForeignKeyField(Target)
    status = CharField()

    @classmethod
    def prompt(cls):
        return {
            {
                "type": "select",
                "name": "single_or_group",
                "message": "Execute against a single target or a group?",
                "choices": ["single", "group"],
            },
            {
                "type": "text",
                "name": "target_id",
                "message": "Enter target ID",
                "validate": validate_target_id,
                "when": lambda answers: answers["single_or_group"] == "single",
            },
            {
                "type": "checkbox",
                "name": "target_groups",
                "message": "Select target group(s)",
                "choices": TargetGroup.choices(),
                "when": lambda answers: answers["single_or_group"] == "group",
            },
            {
                "type": "select",
                "name": "command_or_script",
                "message": "Execute a command or script?",
                "choices": ["command", "script"],
            },
            {
                "type": "text",
                "name": "command",
                "message": "Enter command",
                "when": lambda answers: answers["command_or_script"] == "command",
            },
            {
                "type": "path",
                "name": "script",
                "message": "Enter script path",
                "when": lambda answers: answers["command_or_script"] == "script",
            },
        }

    @classmethod
    def prompt_and_run(cls):
        answers = questionary.prompt(cls.prompt())

        if answers["single_or_group"] == "single":
            targets = [Target.get(id=int(answers["target_id"]))]
        else:
            group_ids = [g.value for g in answers["target_groups"]]
            targets = (
                Target.select()
                .distinct()
                .join(TargetGroup)
                .where(TargetGroup.id << group_ids)
            )

        

    @classmethod
    def prompt_and_schedule(cls):
        pass


def validate_target_id(target_id):
    try:
        target_id = int(target_id)
    except ValueError:
        raise questionary.ValidationError("Target ID must be an integer")
    try:
        Target.get(id=target_id)
    except Target.DoesNotExist:
        raise questionary.ValidationError("Target does not exist")


def validate_email(email):
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        raise questionary.ValidationError("Invalid email address")
    elif Target.select().where(Target.email == email).exists():
        raise questionary.ValidationError("Target with this email already exists")


def validate_data(data):
    try:
        json.loads(data)
    except json.JSONDecodeError:
        raise questionary.ValidationError("Invalid JSON")


def validate_duration(duration):
    duration_pattern = r"^(\d+d)?(\d+h)?(\d+m)?(\d+s)?$"
    match = re.match(duration_pattern, duration)

    if not match:
        raise questionary.ValidationError(
            "Invalid duration format. Expected e.g. 1d2h3m5s"
        )
