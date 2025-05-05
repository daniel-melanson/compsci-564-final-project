from models.base import BaseModel
import os
from models.target import Target, validate_target_id
from models.group import Group
from playhouse.postgres_ext import *
import questionary
import re
from datetime import datetime
from tabulate import tabulate


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
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="executions")
    status = CharField()
    command = TextField()
    run_at = DateTimeField()
    result = TextField(null=True)

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
        return [
            {
                "type": "select",
                "name": "single_or_group",
                "message": "Execute against a specific target or a group?",
                "choices": ["specific", "group"],
            },
            {
                "type": "checkbox",
                "name": "target_ids",
                "message": "Select target(s)",
                "choices": Target.choices(),
                "validate": lambda targets: (
                    True if len(targets) > 0 else "Please select at least one target"
                ),
                "when": lambda answers: answers["single_or_group"] == "specific",
            },
            {
                "type": "checkbox",
                "name": "target_groups",
                "message": "Select target group(s)",
                "choices": Group.choices(),
                "validate": lambda groups: (
                    True if len(groups) > 0 else "Please select at least one group"
                ),
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
                "validate": lambda script: (
                    True
                    if os.path.exists(script)
                    and os.path.isfile(script)
                    and os.access(script, os.R_OK)
                    else "Script does not exist or is not readable"
                ),
                "when": lambda answers: answers["command_or_script"] == "script",
            },
        ]

    @classmethod
    def prompt_and_run(cls):
        answers = questionary.prompt(cls.prompt())

        if answers["single_or_group"] == "specific":
            targets = Target.select().where(Target.id << answers["target_ids"])
        else:
            assert answers["target_groups"] and len(answers["target_groups"]) > 0
            targets = Target.select_in_groups(answers["target_groups"])

        if answers["command_or_script"] == "script":
            with open(answers["script"], "r") as f:
                command = f.read()
        else:
            command = answers["command"]

        for target in targets:
            execution = cls.create(
                target=target,
                status="pending",
                command=command,
                run_at=datetime.now(),
            )
            questionary.print(f"Created {execution}")

    @classmethod
    def prompt_and_schedule(cls):
        questions = cls.prompt() + [
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
        ]

        answers = questionary.prompt(questions)
