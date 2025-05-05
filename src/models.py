from playhouse.postgres_ext import *
import uuid
import shutil
from datetime import datetime
import re
import json
import hashlib
import questionary
import psycopg2
from tabulate import tabulate


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
    def select_in_groups(cls, group_ids):
        return (
            cls.select()
            .distinct()
            .join(TargetGroup)
            .where(TargetGroup.group_id << group_ids)
        )

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
        group_choices = Group.choices()
        answers = questionary.prompt(
            [
                {
                    "type": "text",
                    "name": "email",
                    "message": "Enter target email",
                    "validate": validate_email,
                },
                {
                    "type": "text",
                    "name": "data",
                    "message": "Enter target data (JSON)",
                    "default": "{}",
                    "validate": validate_data,
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

        target = cls.create(
            email=answers["email"].strip().lower(),
            data=answers["data"],
            fingerprint=hashlib.sha256(answers["email"].encode()).hexdigest(),
        )

        for group_id in answers.get("groups", []):
            group = Group.get(id=int(group_id))
            TargetGroup.create(target=target, group=group)

        questionary.print(f"Created {target}")
        return target


class Group(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(unique=True)

    def __str__(self):
        return f"Group[{self.id}] (name={self.name})"

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
        group = cls.create(name=name.strip())
        questionary.print(f"Created {group}")
        return group


class TargetGroup(BaseModel):
    group = ForeignKeyField(Group, on_delete="CASCADE", related_name="targets")
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="groups")

    class Meta:
        unique_together = ("group", "target")


class PhishingEmailTemplate(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(unique=True)
    subject = CharField()
    path = CharField(unique=True)

    def __str__(self):
        return f"PhishingEmailTemplate[{self.id}] (name={self.name})"

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def choices(cls):
        return [
            questionary.Choice(template.name, template.id) for template in cls.select()
        ]

    @classmethod
    def prompt_and_create(cls):
        id = uuid.uuid4().hex[:8]
        name = questionary.text(
            "Enter template name",
            validate=validate_template_name,
        ).ask()
        subject = questionary.text(
            "Enter template subject (as seen by the target; supports Jinja)",
            validate=validate_template_subject,
        ).ask()

        template = cls.create(
            id=id,
            name=name.strip(),
            subject=subject,
            path=f"templates/{id}_{name.strip()}",
        )
        shutil.copyfile("templates/default.html", template.path)
        questionary.print(f"Created {template}")
        questionary.print(f"Write template contents to: {template.path}")
        return template


class Attachment(BaseModel):
    id = CharField(primary_key=True, max_length=8)
    name = CharField()
    path = CharField(unique=True)

    def __str__(self):
        return f"Attachment[{self.id}] (name='{self.name}')"

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

    @classmethod
    def prompt_and_create(cls):
        id = uuid.uuid4().hex[:8]
        name = questionary.text(
            "Enter the attachment name as seen by the target",
            validate=validate_attachment_name,
        ).ask()
        attachment = cls.create(
            id=id, name=name.strip(), path=f"attachments/{id}_{name.strip()}"
        )
        with open(attachment.path, "w") as f:
            f.write("")

        questionary.print(f"Created {attachment}")
        questionary.print(f"Write attachment contents to: {attachment.path}")
        return attachment


class PhishingEmail(BaseModel):
    id = AutoField(primary_key=True)
    subject = CharField()
    target = ForeignKeyField(
        Target, on_delete="CASCADE", related_name="phishing_emails"
    )
    template = ForeignKeyField(
        PhishingEmailTemplate, on_delete="CASCADE", related_name="phishing_emails"
    )
    attachments = ManyToManyField(Attachment, backref="phishing_emails")
    celery_task_id = CharField(unique=True)
    status = CharField()

    def __str__(self):
        return f"PhishingEmail[{self.id}] (subject='{self.subject}')"

    @classmethod
    def prompt_and_create(cls):
        result = questionary.prompt(
            {
                {
                    "type": "select",
                    "name": "single_or_group",
                    "message": "Send a phishing email to a single target or a group?",
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
                    "choices": Group.choices(),
                    "when": lambda answers: answers["single_or_group"] == "group",
                },
                {
                    "type": "select",
                    "name": "template",
                    "message": "Select template",
                    "choices": PhishingEmailTemplate.choices(),
                },
                {
                    "type": "checkbox",
                    "name": "attachments",
                    "message": "Select attachment",
                    "choices": Attachment.choices(),
                },
            }
        ).ask()

        if result["single_or_group"] == "single":
            targets = [Target.get(id=int(result["target_id"]))]
        else:
            targets = Target.select_in_groups(result["target_groups"])

        template = PhishingEmailTemplate.get(id=int(result["template"]))
        attachments = Attachment.select_in(result["attachments"])

        for target in targets:
            phishing_email = cls.create(
                target=target,
                template=template,
                attachments=attachments,
                celery_task_id=uuid.uuid4().hex,
                status="pending",
            )

            task = send_phishing_email.delay(phishing_email)
            phishing_email.celery_task_id = task.id
            phishing_email.save()

            questionary.print(f"Created {phishing_email}")

        return phishing_email


class Execution(BaseModel):
    id = AutoField(primary_key=True)
    celery_task_id = CharField(unique=True)
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="executions")
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
                "choices": Group.choices(),
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
            targets = Target.select_in_groups(group_ids)

        for target in targets:
            if answers["command_or_script"] == "command":
                task = execute_command.delay(target, answers["command"])
            else:
                task = execute_script.delay(target, answers["script"])

            cls.create(target=target, status="pending", celery_task_id=task.id)

    @classmethod
    def prompt_and_schedule(cls):
        questions = cls.prompt() | {
            {
                "type": "confirmation",
                "name": "repeat",
                "default": False,
                "message": "Is this a repeated execution?",
            },
            {
                "type": "text",
                "name": "cron_schedule",
                "message": "Enter cron schedule",
                "when": lambda answers: answers["repeat"],
            },
            {
                "type": "text",
                "name": "date",
                "message": "Enter date and time (ISO 8601)",
                "validate": validate_date,
                "when": lambda answers: not answers["repeat"],
            },
            {
                "type": "confirmation",
                "name": "random_offset",
                "message": "Add random offset to execution time?",
            },
            {
                "type": "text",
                "name": "random_offset_duration",
                "message": "Enter random offset duration (e.g. 1d2h3m5s)",
                "validate": validate_duration,
                "default": None,
                "when": lambda answers: answers["random_offset"],
            },
        }

        answers = questionary.prompt(questions)


def validate_date(date):
    try:
        date = datetime.fromisoformat(date)
    except ValueError:
        return "Invalid date format"

    if date < datetime.now():
        return "Date must be in the future"

    return True


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


def validate_email(email):
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        return "Invalid email address"
    elif Target.select().where(Target.email == email).exists():
        return "Target with this email already exists"
    else:
        return True


def validate_data(data):
    try:
        json.loads(data)
    except json.JSONDecodeError:
        return "Invalid JSON"
    else:
        return True


def validate_duration(duration):
    duration_pattern = r"^(\d+d)?(\d+h)?(\d+m)?(\d+s)?$"
    match = re.match(duration_pattern, duration)

    if not match:
        return "Invalid duration format. Expected e.g. 1d2h3m5s"
    else:
        return True


def validate_attachment_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Attachment name must be at least 3 characters long"
    elif len(name) > 100:
        return "Attachment name cannot be longer than 100 characters"
    elif Attachment.select().where(Attachment.name == name).exists():
        return "Attachment name already exists"
    else:
        return True


def validate_template_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Template name must be at least 3 characters long"
    elif len(name) > 100:
        return "Template name cannot be longer than 100 characters"
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


def validate_group_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Target group name must be at least 3 characters long"
    elif len(name) > 100:
        return "Target group name cannot be longer than 100 characters"
    elif Group.select().where(Group.name == name).exists():
        return "Target group name already exists"
    else:
        return True
