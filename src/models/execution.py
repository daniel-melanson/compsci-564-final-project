from models.base import BaseModel
from models.target import Target, validate_target_id
from models.group import Group
from playhouse.postgres_ext import AutoField, CharField, ForeignKeyField
import questionary
import re
from datetime import datetime
import tabulate


def validate_date(date):
    try:
        date = datetime.fromisoformat(date)
    except ValueError:
        return "Invalid date format"

    if date < datetime.now():
        return "Date must be in the future"

    return True


def validate_duration(duration):
    duration_pattern = r"^(\d+d)?(\d+h)?(\d+m)?(\d+s)?$"
    match = re.match(duration_pattern, duration)

    if not match:
        return "Invalid duration format. Expected e.g. 1d2h3m5s"
    else:
        return True


class Execution(BaseModel):
    id = AutoField(primary_key=True)
    celery_task_id = CharField(unique=True)
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="executions")
    status = CharField()

    def __str__(self):
        return f"Execution[{self.id}] (target={self.target}, status={self.status})"

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("execution", help="Manage executions")
        parser.add_argument("subcommand", choices=["run", "schedule", "list", "clear"])

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
